package controllers

import (
	"context"
	"fmt"

	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/errors"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/types"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/log"

	arkhev1alpha1 "github.com/arkhe-n/arkhe-operator/api/v1alpha1"
)

type TzinorReconciler struct {
	client.Client
	Scheme *runtime.Scheme
}

func (r *TzinorReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
	logger := log.FromContext(ctx)

	tzinor := &arkhev1alpha1.Tzinor{}
	if err := r.Get(ctx, req.NamespacedName, tzinor); err != nil {
		return ctrl.Result{}, client.IgnoreNotFound(err)
	}

	desiredService := &corev1.Service{
		ObjectMeta: ctrl.ObjectMeta{
			Name:      tzinor.Name,
			Namespace: tzinor.Namespace,
			Annotations: map[string]string{
				"arkhe.io/source-epoch": tzinor.Spec.SourceEpoch,
				"arkhe.io/target-epoch": tzinor.Spec.TargetEpoch,
				"arkhe.io/impedance":    fmt.Sprintf("%f", tzinor.Spec.Impedance),
			},
		},
		Spec: corev1.ServiceSpec{
			ClusterIP: "None",
			Selector: map[string]string{
				"arkhe.io/tzinor-name": tzinor.Name,
			},
			Ports: []corev1.ServicePort{
				{Name: "tunnel", Port: 162025, Protocol: corev1.ProtocolTCP},
			},
		},
	}

	if err := ctrl.SetControllerReference(tzinor, desiredService, r.Scheme); err != nil {
		return ctrl.Result{}, err
	}

	found := &corev1.Service{}
	err := r.Get(ctx, types.NamespacedName{Name: tzinor.Name, Namespace: tzinor.Namespace}, found)
	if err != nil && errors.IsNotFound(err) {
		logger.Info("Creating Service for Tzinor channel.")
		if err := r.Create(ctx, desiredService); err != nil {
			return ctrl.Result{}, err
		}
	} else if err != nil {
		return ctrl.Result{}, err
	}

	if tzinor.Spec.LockMode == arkhev1alpha1.LockModeLocked {
		tzinor.Status.Locked = true
		tzinor.Status.PhaseError = 0.003
		tzinor.Status.LatencyPicos = 0.25
	} else {
		tzinor.Status.Locked = false
		tzinor.Status.PhaseError = 0.1
		tzinor.Status.LatencyPicos = 2.5
	}

	if err := r.Status().Update(ctx, tzinor); err != nil {
		return ctrl.Result{}, err
	}

	return ctrl.Result{}, nil
}

func (r *TzinorReconciler) SetupWithManager(mgr ctrl.Manager) error {
	return ctrl.NewControllerManagedBy(mgr).
		For(&arkhev1alpha1.Tzinor{}).
		Owns(&corev1.Service{}).
		Complete(r)
}
