package keystore

import (
	"bytes"
	"crypto/rand"
	"crypto/rsa"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/pem"
	"fmt"
	"math/big"
	"time"

	"software.sslmate.com/src/go-pkcs12"
)

// GeneratePKCS12 creates a PKCS12 keystore from certificate and private key
func GeneratePKCS12(certPEM, keyPEM []byte, alias string, password []byte) ([]byte, error) {
	certBlock, _ := pem.Decode(certPEM)
	if certBlock == nil {
		return nil, fmt.Errorf("failed to decode certificate PEM")
	}
	cert, err := x509.ParseCertificate(certBlock.Bytes)
	if err != nil {
		return nil, fmt.Errorf("failed to parse certificate: %w", err)
	}

	keyBlock, _ := pem.Decode(keyPEM)
	if keyBlock == nil {
		return nil, fmt.Errorf("failed to decode private key PEM")
	}
	privateKey, err := x509.ParsePKCS1PrivateKey(keyBlock.Bytes)
	if err != nil {
		pk, err2 := x509.ParsePKCS8PrivateKey(keyBlock.Bytes)
		if err2 != nil {
			return nil, fmt.Errorf("failed to parse private key: %w", err)
		}
		var ok bool
		privateKey, ok = pk.(*rsa.PrivateKey)
		if !ok {
			return nil, fmt.Errorf("unsupported private key type")
		}
	}

	bundle, err := pkcs12.Encode(rand.Reader, privateKey, cert, nil, string(password))
	if err != nil {
		return nil, fmt.Errorf("failed to encode PKCS12: %w", err)
	}

	return bundle, nil
}

// GenerateTruststorePKCS12 creates a truststore containing CA certificates
func GenerateTruststorePKCS12(caCertPEM []byte, password []byte) ([]byte, error) {
	caBlock, _ := pem.Decode(caCertPEM)
	if caBlock == nil {
		return nil, fmt.Errorf("failed to decode CA certificate PEM")
	}
	caCert, err := x509.ParseCertificate(caBlock.Bytes)
	if err != nil {
		return nil, fmt.Errorf("failed to parse CA certificate: %w", err)
	}

	dummyKey, err := rsa.GenerateKey(rand.Reader, 2048)
	if err != nil {
		return nil, err
	}
	dummyCert := &x509.Certificate{
		SerialNumber: big.NewInt(1),
		Subject: pkix.Name{
			CommonName: "arkhe-truststore-dummy",
		},
		NotBefore:             time.Now(),
		NotAfter:              time.Now().Add(24 * time.Hour),
		KeyUsage:              x509.KeyUsageDigitalSignature,
		ExtKeyUsage:           []x509.ExtKeyUsage{x509.ExtKeyUsageServerAuth},
		BasicConstraintsValid: true,
	}
	dummyCertDER, err := x509.CreateCertificate(rand.Reader, dummyCert, dummyCert, &dummyKey.PublicKey, dummyKey)
	if err != nil {
		return nil, err
	}
	dummyCertParsed, err := x509.ParseCertificate(dummyCertDER)
	if err != nil {
		return nil, err
	}

	truststore, err := pkcs12.EncodeTrustStore(rand.Reader, []*x509.Certificate{caCert}, string(password))
	if err != nil {
		return pkcs12.Encode(rand.Reader, dummyKey, dummyCertParsed, []*x509.Certificate{caCert}, string(password))
	}

	return truststore, nil
}
