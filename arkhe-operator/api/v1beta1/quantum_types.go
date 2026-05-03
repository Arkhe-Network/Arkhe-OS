package v1beta1

import (
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
)

// PolaritonBatterySpec defines the desired state of PolaritonBattery
type PolaritonBatterySpec struct {
	Microcavity Microcavity    `json:"microcavity"`
	Charging    ChargingConfig `json:"charging"`
	Storage     StorageConfig  `json:"storage"`
}

type Microcavity struct {
	Material string `json:"material"`
	Layers   int    `json:"layers"`
	Coupling string `json:"coupling"`
}

type ChargingConfig struct {
	Method          string  `json:"method"`
	PulseDuration   float64 `json:"pulseDuration"`
	Superabsorption bool    `json:"superabsorption"`
}

type StorageConfig struct {
	TargetLifetime float64 `json:"targetLifetime"`
}

// PolaritonBatteryStatus defines the observed state of PolaritonBattery
type PolaritonBatteryStatus struct {
	ChargeLevel       float64 `json:"chargeLevel"`
	StorageEfficiency float64 `json:"storageEfficiency"`
	DecoherenceRate   float64 `json:"decoherenceRate"`
}

// +kubebuilder:object:root=true
// +kubebuilder:subresource:status
// +kubebuilder:resource:shortName=pb
type PolaritonBattery struct {
	metav1.TypeMeta   `json:",inline"`
	metav1.ObjectMeta `json:"metadata,omitempty"`
	Spec              PolaritonBatterySpec   `json:"spec,omitempty"`
	Status            PolaritonBatteryStatus `json:"status,omitempty"`
}

// +kubebuilder:object:root=true
type PolaritonBatteryList struct {
	metav1.TypeMeta `json:",inline"`
	metav1.ListMeta `json:"metadata,omitempty"`
	Items           []PolaritonBattery `json:"items"`
}

// IoQTDeviceSpec defines the desired state of IoQTDevice
type IoQTDeviceSpec struct {
	QCAConfiguration QCAConfig   `json:"qcaConfiguration"`
	SensorType       string      `json:"sensorType"`
	ImplantLocation  *Location   `json:"implantLocation,omitempty"`
	PowerSource      PowerSource `json:"powerSource"`
}

type QCAConfig struct {
	CellCount   int    `json:"cellCount"`
	ClockZones  int    `json:"clockZones"`
	Fabrication string `json:"fabrication"`
}

type Location struct {
	Organ       string       `json:"organ"`
	Coordinates *Coordinates `json:"coordinates,omitempty"`
}

type Coordinates struct {
	X float64 `json:"x"`
	Y float64 `json:"y"`
	Z float64 `json:"z"`
}

type PowerSource struct {
	Type       string `json:"type"`
	BatteryRef string `json:"batteryRef,omitempty"`
}

// IoQTDeviceStatus defines the observed state of IoQTDevice
type IoQTDeviceStatus struct {
	Operational   bool    `json:"operational"`
	TunnelingRate float64 `json:"tunnelingRate"`
	ErrorRate     float64 `json:"errorRate"`
}

// +kubebuilder:object:root=true
// +kubebuilder:subresource:status
// +kubebuilder:resource:shortName=ioqt
type IoQTDevice struct {
	metav1.TypeMeta   `json:",inline"`
	metav1.ObjectMeta `json:"metadata,omitempty"`
	Spec              IoQTDeviceSpec   `json:"spec,omitempty"`
	Status            IoQTDeviceStatus `json:"status,omitempty"`
}

// +kubebuilder:object:root=true
type IoQTDeviceList struct {
	metav1.TypeMeta `json:",inline"`
	metav1.ListMeta `json:"metadata,omitempty"`
	Items           []IoQTDevice `json:"items"`
}

// QuantumNeuralNetworkSpec defines the desired state of QuantumNeuralNetwork
type QuantumNeuralNetworkSpec struct {
	Architecture    string         `json:"architecture"`
	Application     string         `json:"application"`
	Training        TrainingConfig `json:"training"`
	HardwareBackend []string       `json:"hardwareBackend,omitempty"`
}

type TrainingConfig struct {
	Federated bool   `json:"federated"`
	Privacy   string `json:"privacy"`
}

// QuantumNeuralNetworkStatus defines the observed state of QuantumNeuralNetwork
type QuantumNeuralNetworkStatus struct {
	Accuracy             float64 `json:"accuracy"`
	QuantumAdvantage     bool    `json:"quantumAdvantage"`
	EntanglementFidelity float64 `json:"entanglementFidelity"`
}

// +kubebuilder:object:root=true
// +kubebuilder:subresource:status
// +kubebuilder:resource:shortName=qnn
type QuantumNeuralNetwork struct {
	metav1.TypeMeta   `json:",inline"`
	metav1.ObjectMeta `json:"metadata,omitempty"`
	Spec              QuantumNeuralNetworkSpec   `json:"spec,omitempty"`
	Status            QuantumNeuralNetworkStatus `json:"status,omitempty"`
}

// +kubebuilder:object:root=true
type QuantumNeuralNetworkList struct {
	metav1.TypeMeta `json:",inline"`
	metav1.ListMeta `json:"metadata,omitempty"`
	Items           []QuantumNeuralNetwork `json:"items"`
}

// PostQuantumCryptoSpec defines the desired state of PostQuantumCrypto
type PostQuantumCryptoSpec struct {
	Algorithm       string          `json:"algorithm"`
	KeyDistribution KeyDistribution `json:"keyDistribution"`
	Lattice         LatticeConfig   `json:"lattice,omitempty"`
}

type KeyDistribution struct {
	Method      string  `json:"method"`
	FiberLength float64 `json:"fiberLength"`
	SecureRate  float64 `json:"secureRate"`
}

type LatticeConfig struct {
	Dimension int    `json:"dimension"`
	Structure string `json:"structure"`
}

// PostQuantumCryptoStatus defines the observed state of PostQuantumCrypto
type PostQuantumCryptoStatus struct {
	SecurityLevel     string  `json:"securityLevel"`
	QuantumResistance bool    `json:"quantumResistance"`
	KeyRate           float64 `json:"keyRate"`
}

// +kubebuilder:object:root=true
// +kubebuilder:subresource:status
// +kubebuilder:resource:shortName=pqc
type PostQuantumCrypto struct {
	metav1.TypeMeta   `json:",inline"`
	metav1.ObjectMeta `json:"metadata,omitempty"`
	Spec              PostQuantumCryptoSpec   `json:"spec,omitempty"`
	Status            PostQuantumCryptoStatus `json:"status,omitempty"`
}

// +kubebuilder:object:root=true
type PostQuantumCryptoList struct {
	metav1.TypeMeta `json:",inline"`
	metav1.ListMeta `json:"metadata,omitempty"`
	Items           []PostQuantumCrypto `json:"items"`
}

func init() {
	SchemeBuilder.Register(&PolaritonBattery{}, &PolaritonBatteryList{})
	SchemeBuilder.Register(&IoQTDevice{}, &IoQTDeviceList{})
	SchemeBuilder.Register(&QuantumNeuralNetwork{}, &QuantumNeuralNetworkList{})
	SchemeBuilder.Register(&PostQuantumCrypto{}, &PostQuantumCryptoList{})
}

func (in *PolaritonBattery) DeepCopyObject() runtime.Object {
	return &PolaritonBattery{}
}

func (in *PolaritonBatteryList) DeepCopyObject() runtime.Object {
	return &PolaritonBatteryList{}
}

func (in *IoQTDevice) DeepCopyObject() runtime.Object {
	return &IoQTDevice{}
}

func (in *IoQTDeviceList) DeepCopyObject() runtime.Object {
	return &IoQTDeviceList{}
}

func (in *QuantumNeuralNetwork) DeepCopyObject() runtime.Object {
	return &QuantumNeuralNetwork{}
}

func (in *QuantumNeuralNetworkList) DeepCopyObject() runtime.Object {
	return &QuantumNeuralNetworkList{}
}

func (in *PostQuantumCrypto) DeepCopyObject() runtime.Object {
	return &PostQuantumCrypto{}
}

func (in *PostQuantumCryptoList) DeepCopyObject() runtime.Object {
	return &PostQuantumCryptoList{}
}
