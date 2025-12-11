FROM python:3.11-alpine3.20
RUN apk update \
	&& apk add --no-cache binutils gcc zlib-dev libc-dev \
	&& pip install --upgrade pip \
	&& pip install --no-cache-dir pyinstaller