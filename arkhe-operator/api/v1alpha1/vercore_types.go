package v1alpha1

import (
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
)

type VerCoreSpec struct {
	ClockRateGHz          float64 `json:"clockRateGHz"`
	Replicas              int32   `json:"replicas"`
	TargetTempMilliKelvin float64 `json:"targetTempMilliKelvin"`
	Image                 string  `json:"image"`
}

type VerCoreStatus struct {
	ReadyReplicas      int32              `json:"readyReplicas"`
	AvgTempMilliKelvin float64            `json:"avgTempMilliKelvin"`
	CoreMark           int                `json:"coreMark"`
	Conditions         []metav1.Condition `json:"conditions,omitempty"`
}

type VerCore struct {
	metav1.TypeMeta   `json:",inline"`
	metav1.ObjectMeta `json:"metadata,omitempty"`
	Spec              VerCoreSpec   `json:"spec,omitempty"`
	Status            VerCoreStatus `json:"status,omitempty"`
}

type VerCoreList struct {
	metav1.TypeMeta `json:",inline"`
	metav1.ListMeta `json:"metadata,omitempty"`
	Items           []VerCore `json:"items"`
}

func init() {
	SchemeBuilder.Register(&VerCore{}, &VerCoreList{})
}

func (in *VerCore) DeepCopyObject() runtime.Object {
	return &VerCore{}
}

func (in *VerCoreList) DeepCopyObject() runtime.Object {
	return &VerCoreList{}
}
