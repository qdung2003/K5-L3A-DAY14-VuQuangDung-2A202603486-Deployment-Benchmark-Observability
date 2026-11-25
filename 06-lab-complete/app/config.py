"""
Config — 12-Factor: mọi cấu hình đọc từ biến môi trường.

Giá trị mặc định chỉ để chạy local cho tiện. Secret (AGENT_API_KEY) KHÔNG có giá trị
mặc định: thiếu biến này thì mọi request /ask bị 401 (fail-closed), không bao giờ mở cửa.
Danh sách đầy đủ các biến nằm trong .env.example.
"""
import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    port: int
    environment: str
    log_level: str
    agent_api_key: str = field(repr=False)  # repr=False: lỡ log/print settings cũng không lộ key
    redis_url: str
    rate_limit_per_minute: int
    daily_budget_usd: float
    monthly_budget_usd: float


def load_settings() -> Settings:
    return Settings(
        port=int(os.getenv("PORT", "8000")),
        environment=os.getenv("ENVIRONMENT", "development"),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        agent_api_key=os.getenv("AGENT_API_KEY", ""),
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        rate_limit_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "10")),
        daily_budget_usd=float(os.getenv("DAILY_BUDGET_USD", "1.0")),
        monthly_budget_usd=float(os.getenv("MONTHLY_BUDGET_USD", "10.0")),
    )


settings = load_settings()
