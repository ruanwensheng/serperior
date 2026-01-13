# Hướng dẫn Triển khai Docker Chuyên nghiệp (Full Stack)

Trong môi trường chuyên nghiệp (Production), chúng ta không dùng `npm start` hay `python main.py` thủ công. Chúng ta sử dụng kiến trúc **Microservices** được đóng gói (Containerized) và quản lý bằng **Docker Compose**.

## 1. Kiến trúc Hệ thống

1.  **Backend Service**: API Server (Python/FastAPI).
    *   Chạy code Python.
    *   Chứa **ChromaDB (Embedded)**: Database được lưu trong một "Volume" (ổ đĩa ảo) để dữ liệu không bị mất khi tắt Docker.
2.  **Frontend Service**: Web Server (Nginx).
    *   Không chạy Node.js server! (Nặng và chậm).
    *   Build React thành các file tĩnh (HTML/CSS/JS) và dùng **Nginx** (siêu nhẹ, hiệu năng cao) để phục vụ người dùng.

---

## 2. Thiết lập Frontend (React + Nginx)

Đây là cách "chuẩn" để deploy React.

### Bước 2.1: Tạo file cấu hình Nginx
Tạo file `frontend/nginx.conf`:

```nginx
server {
    listen 80;

    # Phục vụ file Static (React Build)
    location / {
        root   /usr/share/nginx/html;
        index  index.html index.htm;
        # Fix cho React Router: Nếu không tìm thấy file, trả về index.html
        try_files $uri $uri/ /index.html;
    }

    # (Tùy chọn) Proxy API requests sang Backend container
    # Giúp frontend gọi "/api/..." thay vì hardcode "http://localhost:8000"
    # location /api/ {
    #     proxy_pass http://backend:8000;
    # }
}
```

### Bước 2.2: Tạo `Dockerfile` cho Frontend (Multi-stage Build)
Tạo file `frontend/Dockerfile`. Kỹ thuật **Multi-stage** giúp image cuối cùng cực nhẹ (<20MB) so với image Node.js gốc (>500MB).

```dockerfile
# Stage 1: Build (Dùng Node để compile code)
FROM node:18-alpine as build-stage
WORKDIR /app
COPY package.json .
RUN npm install
COPY . .
# Tạo folder 'build' chứa file tĩnh
RUN npm run build

# Stage 2: Production (Dùng Nginx để chạy)
FROM nginx:alpine as production-stage
# Copy file build từ Stage 1 sang Nginx
COPY --from=build-stage /app/build /usr/share/nginx/html
# Copy cấu hình Nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

---

## 3. Thiết lập Backend & Database

Database hiện tại của bạn là **ChromaDB** chạy dạng embedded (nhúng trong code Python).
Để dữ liệu tồn tại vĩnh viễn (Persist), chúng ta map folder chứa dữ liệu ra ngoài máy thật.

File `backend/Dockerfile` (Bạn đã có, nhưng hãy đảm bảo nó như sau):
```dockerfile
FROM python:3.9-slim
WORKDIR /app

# Cài thêm thư viện hệ thống cho ChromaDB/Build
RUN apt-get update && apt-get install -y build-essential curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Chạy server
CMD ["uvicorn", "serperior.api.api:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 4. Orchestration (Docker Compose)

Đây là "nhạc trưởng" điều khiển toàn bộ hệ thống.
Tạo/Cập nhật file `docker-compose.yml` ở thư mục gốc:

```yaml
version: '3.8'

services:
  # 1. Backend Service
  backend:
    build: ./backend
    container_name: serperior-api
    ports:
      - "8000:8000"
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      # Có thể thêm biến môi trường CHROMA_DB_PATH nếu code hỗ trợ
    volumes:
      # QUAN TRỌNG: Lưu dữ liệu ChromaDB ra máy thật để không bị mất
      # Giả sử code lưu DB tại /app/data/real_chroma_db
      - chroma_data:/app/data/real_chroma_db
      # (Option development only) Mount code để sửa ko cần rebuild
      # - ./backend:/app
    networks:
      - serperior-net

  # 2. Frontend Service
  frontend:
    build: ./frontend
    container_name: serperior-web
    ports:
      - "80:80"  # Chạy ở port 80 (chuẩn web)
    depends_on:
      - backend
    networks:
      - serperior-net

# Định nghĩa Volume và Network
volumes:
  chroma_data: # Docker tự quản lý nơi lưu trữ này

networks:
  serperior-net:
    driver: bridge
```

---

## 5. Cách chạy

1.  **Tạo file .env**: (Nếu chưa có)
    Tạo file `.env` cạnh `docker-compose.yml`, điền key vào:
    ```
    GEMINI_API_KEY=AIzaSy...
    ```

2.  **Chạy lệnh**:
    ```bash
    docker-compose up -d --build
    ```
    *   `-d`: Chạy ngầm (Detached mode).
    *   `--build`: Build lại image mới nhất.

3.  **Truy cập**:
    *   Web Frontend: `http://localhost` (Không cần :3000 nữa).
    *   API Backend: `http://localhost:8000`.

## Lưu ý quan trọng về API URL
Trong `Dashboard.jsx`, bạn đang trỏ tới `http://127.0.0.1:8000`.
*   Khi chạy Docker, Frontend (trên Browser người dùng) vẫn gọi tới `localhost/127.0.0.1` của máy người dùng. -> **Code cũ vẫn hoạt động đúng.**
*   (Nâng cao) Nếu deploy lên Server thật (VPS), bạn cần thay `http://127.0.0.1:8000` bằng IP của VPS hoặc domain.
