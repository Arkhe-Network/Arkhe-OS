package controllers

import (
	"context"
	"math"
	"time"

	arkhev1beta1 "arkhe-operator/api/v1beta1"
	"k8s.io/apimachinery/pkg/runtime"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"
)

// ThetaRhythmReconciler reconciles a ThetaRhythm object
type ThetaRhythmReconciler struct {
	client.Client
	Scheme *runtime.Scheme
}

// +kubebuilder:rbac:groups=arkhe.io,resources=thetarhythms,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups=arkhe.io,resources=thetarhythms/status,verbs=get;update;patch
// +kubebuilder:rbac:groups=arkhe.io,resources=thetarhythms/finalizers,verbs=update

func (r *ThetaRhythmReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
	rhythm := &arkhev1beta1.ThetaRhythm{}
	if err := r.Get(ctx, req.NamespacedName, rhythm); err != nil {
		return ctrl.Result{}, client.IgnoreNotFound(err)
	}

	// Simulate theta oscillation: f(t) = A * sin(2πft + φ)
	freq := rhythm.Spec.Frequency
	if freq == 0 {
		freq = 6.0 // Default theta frequency
	}

	// Calculate current phase based on time
	now := time.Now().UnixNano() / int64(time.Millisecond)
	cyclePeriod := 1000.0 / freq
	currentPhase := math.Mod(float64(now), cyclePeriod) / cyclePeriod * 2 * math.Pi

	// Determine state: Encoding (0-π) vs Retrieval (π-2π)
	if currentPhase < math.Pi {
		rhythm.Status.CurrentPhase = "Encoding"
		rhythm.Status.MemoryConsolidation = 0.1 // Low during encoding
	} else {
		rhythm.Status.CurrentPhase = "Retrieval"
		rhythm.Status.MemoryConsolidation = 0.8 // High during retrieval
	}

	// Coherence with gamma oscillations (40-80 Hz)
	rhythm.Status.Coherence = rhythm.Spec.Amplitude * (1.0 - math.Abs(math.Sin(currentPhase/2)))

	if err := r.Status().Update(ctx, rhythm); err != nil {
		return ctrl.Result{}, err
	}

	// Reconcile at 100ms intervals to maintain synchronization
	return ctrl.Result{RequeueAfter: 100 * time.Millisecond}, nil
}

func (r *ThetaRhythmReconciler) SetupWithManager(mgr ctrl.Manager) error {
	return ctrl.NewControllerManagedBy(mgr).
		For(&arkhev1beta1.ThetaRhythm{}).
		Complete(r)
}
