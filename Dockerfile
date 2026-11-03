# CPU image for Moot Court. The data root is a volume: mount your ledger, models, reports and cards there.
#   docker build -t mootcourt .
#   docker run --rm -v "$PWD/mootcourt-data:/data" mootcourt            # runs `moot doctor`
#   docker run --rm -v "$PWD/mootcourt-data:/data" mootcourt moot card --help
FROM python:3.12-slim AS build
# The image installs exactly what uv.lock pins (uv sync --locked), with the same uv version as the project's own tooling.
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1 UV_PROJECT_ENVIRONMENT=/opt/venv UV_LINK_MODE=copy
WORKDIR /src
RUN pip install "uv==0.10.5"
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src ./src
RUN uv sync --locked --no-dev --no-editable

FROM python:3.12-slim
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    MOOTCOURT_DATA_ROOT=/data
COPY --from=build /opt/venv /opt/venv
RUN useradd --create-home --uid 10001 moot && mkdir /data && chown moot:moot /data
USER moot
WORKDIR /home/moot
VOLUME /data
EXPOSE 8000
HEALTHCHECK --interval=60s --timeout=10s CMD ["moot", "--version"]
CMD ["moot", "doctor"]
