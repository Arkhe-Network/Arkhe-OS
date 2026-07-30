import onnxruntime as ort
import numpy as np

class WindowsDirectMLBackend:
    """Inferência via DirectML — funciona em qualquer GPU DirectX 12."""

    def __init__(self, model_path: str):
        # DirectML funciona com NVIDIA, AMD, Intel
        self.session = ort.InferenceSession(
            model_path,
            providers=['DmlExecutionProvider', 'CPUExecutionProvider']
        )
        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name

    def infer(self, input_data: np.ndarray) -> np.ndarray:
        results = self.session.run([self.output_name], {self.input_name: input_data})
        return results[0]
