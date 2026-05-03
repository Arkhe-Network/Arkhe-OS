package v1alpha1

import (
	"k8s.io/apimachinery/pkg/runtime/schema"
	"k8s.io/apimachinery/pkg/runtime/serializer"
	utilruntime "k8s.io/apimachinery/pkg/util/runtime"
	"k8s.io/client-go/kubernetes/scheme"
)

var (
	SchemeBuilder = runtime.NewSchemeBuilder(addKnownTypes)
	AddToScheme   = SchemeBuilder.AddToScheme
	Scheme        = scheme.Scheme
	Codecs       = serializer.NewCodecFactory(Scheme)
)

func addKnownTypes(scheme *runtime.Scheme) error {
	utilruntime.Must(AddToScheme(scheme))
	scheme.AddKnownTypes(
		schema.GroupVersion{Group: "cert.arkhe.os", Version: "v1alpha1"},
		&ArkheCertificate{},
		&ArkheCertificateList{},
	)
	return nil
}
