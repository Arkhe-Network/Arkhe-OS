package v1beta1

import (
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

// ProofVerifierPhase represents the current phase of proof verification
type ProofVerifierPhase string

const (
	ProofVerifierPhasePending   ProofVerifierPhase = "Pending"
	ProofVerifierPhaseComputing ProofVerifierPhase = "Computing"
	ProofVerifierPhaseProving   ProofVerifierPhase = "Proving"
	ProofVerifierPhaseVerifying ProofVerifierPhase = "Verifying"
	ProofVerifierPhaseVerified  ProofVerifierPhase = "Verified"
	ProofVerifierPhaseFailed    ProofVerifierPhase = "Failed"
)

// ProofSystem represents the ZK proof system to use
type ProofSystem string

const (
	ProofSystemGroth16 ProofSystem = "Groth16"
	ProofSystemPlonk   ProofSystem = "Plonk"
	ProofSystemSTARK   ProofSystem = "STARK"
	ProofSystemHalo2   ProofSystem = "Halo2"
)

// ProofLanguage represents supported programming languages
type ProofLanguage string

const (
	LanguageSolidity ProofLanguage = "Solidity"
	LanguageRust     ProofLanguage = "Rust"
	LanguagePython   ProofLanguage = "Python"
	LanguageC        ProofLanguage = "C"
	LanguageCpp      ProofLanguage = "Cpp"
	LanguageK        ProofLanguage = "K"
	LanguageMove     ProofLanguage = "Move"
	LanguageCairo    ProofLanguage = "Cairo"
	LanguageNeural   ProofLanguage = "Neural"
)

// InputType represents the type of program input
type InputType string

const (
	InputTypeJson         InputType = "Json"
	InputTypeBinary       InputType = "Binary"
	InputTypeNeuralIntent InputType = "NeuralIntent"
	InputTypeNone         InputType = "None"
)

// OutputType represents the type of expected output
type OutputType string

const (
	OutputTypeJson           OutputType = "Json"
	OutputTypeBinary         OutputType = "Binary"
	OutputTypeMerkleRoot     OutputType = "MerkleRoot"
	OutputTypeCoherenceScore OutputType = "CoherenceScore"
)

// SourceRef defines the source code reference
type SourceRef struct {
	ConfigMapRef *ConfigMapRef `json:"configMapRef,omitempty"`
	GitRef       *GitRef       `json:"gitRef,omitempty"`
}

// ConfigMapRef references a ConfigMap
type ConfigMapRef struct {
	Name string `json:"name"`
	Key  string `json:"key"`
}

// GitRef references code in a git repository
type GitRef struct {
	Repository string `json:"repository"`
	Commit     string `json:"commit"`
	Path       string `json:"path"`
}

// ProgramInput defines input to the program
type ProgramInput struct {
	Type InputType `json:"type"`
	Data string    `json:"data,omitempty"`
}

// ExpectedOutput defines the expected program output
type ExpectedOutput struct {
	Type      OutputType `json:"type"`
	Data      string     `json:"data"`
	Tolerance float64    `json:"tolerance,omitempty"`
}

// VerifierConfig defines configuration for the proof verifier
type VerifierConfig struct {
	ProofSystem         ProofSystem `json:"proofSystem,omitempty"`
	SecurityLevel       int         `json:"securityLevel,omitempty"`
	VerificationTimeout string      `json:"verificationTimeout,omitempty"`
}

// ChainIntegration defines integration with blockchain
type ChainIntegration struct {
	SubmitToChain bool   `json:"submitToChain,omitempty"`
	WalletRef     string `json:"walletRef,omitempty"`
	EraRef        string `json:"eraRef,omitempty"`
	GasLimit      int    `json:"gasLimit,omitempty"`
}

// NeuralIntegration defines integration with Bexorg neural network
type NeuralIntegration struct {
	BexorgRef          string  `json:"bexorgRef,omitempty"`
	CoherenceThreshold float64 `json:"coherenceThreshold,omitempty"`
	ThetaPhase         float64 `json:"thetaPhase,omitempty"`
}

// ProofVerifierSpec defines the desired state of ProofVerifier
type ProofVerifierSpec struct {
	Language          ProofLanguage      `json:"language"`
	SourceRef         *SourceRef         `json:"sourceRef,omitempty"`
	ProgramHash       string             `json:"programHash"`
	Input             *ProgramInput      `json:"input,omitempty"`
	ExpectedOutput    ExpectedOutput     `json:"expectedOutput"`
	VerifierConfig    *VerifierConfig    `json:"verifierConfig,omitempty"`
	ChainIntegration  *ChainIntegration  `json:"chainIntegration,omitempty"`
	NeuralIntegration *NeuralIntegration `json:"neuralIntegration,omitempty"`
}

// ProofStatus contains proof generation information
type ProofStatus struct {
	ProofHash string `json:"proofHash,omitempty"`
	ProofType string `json:"proofType,omitempty"`
	ProofData string `json:"proofData,omitempty"`
	ProofSize int    `json:"proofSize,omitempty"`
}

// ZKCertificateStatus contains ZK certificate information
type ZKCertificateStatus struct {
	CertificateHash string `json:"certificateHash,omitempty"`
	CertificateData string `json:"certificateData,omitempty"`
	CircuitId       string `json:"circuitId,omitempty"`
	VerificationKey string `json:"verificationKey,omitempty"`
}

// VerificationMetrics contains timing and resource metrics
type VerificationMetrics struct {
	ComputeTime         string `json:"computeTime,omitempty"`
	ProofGenerationTime string `json:"proofGenerationTime,omitempty"`
	VerificationTime    string `json:"verificationTime,omitempty"`
	GasUsed             int    `json:"gasUsed,omitempty"`
}

// OnChainRef contains on-chain reference information
type OnChainRef struct {
	TxHash      string `json:"txHash,omitempty"`
	BlockHeight int    `json:"blockHeight,omitempty"`
	EraRef      string `json:"eraRef,omitempty"`
}

// Condition represents a condition in the status
type Condition struct {
	Type               string                 `json:"type"`
	Status             metav1.ConditionStatus `json:"status"`
	Reason             string                 `json:"reason,omitempty"`
	Message            string                 `json:"message,omitempty"`
	LastTransitionTime *metav1.Time           `json:"lastTransitionTime,omitempty"`
}

// ProofVerifierStatus defines the observed state of ProofVerifier
type ProofVerifierStatus struct {
	Phase          ProofVerifierPhase   `json:"phase,omitempty"`
	Proof          *ProofStatus         `json:"proof,omitempty"`
	ZKCertificate  *ZKCertificateStatus `json:"zkCertificate,omitempty"`
	Metrics        *VerificationMetrics `json:"metrics,omitempty"`
	OnChainRef     *OnChainRef          `json:"onChainRef,omitempty"`
	Conditions     []Condition          `json:"conditions,omitempty"`
	StartTime      string               `json:"startTime,omitempty"`
	CompletionTime string               `json:"completionTime,omitempty"`
}

//+kubebuilder:object:root=true
//+kubebuilder:subresource:status
//+kubebuilder:resource:shortName=pv
//+kubebuilder:printcolumn:name="Language",type="string",JSONPath=".spec.language"
//+kubebuilder:printcolumn:name="Phase",type="string",JSONPath=".status.phase"
//+kubebuilder:printcolumn:name="Proof Hash",type="string",JSONPath=".status.proof.proofHash",priority=1
//+kubebuilder:printcolumn:name="Age",type="date",JSONPath=".metadata.creationTimestamp"

// ProofVerifier is the Schema for the proofverifiers API
type ProofVerifier struct {
	metav1.TypeMeta   `json:",inline"`
	metav1.ObjectMeta `json:"metadata,omitempty"`

	Spec   ProofVerifierSpec   `json:"spec,omitempty"`
	Status ProofVerifierStatus `json:"status,omitempty"`
}

//+kubebuilder:object:root=true

// ProofVerifierList contains a list of ProofVerifier
type ProofVerifierList struct {
	metav1.TypeMeta `json:",inline"`
	metav1.ListMeta `json:"metadata,omitempty"`
	Items           []ProofVerifier `json:"items"`
}

func init() {
	SchemeBuilder.Register(&ProofVerifier{}, &ProofVerifierList{})
}
