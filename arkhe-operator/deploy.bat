@echo off
REM Arkhe(n) Operator Deployment Script for Windows
REM Run this from the arkhe-operator directory

echo ========================================
echo  ARKHE(N) OPERATOR DEPLOYMENT
echo ========================================
echo.

set NAMESPACE=arkhe-quantum
set IMG=arkhe/arkhe-operator:latest

echo [1/8] Creating namespace...
kubectl create namespace %NAMESPACE% --dry-run=client -o yaml | kubectl apply -f -
if errorlevel 1 goto :error

echo.
echo [2/8] Applying v1beta1 CRDs and resources...
kubectl apply -f deploy\arkhe-crds-v1beta1.yaml
if errorlevel 1 goto :error

echo.
echo [3/8] Verifying CRDs...
kubectl get crds | findstr arkhe.io

echo.
echo [4/8] Checking custom resources...
kubectl get thermalengines,thetarhythms,gkpatoms,polaritonbatteries,ioqtdevices,quantumneuralnetworks,postquantumcryptos -n %NAMESPACE%

echo.
echo [5/8] Applying RBAC...
kubectl apply -f config\rbac\role.yaml
kubectl apply -f config\rbac\auth.yaml

echo.
echo [6/8] Building operator image...
docker build -t "%IMG%" . 2>nul
if errorlevel 1 (
    echo Docker build skipped
)

echo.
echo [7/8] Applying deployment...
if exist config\manager\deployment.yaml (
    kubectl apply -f config\manager\deployment.yaml
)

echo.
echo [8/8] Running operator...
go run main.go
if errorlevel 1 (
    echo Go run skipped (kind cluster may not be available)
)

echo.
echo ========================================
echo  DEPLOYMENT SUMMARY
echo ========================================
echo.
echo Namespaces:
kubectl get namespaces | findstr arkhe

echo.
echo CRDs installed:
kubectl get crds | findstr arkhe

echo.
echo Custom Resources:
kubectl get thermalengines,thetarhythms,gkpatoms,polaritonbatteries,ioqtdevices,quantumneuralnetworks,postquantumcryptos -n %NAMESPACE%

echo.
echo Standard Resources:
kubectl get pods,deployments,services -n %NAMESPACE%

echo.
echo ========================================
echo  The time is the value.
echo  The coherence is the proof.
echo ========================================
goto :end

:error
echo.
echo ========================================
echo  ERROR: Deployment failed!
echo ========================================
exit /b 1

:end
