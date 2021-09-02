FROM docker.io/python:3.9-slim-bullseye AS compile

ENV PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    LANG=C.UTF-8 \
    PATH="/root/.local/bin/:${PATH}"

COPY pyproject.toml poetry.lock ./

RUN apt-get update \
    && apt-get -y upgrade \
    && apt-get -y install --no-install-recommends gcc python3.9-dev \
    && pip install --user pip-autoremove poetry \
    && poetry config virtualenvs.in-project true \
    && poetry install --no-root --no-dev --no-interaction --no-ansi \
    && pip-autoremove -y pip-autoremove poetry \
    && apt-get clean  \
    && rm -rf /var/lib/apt/lists/*



FROM docker.io/python:3.9-slim-bullseye AS app

ENV PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    LANG=C.UTF-8

COPY install-packages.sh .
RUN ./install-packages.sh

RUN useradd --create-home podping
COPY --from=compile --chown=podping:podping /.venv /home/podping/.venv
WORKDIR /home/podping
USER podping
# podping and poetry commands install here from pip
ENV PATH="/home/podping/.venv/bin:/home/podping/.local/bin/:${PATH}"

COPY --chown=podping:podping . .
RUN pip install --user pip-autoremove poetry \
    && poetry config virtualenvs.in-project true \
    && poetry install --no-dev --no-interaction --no-ansi \
    && pip-autoremove -y pip-autoremove poetry

EXPOSE 9999/tcp

CMD ["podping", "server", "--i-know-what-im-doing", "0.0.0.0", "9999"]