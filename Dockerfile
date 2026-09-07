FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential bison ca-certificates ccache clang file flex g++ gawk gettext git \
    libelf-dev libncurses-dev libssl-dev python3 python3-setuptools rsync swig time \
    unzip wget zlib1g-dev zstd \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 1000 builder
WORKDIR /workspace
USER builder
ENTRYPOINT ["python3", "scripts/build.py"]
