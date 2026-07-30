import re
with open("substrates/t/16_2_zvec/cathedral_arkhe_v16_2_zvec.py", "r") as f:
    content = f.read()

content = content.replace(
'''
class RustBridgeStub:
    async def hnsw_search(self, vector, k=5): return [] # HNSW agora é gerenciado pelo zVEC
    async def close(self): pass
''',
'''
# NOTA: O Data Plane Rust usa zvec-bindings
if HAS_GRPC:
    try:
        import arkhe_pb2
        import arkhe_pb2_grpc
        HAS_PROTO = True
    except ImportError:
        HAS_PROTO = False

class RustBridgeGRPC:
    """Cliente gRPC real para o Data Plane Rust (libarkhe_data.so)."""
    def __init__(self, target: str = "localhost:50051"):
        if not HAS_GRPC or not HAS_PROTO:
            raise ImportError("grpcio e/ou arkhe_pb2 não encontrados.")
        self.channel = grpc.aio.insecure_channel(target, options=[('grpc.max_receive_message_length', 4 * 1024 * 1024)])
        self.stub = arkhe_pb2_grpc.CognitiveDataPlaneStub(self.channel)
        log.info("RustBridge gRPC conectado a {0}".format(target))

    async def hnsw_search(self, vector: List[float], k: int = 5) -> List[Dict]:
        """Busca vetorial no HNSW do Rust via zvec-bindings."""
        try:
            request = arkhe_pb2.SearchRequest(vector=vector, k=k)
            response = await self.stub.SearchHNSW(request)
            return [{"id": r.id, "distance": r.distance, "metadata": dict(r.metadata)} for r in response.results]
        except grpc.aio.AioRpcError as e:
            log.error("gRPC HNSW Error: {0}".format(e.code()))
            return []

    async def dvfs_control_rust(self, target_freq_mhz: float) -> bool:
        """Delega controle de DVFS para o Rust (se aplicável)."""
        try:
            request = arkhe_pb2.DVFSRequest(target_freq_mhz=target_freq_mhz)
            response = await self.stub.SetDVFS(request)
            return response.success
        except Exception as e:
            return False

    async def close(self):
        await self.channel.close()

class RustBridgeStub:
    async def hnsw_search(self, vector, k=5): return [] # HNSW agora é gerenciado pelo zVEC
    async def close(self): pass
''')

content = content.replace(
'''
        self.detector = YOLODetector()
        self.rust_bridge = RustBridgeStub()
        self.zvec_memory = zvec_memory # NOVA INTEGRAÇÃO
''',
'''
        self.detector = YOLODetector()
        try:
            self.rust_bridge = RustBridgeGRPC("localhost:50051")
        except:
            log.warning("Usando RustBridgeStub pois gRPC/Protos não estão disponíveis.")
            self.rust_bridge = RustBridgeStub()
        self.zvec_memory = zvec_memory # NOVA INTEGRAÇÃO
''')

with open("substrates/t/16_2_zvec/cathedral_arkhe_v16_2_zvec.py", "w") as f:
    f.write(content)
