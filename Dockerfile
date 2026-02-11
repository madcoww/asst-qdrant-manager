## builder / 1단계 : Python 환경 & 종속성 설치
FROM registry.seculayer.com:31500/eyecloudai/python:3.11 as builder
ARG APP_DIR="/opt/app"
WORKDIR ${APP_DIR}

# Poetry 메타데이터 복사 및 캐싱 최적화
COPY pyproject.toml poetry.lock ${APP_DIR}/

RUN --mount=type=secret,id=gitconfig,target=/root/.gitconfig,required=true \
    --mount=type=secret,id=cert,dst=/etc/pki/ca-trust/source/anchors/slca.crt,required=true \
    echo "/etc/pki/ca-trust/source/anchors/slca.crt\n" >> /etc/ca-certificates.conf && \
    update-ca-certificates && \
    poetry config experimental.system-git-client true && \
    poetry config installer.parallel true && \
    poetry config installer.max-workers 4 && \
    poetry install --no-dev --no-root --no-interaction --no-ansi

## app / 2단계 : 실제 애플리케이션 실행 환경
FROM registry.seculayer.com:31500/eyecloudai/python:3.11 as app
ARG APP_DIR="/opt/app"
ENV MODULE_DIR="/eyeCloudAI/app"
WORKDIR ${MODULE_DIR}

# JRE 설치 (opendataloader_pdf용)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    openjdk-11-jre-headless \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 사용자 및 권한 설정
RUN groupadd -g 1000 aiuser && \
    useradd -m -u 1000 -g aiuser aiuser && \
    mkdir -p /home/aiuser/.local/bin \
             /eyeCloudAI/app/conf \
             /eyeCloudAI/app/logs \
             /eyeCloudAI/data/vectordb/docs \
    && chown -R aiuser:aiuser /home/aiuser /eyeCloudAI && \
    echo "root:eyecloudai!23" | chpasswd && \
    echo "aiuser:eyecloudai!23" | chpasswd
# .venv 복사
COPY --chown=aiuser:aiuser --from=builder ${APP_DIR}/.venv ${MODULE_DIR}/.venv

# 소스 코드 복사
COPY --chown=aiuser:aiuser src ${MODULE_DIR}/src

# 환경 변수 설정
ENV PATH="${MODULE_DIR}/.venv/bin:$PATH" \
    PYTHONPATH="${MODULE_DIR}:${MODULE_DIR}/src" \
    VENV_PATH="${MODULE_DIR}/.venv" \
    PYTHON_BIN="${MODULE_DIR}/.venv/bin/python"

ENV JAVA_HOME="/usr/lib/jvm/java-11-openjdk-amd64"
ENV PATH="$JAVA_HOME/bin:$PATH"
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

# aiuser로 전환
USER aiuser

# 기본 실행
CMD ["python", "src/QdrantManagerServer.py"]
