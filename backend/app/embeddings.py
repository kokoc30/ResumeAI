"""Local sentence-transformers embedding helpers."""

import logging

import torch
from sentence_transformers import SentenceTransformer

from app.config import settings


logger = logging.getLogger("uvicorn.error")

_MODEL: SentenceTransformer | None = None
_MODEL_DEVICE: str | None = None
_MODEL_NAME: str | None = None


def is_cuda_available() -> bool:
    """Return whether PyTorch can use CUDA on this machine."""
    return bool(torch.cuda.is_available())


def resolve_embedding_device() -> str:
    """Choose the embedding device from settings and CUDA availability."""
    requested_device = settings.embedding_device.strip().lower()

    if requested_device == "auto":
        return "cuda" if is_cuda_available() else "cpu"

    if requested_device == "cpu":
        return "cpu"

    if requested_device == "cuda":
        if is_cuda_available():
            return "cuda"

        logger.warning(
            "EMBEDDING_DEVICE=cuda was requested, but CUDA is not available. "
            "Falling back to CPU."
        )
        return "cpu"

    logger.warning(
        "Unsupported EMBEDDING_DEVICE=%r. Expected auto, cuda, or cpu. "
        "Using auto device selection.",
        settings.embedding_device,
    )
    return "cuda" if is_cuda_available() else "cpu"


def get_embedding_model() -> SentenceTransformer:
    """Load and cache the sentence-transformers model on the selected device."""
    global _MODEL, _MODEL_DEVICE, _MODEL_NAME

    selected_device = resolve_embedding_device()
    selected_model_name = settings.embedding_model_name

    if (
        _MODEL is None
        or _MODEL_DEVICE != selected_device
        or _MODEL_NAME != selected_model_name
    ):
        logger.info(
            "Loading embedding model '%s' on device '%s'.",
            selected_model_name,
            selected_device,
        )
        _MODEL = SentenceTransformer(selected_model_name, device=selected_device)
        _MODEL_DEVICE = selected_device
        _MODEL_NAME = selected_model_name
        logger.info(
            "Embedding model ready: model=%s, device=%s, cuda_available=%s.",
            _MODEL_NAME,
            _MODEL_DEVICE,
            is_cuda_available(),
        )

    return _MODEL


def get_embedding_device() -> str:
    """Return the active embedding device, resolving it if the model is not loaded."""
    return _MODEL_DEVICE or resolve_embedding_device()


def warmup_embedding_model() -> None:
    """Load the embedding model and run a tiny encode call at startup."""
    model = get_embedding_model()
    model.encode(
        ["warmup"],
        batch_size=1,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    logger.info("Embedding model warmup completed on device '%s'.", get_embedding_device())


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a list of text strings."""
    if not texts:
        raise ValueError("The texts list cannot be empty.")

    for text in texts:
        if not text or not text.strip():
            raise ValueError("Text items cannot be empty or blank.")

    model = get_embedding_model()
    embeddings = model.encode(
        texts,
        batch_size=settings.embedding_batch_size,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    return embeddings.tolist()


def embed_text(text: str) -> list[float]:
    """Generate an embedding for a single text string."""
    return embed_texts([text])[0]
