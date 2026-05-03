package main

import (
	"flag"
	"fmt"
	"os"

	"k8s.io/apimachinery/pkg/runtime"
	utilruntime "k8s.io/apimachinery/pkg/util/runtime"
	clientgoscheme "k8s.io/client-go/kubernetes/scheme"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/healthz"
	"sigs.k8s.io/controller-runtime/pkg/log/zap"

	arkhev1alpha1 "github.com/arkhe-n/arkhe-operator/api/v1alpha1"
	arkhev1beta1 "github.com/arkhe-n/arkhe-operator/api/v1beta1"
	"github.com/arkhe-n/arkhe-operator/controllers"
	v1beta1controllers "github.com/arkhe-n/arkhe-operator/controllers/v1beta1"
)

var (
	scheme   = runtime.NewScheme()
	setupLog = ctrl.Log.WithName("setup")
)

func init() {
	utilruntime.Must(clientgoscheme.AddToScheme(scheme))
	utilruntime.Must(arkhev1alpha1.AddToScheme(scheme))
	utilruntime.Must(arkhev1beta1.AddToScheme(scheme))
}

func main() {
	var enableLeaderElection bool
	var probeAddr string

	flag.StringVar(&probeAddr, "health-probe-addr", ":8081", "Address for health probe server")
	flag.BoolVar(&enableLeaderElection, "leader-elect", false,
		"Enable leader election for controller manager")

	opts := zap.Options{
		Development: true,
	}
	opts.BindFlags(flag.CommandLine)
	flag.Parse()

	ctrl.SetLogger(zap.New(zap.UseFlagOptions(&opts)))

	mgr, err := ctrl.NewManager(ctrl.GetConfigOrDie(), ctrl.Options{
		Scheme:                 scheme,
		HealthProbeBindAddress: probeAddr,
		LeaderElection:         enableLeaderElection,
		LeaderElectionID:       "arkhe-operator-lock",
	})
	if err != nil {
		setupLog.Error(err, "Unable to start manager")
		os.Exit(1)
	}

	if err = (&controllers.EraReconciler{
		Client: mgr.GetClient(),
		Scheme: mgr.GetScheme(),
	}).SetupWithManager(mgr); err != nil {
		setupLog.Error(err, "Unable to create controller", "controller", "Era")
		os.Exit(1)
	}

	if err = (&controllers.TzinorReconciler{
		Client: mgr.GetClient(),
		Scheme: mgr.GetScheme(),
	}).SetupWithManager(mgr); err != nil {
		setupLog.Error(err, "Unable to create controller", "controller", "Tzinor")
		os.Exit(1)
	}

	if err = (&controllers.VerCoreReconciler{
		Client: mgr.GetClient(),
		Scheme: mgr.GetScheme(),
	}).SetupWithManager(mgr); err != nil {
		setupLog.Error(err, "Unable to create controller", "controller", "VerCore")
		os.Exit(1)
	}

	if err = (&controllers.EntropyShieldReconciler{
		Client: mgr.GetClient(),
		Scheme: mgr.GetScheme(),
	}).SetupWithManager(mgr); err != nil {
		setupLog.Error(err, "Unable to create controller", "controller", "EntropyShield")
		os.Exit(1)
	}

	if err = (&controllers.LambdaTReconciler{
		Client: mgr.GetClient(),
		Scheme: mgr.GetScheme(),
	}).SetupWithManager(mgr); err != nil {
		setupLog.Error(err, "Unable to create controller", "controller", "LambdaT")
		os.Exit(1)
	}

	if err = (&v1beta1controllers.GKPAtomReconciler{
		Client: mgr.GetClient(),
		Scheme: mgr.GetScheme(),
	}).SetupWithManager(mgr); err != nil {
		setupLog.Error(err, "Unable to create controller", "controller", "GKPAtom")
		os.Exit(1)
	}

	if err = (&v1beta1controllers.ThermalEngineReconciler{
		Client: mgr.GetClient(),
		Scheme: mgr.GetScheme(),
	}).SetupWithManager(mgr); err != nil {
		setupLog.Error(err, "Unable to create controller", "controller", "ThermalEngine")
		os.Exit(1)
	}

	if err = (&v1beta1controllers.ThetaRhythmReconciler{
		Client: mgr.GetClient(),
		Scheme: mgr.GetScheme(),
	}).SetupWithManager(mgr); err != nil {
		setupLog.Error(err, "Unable to create controller", "controller", "ThetaRhythm")
		os.Exit(1)
	}

	if err = (&v1beta1controllers.PolaritonBatteryReconciler{
		Client: mgr.GetClient(),
		Scheme: mgr.GetScheme(),
	}).SetupWithManager(mgr); err != nil {
		setupLog.Error(err, "Unable to create controller", "controller", "PolaritonBattery")
		os.Exit(1)
	}

	if err = (&v1beta1controllers.PostQuantumCryptoReconciler{
		Client: mgr.GetClient(),
		Scheme: mgr.GetScheme(),
	}).SetupWithManager(mgr); err != nil {
		setupLog.Error(err, "Unable to create controller", "controller", "PostQuantumCrypto")
		os.Exit(1)
	}

	if err := mgr.AddHealthzCheck("healthz", healthz.Ping); err != nil {
		setupLog.Error(err, "Unable to set up health check")
		os.Exit(1)
	}

	if err := mgr.AddReadyzCheck("readyz", healthz.Ping); err != nil {
		setupLog.Error(err, "Unable to set up ready check")
		os.Exit(1)
	}

	setupLog.Info("Starting Arkhe(n) Operator")
	setupLog.Info(fmt.Sprintf("Phase domain: ℂ (continuous, coherent)"))
	setupLog.Info(fmt.Sprintf("Structure domain: ℤ (discrete, entropic)"))

	if err := mgr.Start(ctrl.SetupSignalHandler()); err != nil {
		setupLog.Error(err, "Problem running manager")
		os.Exit(1)
	}
}
