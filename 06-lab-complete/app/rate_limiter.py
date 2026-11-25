"""
Rate limiting (tiêu chí 7) — sliding window 60 giây, state trong Redis.

Mỗi API key có một sorted set trong Redis: member = 1 request, score = thời điểm gửi.
Vì state nằm trong Redis nên mọi worker / instance dùng chung một bộ đếm, và restart
agent không làm mất bộ đếm (script chấm restart agent để kiểm tra điều này).
"""
import hashlib
import time
import uuid

from fastapi import HTTPException

from app.config import settings
from app.redis_client import r

WINDOW_SECONDS = 60


def _bucket(key: str) -> str:
    # Băm API key trước khi làm tên key Redis — không lưu key gốc trong Redis.
    return "ratelimit:" + hashlib.sha256(key.encode()).hexdigest()[:16]


def check_rate_limit(key: str) -> None:
    limit = settings.rate_limit_per_minute
    bucket = _bucket(key)
    now = time.time()
    member = f"{now}:{uuid.uuid4().hex}"

    # pipeline() mặc định chạy trong MULTI/EXEC → 4 lệnh thực thi liền một khối (atomic),
    # nên 2 worker gửi cùng lúc không đếm sai.
    pipe = r.pipeline()
    pipe.zremrangebyscore(bucket, 0, now - WINDOW_SECONDS)  # bỏ request cũ hơn 60s
    pipe.zadd(bucket, {member: now})                        # ghi request hiện tại
    pipe.zcard(bucket)                                      # đếm số request trong cửa sổ
    pipe.expire(bucket, WINDOW_SECONDS)                     # key tự xoá khi không còn dùng
    _, _, count, _ = pipe.execute()

    if count > limit:
        r.zrem(bucket, member)  # request bị từ chối thì không tính vào hạn mức
        oldest = r.zrange(bucket, 0, 0, withscores=True)
        retry_after = int(oldest[0][1] + WINDOW_SECONDS - now) + 1 if oldest else WINDOW_SECONDS
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: {limit} requests per minute",
            headers={"Retry-After": str(retry_after)},
        )
