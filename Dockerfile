FROM python:3.11-alpine3.20 as builder
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN apk update \
    && apk add --no-cache binutils gcc zlib-dev libc-dev \
    && pip install --upgrade pip \
    && pip install --no-cache-dir -r /app/requirements.txt \
    && pip install --no-cache-dir pyinstaller
COPY . /app
RUN pyinstaller openlistsync.spec

FROM alpine:3.20.2
RUN apk update && apk add --no-cache tzdata
VOLUME /app/data
WORKDIR /app
COPY --from=builder /app/dist/openlistsync /app/
ENV TAO_PORT=8023 TAO_EXPIRES=2 TAO_LOG_LEVEL=1 TAO_CONSOLE_LEVEL=2 TAO_LOG_SAVE=7 TAO_TASK_SAVE=0 TAO_TASK_TIMEOUT=72 TZ=Asia/Shanghai
EXPOSE 8023
CMD ["./openlistsync"]
