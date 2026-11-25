"""
Kết nối Redis dùng chung cho rate limiter và cost guard.

  • redis.from_url() KHÔNG mở kết nối ngay — kết nối chỉ được tạo ở lệnh đầu tiên,
    nên app vẫn khởi động được khi Redis chưa sẵn sàng (/health vẫn 200).
  • Timeout ngắn để /ready và /ask không bị treo lâu khi Redis chết.
  • redis_healthy() dùng cho GET /ready.
"""
import redis

from app.config import settings

r = redis.from_url(
    settings.redis_url,
    decode_responses=True,
    socket_connect_timeout=2,
    socket_timeout=2,
)


def redis_healthy() -> bool:
    try:
        return bool(r.ping())
    except redis.RedisError:
        return False
