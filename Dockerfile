FROM ubuntu:18.04
ENV TZ=Etc/UTC
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
RUN apt-get -o Acquire::https::Verify-Peer=false update && \
     apt-get -y install ca-certificates

RUN apt-get update && \
    apt-get install -y python python3 wget sudo lsb-release software-properties-common gnupg

RUN apt-get install -y --no-install-recommends \
    autoconf2.13 cmake curl git libtool \
    libglu1-mesa-dev libgtk-3-dev libpulse-dev \
    p7zip-full subversion libasound2-dev libatspi2.0-dev \
    libcups2-dev libdbus-1-dev libglib2.0-dev \
    libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev \
    libx11-xcb-dev libxi-dev libxrender-dev libxss1


RUN add-apt-repository universe
RUN wget -O - https://apt.llvm.org/llvm-snapshot.gpg.key | sudo apt-key add -
RUN echo deb http://apt.llvm.org/bionic/ llvm-toolchain-bionic-12 main | tee /etc/apt/sources.list.d/llvm.list

RUN apt-get update && \
    apt-get install -y clang-12 lld-12 x11-utils llvm-12 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*


                       
RUN rm /usr/bin/python && ln -s /usr/bin/python2 /usr/bin/python

ADD . /build_tools
WORKDIR /build_tools

# Define build arguments
ARG BRANCH
ARG PLATFORM
ARG HTTP_PROXY
ARG HTTPS_PROXY

ENV http_proxy=${HTTP_PROXY}
ENV https_proxy=${HTTPS_PROXY}

# Set default values for environment variables
ENV BRANCH ${BRANCH}
ENV PLATFORM ${PLATFORM}

# Define the command to run
CMD cd tools/linux && \
    if [ -n "$BRANCH" ]; then \
        BRANCH_ARG="--branch=${BRANCH}"; \
    else \
        BRANCH_ARG=""; \
    fi && \
    if [ -n "$PLATFORM" ]; then \
        PLATFORM_ARG="--platform=${PLATFORM}"; \
    else \
        PLATFORM_ARG=""; \
    fi && \
    python3 ./automate.py $BRANCH_ARG $PLATFORM_ARG

