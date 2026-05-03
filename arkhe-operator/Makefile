.PHONY: all build test clean install uninstall deploy undeploy manifests generate fmt vet

IMG ?= arkhe/arkhe-operator:latest
VERSION ?= latest
ENVTEST_ASSETS_DIR = $(shell pwd)/testbin

all: build

build: manifests generate fmt vet
	go build -o bin/manager main.go

test: manifests generate fmt vet
	go test ./... -v

clean:
	rm -rf bin/

install: manifests kustomize
	$(KUSTOMIZE) build config/default | kubectl apply -f -

uninstall: manifests kustomize
	$(KUSTOMIZE) build config/default | kubectl delete -f -

deploy: manifests kustomize
	cd config/manager && $(KUSTOMIZE) edit set image controller=$(IMG)
	$(KUSTOMIZE) build config/default | kubectl apply -f -

undeploy:
	$(KUSTOMIZE) build config/default | kubectl delete -f -

CONTROLLER_GEN = $(shell pwd)/bin/controller-gen
controller-gen:
	$(call go-get-tool,$(CONTROLLER_GEN),sigs.k8s.io/controller-tools/cmd/controller-gen@v0.13.0)

KUSTOMIZE = $(shell pwd)/bin/kustomize
kustomize:
	$(call go-get-tool,$(KUSTOMIZE),sigs.k8s.io/kustomize/kustomize/v5@v5.2.1)

 manifests: controller-gen
	$(CONTROLLER_GEN) crd paths="./..." output:crd:artifacts:config=config/crd/bases

generate: controller-gen
	$(CONTROLLER_GEN) object:headerFile="hack/boilerplate.go.txt" paths="./..."

define go-get-tool
@mkdir -p $(shell dirname $(2))
@GOBIN=$(shell pwd)/bin go install $(1)@latest
endef

fmt:
	go fmt ./...

vet:
	go vet ./...
