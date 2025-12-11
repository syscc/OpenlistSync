FROM syscc/openlistsync:not-for-use-pip-req as builder
WORKDIR /app
COPY . /app
RUN pyinstaller openlistsync.spec

FROM syscc/openlistsync:not-for-use-alpine
VOLUME /app/data
WORKDIR /app
COPY --from=builder /app/dist/openlistsync /app/
ENV TAO_PORT=8023 TAO_EXPIRES=2 TAO_LOG_LEVEL=1 TAO_CONSOLE_LEVEL=2 TAO_LOG_SAVE=7 TAO_TASK_SAVE=0 TAO_TASK_TIMEOUT=72 TZ=Asia/Shanghai
EXPOSE 8023
CMD ["./openlistsync"]
