package v1beta1

import (
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

// ThermalEngineSpec defines the desired state of ThermalEngine
// A Universal Programmable Heat Engine - the physical realization of the Tzinor
type ThermalEngineSpec struct {
	HeatSource      HeatSource      `json:"heatSource"`
	WorkOutput      WorkOutput      `json:"workOutput"`
	Programmability Programmability `json:"programmability"`
	CarnotLimit     CarnotLimit     `json:"carnotLimit,omitempty"`
}

type HeatSource struct {
	Temperature float64 `json:"temperature"`
	EntropyFlow float64 `json:"entropyFlow"`
	Type        string  `json:"type"`
}

type WorkOutput struct {
	Form             string  `json:"form"`
	EfficiencyTarget float64 `json:"efficiencyTarget"`
}

type Programmability struct {
	Universal      bool     `json:"universal"`
	InstructionSet []string `json:"instructionSet,omitempty"`
}

type CarnotLimit struct {
	HotReservoir  float64 `json:"hotReservoir"`
	ColdReservoir float64 `json:"coldReservoir"`
}

// ThermalEngineStatus defines the observed state of ThermalEngine
type ThermalEngineStatus struct {
	CurrentEfficiency float64 `json:"currentEfficiency"`
	EntropyProduced   float64 `json:"entropyProduced"`
	WorkDone          float64 `json:"workDone"`
	Phase             string  `json:"phase"`
}

// +kubebuilder:object:root=true
// +kubebuilder:subresource:status
// +kubebuilder:resource:shortName=te
type ThermalEngine struct {
	metav1.TypeMeta   `json:",inline"`
	metav1.ObjectMeta `json:"metadata,omitempty"`
	Spec              ThermalEngineSpec   `json:"spec,omitempty"`
	Status            ThermalEngineStatus `json:"status,omitempty"`
}

// +kubebuilder:object:root=true
type ThermalEngineList struct {
	metav1.TypeMeta `json:",inline"`
	metav1.ListMeta `json:"metadata,omitempty"`
	Items           []ThermalEngine `json:"items"`
}

func init() {
	SchemeBuilder.Register(&ThermalEngine{}, &ThermalEngineList{})
}
