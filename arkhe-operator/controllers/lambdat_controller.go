package controllers

import (
	"context"
	"fmt"

	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"
	networkingv1 "k8s.io/api/networking/v1"
	"k8s.io/apimachinery/pkg/api/errors"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/types"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/log"

	arkhev1alpha1 "github.com/arkhe-n/arkhe-operator/api/v1alpha1"
)

type LambdaTReconciler struct {
	client.Client
	Scheme *runtime.Scheme
}

func (r *LambdaTReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
	logger := log.FromContext(ctx)

	lambda := &arkhev1alpha1.LambdaT{}
	if err := r.Get(ctx, req.NamespacedName, lambda); err != nil {
		return ctrl.Result{}, client.IgnoreNotFound(err)
	}

	logger.Info("Reconciling LambdaT", "handler", lambda.Spec.Handler)

	desiredDeployment := &appsv1.Deployment{
		ObjectMeta: metav1.ObjectMeta{
			Name:      lambda.Name,
			Namespace: lambda.Namespace,
			Labels:    map[string]string{"app": "lambda-t", "trigger": lambda.Spec.Trigger.Type},
		},
		Spec: appsv1.DeploymentSpec{
			Replicas: int32Ptr(0),
			Selector: &metav1.LabelSelector{
				MatchLabels: map[string]string{"app": "lambda-t"},
			},
			Template: corev1.PodTemplateSpec{
				ObjectMeta: metav1.ObjectMeta{
					Labels: map[string]string{"app": "lambda-t"},
				},
				Spec: corev1.PodSpec{
					Containers: []corev1.Container{
						{
							Name:  "lambda-handler",
							Image: lambda.Spec.Image,
							Env: []corev1.EnvVar{
								{Name: "HANDLER", Value: lambda.Spec.Handler},
								{Name: "TRIGGER_TYPE", Value: lambda.Spec.Trigger.Type},
								{Name: "LIFETIME_PS", Value: fmt.Sprintf("%f", lambda.Spec.Trigger.LifetimePs)},
								{Name: "COHERENCE_SIGMA", Value: fmt.Sprintf("%f", lambda.Spec.CoherenceSigma)},
							},
						},
					},
				},
			},
		},
	}

	if lambda.Spec.Trigger.Type == "Schedule" {
		replicas := int32(1)
		desiredDeployment.Spec.Replicas = &replicas
	}

	if err := ctrl.SetControllerReference(lambda, desiredDeployment, r.Scheme); err != nil {
		return ctrl.Result{}, err
	}

	found := &appsv1.Deployment{}
	err := r.Get(ctx, types.NamespacedName{Name: lambda.Name, Namespace: lambda.Namespace}, found)
	if err != nil && errors.IsNotFound(err) {
		logger.Info("Creating Deployment for LambdaT.")
		if err := r.Create(ctx, desiredDeployment); err != nil {
			return ctrl.Result{}, err
		}
	} else if err != nil {
		return ctrl.Result{}, err
	}

	service := &corev1.Service{
		ObjectMeta: metav1.ObjectMeta{
			Name:      lambda.Name,
			Namespace: lambda.Namespace,
		},
		Spec: corev1.ServiceSpec{
			Selector: map[string]string{"app": "lambda-t"},
			Ports: []corev1.ServicePort{
				{Name: "http", Port: 8080},
			},
		},
	}

	if err := ctrl.SetControllerReference(lambda, service, r.Scheme); err != nil {
		return ctrl.Result{}, err
	}

	svcFound := &corev1.Service{}
	if err := r.Get(ctx, types.NamespacedName{Name: lambda.Name, Namespace: lambda.Namespace}, svcFound); err != nil && errors.IsNotFound(err) {
		logger.Info("Creating Service for LambdaT.")
		r.Create(ctx, service)
	}

	ingress := &networkingv1.Ingress{
		ObjectMeta: metav1.ObjectMeta{
			Name:      lambda.Name,
			Namespace: lambda.Namespace,
			Annotations: map[string]string{
				"arkhe.io/lambda-trigger": lambda.Spec.Trigger.Type,
			},
		},
		Spec: networkingv1.IngressSpec{
			Rules: []networkingv1.IngressRule{
				{
					Host: lambda.Name + ".arkhe.io",
					IngressRuleValue: networkingv1.IngressRuleValue{
						HTTP: &networkingv1.HTTPIngressRuleValue{
							Paths: []networkingv1.HTTPIngressPath{
								{
									Path:     "/",
									PathType: func() *networkingv1.PathType { v := networkingv1.PathTypePrefix; return &v }(),
									Backend: networkingv1.IngressBackend{
										Service: &networkingv1.IngressServiceBackend{
											Name: lambda.Name,
											Port: networkingv1.ServiceBackendPort{Number: 8080},
										},
									},
								},
							},
						},
					},
				},
			},
		},
	}

	if err := ctrl.SetControllerReference(lambda, ingress, r.Scheme); err != nil {
		return ctrl.Result{}, err
	}

	ingFound := &networkingv1.Ingress{}
	if err := r.Get(ctx, types.NamespacedName{Name: lambda.Name, Namespace: lambda.Namespace}, ingFound); err != nil && errors.IsNotFound(err) {
		logger.Info("Creating Ingress for LambdaT.")
		r.Create(ctx, ingress)
	}

	lambda.Status.Invocations = 0
	lambda.Status.AvgTimePs = lambda.Spec.Trigger.LifetimePs

	if err := r.Status().Update(ctx, lambda); err != nil {
		return ctrl.Result{}, err
	}

	return ctrl.Result{}, nil
}

func int32Ptr(i int32) *int32 {
	return &i
}

func (r *LambdaTReconciler) SetupWithManager(mgr ctrl.Manager) error {
	return ctrl.NewControllerManagedBy(mgr).
		For(&arkhev1alpha1.LambdaT{}).
		Owns(&appsv1.Deployment{}).
		Owns(&corev1.Service{}).
		Owns(&networkingv1.Ingress{}).
		Complete(r)
}
