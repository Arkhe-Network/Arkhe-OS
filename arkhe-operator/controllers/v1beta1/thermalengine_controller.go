package controllers

import (
	"context"
	"math"

	arkhev1beta1 "github.com/arkhe-n/arkhe-operator/api/v1beta1"
	"k8s.io/apimachinery/pkg/runtime"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"
)

// ThermalEngineReconciler reconciles a ThermalEngine object
type ThermalEngineReconciler struct {
	client.Client
	Scheme *runtime.Scheme
}

// +kubebuilder:rbac:groups=arkhe.io,resources=thermalengines,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups=arkhe.io,resources=thermalengines/status,verbs=get;update;patch
// +kubebuilder:rbac:groups=arkhe.io,resources=thermalengines/finalizers,verbs=update

func (r *ThermalEngineReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
	engine := &arkhev1beta1.ThermalEngine{}
	if err := r.Get(ctx, req.NamespacedName, engine); err != nil {
		return ctrl.Result{}, client.IgnoreNotFound(err)
	}

	// Calculate Carnot efficiency: η = 1 - T_cold/T_hot
	hot := engine.Spec.HeatSource.Temperature
	var cold float64
	if engine.Spec.CarnotLimit.ColdReservoir > 0 {
		cold = engine.Spec.CarnotLimit.ColdReservoir
	} else {
		cold = 273.15 // Default cold reservoir (0°C)
	}
	efficiency := 1.0 - (cold / hot)

	// If universal, convert entropy to computational work
	if engine.Spec.Programmability.Universal {
		// W = Q̇ * η * log(2) for reversible isothermal expansion
		work := engine.Spec.HeatSource.EntropyFlow * efficiency * math.Log(2)
		engine.Status.WorkDone = work

		// Phase: if efficiency > 0.5, it is processing information
		if efficiency > 0.5 {
			engine.Status.Phase = "Computing"
		} else if efficiency > 0.3 {
			engine.Status.Phase = "Charging"
		} else {
			engine.Status.Phase = "Idle"
		}
	} else {
		engine.Status.Phase = "Fixed"
	}

	engine.Status.CurrentEfficiency = efficiency
	engine.Status.EntropyProduced = engine.Spec.HeatSource.EntropyFlow * (1 - efficiency)

	if err := r.Status().Update(ctx, engine); err != nil {
		return ctrl.Result{}, err
	}

	return ctrl.Result{}, nil
}

func (r *ThermalEngineReconciler) SetupWithManager(mgr ctrl.Manager) error {
	return ctrl.NewControllerManagedBy(mgr).
		For(&arkhev1beta1.ThermalEngine{}).
		Complete(r)
}
