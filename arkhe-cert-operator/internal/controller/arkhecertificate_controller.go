package controller

import (
	"context"
	"fmt"
	"time"

	certv1alpha1 "github.com/arkhe-os/arkhe-cert-operator/api/v1alpha1"
	"github.com/arkhe-os/arkhe-cert-operator/internal/certmanager"
	"github.com/arkhe-os/arkhe-cert-operator/internal/keystore"
	"github.com/arkhe-os/arkhe-cert-operator/pkg/metrics"
	"github.com/go-logr/logr"
	certmanagerv1 "github.com/cert-manager/cert-manager/pkg/apis/certmanager/v1"
	corev1 "k8s.io/api/core/v1"
	appsv1 "k8s.io/api/apps/v1"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/types"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/controller/controllerutil"
	"sigs.k8s.io/controller-runtime/pkg/log"
)

type ArkheCertificateReconciler struct {
	client.Client
	Scheme          *runtime.Scheme
	CertManagerClient *certmanager.Client
	Log             logr.Logger
}

//+kubebuilder:rbac:groups=cert.arkhe.os,resources=arkhecertificates,verbs=get;list;watch;create;update;patch;delete
//+kubebuilder:rbac:groups=cert.arkhe.os,resources=arkhecertificates/status,verbs=get;update;patch
//+kubebuilder:rbac:groups=cert-manager.io,resources=certificates;issuers;clusterissuers,verbs=get;list;watch;create;update;patch;delete
//+kubebuilder:rbac:groups=core,resources=secrets,verbs=get;list;watch;create;update;patch;delete
//+kubebuilder:rbac:groups=apps,resources=deployments,verbs=get;list;watch;update;patch

func (r *ArkheCertificateReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
	logger := log.FromContext(ctx).WithValues("arkhecertificate", req.NamespacedName)

	var arkheCert certv1alpha1.ArkheCertificate
	if err := r.Get(ctx, req.NamespacedName, &arkheCert); err != nil {
		if apierrors.IsNotFound(err) {
			return ctrl.Result{}, nil
		}
		logger.Error(err, "Failed to fetch ArkheCertificate")
		return ctrl.Result{}, err
	}

	if !arkheCert.DeletionTimestamp.IsZero() {
		return r.handleDeletion(ctx, &arkheCert, logger)
	}

	if !controllerutil.ContainsFinalizer(&arkheCert, "cert.arkhe.os/finalizer") {
		controllerutil.AddFinalizer(&arkheCert, "cert.arkhe.os/finalizer")
		if err := r.Update(ctx, &arkheCert); err != nil {
			return ctrl.Result{}, err
		}
		return ctrl.Result{Requeue: true}, nil
	}

	return r.reconcileNormal(ctx, &arkheCert, logger)
}

func (r *ArkheCertificateReconciler) reconcileNormal(ctx context.Context,
	arkheCert *certv1alpha1.ArkheCertificate, logger logr.Logger) (ctrl.Result, error) {

	if arkheCert.Status.CurrentCertificate != nil {
		metrics.CertificateExpirySeconds.WithLabelValues(
			arkheCert.Spec.ServiceName,
			arkheCert.Namespace,
		).Set(float64(arkheCert.Status.CurrentCertificate.DaysUntilExpiry * 86400))
	}

	needsRotation, reason, err := r.shouldRotate(ctx, arkheCert, logger)
	if err != nil {
		r.updateStatus(ctx, arkheCert, certv1alpha1.ConditionError, "RotationCheckFailed", err.Error(), logger)
		return ctrl.Result{}, err
	}

	if needsRotation {
		logger.Info("Certificate rotation required", "reason", reason)
		return r.rotateCertificate(ctx, arkheCert, logger)
	}

	r.updateStatus(ctx, arkheCert, certv1alpha1.ConditionReady, "CertificateValid",
		fmt.Sprintf("Certificate valid for %d more days", arkheCert.Status.CurrentCertificate.DaysUntilExpiry), logger)

	requeueAfter := time.Duration(arkheCert.Spec.RotationThresholdDays) * 24 * time.Hour
	if arkheCert.Status.CurrentCertificate.DaysUntilExpiry < arkheCert.Spec.RotationThresholdDays {
		requeueAfter = 24 * time.Hour
	}

	return ctrl.Result{RequeueAfter: requeueAfter}, nil
}

func (r *ArkheCertificateReconciler) shouldRotate(ctx context.Context,
	arkheCert *certv1alpha1.ArkheCertificate, logger logr.Logger) (bool, string, error) {

	if arkheCert.Status.CurrentCertificate == nil {
		return true, "NoCertificateIssued", nil
	}

	daysUntilExpiry := arkheCert.Status.CurrentCertificate.DaysUntilExpiry
	threshold := arkheCert.Spec.RotationThresholdDays

	if daysUntilExpiry <= threshold {
		return true, fmt.Sprintf("ExpiringIn%dDays", daysUntilExpiry), nil
	}

	return false, "", nil
}

func (r *ArkheCertificateReconciler) rotateCertificate(ctx context.Context,
	arkheCert *certv1alpha1.ArkheCertificate, logger logr.Logger) (ctrl.Result, error) {

	r.updateStatus(ctx, arkheCert, certv1alpha1.ConditionRotating, "RotationStarted",
		"Certificate rotation initiated", logger)

	certRequest := &certmanagerv1.Certificate{
		ObjectMeta: metav1.ObjectMeta{
			Name:      fmt.Sprintf("%s-rotation", arkheCert.Name),
			Namespace: arkheCert.Namespace,
		},
		Spec: certmanagerv1.CertificateSpec{
			CommonName:  arkheCert.Spec.CommonName,
			DNSNames:    arkheCert.Spec.DNSNames,
			SecretName:  fmt.Sprintf("%s-cert-tls", arkheCert.Spec.ServiceName),
			IssuerRef:   arkheCert.Spec.IssuerRef,
			Duration:    &metav1.Duration{Duration: time.Duration(arkheCert.Spec.ValidityDays) * 24 * time.Hour},
		},
	}

	if err := controllerutil.SetControllerReference(arkheCert, certRequest, r.Scheme); err != nil {
		return ctrl.Result{}, err
	}

	if err := r.Create(ctx, certRequest); err != nil && !apierrors.IsAlreadyExists(err) {
		logger.Error(err, "Failed to create cert-manager Certificate")
		return ctrl.Result{}, err
	}

	secretName := fmt.Sprintf("%s-cert-tls", arkheCert.Spec.ServiceName)
	var certSecret corev1.Secret
	if err := r.Get(ctx, types.NamespacedName{Name: secretName, Namespace: arkheCert.Namespace}, &certSecret); err != nil {
		logger.Error(err, "Failed to fetch certificate Secret")
		return ctrl.Result{RequeueAfter: 10 * time.Second}, nil
	}

	keystorePassword, err := r.getKeystorePassword(ctx, arkheCert)
	if err != nil {
		return ctrl.Result{}, err
	}

	pkcs12Data, err := keystore.GeneratePKCS12(
		certSecret.Data[corev1.TLSCertKey],
		certSecret.Data[corev1.TLSPrivateKeyKey],
		arkheCert.Spec.CommonName,
		[]byte(keystorePassword),
	)
	if err != nil {
		logger.Error(err, "Failed to generate PKCS12")
		return ctrl.Result{}, err
	}

	keystoreSecret := &corev1.Secret{
		ObjectMeta: metav1.ObjectMeta{
			Name:      fmt.Sprintf("%s-keystore", arkheCert.Spec.ServiceName),
			Namespace: arkheCert.Namespace,
		},
		Type: corev1.SecretTypeOpaque,
		Data: map[string][]byte{
			"server-keystore.p12": pkcs12Data,
			"ca-cert.pem":        certSecret.Data["ca.crt"],
		},
	}

	if err := controllerutil.SetControllerReference(arkheCert, keystoreSecret, r.Scheme); err != nil {
		return ctrl.Result{}, err
	}

	if err := r.Create(ctx, keystoreSecret); err != nil && !apierrors.IsAlreadyExists(err) {
		return ctrl.Result{}, err
	}

	if arkheCert.Spec.TriggerRollingUpdate {
		r.triggerRollingUpdate(ctx, arkheCert, logger)
	}

	arkheCert.Status.KeystoreSecretName = keystoreSecret.Name
	if err := r.Status().Update(ctx, arkheCert); err != nil {
		return ctrl.Result{}, err
	}

	metrics.CertificateRotationsTotal.WithLabelValues(arkheCert.Spec.ServiceName, arkheCert.Namespace).Inc()

	logger.Info("Certificate rotation completed")
	r.updateStatus(ctx, arkheCert, certv1alpha1.ConditionReady, "RotationComplete",
		"Certificate rotated successfully", logger)

	return ctrl.Result{RequeueAfter: time.Duration(arkheCert.Spec.RotationThresholdDays) * 24 * time.Hour}, nil
}

func (r *ArkheCertificateReconciler) getKeystorePassword(ctx context.Context, arkheCert *certv1alpha1.ArkheCertificate) (string, error) {
	if arkheCert.Spec.KeystorePasswordSecret == nil {
		return "changeit", nil
	}
	var secret corev1.Secret
	if err := r.Get(ctx, types.NamespacedName{
		Name:      arkheCert.Spec.KeystorePasswordSecret.Name,
		Namespace: arkheCert.Namespace,
	}, &secret); err != nil {
		return "", err
	}
	return string(secret.Data[arkheCert.Spec.KeystorePasswordSecret.Key]), nil
}

func (r *ArkheCertificateReconciler) triggerRollingUpdate(ctx context.Context,
	arkheCert *certv1alpha1.ArkheCertificate, logger logr.Logger) error {

	var deployment appsv1.Deployment
	if err := r.Get(ctx, types.NamespacedName{
		Name:      arkheCert.Spec.ServiceName,
		Namespace: arkheCert.Namespace,
	}, &deployment); err != nil {
		if apierrors.IsNotFound(err) {
			return nil
		}
		return err
	}

	if deployment.Spec.Template.Annotations == nil {
		deployment.Spec.Template.Annotations = make(map[string]string)
	}
	deployment.Spec.Template.Annotations["cert.arkhe.os/last-rotation"] = time.Now().Format(time.RFC3339)

	return r.Update(ctx, &deployment)
}

func (r *ArkheCertificateReconciler) updateStatus(ctx context.Context,
	arkheCert *certv1alpha1.ArkheCertificate, conditionType, reason, message string, logger logr.Logger) {

	condition := metav1.Condition{
		Type:               conditionType,
		Status:             metav1.ConditionTrue,
		Reason:             reason,
		Message:            message,
		LastTransitionTime: metav1.Now(),
		ObservedGeneration: arkheCert.Generation,
	}

	found := false
	for i := range arkheCert.Status.Conditions {
		if arkheCert.Status.Conditions[i].Type == conditionType {
			arkheCert.Status.Conditions[i] = condition
			found = true
			break
		}
	}
	if !found {
		arkheCert.Status.Conditions = append(arkheCert.Status.Conditions, condition)
	}

	if err := r.Status().Update(ctx, arkheCert); err != nil {
		logger.Error(err, "Failed to update status")
	}
}

func (r *ArkheCertificateReconciler) handleDeletion(ctx context.Context,
	arkheCert *certv1alpha1.ArkheCertificate, logger logr.Logger) (ctrl.Result, error) {

	if controllerutil.ContainsFinalizer(arkheCert, "cert.arkhe.os/finalizer") {
		certName := fmt.Sprintf("%s-rotation", arkheCert.Name)
		cert := &certmanagerv1.Certificate{}
		if err := r.Get(ctx, types.NamespacedName{Name: certName, Namespace: arkheCert.Namespace}, cert); err == nil {
			r.Delete(ctx, cert)
		}

		controllerutil.RemoveFinalizer(arkheCert, "cert.arkhe.os/finalizer")
		if err := r.Update(ctx, arkheCert); err != nil {
			return ctrl.Result{}, err
		}
	}
	return ctrl.Result{}, nil
}

func (r *ArkheCertificateReconciler) SetupWithManager(mgr ctrl.Manager) error {
	return ctrl.NewControllerManagedBy(mgr).
		For(&certv1alpha1.ArkheCertificate{}).
		Owns(&certmanagerv1.Certificate{}).
		Complete(r)
}
