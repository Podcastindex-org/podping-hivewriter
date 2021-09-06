FROM docker.io/python:3.9-bullseye AS compile

ENV PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH="/home/podping/.local/bin:${PATH}"

RUN useradd --create-home podping && mkdir /home/podping/app && chown -R podping:podping /home/podping

RUN apt-get update \
    && apt-get -y upgrade \
    # rustc, cargo for armhf "cryptography"
    # libzmq3-dev for armhf "pyzmq"
    && apt-get -y install --no-install-recommends rustc cargo libzmq3-dev

USER podping
WORKDIR /home/podping/app

COPY pyproject.toml poetry.lock ./

RUN pip install --user poetry \
    && poetry config virtualenvs.in-project true \
    && poetry install --no-root --no-dev --no-interaction --no-ansi

FROM docker.io/python:3.9-slim-bullseye AS app

ENV PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

COPY install-packages.sh .
RUN ./install-packages.sh

RUN useradd --create-home podping
WORKDIR /home/podping/app
COPY --from=compile --chown=podping:podping /home/podping/.local /home/podping/.local
COPY --from=compile --chown=podping:podping /home/podping/app/.venv /home/podping/app/.venv
USER podping
# podping and poetry commands install here from pip
ENV PATH="/home/podping/.local/bin:/home/podping/app/.venv/bin:${PATH}"

COPY --chown=podping:podping . .
RUN /usr/local/bin/pip install poetry \
    && poetry config virtualenvs.in-project true \
    && poetry install --no-dev --no-interaction --no-ansi

EXPOSE 9999/tcp

ENTRYPOINT ["podping"]