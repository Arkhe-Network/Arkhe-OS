package v1beta1

import (
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
)

// ThetaRhythmSpec defines the desired state of ThetaRhythm
// The biological clock that synchronizes information injection into Bexorg
type ThetaRhythmSpec struct {
	Frequency               float64     `json:"frequency"`
	Phase                   float64     `json:"phase"`
	Amplitude               float64     `json:"amplitude"`
	EncodingWindow          float64     `json:"encodingWindow"`
	RetrievalWindow         float64     `json:"retrievalWindow"`
	Target                  ThetaTarget `json:"target"`
	AcetylcholineModulation bool        `json:"acetylcholineModulation"`
}

type ThetaTarget struct {
	BexorgRef    string `json:"bexorgRef,omitempty"`
	CortexRegion string `json:"cortexRegion"`
}

// ThetaRhythmStatus defines the observed state of ThetaRhythm
type ThetaRhythmStatus struct {
	CurrentPhase        string  `json:"currentPhase"`
	Coherence           float64 `json:"coherence"`
	MemoryConsolidation float64 `json:"memoryConsolidation"`
}

// +kubebuilder:object:root=true
// +kubebuilder:subresource:status
// +kubebuilder:resource:shortName=tr
type ThetaRhythm struct {
	metav1.TypeMeta   `json:",inline"`
	metav1.ObjectMeta `json:"metadata,omitempty"`
	Spec              ThetaRhythmSpec   `json:"spec,omitempty"`
	Status            ThetaRhythmStatus `json:"status,omitempty"`
}

// +kubebuilder:object:root=true
type ThetaRhythmList struct {
	metav1.TypeMeta `json:",inline"`
	metav1.ListMeta `json:"metadata,omitempty"`
	Items           []ThetaRhythm `json:"items"`
}

func init() {
	SchemeBuilder.Register(&ThetaRhythm{}, &ThetaRhythmList{})
}

func (in *ThetaRhythm) DeepCopyObject() runtime.Object {
	return &ThetaRhythm{}
}

func (in *ThetaRhythmList) DeepCopyObject() runtime.Object {
	return &ThetaRhythmList{}
}
