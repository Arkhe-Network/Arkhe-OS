module github.com/arkhe-os/arkhe-cert-operator

go 1.21

require (
	github.com/go-logr/logr v1.4.1
	github.com/onsi/ginkgo/v2 v2.19.0
	github.com/onsi/gomega v1.30.0
	github.com/prometheus/client_golang v1.19.1
	github.com/software.sslmate.com/src/go-pkcs12 v0.4.0
	github.com/stretchr/testify v1.9.0
	k8s.io/api v0.30.1
	k8s.io/apimachinery v0.30.1
	k8s.io/client-go v0.30.1
	sigs.k8s.io/controller-runtime v0.18.4
	github.com/cert-manager/cert-manager v1.15.0
)
