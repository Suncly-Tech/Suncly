# syntax=docker/dockerfile:1.7
#
# One image, three commands (docs: deploy/README.md):
#   suncly api serve      the HTTP API (Cloud Run service)
#   suncly worker run     the trusted Runner boundary (Cloud Run Job)
#   suncly worker tick    the dispatcher / recovery pass (Cloud Run Job, scheduled)
#
# Base images are pinned by tag here and by digest at build time
# (`deploy/validate.py --pin` resolves the digests with `docker buildx imagetools inspect`
# and refuses an unpinned reference in the Cloud Run manifests). No step needs a privileged
# daemon: the build runs under BuildKit's default rootless-compatible settings.

ARG PYTHON_IMAGE=python:3.12.8-slim-bookworm
ARG NODE_IMAGE=node:22.12.0-bookworm-slim

# ---- stage: promptfoo, pinned, installed with npm ci from a lockfile we own ---------------
FROM ${NODE_IMAGE} AS promptfoo
WORKDIR /opt/promptfoo
COPY deploy/tools/promptfoo/package.json deploy/tools/promptfoo/package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci --omit=dev --ignore-scripts \
    && node_modules/.bin/promptfoo --version

# ---- stage: python dependencies -------------------------------------------------------------
FROM ${PYTHON_IMAGE} AS build
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1 PYTHONDONTWRITEBYTECODE=1
RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /src
COPY pyproject.toml README.md ./
COPY src ./src
COPY db ./db
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --require-hashes -r deploy/requirements.lock.txt 2>/dev/null \
    || /opt/venv/bin/pip install ".[gcp,anthropic]"
# The A2A TCK, at the pinned tag (Apache-2.0). Its own dependencies are installed into a
# separate environment so they never shadow Suncly's.
ARG A2A_TCK_REF=1.0.0.alpha2
ARG A2A_TCK_COMMIT=29063fe95e903cddac5d8ff811ab94df1ad6ef86
RUN git clone --depth 1 --branch "${A2A_TCK_REF}" https://github.com/a2aproject/a2a-tck.git /opt/a2a-tck \
    && cd /opt/a2a-tck \
    && test "$(git rev-parse HEAD)" = "${A2A_TCK_COMMIT}" \
    && python -m venv /opt/a2a-tck-venv \
    && /opt/a2a-tck-venv/bin/pip install -e . \
    && git rev-parse HEAD > .suncly-pin \
    && rm -rf .git

# ---- stage: runtime ---------------------------------------------------------------------------
FROM ${PYTHON_IMAGE} AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:/opt/promptfoo/node_modules/.bin:${PATH}" \
    SUNCLY_HOME=/var/suncly \
    SUNCLY_A2A_TCK_DIR=/opt/a2a-tck \
    SUNCLY_A2A_TCK_PYTHON=/opt/a2a-tck-venv/bin/python \
    SUNCLY_PROMPTFOO_BIN=/opt/promptfoo/node_modules/.bin/promptfoo
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates tini \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system suncly && useradd --system --gid suncly --home /var/suncly suncly \
    && mkdir -p /var/suncly && chown suncly:suncly /var/suncly
COPY --from=build /opt/venv /opt/venv
COPY --from=build /opt/a2a-tck /opt/a2a-tck
COPY --from=build /opt/a2a-tck-venv /opt/a2a-tck-venv
COPY --from=promptfoo /usr/local/bin/node /usr/local/bin/node
COPY --from=promptfoo /opt/promptfoo /opt/promptfoo
COPY --from=build /src/db/migrations /opt/suncly/migrations
COPY deploy/entrypoint.sh /usr/local/bin/suncly-entrypoint
RUN chmod 0755 /usr/local/bin/suncly-entrypoint
USER suncly
WORKDIR /var/suncly
EXPOSE 8080
ENTRYPOINT ["tini", "--", "suncly-entrypoint"]
CMD ["api"]
