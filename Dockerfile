FROM docker.io/python:3.9-slim-buster


ENV PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    PYTHONUNBUFFERED=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN useradd --create-home podping
WORKDIR /home/podping
USER podping
# podping and poetry commands install here from pip
ENV PATH="/home/podping/.local/bin/:${PATH}"

COPY --chown=podping:podping pyproject.toml poetry.lock ./
# Install dependencies only first for caching
RUN pip install --quiet poetry && poetry config virtualenvs.create false
RUN poetry install --no-root --no-dev --quiet --no-interaction --no-ansi

COPY --chown=podping:podping . .
RUN poetry install --no-dev --quiet --no-interaction --no-ansi \
    && pip uninstall --yes --quiet poetry

EXPOSE 9999/tcp

CMD ["podping", "server", "--i-know-what-im-doing", "0.0.0.0", "9999"]