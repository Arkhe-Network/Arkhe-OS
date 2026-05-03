package controllers

import (
	"context"
	"fmt"

	appsv1 "k8s.io/api/apps/v1"
	autoscalingv2 "k8s.io/api/autoscaling/v2"
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

type VerCoreReconciler struct {
	client.Client
	Scheme *runtime.Scheme
}

func (r *VerCoreReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
	logger := log.FromContext(ctx)

	vercore := &arkhev1alpha1.VerCore{}
	if err := r.Get(ctx, req.NamespacedName, vercore); err != nil {
		return ctrl.Result{}, client.IgnoreNotFound(err)
	}

	cpuReq, _ := resource.ParseQuantity("2000m")
	memReq, _ := resource.ParseQuantity("4Gi")
	cpuLim, _ := resource.ParseQuantity("4000m")
	memLim, _ := resource.ParseQuantity("8Gi")

	desiredDeployment := &appsv1.Deployment{
		ObjectMeta: metav1.ObjectMeta{
			Name:      vercore.Name,
			Namespace: vercore.Namespace,
			Labels:    map[string]string{"app": "vercore", "clock-rate": fmt.Sprintf("%f", vercore.Spec.ClockRateGHz)},
		},
		Spec: appsv1.DeploymentSpec{
			Replicas: &vercore.Spec.Replicas,
			Selector: &metav1.LabelSelector{
				MatchLabels: map[string]string{"app": "vercore"},
			},
			Template: corev1.PodTemplateSpec{
				ObjectMeta: metav1.ObjectMeta{
					Labels: map[string]string{"app": "vercore"},
				},
				Spec: corev1.PodSpec{
					Containers: []corev1.Container{
						{
							Name:  "vercore-cpu",
							Image: vercore.Spec.Image,
							Env: []corev1.EnvVar{
								{Name: "CLOCK_RATE_GHZ", Value: fmt.Sprintf("%f", vercore.Spec.ClockRateGHz)},
								{Name: "TARGET_TEMP_MK", Value: fmt.Sprintf("%f", vercore.Spec.TargetTempMilliKelvin)},
							},
							Resources: corev1.ResourceRequirements{
								Requests: corev1.ResourceList{
									corev1.ResourceCPU:    cpuReq,
									corev1.ResourceMemory: memReq,
								},
								Limits: corev1.ResourceList{
									corev1.ResourceCPU:    cpuLim,
									corev1.ResourceMemory: memLim,
								},
							},
						},
					},
				},
			},
		},
	}

	if err := ctrl.SetControllerReference(vercore, desiredDeployment, r.Scheme); err != nil {
		return ctrl.Result{}, err
	}

	found := &appsv1.Deployment{}
	err := r.Get(ctx, types.NamespacedName{Name: vercore.Name, Namespace: vercore.Namespace}, found)
	if err != nil && errors.IsNotFound(err) {
		logger.Info("Creating Deployment for VerCore.")
		if err := r.Create(ctx, desiredDeployment); err != nil {
			return ctrl.Result{}, err
		}
	} else if err != nil {
		return ctrl.Result{}, err
	}

	readyReplicas := found.Status.ReadyReplicas
	vercore.Status.ReadyReplicas = readyReplicas
	vercore.Status.AvgTempMilliKelvin = vercore.Spec.TargetTempMilliKelvin + (float64(readyReplicas) * 0.5)
	vercore.Status.CoreMark = int(vercore.Spec.ClockRateGHz * 1000)

	if err := r.Status().Update(ctx, vercore); err != nil {
		return ctrl.Result{}, err
	}

	maxReplicas := vercore.Spec.Replicas * 3
	hpa := &autoscalingv2.HorizontalPodAutoscaler{
		ObjectMeta: metav1.ObjectMeta{
			Name:      vercore.Name + "-hpa",
			Namespace: vercore.Namespace,
		},
		Spec: autoscalingv2.HorizontalPodAutoscalerSpec{
			ScaleTargetRef: autoscalingv2.CrossVersionObjectReference{
				Kind:       "Deployment",
				Name:       vercore.Name,
				APIVersion: "apps/v1",
			},
			MinReplicas: &vercore.Spec.Replicas,
			MaxReplicas: maxReplicas,
			Metrics: []autoscalingv2.MetricSpec{
				{
					Type: autoscalingv2.ResourceMetricSourceType,
					Resource: &autoscalingv2.ResourceMetricSource{
						Name: corev1.ResourceCPU,
						Target: autoscalingv2.MetricTarget{
							Type:               autoscalingv2.UtilizationMetricType,
							AverageUtilization: ptrInt32(70),
						},
					},
				},
			},
		},
	}

	if err := ctrl.SetControllerReference(vercore, hpa, r.Scheme); err != nil {
		return ctrl.Result{}, err
	}

	hpaFound := &autoscalingv2.HorizontalPodAutoscaler{}
	if err := r.Get(ctx, types.NamespacedName{Name: hpa.Name, Namespace: hpa.Namespace}, hpaFound); err != nil && errors.IsNotFound(err) {
		logger.Info("Creating HPA for VerCore.")
		r.Create(ctx, hpa)
	}

	return ctrl.Result{}, nil
}

func (r *VerCoreReconciler) SetupWithManager(mgr ctrl.Manager) error {
	return ctrl.NewControllerManagedBy(mgr).
		For(&arkhev1alpha1.VerCore{}).
		Owns(&appsv1.Deployment{}).
		Owns(&autoscalingv2.HorizontalPodAutoscaler{}).
		Complete(r)
}

func ptrInt32(i int32) *int32 {
	return &i
}
