package controllers

import (
	"context"

	admissionv1 "k8s.io/api/admissionregistration/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/log"

	arkhev1alpha1 "github.com/arkhe-n/arkhe-operator/api/v1alpha1"
)

type EntropyShieldReconciler struct {
	client.Client
	Scheme *runtime.Scheme
}

func (r *EntropyShieldReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
	logger := log.FromContext(ctx)

	shield := &arkhev1alpha1.EntropyShield{}
	if err := r.Get(ctx, req.NamespacedName, shield); err != nil {
		return ctrl.Result{}, client.IgnoreNotFound(err)
	}

	logger.Info("Reconciling EntropyShield", "maxEntropy", shield.Spec.MaxEntropynW)

	shield.Status.Active = true
	shield.Status.CurrentEntropynW = shield.Spec.MaxEntropynW * 0.1
	shield.Status.AttacksNeutralized = 0

	if err := r.Status().Update(ctx, shield); err != nil {
		return ctrl.Result{}, err
	}

	sideEffectNone := admissionv1.SideEffectClassNone
	mutatingWebhook := &admissionv1.MutatingWebhookConfiguration{
		ObjectMeta: metav1.ObjectMeta{
			Name: shield.Name + "-mutating-webhook",
			Labels: map[string]string{
				"arkhe.io/shield": shield.Name,
			},
		},
		Webhooks: []admissionv1.MutatingWebhook{
			{
				Name: "mentropyshield.arkhe.io",
				Rules: []admissionv1.RuleWithOperations{
					{
						Operations: []admissionv1.OperationType{admissionv1.Create, admissionv1.Update},
						Rule: admissionv1.Rule{
							APIGroups:   []string{""},
							APIVersions: []string{"v1"},
							Resources:   []string{"pods"},
						},
					},
				},
				ClientConfig: admissionv1.WebhookClientConfig{
					Service: &admissionv1.ServiceReference{
						Name:      "entropy-shield-webhook",
						Namespace: shield.Namespace,
					},
				},
				SideEffects: &sideEffectNone,
			},
		},
	}

	if err := ctrl.SetControllerReference(shield, mutatingWebhook, r.Scheme); err != nil {
		return ctrl.Result{}, err
	}

	return ctrl.Result{}, nil
}

func (r *EntropyShieldReconciler) SetupWithManager(mgr ctrl.Manager) error {
	return ctrl.NewControllerManagedBy(mgr).
		For(&arkhev1alpha1.EntropyShield{}).
		Owns(&admissionv1.MutatingWebhookConfiguration{}).
		Complete(r)
}
