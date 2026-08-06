# Dockerfile for deterministic build
FROM python:3.11.9-slim-bookworm

RUN pip install --no-cache-dir \
    jax==0.4.38 jaxlib==0.4.38 numpyro==0.16.2 arviz==0.20.0 \
    numpy==1.26.4 scipy==1.14.1 nuitka==2.6.9 rpy2==3.5.17

COPY arkhe_inference_v3.py /app/
WORKDIR /app

RUN nuitka --standalone --onefile --windows-console-mode=disable \
    --output-dir=build arkhe_inference_v3.py

# Compute SHA‑256
RUN sha256sum build/arkhe_inference_v3.exe > arkhe_sha256.txt
