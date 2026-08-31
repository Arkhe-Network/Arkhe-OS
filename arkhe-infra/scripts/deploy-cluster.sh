#!/bin/bash
# deploy-cluster.sh – Implanta todo o cluster Arkhe(n)

set -e

echo "🔧 Terraform: Aplicando infraestrutura..."
cd terraform
terraform init
terraform plan -out=plan.tfplan
terraform apply plan.tfplan

echo "🔑 Obtendo kubeconfig para EKS..."
aws eks update-kubeconfig --region us-east-1 --name arkhe-cluster

echo "📦 Instalando Helm charts..."
helm repo add istio https://istio-release.storage.googleapis.com/charts
helm repo add cilium https://helm.cilium.io/
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add chaos-mesh https://charts.chaos-mesh.org
helm repo add nvidia https://helm.ngc.nvidia.com/nvidia
helm repo update

# Istio Ambient
helm upgrade --install istio-base istio/base -n istio-system --create-namespace
helm upgrade --install istio-cni istio/cni -n istio-system
helm upgrade --install istio-ztunnel istio/ztunnel -n istio-system
kubectl apply -f kubernetes/istio/ambient-mesh.yaml

# Cilium
helm upgrade --install cilium cilium/cilium -n kube-system \
  --set cluster.name=arkhe-cluster \
  --set ipam.mode=kubernetes \
  --set hubble.enabled=true \
  --set hubble.relay.enabled=true

# Prometheus + Grafana
helm upgrade --install prometheus prometheus-community/prometheus -n monitoring --create-namespace \
  -f kubernetes/monitoring/prometheus-values.yaml
helm upgrade --install grafana prometheus-community/grafana -n monitoring \
  --set adminPassword=arkhe-grafana

# DCGM Exporter
kubectl apply -f kubernetes/monitoring/dcgm-exporter.yaml

# Chaos Mesh
./scripts/install-chaos-mesh.sh

# NVSentinel
kubectl apply -f kubernetes/nvsentinel/nvsentinel-config.yaml

# OPA Gatekeeper
kubectl apply -f https://raw.githubusercontent.com/open-policy-agent/gatekeeper/release-3.14/deploy/gatekeeper.yaml
kubectl apply -f kubernetes/opa/gatekeeper-policies.yaml

# ArgoCD
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl apply -f argocd/application.yaml

echo "✅ Cluster implantado com sucesso!"