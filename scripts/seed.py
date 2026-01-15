import json
import os
import sys
import urllib.error
import urllib.request

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
EMAIL = os.getenv("SEED_EMAIL", "demo@example.com")
PASSWORD = os.getenv("SEED_PASSWORD", "password123")
VIDEO_PATH = os.getenv("VIDEO_PATH", os.path.join(os.path.dirname(__file__), "sample.mp4"))


def request_json(method: str, url: str, payload: dict | None = None, headers: dict | None = None):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = headers or {}
    headers.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def put_file(url: str, path: str, content_type: str) -> int:
    with open(path, "rb") as f:
        data = f.read()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": content_type}, method="PUT")
    with urllib.request.urlopen(req) as resp:
        return resp.status


def main() -> None:
    if not os.path.exists(VIDEO_PATH):
        print(f"Sample video not found: {VIDEO_PATH}")
        print("Please provide a valid mp4 file via VIDEO_PATH env.")
        sys.exit(1)

    status, register_resp = request_json(
        "POST",
        f"{BASE_URL}/auth/register",
        {"email": EMAIL, "password": PASSWORD},
    )
    if status != 200:
        print("Register failed, try login.", register_resp)

    status, login_resp = request_json(
        "POST",
        f"{BASE_URL}/auth/login",
        {"email": EMAIL, "password": PASSWORD},
    )
    if status != 200:
        print("Login failed", login_resp)
        sys.exit(1)

    access_token = login_resp["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    size_bytes = os.path.getsize(VIDEO_PATH)
    init_payload = {
        "title": "demo",
        "filename": os.path.basename(VIDEO_PATH),
        "content_type": "video/mp4",
        "size_bytes": size_bytes,
    }

    status, init_resp = request_json(
        "POST",
        f"{BASE_URL}/videos/upload/init",
        init_payload,
        headers=headers,
    )
    if status != 200:
        print("Init upload failed", init_resp)
        sys.exit(1)

    upload_url = init_resp["upload_url"]
    object_key = init_resp["object_key"]
    video_id = init_resp["video_id"]

    put_status = put_file(upload_url, VIDEO_PATH, "video/mp4")
    if put_status not in (200, 204):
        print("Upload failed", put_status)
        sys.exit(1)

    status, complete_resp = request_json(
        "POST",
        f"{BASE_URL}/videos/upload/complete",
        {"video_id": video_id},
        headers=headers,
    )
    if status != 200:
        print("Complete failed", complete_resp)
        sys.exit(1)

    status, feed_resp = request_json("GET", f"{BASE_URL}/feed")
    print("Feed:", json.dumps(feed_resp, indent=2))


if __name__ == "__main__":
    main()
