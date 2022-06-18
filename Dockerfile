FROM docker.io/pypy:3.8-bullseye AS compile

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
    && apt-get -y install --no-install-recommends capnproto cargo libzmq3-dev rustc build-essential libssl-dev libffi-dev

USER podping
WORKDIR /home/podping/app

COPY pyproject.toml poetry.lock ./

RUN pip install --upgrade pip \
    && pip install --user poetry \
    && poetry config virtualenvs.in-project true \
    && poetry install --no-root --no-dev --no-interaction --no-ansi

FROM docker.io/pypy:3.8-slim-bullseye AS app

ENV PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN useradd --create-home podping && mkdir /home/podping/app && chown -R podping:podping /home/podping

COPY install-packages.sh .
RUN ./install-packages.sh

COPY --from=compile --chown=podping:podping /home/podping/.local /home/podping/.local
COPY --from=compile --chown=podping:podping /home/podping/app/.venv /home/podping/app/.venv
USER podping
WORKDIR /home/podping/app
# poetry command installs here from pip
ENV PATH="/home/podping/.local/bin:${PATH}"

COPY --chown=podping:podping . .
RUN pip install --upgrade pip \
    && pip install poetry \
    && poetry config virtualenvs.in-project true \
    && poetry install --no-dev --no-interaction --no-ansi

# podping command installs here
ENV PATH="/home/podping/app/.venv/bin:${PATH}"

EXPOSE 9999/tcp

ENTRYPOINT ["podping"]