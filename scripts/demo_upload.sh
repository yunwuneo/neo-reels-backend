#!/usr/bin/env bash
set -euo pipefail

API_BASE=${API_BASE:-http://localhost:8000}
VIDEO_FILE=${VIDEO_FILE:-samples/sample.mp4}
EMAIL=${EMAIL:-demo@example.com}
PASSWORD=${PASSWORD:-password123}

log() {
  echo "[$(date +'%H:%M:%S')] $*"
}

fail() {
  echo "[error] $*" >&2
  exit 1
}

if [ ! -f "$VIDEO_FILE" ]; then
  log "Sample video not found: $VIDEO_FILE"
  if ! command -v ffmpeg >/dev/null 2>&1; then
    fail "ffmpeg not found. Please install ffmpeg or provide VIDEO_FILE."
  fi
  log "Generating 3s test video via ffmpeg (color bars + silent audio)..."
  mkdir -p "$(dirname "$VIDEO_FILE")"
  ffmpeg -y \
    -f lavfi -i testsrc=duration=3:size=1280x720:rate=30 \
    -f lavfi -i anullsrc=channel_layout=stereo:sample_rate=44100 \
    -shortest -c:v libx264 -pix_fmt yuv420p -c:a aac \
    "$VIDEO_FILE" >/dev/null 2>&1 || fail "ffmpeg generate failed"
  log "Generated sample: $VIDEO_FILE"
fi

request() {
  local method=$1
  local url=$2
  local data=${3:-}
  local auth=${4:-}

  if [ -n "$auth" ]; then
    curl -s -X "$method" "$url" -H "Content-Type: application/json" -H "Authorization: Bearer $auth" -d "$data"
  elif [ -n "$data" ]; then
    curl -s -X "$method" "$url" -H "Content-Type: application/json" -d "$data"
  else
    curl -s -X "$method" "$url"
  fi
}

json_get() {
  python3 -c "import sys, json; print(json.load(sys.stdin)[$1])"
}

log "Registering..."
REGISTER_RESP=$(request POST "$API_BASE/auth/register" "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")
if echo "$REGISTER_RESP" | grep -q '"error"'; then
  log "Register response: $REGISTER_RESP"
fi

log "Logging in..."
LOGIN_RESP=$(request POST "$API_BASE/auth/login" "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")
if echo "$LOGIN_RESP" | grep -q '"error"'; then
  fail "Login failed: $LOGIN_RESP"
fi
ACCESS_TOKEN=$(echo "$LOGIN_RESP" | json_get "'access_token'")

log "Init upload..."
SIZE_BYTES=$(stat -f%z "$VIDEO_FILE")
INIT_PAYLOAD=$(cat <<JSON
{"title":"demo","filename":"$(basename "$VIDEO_FILE")","content_type":"video/mp4","size_bytes":$SIZE_BYTES}
JSON
)
INIT_RESP=$(request POST "$API_BASE/videos/upload/init" "$INIT_PAYLOAD" "$ACCESS_TOKEN")
if echo "$INIT_RESP" | grep -q '"error"'; then
  fail "Init failed: $INIT_RESP"
fi
UPLOAD_URL=$(echo "$INIT_RESP" | json_get "'upload_url'")
VIDEO_ID=$(echo "$INIT_RESP" | json_get "'video_id'")
log "Init OK: video_id=$VIDEO_ID"

log "Uploading via presigned URL..."
HTTP_CODE=$(curl -s -o /tmp/upload_resp.txt -w "%{http_code}" -X PUT "$UPLOAD_URL" \
  -H "Content-Type: video/mp4" --data-binary "@$VIDEO_FILE") || true
if [ "$HTTP_CODE" != "200" ] && [ "$HTTP_CODE" != "204" ]; then
  RESP_BODY=$(cat /tmp/upload_resp.txt)
  fail "Upload failed (status=$HTTP_CODE): $RESP_BODY"
fi
log "Upload OK"

log "Complete upload..."
COMPLETE_RESP=$(request POST "$API_BASE/videos/upload/complete" "{\"video_id\":\"$VIDEO_ID\"}" "$ACCESS_TOKEN")
if echo "$COMPLETE_RESP" | grep -q '"error"'; then
  fail "Complete failed: $COMPLETE_RESP"
fi

log "Polling status until ready/failed..."
STATUS=""
for i in $(seq 1 60); do
  DETAIL_RESP=$(request GET "$API_BASE/videos/$VIDEO_ID")
  if echo "$DETAIL_RESP" | grep -q '"error"'; then
    fail "Get video failed: $DETAIL_RESP"
  fi
  STATUS=$(echo "$DETAIL_RESP" | json_get "'status'")
  log "status=$STATUS"
  if [ "$STATUS" = "ready" ] || [ "$STATUS" = "failed" ]; then
    break
  fi
  sleep 2
done

log "Video detail: $DETAIL_RESP"

log "Fetching feed..."
FEED_RESP=$(request GET "$API_BASE/feed")
log "Feed: $FEED_RESP"

if [ "$STATUS" = "failed" ]; then
  fail "Transcode failed"
fi

log "Done"
#!/usr/bin/env bash
set -euo pipefail

API_BASE=${API_BASE:-http://localhost:8000}
VIDEO_FILE=${VIDEO_FILE:-samples/sample.mp4}
EMAIL=${EMAIL:-demo@example.com}
PASSWORD=${PASSWORD:-password123}

log() {
  echo "[$(date +'%H:%M:%S')] $*"
}

fail() {
  echo "[error] $*" >&2
  exit 1
}

if [ ! -f "$VIDEO_FILE" ]; then
  log "Sample video not found: $VIDEO_FILE"
  if ! command -v ffmpeg >/dev/null 2>&1; then
    fail "ffmpeg not found. Please install ffmpeg or provide VIDEO_FILE."
  fi
  log "Generating 3s test video via ffmpeg (color bars + silent audio)..."
  mkdir -p "$(dirname "$VIDEO_FILE")"
  ffmpeg -y \
    -f lavfi -i testsrc=duration=3:size=1280x720:rate=30 \
    -f lavfi -i anullsrc=channel_layout=stereo:sample_rate=44100 \
    -shortest -c:v libx264 -pix_fmt yuv420p -c:a aac \
    "$VIDEO_FILE" >/dev/null 2>&1 || fail "ffmpeg generate failed"
  log "Generated sample: $VIDEO_FILE"
fi

request() {
  local method=$1
  local url=$2
  local data=${3:-}
  local auth=${4:-}

  if [ -n "$auth" ]; then
    curl -s -X "$method" "$url" -H "Content-Type: application/json" -H "Authorization: Bearer $auth" -d "$data"
  elif [ -n "$data" ]; then
    curl -s -X "$method" "$url" -H "Content-Type: application/json" -d "$data"
  else
    curl -s -X "$method" "$url"
  fi
}

json_get() {
  python3 -c "import sys, json; print(json.load(sys.stdin)[$1])"
}

log "Registering..."
REGISTER_RESP=$(request POST "$API_BASE/auth/register" "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")
if echo "$REGISTER_RESP" | grep -q '"error"'; then
  log "Register response: $REGISTER_RESP"
fi

log "Logging in..."
LOGIN_RESP=$(request POST "$API_BASE/auth/login" "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")
if echo "$LOGIN_RESP" | grep -q '"error"'; then
  fail "Login failed: $LOGIN_RESP"
fi
ACCESS_TOKEN=$(echo "$LOGIN_RESP" | json_get "'access_token'")

log "Init upload..."
SIZE_BYTES=$(stat -f%z "$VIDEO_FILE")
INIT_PAYLOAD=$(cat <<JSON
{"title":"demo","filename":"$(basename "$VIDEO_FILE")","content_type":"video/mp4","size_bytes":$SIZE_BYTES}
JSON
)
INIT_RESP=$(request POST "$API_BASE/videos/upload/init" "$INIT_PAYLOAD" "$ACCESS_TOKEN")
if echo "$INIT_RESP" | grep -q '"error"'; then
  fail "Init failed: $INIT_RESP"
fi
UPLOAD_URL=$(echo "$INIT_RESP" | json_get "'upload_url'")
VIDEO_ID=$(echo "$INIT_RESP" | json_get "'video_id'")
log "Init OK: video_id=$VIDEO_ID"

log "Uploading via presigned URL..."
curl -s -X PUT "$UPLOAD_URL" -H "Content-Type: video/mp4" --data-binary "@$VIDEO_FILE" >/dev/null || fail "Upload failed"
log "Upload OK"

log "Complete upload..."
COMPLETE_RESP=$(request POST "$API_BASE/videos/upload/complete" "{\"video_id\":\"$VIDEO_ID\"}" "$ACCESS_TOKEN")
if echo "$COMPLETE_RESP" | grep -q '"error"'; then
  fail "Complete failed: $COMPLETE_RESP"
fi

log "Polling status until ready/failed..."
STATUS=""
for i in $(seq 1 60); do
  DETAIL_RESP=$(request GET "$API_BASE/videos/$VIDEO_ID")
  if echo "$DETAIL_RESP" | grep -q '"error"'; then
    fail "Get video failed: $DETAIL_RESP"
  fi
  STATUS=$(echo "$DETAIL_RESP" | json_get "'status'")
  log "status=$STATUS"
  if [ "$STATUS" = "ready" ] || [ "$STATUS" = "failed" ]; then
    break
  fi
  sleep 2
  done

log "Video detail: $DETAIL_RESP"

log "Fetching feed..."
FEED_RESP=$(request GET "$API_BASE/feed")
log "Feed: $FEED_RESP"

if [ "$STATUS" = "failed" ]; then
  fail "Transcode failed"
fi

log "Done"
