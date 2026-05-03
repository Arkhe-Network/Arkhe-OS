package v1alpha1

import (
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
)

type BreachAction string

const (
	BreachActionLog       BreachAction = "Log"
	BreachActionIsolate   BreachAction = "Isolate"
	BreachActionTerminate BreachAction = "Terminate"
)

type EntropyShieldSpec struct {
	MaxEntropynW            float64      `json:"maxEntropynW"`
	CriticalTempMilliKelvin float64      `json:"criticalTempMilliKelvin"`
	BreachAction            BreachAction `json:"breachAction"`
}

type EntropyShieldStatus struct {
	CurrentEntropynW   float64            `json:"currentEntropynW"`
	AttacksNeutralized int                `json:"attacksNeutralized"`
	Active             bool               `json:"active"`
	Conditions         []metav1.Condition `json:"conditions,omitempty"`
}

type EntropyShield struct {
	metav1.TypeMeta   `json:",inline"`
	metav1.ObjectMeta `json:"metadata,omitempty"`
	Spec              EntropyShieldSpec   `json:"spec,omitempty"`
	Status            EntropyShieldStatus `json:"status,omitempty"`
}

type EntropyShieldList struct {
	metav1.TypeMeta `json:",inline"`
	metav1.ListMeta `json:"metadata,omitempty"`
	Items           []EntropyShield `json:"items"`
}

func init() {
	SchemeBuilder.Register(&EntropyShield{}, &EntropyShieldList{})
}

func (in *EntropyShield) DeepCopyObject() runtime.Object {
	return &EntropyShield{}
}

func (in *EntropyShieldList) DeepCopyObject() runtime.Object {
	return &EntropyShieldList{}
}
