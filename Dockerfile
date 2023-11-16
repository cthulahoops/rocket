FROM python:3.11.6-bookworm

ARG YOUR_ENV

ENV PYTHONFAULTHANDLER=1 \
  PYTHONUNBUFFERED=1 \
  PYTHONHASHSEED=random \
  PIP_NO_CACHE_DIR=off \
  PIP_DISABLE_PIP_VERSION_CHECK=on \
  PIP_DEFAULT_TIMEOUT=100 \
  POETRY_VERSION=1.7.0 \
  PIPX_VERSION=1.2.1

RUN python -m pip install --no-cache-dir --upgrade pip pipx==${PIPX_VERSION}
RUN pipx ensurepath && pipx --version
RUN pipx install --force poetry==${POETRY_VERSION}

WORKDIR /code
COPY poetry.lock pyproject.toml /code/
RUN pipx run poetry install --only main --no-interaction --no-ansi
COPY pets /code/pets

CMD /root/.local/bin/poetry run python -m pets
