package v1alpha1

import (
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	runtime "k8s.io/apimachinery/pkg/runtime"
)

//+kubebuilder:object:generate=true
//+groupName=cert.arkhe.os

type ArkheCertificateSpec struct {
	// ServiceName is the name of the ARKHE microservice
	//+kubebuilder:validation:Required
	ServiceName string `json:"serviceName"`

	// CommonName for the certificate (must match service DNS)
	//+kubebuilder:validation:Required
	CommonName string `json:"commonName"`

	// DNSNames for additional Subject Alternative Names
	//+kubebuilder:validation:Optional
	DNSNames []string `json:"dnsNames,omitempty"`

	// ValidityDays is the certificate validity period in days (30-365)
	//+kubebuilder:validation:Minimum=30
	//+kubebuilder:validation:Maximum=365
	//+kubebuilder:default=90
	ValidityDays int `json:"validityDays,omitempty"`

	// RotationThresholdDays triggers rotation when cert expires within this many days
	//+kubebuilder:validation:Minimum=1
	//+kubebuilder:validation:Maximum=30
	//+kubebuilder:default=14
	RotationThresholdDays int `json:"rotationThresholdDays,omitempty"`

	// KeystoreType determines the keystore format (PKCS12 or JKS)
	//+kubebuilder:validation:Enum=PKCS12;JKS
	//+kubebuilder:default=PKCS12
	KeystoreType string `json:"keystoreType,omitempty"`

	// KeystorePasswordSecret references a Secret containing the keystore password
	//+kubebuilder:validation:Optional
	KeystorePasswordSecret *SecretReference `json:"keystorePasswordSecret,omitempty"`

	// TruststoreCARef references CA certificate for truststore generation
	//+kubebuilder:validation:Optional
	TruststoreCARef *SecretReference `json:"truststoreCARef,omitempty"`

	// TriggerRollingUpdate triggers a rolling update on certificate rotation
	//+kubebuilder:default=true
	TriggerRollingUpdate bool `json:"triggerRollingUpdate,omitempty"`

	// IssuerRef references the cert-manager Issuer/ClusterIssuer
	//+kubebuilder:validation:Required
	IssuerRef IssuerReference `json:"issuerRef"`
}

type SecretReference struct {
	Name   string `json:"name"`
	Key    string `json:"key,omitempty"`
}

type IssuerReference struct {
	Name string `json:"name"`
	Kind string `json:"kind,omitempty"`
	Group string `json:"group,omitempty"`
}

type ArkheCertificateStatus struct {
	Conditions []metav1.Condition `json:"conditions,omitempty"`

	CurrentCertificate *CertificateInfo `json:"currentCertificate,omitempty"`

	LastRotationTime *metav1.Time `json:"lastRotationTime,omitempty"`

	KeystoreSecretName string `json:"keystoreSecretName,omitempty"`
}

type CertificateInfo struct {
	SerialNumber    string      `json:"serialNumber,omitempty"`
	NotBefore       metav1.Time `json:"notBefore,omitempty"`
	NotAfter        metav1.Time `json:"notAfter,omitempty"`
	DaysUntilExpiry int         `json:"daysUntilExpiry,omitempty"`
}

//+kubebuilder:object:generate=true
//+kubebuilder:subresource:status
//+kubebuilder:printcolumn:name="Service",type="string",JSONPath=".spec.serviceName"
//+kubebuilder:printcolumn:name="CommonName",type="string",JSONPath=".spec.commonName"
//+kubebuilder:printcolumn:name="DaysUntilExpiry",type="integer",JSONPath=".status.currentCertificate.daysUntilExpiry"
//+kubebuilder:printcolumn:name="Status",type="string",JSONPath=".status.conditions[?(@.type==\"Ready\")].status"
//+kubebuilder:printcolumn:name="Age",type="date",JSONPath=".metadata.creationTimestamp"

type ArkheCertificate struct {
	metav1.TypeMeta   `json:",inline"`
	metav1.ObjectMeta `json:"metadata,omitempty"`

	Spec   ArkheCertificateSpec   `json:"spec,omitempty"`
	Status ArkheCertificateStatus `json:"status,omitempty"`
}

//+kubebuilder:object:generate=true

type ArkheCertificateList struct {
	metav1.TypeMeta `json:",inline"`
	metav1.ListMeta `json:"metadata,omitempty"`
	Items           []ArkheCertificate `json:"items"`
}

func init() {
	SchemeBuilder.Register(&ArkheCertificate{}, &ArkheCertificateList{})
}
