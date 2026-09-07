from openclaw_mesh.engines import (
    AutoModelManager,
    DistributedMoEOrchestrator,
    DistributedRAG,
    DistributedVectorStore,
    HardwareDetector,
    ModelCache,
    SemanticKVCache,
    UniversalEmbeddingEngine,
    UniversalInferenceEngine,
)


def test_hardware_detection():
    status = HardwareDetector.detect()
    assert status.available is True
    assert status.backend.value in {"cpu", "cuda", "rocm", "openvino", "mlx"}


def test_inference_and_embedding_engine():
    engine = UniversalInferenceEngine(model_name="demo-model")
    result = engine.generate("hello")
    assert "hello" in result["text"] or "stub response" in result["text"]

    emb = UniversalEmbeddingEngine()
    assert len(emb.encode("abc")) == 3


def test_model_cache_and_kv_cache():
    cache = ModelCache(max_size=2)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)
    assert "a" not in cache._cache

    kv = SemanticKVCache(max_entries=2)
    kv.set("x", {"n": 1})
    assert kv.get("x") == {"n": 1}


def test_distributed_components():
    moe = DistributedMoEOrchestrator()
    assert len(moe.route("hi")["experts"]) >= 1

    vect = DistributedVectorStore()
    vect.add("doc-1", [0.1, 0.2])
    assert vect.search([0.1, 0.2], k=1) == ["doc-1"]

    rag = DistributedRAG()
    rag.add("The mesh is healthy")
    assert rag.query("mesh")

    manager = AutoModelManager(allowlist=["demo-model", "other-model"])
    assert manager.select_model("other-model") == "other-model"
