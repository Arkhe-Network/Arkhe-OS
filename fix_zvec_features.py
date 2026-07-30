import re
with open("substrates/t/16_2_zvec/cathedral_arkhe_v16_2_zvec.py", "r") as f:
    content = f.read()

content = content.replace(
'''
            # Define o esquema: Vetor Denso (Estado RSSM) + JSON (Ação/Recompensa) + Escalar (Importância)
            schema = zvec.CollectionSchema(fields=[
                zvec.FieldSchema("id", zvec.DataType.UINT64, is_primary=True),
                zvec.FieldSchema("rssm_state_vector", zvec.DataType.FLOAT_VECTOR, vector={
                    "dimension": state_dim,
                    "metric_type": zvec.MetricType.IP, # Inner Product (similaridade cosseno se normalizado)
                    "index_type": zvec.IndexType.HNSW,
                    "index_params": {"ef_construction": 200, "M": 16}
                }),
                zvec.FieldSchema("episode_data", zvec.DataType.JSON),
                zvec.FieldSchema("importance", zvec.DataType.FLOAT),
            ])
''',
'''
            # Define o esquema: Vetor Denso (Estado RSSM) + JSON (Ação/Recompensa) + Escalar (Importância)
            schema = zvec.CollectionSchema(fields=[
                zvec.FieldSchema("id", zvec.DataType.UINT64, is_primary=True),
                zvec.FieldSchema("rssm_state_vector", zvec.DataType.FLOAT_VECTOR, vector=dict(
                    dimension=state_dim,
                    metric_type=zvec.MetricType.IP, # Inner Product (similaridade cosseno se normalizado)
                    index_type=zvec.IndexType.HNSW,
                    index_params=dict(ef_construction=200, M=16)
                )),
                zvec.FieldSchema("sparse_vector", zvec.DataType.SPARSE_FLOAT_VECTOR),
                zvec.FieldSchema("episode_data", zvec.DataType.JSON),
                zvec.FieldSchema("importance", zvec.DataType.FLOAT),
            ])
''')

content = content.replace(
'''
    def store_transition(self, state_features: np.ndarray, action: np.ndarray,
                         reward: float, done: bool, importance: float = 1.0):
        """Persiste uma transição (s, a, r, s', done) no banco vetorial com WAL."""
        if not self.collection: return

        doc = zvec.Doc(
            id=self.next_id,
            values={
                "rssm_state_vector": state_features.tolist(),
                "episode_data": {
                    "action": action.tolist(),
                    "reward": reward,
                    "done": done,
                    "timestamp": time.time()
                },
                "importance": importance
            }
        )
        self.collection.insert([doc])
        self.next_id += 1

    def retrieve_similar_memories(self, query_state: np.ndarray, top_k: int = 5, min_importance: float = 0.5) -> List[Dict]:
        """
        Busca experiências passadas semanticamente semelhantes ao estado atual.
        Pode ser usado para Few-Shot Meta-Learning ou Análise de Risco.
        """
        if not self.collection: return []

        try:
            # Busca HNSW com filtro escalar (ex: ignorar memórias de baixa importância)
            results = self.collection.query(
                query_state.tolist(),
                top_k=top_k,
                expr="importance >= {0}".format(min_importance),
                params=dict(ef=50) # Parâmetro de busca HNSW
            )
''',
'''
    def store_transition(self, state_features: np.ndarray, sparse_features: Dict[str, float], action: np.ndarray,
                         reward: float, done: bool, importance: float = 1.0):
        """Persiste uma transição (s, a, r, s', done) no banco vetorial com WAL."""
        if not self.collection: return

        doc = zvec.Doc(
            id=self.next_id,
            values={
                "rssm_state_vector": state_features.tolist(),
                "sparse_vector": sparse_features,
                "episode_data": {
                    "action": action.tolist(),
                    "reward": reward,
                    "done": done,
                    "timestamp": time.time()
                },
                "importance": importance
            }
        )
        self.collection.insert([doc])
        self.next_id += 1

    def retrieve_similar_memories(self, query_state: np.ndarray, sparse_query: Dict[str, float], top_k: int = 5, min_importance: float = 0.5) -> List[Dict]:
        """
        Busca experiências passadas semanticamente semelhantes ao estado atual.
        Pode ser usado para Few-Shot Meta-Learning ou Análise de Risco.
        """
        if not self.collection: return []

        try:
            # Busca híbrida usando HNSW para denso e busca esparsa, com reranker RRF
            results = self.collection.hybrid_search(
                dense_vector=query_state.tolist(),
                sparse_vector=sparse_query,
                rerank=zvec.RRF(k=60),
                top_k=top_k,
                expr="importance >= {0}".format(min_importance),
                params=dict(ef=50) # Parâmetro de busca HNSW
            )
''')

content = content.replace(
'''
                # Persiste a experiência no banco de dados vetorial
                zvec_mem.store_transition(
                    state_features=latent_features,
                    action=action,
                    reward=reward,
                    done=timestep.last(),
                    importance=1.0 if is_safe else 0.1 # Memórias de violação têm menos importância
                )

            # 6. Busca Semântica de Memórias Similares (A cada 10 steps para não onerar)
            if step % 10 == 0 and zvec_mem.collection:
                similar_memories = zvec_mem.retrieve_similar_memories(latent_features, top_k=2)
''',
'''
                # Extrai as tags do YOLO para busca esparsa
                sparse_features = {}
                for ent in entities:
                    ent_id = ent.get("id", "")
                    if "_" in ent_id:
                        tag = ent_id.split("_")[0]
                        sparse_features[tag] = sparse_features.get(tag, 0.0) + 1.0

                # Persiste a experiência no banco de dados vetorial
                zvec_mem.store_transition(
                    state_features=latent_features,
                    sparse_features=sparse_features,
                    action=action,
                    reward=reward,
                    done=timestep.last(),
                    importance=1.0 if is_safe else 0.1 # Memórias de violação têm menos importância
                )

            # 6. Busca Semântica de Memórias Similares (A cada 10 steps para não onerar)
            if step % 10 == 0 and zvec_mem.collection:
                sparse_query = {}
                for ent in entities:
                    ent_id = ent.get("id", "")
                    if "_" in ent_id:
                        tag = ent_id.split("_")[0]
                        sparse_query[tag] = sparse_query.get(tag, 0.0) + 1.0

                similar_memories = zvec_mem.retrieve_similar_memories(latent_features, sparse_query, top_k=2)
''')

with open("substrates/t/16_2_zvec/cathedral_arkhe_v16_2_zvec.py", "w") as f:
    f.write(content)
