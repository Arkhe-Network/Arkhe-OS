"""
Cathedral ARKHE v17.0 - Benchmark Suite
Reproduz os testes do Section 8 do guia.
"""
import asyncio
import time
import logging
import numpy as np
from pathlib import Path

logging.basicConfig(level=logging.WARNING)

from v17.config_loader import CathedralConfig
from v17.fast_brain import FastBrain, VisionModule, WorldModelRSSM, SafetyEngineZ3, EpisodicMemoryHNSW, MetaLearningModule

def benchmark_vision():
    print("=" * 60)
    print("BENCHMARK: Vision Module (YOLOv8-Nano)")
    print("=" * 60)

    vision = VisionModule("yolov8n", "cuda", 0.5)
    dummy_frame = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)

    # Warmup
    for _ in range(3):
        vision.process(dummy_frame)

    # Batch 1
    times = []
    for _ in range(100):
        t0 = time.perf_counter()
        vision.process(dummy_frame)
        times.append((time.perf_counter() - t0) * 1000)

    print("  Batch=1:  {0:.2f}ms avg, {1:.0f} Hz".format(np.mean(times), 1000/np.mean(times)))

    # Batch 4
    if vision.model:
        frames = [dummy_frame] * 4
        times4 = []
        for _ in range(50):
            t0 = time.perf_counter()
            for f in frames:
                vision.process(f)
            times4.append((time.perf_counter() - t0) * 1000)
        print("  Batch=4:  {0:.2f}ms avg, {1:.0f} Hz total".format(np.mean(times4), 4000/np.mean(times4)))

    print()


def benchmark_world_model():
    print("=" * 60)
    print("BENCHMARK: World Model (RSSM)")
    print("=" * 60)

    wm = WorldModelRSSM(256, 32, 256, "cpu")
    features = np.random.randn(256).astype(np.float32)
    action = np.random.randn(4).astype(np.float32)

    # Warmup
    for _ in range(10):
        wm.step(features, action)

    times = []
    for _ in range(1000):
        t0 = time.perf_counter()
        wm.step(features, action)
        times.append((time.perf_counter() - t0) * 1000)

    print("  1 step:   {0:.1f}µs avg, {1:.0f} Hz".format(np.mean(times)*1000, 1000/np.mean(times)))
    print()


def benchmark_safety():
    print("=" * 60)
    print("BENCHMARK: Safety Engine (Z3)")
    print("=" * 60)

    safety = SafetyEngineZ3(10.0, ["humano", "animal", "objeto_fragil"])
    action = np.array([0.5, 0.3, 0.1, 0.0], dtype=np.float32)

    # Regras simples
    times_simple = []
    for _ in range(1000):
        t0 = time.perf_counter()
        safety.check(action, [])
        times_simple.append((time.perf_counter() - t0) * 1000)
    print("  Simples:  {0:.2f}ms avg, {1:.0f} Hz".format(np.mean(times_simple), 1000/np.mean(times_simple)))

    # Regras complexas (com detecções)
    detections = [dict(cls=0, confidence=0.9, xyxy=[100, 100, 200, 200])]
    action_unsafe = np.array([5.0, 3.0, 0.0, 0.0], dtype=np.float32)
    times_complex = []
    for _ in range(100):
        t0 = time.perf_counter()
        safety.check(action_unsafe, detections)
        times_complex.append((time.perf_counter() - t0) * 1000)
    print("  Complexo: {0:.2f}ms avg, {1:.0f} Hz".format(np.mean(times_complex), 1000/np.mean(times_complex)))
    print()


def benchmark_memory():
    print("=" * 60)
    print("BENCHMARK: Episodic Memory (HNSW)")
    print("=" * 60)

    mem = EpisodicMemoryHNSW(dim=288, data_dir="zvec_data/bench_temp")

    # Popula com 10k vetores
    print("  Populando 10.000 memórias...")
    t0 = time.perf_counter()
    for i in range(10000):
        vec = np.random.randn(288).astype(np.float32)
        mem.store(vec, {"step": i, "label": "mem_{0}".format(i)})
    populate_time = time.perf_counter() - t0
    print("  População: {0:.2f}s ({1:.0f} mem/s)".format(populate_time, 10000/populate_time))

    # Retrieval
    query = np.random.randn(288).astype(np.float32)
    times = []
    for _ in range(1000):
        t0 = time.perf_counter()
        mem.retrieve(query, top_k=5)
        times.append((time.perf_counter() - t0) * 1000)
    print("  Retrieval: {0:.2f}ms avg, {1:.0f} Hz".format(np.mean(times), 1000/np.mean(times)))
    print()


def benchmark_full_cycle():
    print("=" * 60)
    print("BENCHMARK: Full Fast Brain Cycle")
    print("=" * 60)

    config = CathedralConfig()
    fb = FastBrain(config)

    # Warmup
    for _ in range(5):
        fb.cycle()

    times = []
    for _ in range(100):
        t0 = time.perf_counter()
        fb.cycle()
        times.append((time.perf_counter() - t0) * 1000)

    mean_ms = np.mean(times)
    freq = 1000 / mean_ms
    target_pass = mean_ms < 5.0

    print("  Média:    {0:.2f}ms".format(mean_ms))
    print("  Min:      {0:.2f}ms".format(np.min(times)))
    print("  Max:      {0:.2f}ms".format(np.max(times)))
    print("  P99:      {0:.2f}ms".format(np.percentile(times, 99)))
    print("  Freq:     {0:.0f} Hz".format(freq))
    print("  Alvo:     < 5ms, > 100 Hz  ->  {0}".format('✅ PASS' if target_pass else '❌ FAIL'))
    print()


async def benchmark_slow_brain():
    print("=" * 60)
    print("BENCHMARK: Slow Brain (SGLang)")
    print("=" * 60)

    config = CathedralConfig()
    from v17.slow_brain import SlowBrainSGLang
    sb = SlowBrainSGLang(config)

    healthy = await sb.health_check()
    if not healthy:
        print("  ❌ SGLang offline — pulando benchmark do Slow Brain")
        print("  Inicie o SGLang no WSL2 e rode novamente.")
        print()
        return

    prompts = [
        ("Simples", "O robô deve seguir em frente.", 512),
        ("RAG", "Contexto com 5 memórias episódicas recuperadas do zVEC.", 2048),
        ("Complexo", "Dilema: copo de vidro + humano à frente + baixa confiança do Fast Brain.", 4096),
    ]

    for name, prompt, _ in prompts:
        times = []
        for _ in range(3):
            t0 = time.perf_counter()
            await sb.reason(dilemma=prompt)
            times.append((time.perf_counter() - t0) * 1000)
        print("  {0:12s}: {1:.0f}ms avg".format(name, np.mean(times)))

    print()


def benchmark_router():
    print("=" * 60)
    print("BENCHMARK: Router Decisions")
    print("=" * 60)

    config = CathedralConfig()
    from v17.orchestrator_v17 import Router
    from v17.fast_brain import FastBrainState

    router = Router(config)

    scenarios = [
        ("Corredor limpo", 0.8, True, []),
        ("Copo de vidro", 0.2, False, []),
        ("Baixa confiança", 0.1, True, []),
    ]

    for name, conf, safety, mems in scenarios:
        state = FastBrainState(
            confidence=conf,
            safety_approved=safety,
            zvec_memories=mems,
            action=np.zeros(4),
        )
        times = []
        for _ in range(1000):
            t0 = time.perf_counter()
            route = router.decide(state)
            times.append((time.perf_counter() - t0) * 1000)
        print("  {0:20s}: route={1:5s}, {2:.0f}µs avg".format(name, route, np.mean(times)))

    print()


def print_hardware_info():
    print("=" * 60)
    print("HARDWARE INFO")
    print("=" * 60)
    import torch
    import psutil

    if torch.cuda.is_available():
        props = torch.cuda.get_device_properties(0)
        print("  GPU: {0}".format(props.name))
        print("  VRAM: {0:.1f} GB".format(props.total_mem / 1024**3))
        print("  Compute: sm_{0}{1}".format(props.major, props.minor))
    else:
        print("  GPU: N/A (CUDA não disponível)")

    print("  RAM: {0:.0f} GB".format(psutil.virtual_memory().total / 1024**3))
    print("  CPU: {0} cores / {1} threads".format(psutil.cpu_count(logical=False), psutil.cpu_count()))
    print("  PyTorch: {0}".format(torch.__version__))
    print()


if __name__ == "__main__":
    print_hardware_info()
    benchmark_vision()
    benchmark_world_model()
    benchmark_safety()
    benchmark_memory()
    benchmark_full_cycle()
    benchmark_router()
    asyncio.run(benchmark_slow_brain())

    print("=" * 60)
    print("BENCHMARKS COMPLETOS")
    print("=" * 60)
