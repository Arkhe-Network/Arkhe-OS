package v1alpha1

import (
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
)

type BlockRange struct {
	Start int64 `json:"start"`
	End   int64 `json:"end"`
}

type ThermalState string

const (
	ThermalStateFrozen ThermalState = "Frozen"
	ThermalStateActive ThermalState = "Active"
)

type CoreResourceSpec struct {
	CPU    string `json:"cpu,omitempty"`
	Memory string `json:"memory,omitempty"`
}

type EraSpec struct {
	Index        int              `json:"index"`
	BlockRange   BlockRange       `json:"blockRange"`
	AlphaWeight  float64          `json:"alphaWeight"`
	ThermalState ThermalState     `json:"thermalState"`
	Resources    CoreResourceSpec `json:"resources,omitempty"`
}

type EraStatus struct {
	TemperatureMilliKelvin float64            `json:"temperatureMilliKelvin"`
	Active                 bool               `json:"active"`
	EntropyNanoWatts       float64            `json:"entropyNanoWatts"`
	BlocksProcessed        int64              `json:"blocksProcessed"`
	MerkleRoot             string             `json:"merkleRoot"`
	Conditions             []metav1.Condition `json:"conditions,omitempty"`
}

type Era struct {
	metav1.TypeMeta   `json:",inline"`
	metav1.ObjectMeta `json:"metadata,omitempty"`
	Spec              EraSpec   `json:"spec,omitempty"`
	Status            EraStatus `json:"status,omitempty"`
}

type EraList struct {
	metav1.TypeMeta `json:",inline"`
	metav1.ListMeta `json:"metadata,omitempty"`
	Items           []Era `json:"items"`
}

func init() {
	SchemeBuilder.Register(&Era{}, &EraList{})
}

func (in *Era) DeepCopyObject() runtime.Object {
	return &Era{}
}

func (in *EraList) DeepCopyObject() runtime.Object {
	return &EraList{}
}
