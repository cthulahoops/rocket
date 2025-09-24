FROM python:3.11.6-bookworm

ARG YOUR_ENV

ENV PYTHONFAULTHANDLER=1 \
  PYTHONUNBUFFERED=1 \
  PYTHONHASHSEED=random \
  PIP_NO_CACHE_DIR=off \
  PIP_DISABLE_PIP_VERSION_CHECK=on \
  PIP_DEFAULT_TIMEOUT=100

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /code
COPY uv.lock pyproject.toml /code/
RUN uv sync --frozen --no-dev
COPY pets /code/pets

CMD uv run python -m pets
