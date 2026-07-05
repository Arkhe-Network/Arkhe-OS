# syntax=docker/dockerfile:1
# ARKHE ASI multi-stage runtime image.

FROM --platform=$BUILDPLATFORM rust:1-bookworm AS rust-builder

WORKDIR /src
COPY arkhe-sqlite-canonical/ arkhe-sqlite-canonical/
RUN cargo build --release --manifest-path arkhe-sqlite-canonical/Cargo.toml

FROM --platform=$BUILDPLATFORM python:3.12-slim AS package-builder

WORKDIR /src
COPY build/ build/
COPY tests/ tests/
COPY substrate_248/ substrate_248/
COPY arkhe-sqlite-canonical/ arkhe-sqlite-canonical/
COPY --from=rust-builder /src/arkhe-sqlite-canonical/target/release/arkhe-sqlite-canonical /tmp/arkhe-sqlite-canonical
RUN python build/arkhe_build.py inventory \
    && python build/arkhe_build.py package-grammars \
    && python build/arkhe_build.py package --platform linux-container \
    && mkdir -p dist/package-root/bin /src/out \
    && cp /tmp/arkhe-sqlite-canonical dist/package-root/bin/ \
    && cp -a dist/package-root/. /src/out/

FROM debian:bookworm-slim AS runtime

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates python3 libsqlite3-0 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=package-builder /src/out/ /opt/arkhe/
COPY substrate_248/ /opt/arkhe/substrate_248/

ENV ARKHE_HOME=/opt/arkhe
EXPOSE 5000 8080 9108

ENTRYPOINT ["/opt/arkhe/bin/arkhe-sqlite-canonical"]
CMD ["/var/lib/arkhe/arkhe-canonical.db", "container", "{}"]
