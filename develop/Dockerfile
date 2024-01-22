FROM onlyoffice/documentserver:latest
RUN if [ "$(uname -m)" = "aarch64" ]; then \
        echo "deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu-ports/ jammy main restricted universe multiverse" > /etc/apt/sources.list && \
        echo "deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu-ports/ jammy-updates main restricted universe multiverse" >> /etc/apt/sources.list && \
        echo "deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu-ports/ jammy-backports main restricted universe multiverse" >> /etc/apt/sources.list && \
        echo "deb http://ports.ubuntu.com/ubuntu-ports/ jammy-security main restricted universe multiverse" >> /etc/apt/sources.list; \
    else \
        echo "deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ jammy main restricted universe multiverse" > /etc/apt/sources.list && \
        echo "deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ jammy-updates main restricted universe multiverse" >> /etc/apt/sources.list && \
        echo "deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ jammy-backports main restricted universe multiverse" >> /etc/apt/sources.list && \
        echo "deb http://security.ubuntu.com/ubuntu/ jammy-security main restricted universe multiverse" >> /etc/apt/sources.list; \
    fi
RUN apt-get update -y && \
    apt-get install git -y \
    python3 -y \
    openjdk-11-jdk -y \
    bzip2 -y \
    npm -y
RUN npm install -g grunt grunt-cli -y
RUN ln -s /usr/bin/python3 /usr/bin/python && \
    ln -s /usr/bin/pip3 /usr/bin/pip
RUN git clone --depth 1 --branch v7.5.1_bs https://github.com/fernfei/build_tools.git var/www/onlyoffice/documentserver/build_tools
RUN sed -i '/documentserver-static-gzip.sh ${ONLYOFFICE_DATA_CONTAINER}/d' /app/ds/run-document-server.sh
RUN sed -i 's/WARN/ALL/g' /etc/onlyoffice/documentserver/log4js/production.json
RUN if [ -s /etc/supervisor/conf.d/ds-example.conf ] ; then sed -i 's,autostart=false,autostart=true,' /etc/supervisor/conf.d/ds-example.conf; fi
RUN if [ -s /app/ds/setup/config/supervisor/ds/ds-example.conf ] ; then sed -i 's,autostart=false,autostart=true,' /app/ds/setup/config/supervisor/ds/ds-example.conf; fi
RUN rm -rf /var/lib/apt/lists/*
ENTRYPOINT python3 /var/www/onlyoffice/documentserver/build_tools/develop/run_build_js.py /var/www/onlyoffice/documentserver $@ && /bin/sh -c /app/ds/run-document-server.sh