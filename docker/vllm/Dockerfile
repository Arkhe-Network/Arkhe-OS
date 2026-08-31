FROM vllm/vllm-openai:latest

# Modelos suportados (baixados em runtime ou montados via volume)
ENV MODEL_NAME=meta-llama/Llama-4-70B-Instruct
ENV TENSOR_PARALLEL_SIZE=4
ENV GPU_MEMORY_UTILIZATION=0.90
ENV MAX_MODEL_LEN=32768

EXPOSE 8000

CMD ["--model", "$MODEL_NAME", \
     "--tensor-parallel-size", "$TENSOR_PARALLEL_SIZE", \
     "--gpu-memory-utilization", "$GPU_MEMORY_UTILIZATION", \
     "--max-model-len", "$MAX_MODEL_LEN", \
     "--trust-remote-code", \
     "--enable-lora", \
     "--max-loras", "4", \
     "--max-cpu-loras", "8"]
