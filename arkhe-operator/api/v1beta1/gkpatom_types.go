package v1beta1

import (
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

// GKPAtomSpec defines the desired state of GKPAtom
// Quantum computation on a single atom using GKP encoding
type GKPAtomSpec struct {
	AtomicSpecies     string            `json:"atomicSpecies"`
	TrapConfiguration TrapConfig        `json:"trapConfiguration"`
	GKPEncoding       GKPEncoding       `json:"gkpEncoding"`
	VibrationalModes  []VibrationalMode `json:"vibrationalModes,omitempty"`
}

type TrapConfig struct {
	Type        string  `json:"type"`
	Dimensions  int     `json:"dimensions"`
	RFFrequency float64 `json:"rfFrequency"`
}

type GKPEncoding struct {
	LogicalQubits   int     `json:"logicalQubits"`
	ErrorCorrection bool    `json:"errorCorrection"`
	Squeezing       float64 `json:"squeezing"`
}

type VibrationalMode struct {
	ModeID     int     `json:"modeId"`
	Frequency  float64 `json:"frequency"`
	Occupation int     `json:"occupation"`
}

// GKPAtomStatus defines the observed state of GKPAtom
type GKPAtomStatus struct {
	CoherenceTime float64             `json:"coherenceTime"`
	GateFidelity  float64             `json:"gateFidelity"`
	Entanglement  *EntanglementStatus `json:"entanglement,omitempty"`
}

type EntanglementStatus struct {
	ModeA    int     `json:"modeA"`
	ModeB    int     `json:"modeB"`
	Fidelity float64 `json:"fidelity"`
}

// +kubebuilder:object:root=true
// +kubebuilder:subresource:status
// +kubebuilder:resource:shortName=gkp
type GKPAtom struct {
	metav1.TypeMeta   `json:",inline"`
	metav1.ObjectMeta `json:"metadata,omitempty"`
	Spec              GKPAtomSpec   `json:"spec,omitempty"`
	Status            GKPAtomStatus `json:"status,omitempty"`
}

// +kubebuilder:object:root=true
type GKPAtomList struct {
	metav1.TypeMeta `json:",inline"`
	metav1.ListMeta `json:"metadata,omitempty"`
	Items           []GKPAtom `json:"items"`
}

func init() {
	SchemeBuilder.Register(&GKPAtom{}, &GKPAtomList{})
}
