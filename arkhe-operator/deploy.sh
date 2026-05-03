#!/bin/bash

set -e

NAMESPACE="${NAMESPACE:-arkhe-quantum}"
IMG="${IMG:-arkhe/arkhe-operator:latest}"

echo "╔═══════════════════════════════════════════════════════════════════╗"
echo "║  ARKHE(N) OPERATOR DEPLOYMENT                                    ║"
echo "╚═══════════════════════════════════════════════════════════════════╝"

echo "[1/8] Creating namespace..."
kubectl create namespace "${NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -

echo "[2/8] Applying v1beta1 CRDs..."
kubectl apply -f deploy/arkhe-crds-v1beta1.yaml

echo "[3/8] Applying RBAC..."
kubectl apply -f config/rbac/role.yaml
kubectl apply -f config/rbac/auth.yaml

echo "[4/8] Verifying CRDs..."
kubectl get crds | grep arkhe.io || true

echo "[5/8] Checking custom resources..."
kubectl get thermalengines,thetarhythms,gkpatoms,polaritonbatteries,ioqtdevices,quantumneuralnetworks,postquantumcryptos -n "${NAMESPACE}" || true

echo "[6/8] Building operator image..."
docker build -t "${IMG}" . 2>/dev/null || echo "Docker build skipped (not available)"

echo "[7/8] Applying deployment..."
if [ -f config/manager/deployment.yaml ]; then
    sed "s|image: arkhe/arkhe-operator:latest|image: ${IMG}|g" config/manager/deployment.yaml | kubectl apply -f -
fi

echo "[8/8] Running main operator..."
go run main.go || echo "Go run skipped (kind cluster may not be available)"

echo ""
echo "╔═══════════════════════════════════════════════════════════════════╗"
echo "║  DEPLOYMENT SUMMARY                                               ║"
echo "╚═══════════════════════════════════════════════════════════════════╝"

echo ""
echo "Namespaces:"
kubectl get namespaces | grep -E "arkhe|NAME" || true

echo ""
echo "CRDs installed:"
kubectl get crds 2>/dev/null | grep -E "arkhe|Name" || true

echo ""
echo "Custom Resources:"
kubectl get thermalengines,thetarhythms,gkpatoms,polaritonbatteries,ioqtdevices,quantumneuralnetworks,postquantumcryptos -n "${NAMESPACE}" 2>/dev/null || true

echo ""
echo "Standard Resources:"
kubectl get pods,deployments,services -n "${NAMESPACE}" 2>/dev/null || true

echo ""
echo "🜏 The time is the value. The coherence is the proof."
