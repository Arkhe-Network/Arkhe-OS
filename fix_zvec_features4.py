import re
with open("substrates/t/16_2_zvec/cathedral_arkhe_v16_2_zvec.py", "r") as f:
    content = f.read()

content = content.replace(
'''
                # Substitui a chamada local do zVEC pela chamada ao Data Plane Rust via gRPC (zvec-bindings)
                try:
                    similar_memories = await orch.rust_bridge.hybrid_search(latent_features.tolist(), sparse_query, k=2)
                except Exception:
                    # Fallback para o in-process Python se o gRPC falhar
                    similar_memories = zvec_mem.retrieve_similar_memories(latent_features, sparse_query, top_k=2)
''',
'''
                # Substitui a chamada local do zVEC pela chamada ao Data Plane Rust via gRPC (zvec-bindings)
                try:
                    similar_memories = await orch.rust_bridge.hybrid_search(latent_features.tolist(), sparse_query, k=2)
                except Exception:
                    similar_memories = []

                # Se falhou ou gRPC não retornou (retornou []), fallback para in-process Python
                if not similar_memories:
                    similar_memories = zvec_mem.retrieve_similar_memories(latent_features, sparse_query, top_k=2)
''')

with open("substrates/t/16_2_zvec/cathedral_arkhe_v16_2_zvec.py", "w") as f:
    f.write(content)
