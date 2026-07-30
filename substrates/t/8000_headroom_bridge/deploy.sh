#!/bin/bash
# deploy.sh — Script de deploy do Substrato 8000
# CATHEDRAL ARKHE Substrato 8000
# Selo: CATHEDRAL-ARKHE-8000-DEPLOY-v1.0.0-2026-06-18
# Arquiteto: ORCID 0009-0005-2697-4668

set -euo pipefail

# Colors
RED='[0;31m'
GREEN='[0;32m'
YELLOW='[1;33m'
BLUE='[0;34m'
NC='[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.yml"
PROJECT_NAME="cathedral-headroom"
ENV=${ENV:-production}
VERSION="1.0.0"

# Functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    command -v docker >/dev/null 2>&1 || { log_error "Docker is required but not installed."; return 1; }
    command -v docker-compose >/dev/null 2>&1 || { log_error "Docker Compose is required but not installed."; return 1; }

    # Check Docker version
    DOCKER_VERSION=$(docker --version | awk '{print $3}' | sed 's/,//')
    log_info "Docker version: $DOCKER_VERSION"

    # Check available resources
    log_info "Checking system resources..."
    docker system info --format 'CPUs: {{.NCPU}}, Memory: {{.MemTotal}}' | head -1

    log_success "Prerequisites check passed"
}

# Create directories
setup_directories() {
    log_info "Setting up directories..."

    mkdir -p         ./config/grafana/dashboards         ./config/grafana/datasources         ./config/prometheus         ./secrets         ./data/prometheus         ./data/grafana         ./data/loki         ./data/redis         ./data/zvec         ./data/tensorzkp         ./logs

    # Generate secrets if not exist
    if [ ! -f ./secrets/grafana-admin-password.txt ]; then
        openssl rand -base64 32 > ./secrets/grafana-admin-password.txt
        log_info "Generated Grafana admin password"
    fi

    log_success "Directories setup complete"
}

# Generate configs
generate_configs() {
    log_info "Generating configurations..."

    # Prometheus config
    cat > ./config/prometheus/prometheus.yml << 'EOF_PROM'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "rules.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['cathedral-alertmanager:9093']

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'headroom-mcp'
    static_configs:
      - targets: ['cathedral-headroom-mcp:8788']
    metrics_path: '/metrics'

  - job_name: 'headroom-proxy'
    static_configs:
      - targets: ['cathedral-headroom-proxy:8790']
    metrics_path: '/metrics'

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['cathedral-node-exporter:9100']

  - job_name: 'cadvisor'
    static_configs:
      - targets: ['cathedral-cadvisor:8080']

  - job_name: 'zvec'
    static_configs:
      - targets: ['cathedral-zvec:50052']

  - job_name: 'tensorzkp'
    static_configs:
      - targets: ['cathedral-tensorzkp:50062']
EOF_PROM

    # Prometheus rules
    cat > ./config/prometheus/rules.yml << 'EOF_RULES'
groups:
  - name: headroom-alerts
    rules:
      - alert: HeadroomHighErrorRate
        expr: rate(headroom_proxy_errors_total[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate in Headroom proxy"

      - alert: HeadroomLowCompressionRatio
        expr: headroom_compress_ratio_avg < 0.5
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Compression ratio below threshold"

      - alert: HeadroomZkpFailures
        expr: rate(headroom_zkp_failures_total[5m]) > 0.01
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "ZKP verification failures detected"
EOF_RULES

    # Grafana datasource
    cat > ./config/grafana/datasources/prometheus.yml << 'EOF_DATASOURCE'
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://cathedral-prometheus:9090
    isDefault: true
    editable: false
EOF_DATASOURCE

    log_success "Configurations generated"
}

# Build images
build_images() {
    log_info "Building Docker images..."

    export DOCKER_BUILDKIT=1

    docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME build         --build-arg RUST_VERSION=1.75         --parallel

    log_success "Images built successfully"
}

# Deploy stack
deploy() {
    log_info "Deploying Cathedral Headroom Stack v${VERSION}..."

    docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME up -d         --remove-orphans         --wait         --wait-timeout 60

    log_success "Stack deployed successfully"
}

# Health check
health_check() {
    log_info "Running health checks..."

    sleep 5

    # Check MCP
    if curl -sf http://localhost:8787/health > /dev/null; then
        log_success "MCP Server is healthy"
    else
        log_error "MCP Server health check failed"
        docker-compose -f $COMPOSE_FILE logs cathedral-headroom-mcp --tail=50
    fi

    # Check Proxy
    if curl -sf http://localhost:8789/health > /dev/null; then
        log_success "Proxy Server is healthy"
    else
        log_warn "Proxy Server health check failed (may be waiting for upstream)"
    fi

    # Check Prometheus
    if curl -sf http://localhost:9090/-/healthy > /dev/null; then
        log_success "Prometheus is healthy"
    else
        log_warn "Prometheus health check failed"
    fi

    # Check Grafana
    if curl -sf http://localhost:3000/api/health > /dev/null; then
        log_success "Grafana is healthy"
    else
        log_warn "Grafana health check failed"
    fi
}

# Show status
show_status() {
    echo ""
    echo "=========================================="
    echo "  Cathedral Headroom Stack Status"
    echo "=========================================="
    echo ""
    docker-compose -f $COMPOSE_FILE ps
    echo ""
    echo "Services:"
    echo "  MCP Server:      http://localhost:8787"
    echo "  MCP Metrics:     http://localhost:8788/metrics"
    echo "  Proxy Server:    http://localhost:8789"
    echo "  Proxy Metrics:   http://localhost:8790/metrics"
    echo "  Prometheus:      http://localhost:9090"
    echo "  Grafana:         http://localhost:3000"
    echo "  Alertmanager:    http://localhost:9093"
    echo "  zVEC gRPC:       localhost:50051"
    echo "  TensorZKP gRPC:  localhost:50061"
    echo ""
    echo "Logs:"
    echo "  docker-compose -f $COMPOSE_FILE logs -f"
    echo ""
}

# Main
main() {
    case "${1:-deploy}" in
        check)
            check_prerequisites
            ;;
        setup)
            check_prerequisites
            setup_directories
            generate_configs
            ;;
        build)
            check_prerequisites
            setup_directories
            generate_configs
            build_images
            ;;
        deploy)
            check_prerequisites
            setup_directories
            generate_configs
            build_images
            deploy
            health_check
            show_status
            ;;
        stop)
            docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME down
            log_success "Stack stopped"
            ;;
        restart)
            docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME restart
            log_success "Stack restarted"
            ;;
        logs)
            docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME logs -f --tail=100
            ;;
        status)
            show_status
            ;;
        update)
            log_info "Updating stack..."
            docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME pull
            docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME up -d --build
            log_success "Stack updated"
            ;;
        clean)
            docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME down -v
            docker system prune -f
            log_success "Stack cleaned"
            ;;
        *)
            echo "Usage: $0 {check|setup|build|deploy|stop|restart|logs|status|update|clean}"
            return 1
            ;;
    esac
}

main "$@"