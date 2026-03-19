package controllers

import (
	"context"

	arkhev1beta1 "arkhe-operator/api/v1beta1"
	"k8s.io/apimachinery/pkg/runtime"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"
)

// GKPAtomReconciler reconciles a GKPAtom object
type GKPAtomReconciler struct {
	client.Client
	Scheme *runtime.Scheme
}

// +kubebuilder:rbac:groups=arkhe.io,resources=gkpatoms,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups=arkhe.io,resources=gkpatoms/status,verbs=get;update;patch
// +kubebuilder:rbac:groups=arkhe.io,resources=gkpatoms/finalizers,verbs=update

func (r *GKPAtomReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
	atom := &arkhev1beta1.GKPAtom{}
	if err := r.Get(ctx, req.NamespacedName, atom); err != nil {
		return ctrl.Result{}, client.IgnoreNotFound(err)
	}

	// Calculate coherence time based on atomic species and trap configuration
	var baseCoherence float64
	switch atom.Spec.AtomicSpecies {
	case "Ytterbium-171":
		baseCoherence = 2500.0 // µs for Yb
	case "Calcium-40":
		baseCoherence = 1000.0 // µs for Ca
	case "Beryllium-9":
		baseCoherence = 500.0 // µs for Be
	default:
		baseCoherence = 1000.0
	}

	// Adjust for trap RF frequency (higher frequency = shorter coherence)
	rfFactor := 5.5 / atom.Spec.TrapConfiguration.RFFrequency
	if rfFactor < 1 {
		rfFactor = 1
	}

	atom.Status.CoherenceTime = baseCoherence * rfFactor

	// Calculate gate fidelity based on squeezing and error correction
	fidelity := 0.95
	if atom.Spec.GKPEncoding.ErrorCorrection {
		fidelity += 0.04
	}
	fidelity -= atom.Spec.GKPEncoding.Squeezing * 0.01
	atom.Status.GateFidelity = fidelity

	// Initialize entanglement if not set
	if atom.Status.Entanglement == nil {
		atom.Status.Entanglement = &arkhev1beta1.EntanglementStatus{}
	}

	if err := r.Status().Update(ctx, atom); err != nil {
		return ctrl.Result{}, err
	}

	return ctrl.Result{}, nil
}

func (r *GKPAtomReconciler) SetupWithManager(mgr ctrl.Manager) error {
	return ctrl.NewControllerManagedBy(mgr).
		For(&arkhev1beta1.GKPAtom{}).
		Complete(r)
}
