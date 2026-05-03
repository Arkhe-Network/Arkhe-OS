package metrics

import (
	"github.com/prometheus/client_golang/prometheus"
	"sigs.k8s.io/controller-runtime/pkg/metrics"
)

var (
	CertificateExpirySeconds = prometheus.NewGaugeVec(
		prometheus.GaugeOpts{
			Name: "arkhe_certificate_expiry_seconds",
			Help: "Seconds until certificate expiry for ARKHE services",
		},
		[]string{"service", "namespace"},
	)

	CertificateRotationsTotal = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "arkhe_certificate_rotations_total",
			Help: "Total number of certificate rotations performed",
		},
		[]string{"service", "namespace"},
	)

	LastRotationTimestamp = prometheus.NewGaugeVec(
		prometheus.GaugeOpts{
			Name: "arkhe_certificate_last_rotation_timestamp",
			Help: "Unix timestamp of last successful certificate rotation",
		},
		[]string{"service", "namespace"},
	)

	ReconcileErrorsTotal = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "arkhe_cert_operator_reconcile_errors_total",
			Help: "Total number of reconciliation errors",
		},
		[]string{"error_type"},
	)
)

func init() {
	metrics.Registry.MustRegister(
		CertificateExpirySeconds,
		CertificateRotationsTotal,
		LastRotationTimestamp,
		ReconcileErrorsTotal,
	)
}
