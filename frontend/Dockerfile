# syntax=docker/dockerfile:1.7
#
# Flutter web build + nginx runtime for the `web` service.
#
# Requires the additional build context `deploy` (nginx config templates live in
# /deploy/nginx/templates). docker compose passes it automatically; manual build:
#   docker build --build-context deploy=./deploy -t rejestr-web ./frontend

# Flutter SDK is cloned from the official repository at an exact tag, so the
# image matches local development and CI (prebuilt images lag behind stable).
# Keep in sync with .github/workflows/ci.yml (flutter-version).
ARG FLUTTER_VERSION=3.47.5
ARG NGINX_IMAGE=nginx:1.27-alpine

# ---------------------------------------------------------------------------
FROM debian:bookworm-slim AS build

ARG FLUTTER_VERSION
RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl git unzip xz-utils \
 && rm -rf /var/lib/apt/lists/* \
 && git clone --depth 1 --branch "${FLUTTER_VERSION}" \
        https://github.com/flutter/flutter.git /opt/flutter \
 && /opt/flutter/bin/flutter precache --web --no-android --no-ios
ENV PATH="/opt/flutter/bin:/opt/flutter/bin/cache/dart-sdk/bin:${PATH}"

# Base URL of the API as seen by the browser. Behind the bundled nginx the API
# is same-origin under /api.
ARG API_URL=

ENV PUB_CACHE=/root/.pub-cache \
    CI=true

WORKDIR /app

RUN flutter config --no-analytics --enable-web

# Dependencies first - cached as long as pubspec does not change.
COPY pubspec.yaml pubspec.lock* ./
RUN --mount=type=cache,target=/root/.pub-cache \
    flutter pub get

COPY . .

# Code generation (freezed / json_serializable) - only when the project uses
# build_runner. Errors are NOT swallowed: broken codegen must fail the build.
RUN --mount=type=cache,target=/root/.pub-cache \
    flutter pub get \
 && if grep -Eq '^[[:space:]]+build_runner:' pubspec.yaml; then \
        dart run build_runner build; \
    fi \
 && flutter build web --release --csp --no-web-resources-cdn --no-wasm-dry-run \
        --dart-define=API_URL="${API_URL}"

# CSP guard (ADR 0019 §2): CanvasKit must be served from this origin, never from the
# gstatic CDN, and the dart2js output must not use eval / new Function.
RUN grep -qF '"useLocalCanvasKit":true' build/web/flutter_bootstrap.js \
 && test -f build/web/canvaskit/canvaskit.js \
 && test -f build/web/canvaskit/canvaskit.wasm \
 && ! grep -qE 'new Function\(|[^A-Za-z_$.]eval\(' build/web/main.dart.js

# ---------------------------------------------------------------------------
FROM ${NGINX_IMAGE} AS runtime

# Default nginx site replaced by ours (SPA fallback + /api reverse proxy). The
# image entrypoint renders /etc/nginx/templates/**/*.template with envsubst into
# /etc/nginx/conf.d/ at start; only NGINX_* variables are substituted, so nginx's
# own $variables stay intact (ADR 0019).
RUN rm -f /etc/nginx/conf.d/default.conf
COPY --from=deploy nginx/templates /etc/nginx/templates
COPY --from=build /app/build/web /usr/share/nginx/html

# Defaults of the template variables (descriptions: .env.example, WEB_* / NGINX_*).
ENV NGINX_ENVSUBST_FILTER="^NGINX_" \
    NGINX_API_RATE="20r/s" \
    NGINX_API_BURST="100" \
    NGINX_AUTH_RATE="10r/m" \
    NGINX_AUTH_BURST="10" \
    NGINX_REFRESH_RATE="30r/m" \
    NGINX_REFRESH_BURST="20" \
    NGINX_CONN_PER_IP="50" \
    NGINX_RETRY_AFTER="10" \
    NGINX_CLIENT_MAX_BODY_SIZE="26m" \
    NGINX_HSTS="" \
    NGINX_CSP_CONNECT_EXTRA="" \
    NGINX_TRUSTED_PROXIES="127.0.0.1/32"

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -q -O /dev/null http://127.0.0.1/healthz || exit 1
