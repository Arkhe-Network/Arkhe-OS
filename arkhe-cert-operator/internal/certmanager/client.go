package certmanager

import (
	"context"
	"fmt"

	"github.com/go-logr/logr"
	certmanagerv1 "github.com/cert-manager/cert-manager/pkg/apis/certmanager/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"
)

type Client struct {
	client.Client
	Namespace string
	Log    logr.Logger
}

func NewCertManagerClient(c client.Client, namespace string) *Client {
	return &Client{
		Client:    c,
		Namespace: namespace,
		Log:       ctrl.Log.WithName("certmanager-client"),
	}
}

func (c *Client) IssueCertificate(ctx context.Context, name, namespace, commonName string, dnsNames []string, issuerRef certmanagerv1.ObjectReference, duration metav1.Duration) error {
	cert := &certmanagerv1.Certificate{
		ObjectMeta: metav1.ObjectMeta{
			Name:      name,
			Namespace: namespace,
		},
		Spec: certmanagerv1.CertificateSpec{
			CommonName: commonName,
			DNSNames:  dnsNames,
			IssuerRef:  issuerRef,
			Duration:  &duration,
		},
	}

	if err := c.Create(ctx, cert); err != nil {
		return fmt.Errorf("failed to create Certificate: %w", err)
	}
	return nil
}

func (c *Client) GetCertificateStatus(ctx context.Context, name, namespace string) (bool, error) {
	cert := &certmanagerv1.Certificate{}
	if err := c.Get(ctx, client.ObjectKey{Name: name, Namespace: namespace}, cert); err != nil {
		return false, err
	}

	for _, cond := range cert.Status.Conditions {
		if cond.Type == "Ready" && cond.Status == metav1.ConditionTrue {
			return true, nil
		}
	}
	return false, nil
}
