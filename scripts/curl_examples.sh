#!/usr/bin/env bash
set -euo pipefail

BASE_URL=${BASE_URL:-http://localhost:8000}
EMAIL=${EMAIL:-demo@example.com}
PASSWORD=${PASSWORD:-password123}
VIDEO_PATH=${VIDEO_PATH:-./scripts/sample.mp4}

if [ ! -f "$VIDEO_PATH" ]; then
  echo "Sample video not found: $VIDEO_PATH"
  exit 1
fi

REGISTER=$(curl -s -X POST "$BASE_URL/auth/register" \
  -H 'Content-Type: application/json' \
  -d '{"email":"'"$EMAIL"'","password":"'"$PASSWORD"'"}')

echo "Register: $REGISTER"

LOGIN=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H 'Content-Type: application/json' \
  -d '{"email":"'"$EMAIL"'","password":"'"$PASSWORD"'"}')

echo "Login: $LOGIN"

ACCESS_TOKEN=$(echo "$LOGIN" | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

INIT=$(curl -s -X POST "$BASE_URL/videos/upload/init" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{"title":"demo","filename":"'"$(basename "$VIDEO_PATH")"'","content_type":"video/mp4","size_bytes":'"$(stat -f%z "$VIDEO_PATH")"'}')

echo "Init: $INIT"

UPLOAD_URL=$(echo "$INIT" | python -c "import sys, json; print(json.load(sys.stdin)['upload_url'])")
VIDEO_ID=$(echo "$INIT" | python -c "import sys, json; print(json.load(sys.stdin)['video_id'])")

curl -s -X PUT "$UPLOAD_URL" \
  -H "Content-Type: video/mp4" \
  --data-binary "@$VIDEO_PATH" >/dev/null

echo "Upload done"

COMPLETE=$(curl -s -X POST "$BASE_URL/videos/upload/complete" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{"video_id":"'"$VIDEO_ID"'"}')

echo "Complete: $COMPLETE"

FEED=$(curl -s "$BASE_URL/feed")

echo "Feed: $FEED"
