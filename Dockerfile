FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

# Reusable OpenWrt host build environment.
#
# OpenWrt source, SDKs and ImageBuilders are intentionally not baked into this
# image because profiles may target different releases, branches and forks.
# The repository checkout is mounted at /workspace at runtime.
#
# Keep all host prerequisites and common build utilities here so firmware jobs
# can start the OpenWrt build immediately without installing system packages.
RUN apt-get update && apt-get install -y --no-install-recommends \
    autoconf \
    automake \
    autopoint \
    bash \
    bc \
    binutils \
    binutils-gold \
    bison \
    build-essential \
    bzip2 \
    ca-certificates \
    ccache \
    clang \
    cmake \
    coreutils \
    cpio \
    curl \
    device-tree-compiler \
    diffutils \
    file \
    findutils \
    flex \
    g++ \
    g++-multilib \
    gawk \
    gcc \
    gcc-multilib \
    gettext \
    git \
    grep \
    gzip \
    help2man \
    jq \
    libbsd-dev \
    libelf-dev \
    liblzma-dev \
    libncurses-dev \
    libssl-dev \
    libtool \
    libtool-bin \
    make \
    meson \
    mold \
    mtd-utils \
    ninja-build \
    patch \
    pbzip2 \
    perl \
    pigz \
    pkg-config \
    python3 \
    python3-dev \
    python3-pip \
    python3-setuptools \
    python3-venv \
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
    which \
    xsltproc \
    xxd \
    xz-utils \
    zlib1g-dev \
    zstd \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home builder

WORKDIR /workspace
USER builder

# No ENTRYPOINT on purpose: this image is the build environment only.
# The mounted repository supplies scripts/build.py and workflows invoke it
# explicitly, which keeps the image reusable and independent of repo layout.
