# terraform/main.tf
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.0"
    }
  }
  backend "s3" {
    bucket = "arkhe-terraform-state"
    key    = "arkhe/terraform.tfstate"
    region = "us-east-1"
  }
}

# --- Variables ---
variable "aws_region" {
  description = "AWS region for primary cluster"
  default     = "us-east-1"
}
variable "gcp_region" {
  description = "GCP region for backup cluster"
  default     = "us-central1"
}
variable "gpu_instance_types" {
  description = "GPU instance types for node groups"
  default     = ["g4dn.xlarge", "g5.xlarge"]
}
variable "cpu_instance_types" {
  description = "CPU instance types for general workloads"
  default     = ["m5.large", "m6i.large"]
}

# --- AWS VPC ---
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "arkhe-vpc"
  cidr = "10.0.0.0/16"

  azs             = ["us-east-1a", "us-east-1b", "us-east-1c"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]

  enable_nat_gateway = true
  single_nat_gateway = true
}

# --- AWS EKS Cluster ---
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.0"

  cluster_name    = "arkhe-cluster"
  cluster_version = "1.30"

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  # Karpenter para auto-scaling
  enable_karpenter = true
  karpenter_version = "0.37.0"

  # Node Groups
  eks_managed_node_groups = {
    gpu-workers = {
      instance_types = var.gpu_instance_types
      min_size       = 1
      max_size       = 10
      desired_size   = 2
      capacity_type  = "ON_DEMAND"
      taints = {
        dedicated = {
          key    = "nvidia.com/gpu"
          value  = "true"
          effect = "NO_SCHEDULE"
        }
      }
      labels = {
        role = "gpu-worker"
      }
      tags = {
        "karpenter.sh/discovery" = "arkhe-cluster"
      }
    }
    cpu-workers = {
      instance_types = var.cpu_instance_types
      min_size       = 2
      max_size       = 20
      desired_size   = 3
      capacity_type  = "SPOT"
      labels = {
        role = "cpu-worker"
      }
      tags = {
        "karpenter.sh/discovery" = "arkhe-cluster"
      }
    }
  }
}

# --- Karpenter Provisioner (GPU) ---
resource "kubectl_manifest" "gpu_provisioner" {
  depends_on = [module.eks]
  yaml_body = yamlencode({
    apiVersion = "karpenter.sh/v1beta1"
    kind       = "NodePool"
    metadata = {
      name = "gpu-pool"
    }
    spec = {
      template = {
        spec = {
          nodeClassRef = {
            name = "default"
          }
          requirements = [
            { key = "kubernetes.io/arch", operator = "In", values = ["amd64"] },
            { key = "karpenter.sh/capacity-type", operator = "In", values = ["on-demand", "spot"] },
            { key = "nvidia.com/gpu", operator = "Exists" }
          ]
          taints = [
            {
              key    = "nvidia.com/gpu"
              value  = "true"
              effect = "NO_SCHEDULE"
            }
          ]
        }
      }
      limits = {
        cpu    = "100"
        memory = "400Gi"
        "nvidia.com/gpu" = "10"
      }
      disruption = {
        consolidationPolicy = "WhenUnderutilized"
        expireAfter         = "720h"
      }
    }
  })
}

# --- GCP GKE Cluster (backup) ---
resource "google_container_cluster" "arkhe_gke" {
  name     = "arkhe-gke"
  location = var.gcp_region
  project  = "arkhe-project-123"

  remove_default_node_pool = true
  initial_node_count       = 1

  network    = google_compute_network.arkhe_vpc.name
  subnetwork = google_compute_subnetwork.arkhe_subnet.name

  ip_allocation_policy {
    cluster_secondary_range_name  = "pods"
    services_secondary_range_name = "services"
  }
}

resource "google_container_node_pool" "gpu_pool_gcp" {
  name       = "gpu-pool"
  cluster    = google_container_cluster.arkhe_gke.name
  location   = var.gcp_region
  node_count = 1

  node_config {
    machine_type = "n1-standard-8"
    guest_accelerator {
      type  = "nvidia-tesla-t4"
      count = 1
    }
    taint {
      key    = "nvidia.com/gpu"
      value  = "true"
      effect = "NO_SCHEDULE"
    }
    labels = {
      role = "gpu-worker"
    }
  }
}

# --- AWS RDS PostgreSQL with Cross-Region Replica ---
resource "aws_db_instance" "arkhe_postgres_primary" {
  allocated_storage    = 100
  storage_type         = "gp3"
  engine               = "postgres"
  engine_version       = "15.4"
  instance_class       = "db.r6g.large"
  db_name              = "arkhe"
  username             = "arkhe_admin"
  password             = random_password.db_password.result
  db_subnet_group_name = aws_db_subnet_group.arkhe_db.name
  vpc_security_group_ids = [aws_security_group.arkhe_db.id]
  backup_retention_period = 30
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"
  storage_encrypted      = true
  performance_insights_enabled = true
  enabled_cloudwatch_logs_exports = ["postgresql"]
  deletion_protection = true
}

resource "aws_db_instance" "arkhe_postgres_replica" {
  replicate_source_db = aws_db_instance.arkhe_postgres_primary.id
  availability_zone   = "us-east-2a"
  instance_class      = "db.r6g.large"
  vpc_security_group_ids = [aws_security_group.arkhe_db.id]
}

# --- AWS S3 Cross-Region Replication ---
resource "aws_s3_bucket" "arkhe_artifacts" {
  bucket = "arkhe-artifacts-prod"
  force_destroy = false
}

resource "aws_s3_bucket_versioning" "arkhe_artifacts" {
  bucket = aws_s3_bucket.arkhe_artifacts.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_replication_configuration" "arkhe_artifacts_repl" {
  bucket = aws_s3_bucket.arkhe_artifacts.id
  role   = aws_iam_role.s3_replication.arn
  rule {
    id     = "cross-region-replica"
    status = "Enabled"
    destination {
      bucket        = "arn:aws:s3:::arkhe-artifacts-backup"
      storage_class = "STANDARD_IA"
    }
    filter {}
  }
}

# --- AWS Secrets Manager with Auto-Rotation ---
resource "aws_secretsmanager_secret" "arkhe_secrets" {
  name = "arkhe-secrets"
  rotation_rules {
    automatically_after_days = 30
  }
}

resource "aws_secretsmanager_secret_rotation" "arkhe_rotation" {
  secret_id           = aws_secretsmanager_secret.arkhe_secrets.id
  rotation_lambda_arn = aws_lambda_function.secret_rotator.arn
}

# --- Lambda for Secret Rotation ---
resource "aws_lambda_function" "secret_rotator" {
  filename      = "lambda/rotator.zip"
  function_name = "arkhe-secret-rotator"
  role          = aws_iam_role.lambda_exec.arn
  handler       = "index.handler"
  runtime       = "python3.12"
  timeout       = 60
}

# --- FinOps: Cost Tags and Budgets ---
resource "aws_budgets_budget" "arkhe_monthly" {
  name         = "arkhe-monthly-cost"
  budget_type  = "COST"
  limit_amount = "5000"
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  cost_types {
    include_credit = false
    include_discount = true
    include_other_subscription = true
    include_recurring = true
    include_refund = false
    include_subscription = true
    include_support = true
    include_tax = true
    include_upfront = true
    use_amortized = false
  }
  notification {
    comparison_operator   = "GREATER_THAN"
    threshold             = 85
    threshold_type        = "PERCENTAGE"
    notification_type     = "ACTUAL"
    subscriber_email_addresses = ["finops@arkhe.solar"]
  }
}

# --- Outputs ---
output "eks_cluster_endpoint" {
  value = module.eks.cluster_endpoint
}
output "gke_cluster_endpoint" {
  value = google_container_cluster.arkhe_gke.endpoint
}
output "rds_endpoint" {
  value = aws_db_instance.arkhe_postgres_primary.address
}