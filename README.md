# Neo Reels Backend MVP

短视频应用后端 MVP（FastAPI + Postgres + Redis + MinIO + Celery）。

## 接口文档（MVP）

### 基础信息
- Base URL: `http://localhost:8000`
- 响应格式：JSON
- 错误统一格式：

```json
{
  "error": {
    "code": "xxx",
    "message": "xxx",
    "details": {}
  }
}
```

### 1) 健康检查
**GET** `/health`  
无鉴权  
**响应**
```json
{ "status": "ok" }
```

### 2) 鉴权

#### 注册
**POST** `/auth/register`  
**Body**
```json
{
  "email": "demo@example.com",
  "password": "password123"
}
```
**响应**
```json
{
  "access_token": "xxx",
  "refresh_token": "xxx",
  "token_type": "bearer"
}
```

#### 登录
**POST** `/auth/login`  
**Body**
```json
{
  "email": "demo@example.com",
  "password": "password123"
}
```

#### 刷新 Token
**POST** `/auth/refresh`  
**Body**
```json
{
  "refresh_token": "xxx"
}
```

### 3) 视频

#### 初始化上传（生成 presigned PUT URL）
**POST** `/videos/upload/init`  
**鉴权**：需要 `Authorization: Bearer <access_token>`  
**Body**
```json
{
  "title": "demo",
  "filename": "video.mp4",
  "content_type": "video/mp4",
  "size_bytes": 12345678
}
```
**响应**
```json
{
  "upload_url": "https://...",
  "object_key": "raw/<video_id>/<video_id>.mp4",
  "video_id": "uuid"
}
```
**注意**
- `content_type` 必须在允许列表内（`video/mp4`, `video/quicktime`, `video/x-m4v`, `video/webm`）
- `size_bytes` 有上限（默认 500MB）
- `upload_url` 使用 `MINIO_PUBLIC_ENDPOINT` 生成，确保客户端可访问（本地默认为 `http://localhost:9000`）

#### 上传文件到 MinIO（客户端直传）
**PUT** `upload_url`  
**Headers**: `Content-Type: video/mp4`  
**Body**: 原始文件二进制

#### 上传完成回调（触发转码）
**POST** `/videos/upload/complete`  
**鉴权**：需要  
**Body**
```json
{
  "video_id": "uuid"
}
```
**响应**：返回视频详情（见下）

#### 获取视频详情
**GET** `/videos/{id}`  
无鉴权  
**响应**
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "status": "pending|processing|ready|failed",
  "title": "demo",
  "raw_object_key": "raw/...",
  "processed_object_key": "processed/.../video_720p.mp4",
  "cover_object_key": "processed/.../cover.jpg",
  "duration_sec": 10,
  "created_at": "...",
  "updated_at": "...",
  "error_message": null
}
```

#### 获取 Feed（分页）
**GET** `/feed?limit=20&offset=0`  
无鉴权  
**响应**
```json
{
  "items": [ ...VideoOut... ],
  "limit": 20,
  "offset": 0,
  "total": 100
}
```

## 本地调试 / 测试

### 端到端验证（推荐）
使用脚本自动跑通：注册 → 登录 → init → presigned PUT 上传 → complete → 轮询状态 → 详情 → feed。

```
API_BASE=http://localhost:8000 VIDEO_FILE=samples/sample.mp4 bash scripts/demo_upload.sh
```

说明：
- `API_BASE` 默认 `http://localhost:8000`
- `VIDEO_FILE` 默认 `samples/sample.mp4`
- 若 `VIDEO_FILE` 不存在，脚本会尝试用 `ffmpeg` 自动生成 3 秒测试视频
- 若首次注册失败返回 `email_taken`，脚本会自动继续登录

### 方式 A：脚本一键跑通
准备一个 mp4，然后执行：
```
VIDEO_PATH=/path/to/your.mp4 python scripts/seed.py
```
该脚本会依次执行：注册 → 登录 → init → 上传 → complete → feed。

### 方式 B：curl 示例
```
VIDEO_PATH=/path/to/your.mp4 bash scripts/curl_examples.sh
```

### 方式 C：手动调试流程
1. 注册 / 登录，拿到 `access_token`
2. 调用 `POST /videos/upload/init`
3. 使用 `upload_url` 进行 `PUT` 直传
4. 调用 `POST /videos/upload/complete`
5. `GET /videos/{id}` 查看状态变化
6. `GET /feed` 拉取列表

### 常见排查点
- 转码失败：`docker compose logs -f worker`
- 上传直传失败：确认 `Content-Type` 与 `size_bytes` 合规
- MinIO 连接问题：检查 `MINIO_ENDPOINT`、`MINIO_PUBLIC_ENDPOINT` 与桶是否创建
- 上传报 `NoSuchBucket`：执行 `docker compose up -d --force-recreate minio-init`
