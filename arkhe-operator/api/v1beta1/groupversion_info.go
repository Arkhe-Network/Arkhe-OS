// Package v1beta1 contains API Schema definitions for the arkhe.io API group
package v1beta1

import (
	"k8s.io/apimachinery/pkg/runtime/schema"
	"sigs.k8s.io/controller-runtime/pkg/scheme"
)

const (
	GroupName = "arkhe.io"
	Version   = "v1beta1"
)

var (
	GroupVersion = schema.GroupVersion{Group: GroupName, Version: Version}

	SchemeBuilder = &scheme.Builder{GroupVersion: GroupVersion}

	AddToScheme = SchemeBuilder.AddToScheme
)

func Resource(resource string) schema.GroupResource {
	return SchemeBuilder.GroupVersion.WithResource(resource).GroupResource()
}
