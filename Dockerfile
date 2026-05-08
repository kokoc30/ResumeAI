FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    EMBEDDING_DEVICE=cpu \
    HF_HOME=/app/.cache/huggingface

WORKDIR /app

# Install Python deps. CPU-only torch is forced via --extra-index-url plus
# backend/constraints-cpu.txt so sentence-transformers reuses it instead of
# pulling the CUDA wheel from the default PyPI index.
COPY backend/requirements.txt backend/constraints-cpu.txt /app/backend/
RUN pip install --no-cache-dir \
      --extra-index-url https://download.pytorch.org/whl/cpu \
      -c /app/backend/constraints-cpu.txt \
      -r /app/backend/requirements.txt

# Fail the build if a CUDA-tagged torch slipped in. python:3.11-slim has no
# CUDA libs, so torch.cuda.is_available() is False on a correct CPU build.
RUN python -c "import torch; v=torch.__version__; assert ('+cpu' in v) or (not torch.cuda.is_available()), f'Non-CPU torch detected: {v}'; print('torch ok:', v)"

# Verify the full ML import graph BEFORE attempting the model download. This
# isolates dependency-matrix failures (numpy/scipy/sklearn ABI mismatches,
# the "Extended Summary" KeyError, etc.) so they fail at a layer with a
# clear error instead of mid-download.
RUN python -c "import numpy, scipy, sklearn; from sentence_transformers import SentenceTransformer; print('ML deps OK:', 'numpy', numpy.__version__, '| scipy', scipy.__version__, '| sklearn', sklearn.__version__)"

# Pre-download the embedding model so the first request on Render does not
# pay the network cost. Override with: docker build --build-arg PREDOWNLOAD_MODEL=false .
ARG PREDOWNLOAD_MODEL=true
RUN if [ "$PREDOWNLOAD_MODEL" = "true" ]; then \
      python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')" ; \
    fi

# Copy source after deps so small code edits do not invalidate the heavy layers.
COPY backend/ /app/backend/
COPY frontend/ /app/frontend/

WORKDIR /app/backend

EXPOSE 8000

# Render injects $PORT at runtime; default to 8000 for `docker run` locally.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
