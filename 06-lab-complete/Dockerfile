# ============================================================
# Production Dockerfile — multi-stage
#   Stage 1 (builder): cài dependencies vào virtualenv /opt/venv
#   Stage 2 (runtime): image slim sạch, chỉ copy venv + source code, chạy bằng user non-root
# ============================================================

# ---------- Stage 1: builder ----------
FROM python:3.11-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build
# Copy requirements.txt TRƯỚC source code → layer cài thư viện được cache,
# sửa code không phải cài lại thư viện.
COPY requirements.txt .
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install -r requirements.txt

# ---------- Stage 2: runtime ----------
FROM python:3.11-slim AS runtime

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# User không có quyền root, không có shell đăng nhập
RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin appuser

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY app/ ./app/
COPY utils/ ./utils/

USER appuser
EXPOSE 8000

# Docker / platform tự gọi /health định kỳ để biết container còn sống
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/health' % os.getenv('PORT', '8000'), timeout=2)" || exit 1

# `exec` thay tiến trình sh bằng uvicorn → uvicorn là PID 1, nhận thẳng SIGTERM khi `docker stop`.
# ${PORT:-8000}: dùng PORT do Railway/Render cấp, mặc định 8000.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WEB_CONCURRENCY:-2} --no-access-log"]
