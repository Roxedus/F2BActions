FROM python:3.8-alpine

LABEL maintainer="Roxedus"

COPY / /app

# hadolint ignore=DL3018
RUN apk add --no-cache --virtual=build-dependencies --update \
        gcc \
        musl-dev \
        python3-dev && \
    python3 -m pip install -r /app/requirements.txt && \
    apk del build-dependencies

WORKDIR /app

ENTRYPOINT [ "python3", "/app/discordEmbed.py" ]