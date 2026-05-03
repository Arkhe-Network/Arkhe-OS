package controllers

import (
	"context"
	"fmt"

	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/errors"
	"k8s.io/apimachinery/pkg/api/resource"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/types"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/log"

	arkhev1alpha1 "github.com/arkhe-n/arkhe-operator/api/v1alpha1"
)

type EraReconciler struct {
	client.Client
	Scheme *runtime.Scheme
}

func (r *EraReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
	logger := log.FromContext(ctx)

	era := &arkhev1alpha1.Era{}
	if err := r.Get(ctx, req.NamespacedName, era); err != nil {
		return ctrl.Result{}, client.IgnoreNotFound(err)
	}

	if era.Spec.ThermalState == arkhev1alpha1.ThermalStateFrozen {
		logger.Info("Era is Frozen. Ensuring no processing pods are running.")

		deployment := &appsv1.Deployment{}
		err := r.Get(ctx, types.NamespacedName{Name: era.Name, Namespace: era.Namespace}, deployment)
		if err == nil {
			if err := r.Delete(ctx, deployment); err != nil {
				return ctrl.Result{}, err
			}
		}

		era.Status.Active = false
		era.Status.TemperatureMilliKelvin = 10.0
		if err := r.Status().Update(ctx, era); err != nil {
			return ctrl.Result{}, err
		}

		return ctrl.Result{}, nil
	}

	if era.Spec.AlphaWeight < 0.1 {
		logger.Info("Era is Masked. No compute resources allocated.")
		era.Status.Active = false
		era.Status.TemperatureMilliKelvin = 100.2
		if err := r.Status().Update(ctx, era); err != nil {
			return ctrl.Result{}, err
		}
		return ctrl.Result{}, nil
	}

	logger.Info("Era is Active. Reconciling Deployment.", "alpha", era.Spec.AlphaWeight)

	replicas := int32(1)
	if era.Spec.AlphaWeight > 0.5 {
		replicas = 2
	}
	if era.Spec.AlphaWeight > 0.8 {
		replicas = 3
	}

	cpuQty, _ := resource.ParseQuantity(era.Spec.Resources.CPU)
	memQty, _ := resource.ParseQuantity(era.Spec.Resources.Memory)

	desiredDeployment := &appsv1.Deployment{
		ObjectMeta: metav1.ObjectMeta{
			Name:      era.Name,
			Namespace: era.Namespace,
			Labels:    map[string]string{"app": "era-processor", "era-index": fmt.Sprintf("%d", era.Spec.Index)},
		},
		Spec: appsv1.DeploymentSpec{
			Replicas: &replicas,
			Selector: &metav1.LabelSelector{
				MatchLabels: map[string]string{"app": "era-processor", "era-index": fmt.Sprintf("%d", era.Spec.Index)},
			},
			Template: corev1.PodTemplateSpec{
				ObjectMeta: metav1.ObjectMeta{
					Labels: map[string]string{"app": "era-processor", "era-index": fmt.Sprintf("%d", era.Spec.Index)},
				},
				Spec: corev1.PodSpec{
					Containers: []corev1.Container{
						{
							Name:  "attnres-worker",
							Image: "arkhe/era-processor:latest",
							Env: []corev1.EnvVar{
								{Name: "ERA_INDEX", Value: fmt.Sprintf("%d", era.Spec.Index)},
								{Name: "ALPHA_WEIGHT", Value: fmt.Sprintf("%f", era.Spec.AlphaWeight)},
							},
							Resources: corev1.ResourceRequirements{
								Requests: corev1.ResourceList{
									corev1.ResourceCPU:    cpuQty,
									corev1.ResourceMemory: memQty,
								},
							},
						},
					},
				},
			},
		},
	}

	if err := ctrl.SetControllerReference(era, desiredDeployment, r.Scheme); err != nil {
		return ctrl.Result{}, err
	}

	found := &appsv1.Deployment{}
	err := r.Get(ctx, types.NamespacedName{Name: era.Name, Namespace: era.Namespace}, found)
	if err != nil && errors.IsNotFound(err) {
		logger.Info("Creating Deployment for Era.")
		if err := r.Create(ctx, desiredDeployment); err != nil {
			return ctrl.Result{}, err
		}
	} else if err != nil {
		return ctrl.Result{}, err
	} else {
		if *found.Spec.Replicas != replicas {
			found.Spec.Replicas = &replicas
			if err := r.Update(ctx, found); err != nil {
				return ctrl.Result{}, err
			}
			logger.Info("Updated Era deployment replicas", "replicas", replicas)
		}
	}

	era.Status.Active = true
	era.Status.TemperatureMilliKelvin = 100.2
	era.Status.BlocksProcessed = 0
	if err := r.Status().Update(ctx, era); err != nil {
		return ctrl.Result{}, err
	}

	return ctrl.Result{}, nil
}

func (r *EraReconciler) SetupWithManager(mgr ctrl.Manager) error {
	return ctrl.NewControllerManagedBy(mgr).
		For(&arkhev1alpha1.Era{}).
		Owns(&appsv1.Deployment{}).
		Complete(r)
}
