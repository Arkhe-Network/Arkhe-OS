# Build stage
FROM golang:1.24-alpine AS builder

WORKDIR /workspace

# Copy go mod files
COPY go.mod go.sum ./
RUN go mod download

# Copy source code
COPY . .

# Build the operator
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -a -o manager main.go

# Final stage
FROM gcr.io/distroless/static:nonroot

WORKDIR /

# Copy manager binary
COPY --from=builder /workspace/manager .

# Copy webhook certificates (if needed)
# COPY certs/ /certs/

# Set non-root user
USER nonroot:nonroot

# Expose metrics and health ports
EXPOSE 8080 8081

# Set entrypoint
ENTRYPOINT ["/manager"]
