.PHONY: all
all: docker-build docker-push helm-deploy

# Build Docker image
docker-build:
	docker build -t ghcr.io/arkhe-os/cert-operator:$(VERSION) .

# Push Docker image
docker-push:
	docker push ghcr.io/arkhe-os/cert-operator:$(VERSION)

# Deploy via Helm
helm-deploy:
	helm install arkhe-cert-operator ./charts/arkhe-cert-operator \
		--namespace arkhe-system --create-namespace

# Generate deepcopy methods
generate:
	controller-gen object:headerFile="hack/boilerplate.go.txt" paths="./..."

# Run tests
test:
	go test ./... -v

VERSION ?= v0.1.0
