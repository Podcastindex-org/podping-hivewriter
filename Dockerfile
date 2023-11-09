FROM docker.io/python:3.11-slim-bookworm

ENV PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN useradd --create-home podping && mkdir /home/podping/app && mkdir /home/podping/.config && chown -R podping:podping /home/podping

COPY install-packages.sh .
RUN ./install-packages.sh

USER podping
WORKDIR /home/podping/app
# poetry command installs here from pip
ENV PATH="/home/podping/.local/bin:${PATH}"

COPY --chown=podping:podping . .
RUN pip install --user poetry \
    && poetry config virtualenvs.in-project true \
    && poetry install --no-interaction --no-ansi --only main

# podping command installs here
ENV PATH="/home/podping/app/.venv/bin:${PATH}"

EXPOSE 9999/tcp

ENTRYPOINT ["podping"]