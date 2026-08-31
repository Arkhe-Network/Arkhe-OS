#!/bin/bash
# install-chaos-mesh.sh

helm upgrade --install chaos-mesh chaos-mesh/chaos-mesh \
  --namespace chaos-mesh --create-namespace \
  --set chaosDaemon.runtime=containerd \
  --set chaosDaemon.socketPath=/var/run/containerd/containerd.sock \
  --set controllerManager.enableGPU=true \
  --version v2.7.0

kubectl wait --for=condition=available --timeout=300s deployment/chaos-controller-manager -n chaos-mesh
echo "✅ Chaos Mesh instalado."