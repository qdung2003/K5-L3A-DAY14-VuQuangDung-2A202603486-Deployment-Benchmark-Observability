"""
Production AI Agent — Part 6 Final Project.

  GET  /health   liveness  — luôn 200 khi process còn chạy (kể cả khi Redis chết)
  GET  /ready    readiness — 200 khi Redis kết nối được, 503 khi không
  POST /ask      X-API-Key (401) → rate limit (429) → cost guard (402) → mock LLM

Kiểm tra: python check_production_ready.py
"""
import json
import logging
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import redis
from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from app.auth import verify_api_key
from app.config import settings
from app.cost_guard import check_budget, estimate_tokens, record_cost
from app.rate_limiter import check_rate_limit
from app.redis_client import r, redis_healthy
from utils.mock_llm import ask as llm_ask


# ── Structured logging (tiêu chí 10) ─────────────────────────
class JsonFormatter(logging.Formatter):
    """Mỗi bản ghi log → đúng 1 dòng JSON (traceback cũng được escape vào 1 dòng)."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(timespec="milliseconds"),
            "lvl": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }
        payload.update(getattr(record, "fields", {}))
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def _setup_logging() -> logging.Logger:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    log = logging.getLogger("agent")
    log.handlers = [handler]
    log.setLevel(settings.log_level)
    log.propagate = False  # không đẩy lên root logger → không in trùng dạng text
    return log


logger = _setup_logging()


def log_event(event: str, level: int = logging.INFO, **fields) -> None:
    logger.log(level, event, extra={"fields": fields})


# ── Lifespan + graceful shutdown (tiêu chí 11) ───────────────
# Khi nhận SIGTERM, uvicorn tự: (1) ngừng nhận kết nối mới, (2) chờ các request đang chạy
# trả lời xong, (3) chạy phần sau `yield` bên dưới, (4) thoát với exit code 0.
# Vì vậy KHÔNG tự đăng ký signal handler (sẽ đè mất handler của uvicorn), chỉ dọn dẹp ở đây.
START_TIME = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log_event("startup", environment=settings.environment, port=settings.port,
              rate_limit_per_minute=settings.rate_limit_per_minute, redis_ok=redis_healthy())
    yield
    log_event("shutdown", uptime_s=round(time.time() - START_TIME, 1))
    r.close()


app = FastAPI(title="Production AI Agent", lifespan=lifespan)


@app.middleware("http")
async def access_log(request: Request, call_next):
    """Log mỗi request thành 1 dòng JSON: method, path, status, thời gian xử lý (ms)."""
    start = time.perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        log_event("request", method=request.method, path=request.url.path, status=status,
                  ms=round((time.perf_counter() - start) * 1000, 1))


# ── Xử lý lỗi: mã lỗi rõ ràng, không lộ stack trace cho client ──
@app.exception_handler(redis.RedisError)
async def redis_unavailable(request: Request, exc: redis.RedisError):
    log_event("redis_error", logging.ERROR, path=request.url.path, error=type(exc).__name__)
    return JSONResponse(status_code=503, content={"detail": "Service temporarily unavailable"})


@app.exception_handler(Exception)
async def unhandled_error(request: Request, exc: Exception):
    logger.error("unhandled_error", exc_info=exc, extra={"fields": {"path": request.url.path}})
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# ── Endpoints ────────────────────────────────────────────────
class AskRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)  # "   " → rỗng → 422

    question: str = Field(..., min_length=1, max_length=2000)
    user_id: str | None = Field(default=None, max_length=100)


@app.get("/health")
def health():
    """Liveness: chỉ trả lời "process còn sống" — không phụ thuộc Redis."""
    return {"status": "ok", "environment": settings.environment,
            "uptime_s": round(time.time() - START_TIME, 1)}


@app.get("/ready")
def ready():
    """Readiness: có nhận traffic được không — cần Redis cho rate limit + cost guard."""
    if redis_healthy():
        return {"status": "ready"}
    return JSONResponse(status_code=503, content={"status": "not ready", "reason": "redis unavailable"})


@app.post("/ask")
def ask(body: AskRequest, api_key: str = Depends(verify_api_key)):
    check_rate_limit(api_key)   # 429
    check_budget()              # 402 — kiểm tra TRƯỚC khi tốn tiền gọi LLM
    answer = llm_ask(body.question)
    input_tokens, output_tokens = estimate_tokens(body.question), estimate_tokens(answer)
    cost = record_cost(input_tokens, output_tokens)
    log_event("ask", user_id=body.user_id, input_tokens=input_tokens,
              output_tokens=output_tokens, cost_usd=round(cost, 8))
    return {
        "question": body.question,
        "answer": answer,
        "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens, "cost_usd": round(cost, 8)},
    }
