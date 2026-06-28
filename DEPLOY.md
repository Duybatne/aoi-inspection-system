# 🚀 Hướng Dẫn Deploy AOI System

Hệ thống AOI được triển khai theo mô hình Hybrid:
- **Frontend** (Dashboard) → **Vercel** (CDN toàn cầu, miễn phí)
- **Backend** (API + Celery) → **Railway** (container, miễn phí $5/tháng)

---

## Bước 1 — Tạo Tài khoản & Services Free Tier

Truy cập các link dưới đây, đăng ký tài khoản miễn phí và lấy thông tin kết nối:

| Service | Link | Dùng cho |
|---|---|---|
| **Neon** | https://neon.tech | PostgreSQL database |
| **Upstash** | https://upstash.com | Redis (WebSocket events) |
| **CloudAMQP** | https://cloudamqp.com | RabbitMQ (Celery broker) |
| **Cloudinary** | https://cloudinary.com | Image storage |
| **Railway** | https://railway.app | Backend hosting |
| **Vercel** | https://vercel.com | Frontend hosting |

---

## Bước 2 — Tạo Database trên Neon

1. Đăng nhập Neon → **New Project** → đặt tên `aoi-inspection`.
2. Vào **Connection Details** → copy **Connection String** (dạng `postgresql://...?sslmode=require`).
3. Lưu lại — đây là giá trị `DATABASE_URL`.

---

## Bước 3 — Tạo Redis trên Upstash

1. Đăng nhập Upstash → **Create Database** → chọn **Global**.
2. Vào database → copy **Redis URL** (dạng `rediss://default:xxx@global-xxx.upstash.io:6379`).
3. Lưu lại — đây là giá trị `REDIS_URL`.

---

## Bước 4 — Tạo RabbitMQ trên CloudAMQP

1. Đăng nhập CloudAMQP → **Create New Instance** → chọn plan **Little Lemur (Free)**.
2. Vào instance → copy **AMQP URL** (dạng `amqps://user:pass@...`).
3. Lưu lại — đây là giá trị `CELERY_BROKER_URL`.

---

## Bước 5 — Tạo Image Storage trên Cloudinary

1. Đăng nhập Cloudinary → vào **Dashboard**.
2. Copy **Cloud Name**, **API Key**, **API Secret**.
3. Lưu lại — đây là các giá trị `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`.

---

## Bước 6 — Deploy Backend lên Railway

1. Đăng nhập Railway → **New Project** → **Deploy from GitHub repo**.
2. Chọn repository `aoi-inspection-system`.
3. Railway sẽ tự nhận diện Python từ `requirements.txt` và `Procfile`.
4. Vào **Variables** → thêm tất cả biến môi trường từ `.env.example`:

```
DATABASE_URL=<từ Neon>
REDIS_URL=<từ Upstash>
CELERY_BROKER_URL=<từ CloudAMQP>
CLOUDINARY_CLOUD_NAME=<từ Cloudinary>
CLOUDINARY_API_KEY=<từ Cloudinary>
CLOUDINARY_API_SECRET=<từ Cloudinary>
FRONTEND_URL=https://your-app.vercel.app
ENVIRONMENT=production
CAMERA_TYPE=mock
```

5. Railway sẽ tự động deploy. Sau khi deploy thành công, vào **Settings → Domains** → copy URL dạng `https://aoi-xxx.up.railway.app`.

> **Thêm Celery Worker service:**
> Railway → New Service trong cùng project → **Start Command**: `celery -A backend.workers.celery_app.celery_app worker --loglevel=info --pool=solo`
> Thêm lại tất cả biến môi trường cho service này.

---

## Bước 7 — Cập nhật API URL trong Frontend

Mở file `frontend/index.html`, tìm dòng:
```html
<meta name="api-base-url" content="">
```
Thay thành Railway URL vừa lấy:
```html
<meta name="api-base-url" content="https://aoi-xxx.up.railway.app">
```

Commit và push lên Git.

---

## Bước 8 — Deploy Frontend lên Vercel

1. Đăng nhập Vercel → **Add New Project** → Import từ GitHub.
2. Chọn repository → Vercel sẽ tự nhận diện `vercel.json`.
3. Không cần cài thêm gì — Vercel sẽ serve static frontend tự động.
4. Sau khi deploy xong, copy URL Vercel (dạng `https://aoi-xxx.vercel.app`).

---

## Bước 9 — Cập nhật CORS trên Railway

Vào Railway → **Variables** → cập nhật:
```
FRONTEND_URL=https://aoi-xxx.vercel.app
```
Railway sẽ tự động restart và áp dụng CORS mới.

---

## ✅ Kiểm Tra Hệ Thống

1. Mở `https://aoi-xxx.vercel.app` — Dashboard phải tải được.
2. Kiểm tra kết nối WebSocket (góc trên phải hiện "Connected Live").
3. Click **Upload Image** → tải lên ảnh PCB → kiểm tra kết quả PASS/FAIL xuất hiện.

---

## 💡 Tips cho Portfolio / CV

- Thêm URL Vercel vào CV và LinkedIn dưới dạng **Live Demo**.
- Thêm Railway URL `/health` và `/docs` (Swagger UI FastAPI) vào README để chứng minh backend chạy thực tế.
- Có thể demo trực tiếp bằng cách tải lên ảnh PCB thật hoặc ảnh giả lập để thấy Verdict Engine phân loại lỗi.
