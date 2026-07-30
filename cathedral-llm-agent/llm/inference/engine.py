from vllm import LLM, SamplingParams

class CathedralLLMEngine:
    def __init__(self, model_path: str):
        self.llm = LLM(model=model_path, tensor_parallel_size=1)

    async def chat(self, messages, temperature=0.7, max_tokens=1024):
        prompt = "\n".join(["{role}: {content}".format(role=m['role'], content=m['content']) for m in messages])
        sampling = SamplingParams(temperature=temperature, max_tokens=max_tokens)
        outputs = self.llm.generate([prompt], sampling)
        return outputs[0].outputs[0].text

def get_engine():
    # Stub function since server/main.py calls get_engine()
    return CathedralLLMEngine(model_path="dummy")
