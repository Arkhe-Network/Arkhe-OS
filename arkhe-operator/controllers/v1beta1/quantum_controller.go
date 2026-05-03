package controllers

import (
	"context"

	arkhev1beta1 "github.com/arkhe-n/arkhe-operator/api/v1beta1"
	"k8s.io/apimachinery/pkg/runtime"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"
)

// PolaritonBatteryReconciler reconciles a PolaritonBattery object
type PolaritonBatteryReconciler struct {
	client.Client
	Scheme *runtime.Scheme
}

// +kubebuilder:rbac:groups=arkhe.io,resources=polaritonbatteries,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups=arkhe.io,resources=polaritonbatteries/status,verbs=get;update;patch

func (r *PolaritonBatteryReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
	battery := &arkhev1beta1.PolaritonBattery{}
	if err := r.Get(ctx, req.NamespacedName, battery); err != nil {
		return ctrl.Result{}, client.IgnoreNotFound(err)
	}

	// Calculate storage efficiency based on lifetime and superabsorption
	baseEfficiency := 0.7
	if battery.Spec.Charging.Superabsorption {
		baseEfficiency += 0.2
	}

	// Efficiency decreases with shorter target lifetime
	lifetimeFactor := battery.Spec.Storage.TargetLifetime / 1e-9
	if lifetimeFactor > 1 {
		lifetimeFactor = 1
	}

	battery.Status.StorageEfficiency = baseEfficiency * lifetimeFactor
	battery.Status.DecoherenceRate = 1.0 / battery.Spec.Storage.TargetLifetime

	// Simulate charge level
	if battery.Status.ChargeLevel == 0 {
		battery.Status.ChargeLevel = 50.0 // Default charge level
	}

	if err := r.Status().Update(ctx, battery); err != nil {
		return ctrl.Result{}, err
	}

	return ctrl.Result{}, nil
}

func (r *PolaritonBatteryReconciler) SetupWithManager(mgr ctrl.Manager) error {
	return ctrl.NewControllerManagedBy(mgr).
		For(&arkhev1beta1.PolaritonBattery{}).
		Complete(r)
}

// IoQTDeviceReconciler reconciles an IoQTDevice object
type IoQTDeviceReconciler struct {
	client.Client
	Scheme *runtime.Scheme
}

// +kubebuilder:rbac:groups=arkhe.io,resources=ioqtdevices,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups=arkhe.io,resources=ioqtdevices/status,verbs=get;update;patch

func (r *IoQTDeviceReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
	device := &arkhev1beta1.IoQTDevice{}
	if err := r.Get(ctx, req.NamespacedName, device); err != nil {
		return ctrl.Result{}, client.IgnoreNotFound(err)
	}

	// Calculate tunneling rate based on cell count and clock zones
	device.Status.TunnelingRate = float64(device.Spec.QCAConfiguration.CellCount) /
		float64(device.Spec.QCAConfiguration.ClockZones) * 1e9

	// Operational if configured
	device.Status.Operational = device.Spec.QCAConfiguration.CellCount > 0
	device.Status.ErrorRate = 1.0 / float64(device.Spec.QCAConfiguration.CellCount)

	if err := r.Status().Update(ctx, device); err != nil {
		return ctrl.Result{}, err
	}

	return ctrl.Result{}, nil
}

func (r *IoQTDeviceReconciler) SetupWithManager(mgr ctrl.Manager) error {
	return ctrl.NewControllerManagedBy(mgr).
		For(&arkhev1beta1.IoQTDevice{}).
		Complete(r)
}

// QuantumNeuralNetworkReconciler reconciles a QuantumNeuralNetwork object
type QuantumNeuralNetworkReconciler struct {
	client.Client
	Scheme *runtime.Scheme
}

// +kubebuilder:rbac:groups=arkhe.io,resources=quantumneuralnetworks,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups=arkhe.io,resources=quantumneuralnetworks/status,verbs=get;update;patch

func (r *QuantumNeuralNetworkReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
	qnn := &arkhev1beta1.QuantumNeuralNetwork{}
	if err := r.Get(ctx, req.NamespacedName, qnn); err != nil {
		return ctrl.Result{}, client.IgnoreNotFound(err)
	}

	// Default accuracies based on architecture
	switch qnn.Spec.Architecture {
	case "HQCNN":
		qnn.Status.Accuracy = 0.92
		qnn.Status.QuantumAdvantage = true
	case "QENSSF":
		qnn.Status.Accuracy = 0.88
		qnn.Status.QuantumAdvantage = true
	case "Variational":
		qnn.Status.Accuracy = 0.85
		qnn.Status.QuantumAdvantage = false
	default:
		qnn.Status.Accuracy = 0.80
		qnn.Status.QuantumAdvantage = false
	}

	qnn.Status.EntanglementFidelity = 0.95

	if err := r.Status().Update(ctx, qnn); err != nil {
		return ctrl.Result{}, err
	}

	return ctrl.Result{}, nil
}

func (r *QuantumNeuralNetworkReconciler) SetupWithManager(mgr ctrl.Manager) error {
	return ctrl.NewControllerManagedBy(mgr).
		For(&arkhev1beta1.QuantumNeuralNetwork{}).
		Complete(r)
}

// PostQuantumCryptoReconciler reconciles a PostQuantumCrypto object
type PostQuantumCryptoReconciler struct {
	client.Client
	Scheme *runtime.Scheme
}

// +kubebuilder:rbac:groups=arkhe.io,resources=postquantumcryptos,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups=arkhe.io,resources=postquantumcryptos/status,verbs=get;update;patch

func (r *PostQuantumCryptoReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
	crypto := &arkhev1beta1.PostQuantumCrypto{}
	if err := r.Get(ctx, req.NamespacedName, crypto); err != nil {
		return ctrl.Result{}, client.IgnoreNotFound(err)
	}

	// Set security level based on algorithm
	switch crypto.Spec.Algorithm {
	case "Kyber512":
		crypto.Status.SecurityLevel = "NIST1"
		crypto.Status.KeyRate = 2.5
	case "Kyber768":
		crypto.Status.SecurityLevel = "NIST3"
		crypto.Status.KeyRate = 1.5
	case "Kyber1024":
		crypto.Status.SecurityLevel = "NIST5"
		crypto.Status.KeyRate = 1.0
	case "NTRU":
		crypto.Status.SecurityLevel = "NIST3"
		crypto.Status.KeyRate = 2.0
	default:
		crypto.Status.SecurityLevel = "NIST1"
		crypto.Status.KeyRate = 1.0
	}

	crypto.Status.QuantumResistance = true

	if err := r.Status().Update(ctx, crypto); err != nil {
		return ctrl.Result{}, err
	}

	return ctrl.Result{}, nil
}

func (r *PostQuantumCryptoReconciler) SetupWithManager(mgr ctrl.Manager) error {
	return ctrl.NewControllerManagedBy(mgr).
		For(&arkhev1beta1.PostQuantumCrypto{}).
		Complete(r)
}
