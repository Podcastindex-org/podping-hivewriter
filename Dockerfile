FROM python:3.7-buster


ENV PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    PYTHONUNBUFFERED=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app/
COPY . /app/

RUN pip install --quiet poetry \
    && poetry config virtualenvs.create false \
    && poetry install --no-dev --quiet --no-interaction --no-ansi \
    && pip uninstall --yes --quiet poetry

EXPOSE 9999/tcp

ENTRYPOINT ["python3", "podping_hivewriter/hive-writer.py"]
