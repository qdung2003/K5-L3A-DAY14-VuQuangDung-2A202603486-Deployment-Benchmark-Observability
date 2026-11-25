# Day 14 Lab — Mission Answers

> Mọi output và con số trong file này lấy từ lệnh tôi tự chạy trên máy (Windows 11 + WSL2 Ubuntu 24.04 + Docker Desktop).

---

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns trong `01-localhost-vs-production/develop/app.py`
<!-- Ít nhất 5 anti-pattern, mỗi cái ghi kèm dòng code -->
1. 
2. 
3. 
4. 
5. 

### Exercise 1.2: Chạy bản develop
<!-- Lệnh: curl -X POST "http://localhost:8000/ask?question=Hello"  (bản develop nhận question qua query) -->
```text

```

### Exercise 1.3: So sánh develop vs production
| Feature | Develop | Production | Tại sao quan trọng? |
|---------|---------|------------|---------------------|
| Config | | | |
| Secrets | | | |
| Health check | | | |
| Logging | | | |
| Shutdown | | | |

---

## Part 2: Docker

### Exercise 2.1: Câu hỏi về `02-docker/develop/Dockerfile`
1. Base image: 
2. Working directory: 
3. Tại sao `COPY requirements.txt` trước `COPY . .`: 
4. CMD vs ENTRYPOINT: 

### Exercise 2.2: Build và chạy container develop
<!-- docker build -f 02-docker/develop/Dockerfile -t my-agent:develop .  (chạy ở gốc repo) -->
```text

```

### Exercise 2.3: Multi-stage build — kích thước image
<!-- Số đo bằng `docker images | grep my-agent`, không chép từ README -->
- Stage 1 làm gì: 
- Stage 2 làm gì: 
- Tại sao image nhỏ hơn: 

| Image | Size |
|-------|------|
| `my-agent:develop` | ___ MB |
| `my-agent:advanced` | ___ MB |
| Chênh lệch | ___ % |

### Exercise 2.4: Docker Compose stack
<!-- Sơ đồ các service + kết quả curl qua Nginx (cần `touch .env.local` trong 02-docker/production/) -->
```text
(sơ đồ)
```
```text
(output curl http://localhost/health và /ask)
```

---

## Part 3: Cloud Deployment

### Exercise 3.1 / 3.2: Deploy agent Part 6
- Nền tảng chính: 
- URL public: 
- Chi tiết, lệnh test và ảnh: xem [DEPLOYMENT.md](DEPLOYMENT.md)

### So sánh `railway.toml` với `render.yaml`
<!-- Khác nhau chỗ nào, vì sao (file nằm trong 06-lab-complete/) -->

### Exercise 3.3: Pipeline CI/CD của Cloud Run
<!-- 3–5 dòng sau khi đọc 03-cloud-deployment/production-cloud-run/cloudbuild.yaml và service.yaml -->

---

## Part 4: API Security

### Exercise 4.1: API key (`04-api-gateway/develop`)
- API key được check ở đâu: 
- Sai key thì sao: 
- Rotate key thế nào: 

```text
(output curl -i: không key → 401, có key → 200)
```

### Exercise 4.2: JWT (`04-api-gateway/production`, tài khoản student / demo123, `POST /auth/token`)
```text
(output curl -i lấy token và gọi /ask — che token)
```

### Exercise 4.3: Rate limiting
- Algorithm: 
- Limit: 
- Bypass cho admin: 

```text
(output vòng lặp curl -i, thấy 429)
```

### Exercise 4.4: Cost guard
<!-- Giải thích cách làm -->

---

## Part 5: Scaling & Reliability

### Exercise 5.1: Health checks (`/health` vs `/ready`)

### Exercise 5.2: Graceful shutdown

### Exercise 5.3: Stateless design

### Exercise 5.4: Load balancing
<!-- cd 05-scaling-reliability/production && touch .env.local
     docker compose -p k5-day14-scaling up -d --build --scale agent=3 ; stack mở cổng 8080, endpoint POST /chat -->
```text

```

### Exercise 5.5: Test stateless
```text
(output python test_stateless.py + giải thích)
```

---

## Part 6: Final Project — `06-lab-complete/`

Kết quả `python check_production_ready.py` (bản đầy đủ, chạy trong WSL2 Ubuntu 24.04, Docker 29.9.3):

```text
================================================================
  📋 Checklist Deliverable
     ✅ Dockerfile (multi-stage, < 500 MB)
     ✅ docker-compose.yml (agent + redis)
     ✅ .dockerignore
     ✅ Health check endpoint (GET /health)
     ✅ Readiness endpoint (GET /ready)
     ✅ API Key authentication
     ✅ Rate limiting
     ✅ Cost guard
     ✅ Config từ environment variables
     ✅ Structured logging
     ✅ Graceful shutdown
     ✅ Public URL ready (Railway / Render config)
----------------------------------------------------------------
  Result: 12/12 tiêu chí đạt · 43/43 checks passed
  🎉 PASS 12/12 — PRODUCTION READY! Deploy nào!
================================================================
```

Một vài số đo trong lần chạy: image 273 MB; `docker stop` tắt sau 0.7s, exit code 0; rate limit trả 429 sau 5 request thành công (`RATE_LIMIT_PER_MINUTE=5`) và vẫn 429 sau khi restart agent (state trong Redis).

---

## AI log

| # | Hỏi / nhờ AI làm gì | Nhận được gì | Tôi tự sửa / tự kiểm tra thế nào |
|---|---------------------|--------------|-----------------------------------|
| 1 | Claude Code: cài WSL2 bị lỗi `The system cannot find the path specified` | Chẩn đoán: bản WSL 2.7.11 cài bằng MSI trước đây bị mất thư mục `C:\Program Files\WSL\` nhưng registry vẫn trỏ tới; hướng dẫn bật tính năng bằng `dism`, gỡ bản MSI hỏng, cài lại WSL | Tự chạy các lệnh trong PowerShell Admin; kiểm tra `wsl -l -v` → Ubuntu-24.04 VERSION 2, `python3 -c "import os; print(os.name)"` → `posix` |
| 2 | Claude Code: viết code Part 6 trong `06-lab-complete/` — `app/config.py`, `auth.py`, `redis_client.py`, `rate_limiter.py`, `cost_guard.py`, `main.py`, `Dockerfile`, `docker-compose.yml`, `.dockerignore`, `.env.example`, `railway.toml`, `render.yaml` | Code + giải thích từng file (sliding window bằng Redis sorted set trong MULTI/EXEC, cost guard bằng `INCRBYFLOAT` theo ngày/tháng, log JSON bằng `logging.Formatter` tự viết, graceful shutdown dựa vào uvicorn + `lifespan`, Dockerfile 2 stage + user non-root + `exec uvicorn` để là PID 1) | Đọc lại từng file; tự chạy `python check_production_ready.py` bản đầy đủ (có Docker) trong WSL2 → PASS 12/12. Không sửa `check_production_ready.py` |
| | | | |
