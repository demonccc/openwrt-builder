FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

# Keep the image as a reusable OpenWrt build environment. The repository
# checkout is mounted at /workspace at runtime, so builder code and profiles
# do not need to be baked into the image.
RUN apt-get update && apt-get install -y --no-install-recommends \
    bc \
    binutils \
    binutils-gold \
    bison \
    build-essential \
    bzip2 \
    ca-certificates \
    ccache \
    clang \
    curl \
    file \
    flex \
    g++ \
    g++-multilib \
    gawk \
    gcc \
    gcc-multilib \
    gettext \
    git \
    gzip \
    help2man \
    libbsd-dev \
    libelf-dev \
    liblzma-dev \
    libncurses-dev \
    libssl-dev \
    meson \
    mold \
    mtd-utils \
    ninja-build \
    patch \
    pbzip2 \
    pigz \
    pkg-config \
    python3 \
    python3-dev \
    python3-setuptools \
    rsync \
    subversion \
    swig \
    tar \
    texinfo \
    time \
    u-boot-tools \
    unzip \
    util-linux \
    wget \
    xsltproc \
    xxd \
    xz-utils \
    zlib1g-dev \
    zstd \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home builder
WORKDIR /workspace
USER builder

ENTRYPOINT ["python3", "scripts/build.py"]
