#!/usr/bin/env bash
# Generate Go protobuf stubs.
# Requires: protoc, protoc-gen-go, protoc-gen-go-grpc
set -euo pipefail

PROTO_DIR="$(dirname "$0")"
OUT_DIR="$PROTO_DIR/api"

mkdir -p "$OUT_DIR"

protoc \
  --proto_path="$PROTO_DIR" \
  --go_out="$OUT_DIR" \
  --go_opt=paths=source_relative \
  --go-grpc_out="$OUT_DIR" \
  --go-grpc_opt=paths=source_relative \
  "$PROTO_DIR/oracle.proto"
