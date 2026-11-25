"""
Cost guard (tiêu chí 8) — chặn chi tiêu LLM vượt ngân sách.

  • Cộng dồn chi phí vào Redis theo ngày (cost:daily:YYYY-MM-DD) và theo tháng (cost:monthly:YYYY-MM)
  • Tổng vượt DAILY_BUDGET_USD hoặc MONTHLY_BUDGET_USD → HTTP 402 Payment Required
  • Rate limit bảo vệ TỐC ĐỘ (req/phút), cost guard bảo vệ TIỀN (USD/ngày, USD/tháng)
"""
from datetime import datetime, timezone

from fastapi import HTTPException

from app.config import settings
from app.redis_client import r

# Giá USD / 1K tokens (tham khảo gpt-4o-mini)
PRICE_INPUT_PER_1K = 0.00015
PRICE_OUTPUT_PER_1K = 0.0006

DAILY_TTL = 2 * 24 * 3600     # giữ key thêm 1 ngày rồi Redis tự xoá
MONTHLY_TTL = 32 * 24 * 3600


def _keys() -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    return f"cost:daily:{now:%Y-%m-%d}", f"cost:monthly:{now:%Y-%m}"


def estimate_tokens(text: str) -> int:
    """Mock LLM không trả số token → ước lượng theo quy tắc ~4 ký tự / token."""
    return max(1, len(text) // 4)


def check_budget() -> None:
    """Gọi TRƯỚC khi gọi LLM. Hết budget → raise HTTPException(status_code=402)."""
    daily_key, monthly_key = _keys()
    daily, monthly = (float(v or 0) for v in r.mget(daily_key, monthly_key))
    if daily >= settings.daily_budget_usd:
        raise HTTPException(status_code=402, detail=f"Daily budget of ${settings.daily_budget_usd} exceeded")
    if monthly >= settings.monthly_budget_usd:
        raise HTTPException(status_code=402, detail=f"Monthly budget of ${settings.monthly_budget_usd} exceeded")


def record_cost(input_tokens: int, output_tokens: int) -> float:
    """Gọi SAU khi gọi LLM. Cộng chi phí của request vào tổng, trả về chi phí request."""
    cost = input_tokens / 1000 * PRICE_INPUT_PER_1K + output_tokens / 1000 * PRICE_OUTPUT_PER_1K
    daily_key, monthly_key = _keys()
    pipe = r.pipeline()
    pipe.incrbyfloat(daily_key, cost)   # INCRBYFLOAT là atomic → nhiều worker cộng cùng lúc vẫn đúng
    pipe.expire(daily_key, DAILY_TTL)
    pipe.incrbyfloat(monthly_key, cost)
    pipe.expire(monthly_key, MONTHLY_TTL)
    pipe.execute()
    return cost
