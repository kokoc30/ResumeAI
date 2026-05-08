import pytest

from app import embeddings
from app.embeddings import embed_texts, embed_text


def test_resolve_embedding_device_auto_uses_cpu_when_cuda_unavailable(monkeypatch):
    monkeypatch.setattr(embeddings.settings, "embedding_device", "auto")
    monkeypatch.setattr(embeddings.torch.cuda, "is_available", lambda: False)

    assert embeddings.resolve_embedding_device() == "cpu"


def test_resolve_embedding_device_cpu_override(monkeypatch):
    monkeypatch.setattr(embeddings.settings, "embedding_device", "cpu")
    monkeypatch.setattr(embeddings.torch.cuda, "is_available", lambda: True)

    assert embeddings.resolve_embedding_device() == "cpu"


def test_resolve_embedding_device_auto_does_not_crash(monkeypatch):
    monkeypatch.setattr(embeddings.settings, "embedding_device", "auto")

    assert embeddings.resolve_embedding_device() in {"cpu", "cuda"}


def test_resolve_embedding_device_cuda_falls_back_when_unavailable(monkeypatch):
    monkeypatch.setattr(embeddings.settings, "embedding_device", "cuda")
    monkeypatch.setattr(embeddings.torch.cuda, "is_available", lambda: False)

    assert embeddings.resolve_embedding_device() == "cpu"


def test_embed_texts_empty_list():
    with pytest.raises(ValueError, match="The texts list cannot be empty."):
        embed_texts([])

def test_embed_texts_blank_string():
    with pytest.raises(ValueError, match="Text items cannot be empty or blank."):
        embed_texts(["valid text", "   "])

def test_embed_text_blank_string():
    with pytest.raises(ValueError, match="Text items cannot be empty or blank."):
        embed_text("")

@pytest.mark.integration
def test_embed_texts_generation():
    texts = ["hello world", "fastapi backend"]
    embeddings = embed_texts(texts)
    
    assert isinstance(embeddings, list)
    assert len(embeddings) == 2
    assert isinstance(embeddings[0], list)
    assert isinstance(embeddings[0][0], float)
    assert len(embeddings[0]) > 0
