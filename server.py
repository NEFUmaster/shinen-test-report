from __future__ import annotations

import cgi
import base64
import hmac
import json
import mimetypes
import os
import re
import shutil
import uuid
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse


ROOT = Path(__file__).resolve().parent
PUBLIC_DIR = ROOT / "public"
STORAGE_ROOT = Path(os.environ.get("APP_STORAGE_DIR", ROOT)).resolve()
UPLOAD_DIR = STORAGE_ROOT / "uploads"
DATA_FILE = STORAGE_ROOT / "data" / "reports.json"
SEED_UPLOAD_DIR = ROOT / "uploads"
SEED_DATA_FILE = ROOT / "data" / "reports.json"
MAX_UPLOAD_BYTES = 30 * 1024 * 1024
BRAND_PREFIX = "/shinen"
ADMIN_PATH = f"{BRAND_PREFIX}/shinenadmin"
ADMIN_REALM = "Shinen Admin"


def read_reports() -> list[dict]:
    if not DATA_FILE.exists():
        return []
    with DATA_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def write_reports(reports: list[dict]) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp_file = DATA_FILE.with_suffix(".tmp")
    with tmp_file.open("w", encoding="utf-8") as file:
        json.dump(reports, file, ensure_ascii=False, indent=2)
    os.replace(tmp_file, DATA_FILE)


def clean_text(value: str | None, fallback: str = "") -> str:
    if value is None:
        return fallback
    value = re.sub(r"\s+", " ", value).strip()
    return value or fallback


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def seed_storage() -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists() and SEED_DATA_FILE.exists():
        shutil.copy2(SEED_DATA_FILE, DATA_FILE)
    if SEED_UPLOAD_DIR.exists():
        for source in SEED_UPLOAD_DIR.glob("*.pdf"):
            target = UPLOAD_DIR / source.name
            if not target.exists():
                shutil.copy2(source, target)


class ReportServer(BaseHTTPRequestHandler):
    server_version = "ReportServer/1.0"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/":
            self.redirect(f"{BRAND_PREFIX}/")
            return

        if path == f"{BRAND_PREFIX}/api/reports":
            self.send_json({"reports": sorted(read_reports(), key=lambda item: item.get("createdAt", ""), reverse=True)})
            return

        if path.startswith(f"{BRAND_PREFIX}/uploads/"):
            self.serve_upload(path.removeprefix(f"{BRAND_PREFIX}/uploads/"))
            return

        if path in (BRAND_PREFIX, f"{BRAND_PREFIX}/"):
            self.serve_public("index.html")
            return

        if path == ADMIN_PATH:
            if not self.require_admin_auth():
                return
            self.serve_public("admin.html")
            return

        if path.startswith(f"{BRAND_PREFIX}/assets/"):
            self.serve_public(path.removeprefix(f"{BRAND_PREFIX}/assets/"))
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self) -> None:
        if urlparse(self.path).path != f"{BRAND_PREFIX}/api/reports":
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return
        if not self.require_admin_auth():
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0 or content_length > MAX_UPLOAD_BYTES:
            self.send_json({"error": "文件大小不能超过 30MB"}, HTTPStatus.BAD_REQUEST)
            return

        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={
                "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": self.headers.get("Content-Type", ""),
                "CONTENT_LENGTH": str(content_length),
            },
        )

        if "file" not in form:
            self.send_json({"error": "请选择 PDF 文件"}, HTTPStatus.BAD_REQUEST)
            return

        file_item = form["file"]
        original_name = Path(file_item.filename or "report.pdf").name
        file_bytes = file_item.file.read()
        if not original_name.lower().endswith(".pdf") or not file_bytes.startswith(b"%PDF"):
            self.send_json({"error": "只能上传有效的 PDF 文件"}, HTTPStatus.BAD_REQUEST)
            return

        report_id = f"report-{uuid.uuid4().hex[:12]}"
        filename = f"{report_id}.pdf"
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        with (UPLOAD_DIR / filename).open("wb") as file:
            file.write(file_bytes)

        report = {
            "id": report_id,
            "title": clean_text(form.getfirst("title"), Path(original_name).stem),
            "category": clean_text(form.getfirst("category"), "未分类"),
            "description": clean_text(form.getfirst("description"), ""),
            "originalName": original_name,
            "filename": filename,
            "createdAt": now_iso(),
        }

        reports = read_reports()
        reports.append(report)
        write_reports(reports)
        self.send_json({"report": report}, HTTPStatus.CREATED)

    def do_PUT(self) -> None:
        if not self.require_admin_auth():
            return

        report_id = self.report_id_from_path()
        if not report_id:
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return

        payload = self.read_json_body()
        reports = read_reports()
        for report in reports:
            if report.get("id") == report_id:
                report["title"] = clean_text(payload.get("title"), report.get("title", "未命名报告"))
                report["category"] = clean_text(payload.get("category"), report.get("category", "未分类"))
                report["description"] = clean_text(payload.get("description"), "")
                write_reports(reports)
                self.send_json({"report": report})
                return

        self.send_json({"error": "报告不存在"}, HTTPStatus.NOT_FOUND)

    def do_DELETE(self) -> None:
        if not self.require_admin_auth():
            return

        report_id = self.report_id_from_path()
        if not report_id:
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return

        reports = read_reports()
        keep_reports = [report for report in reports if report.get("id") != report_id]
        removed = next((report for report in reports if report.get("id") == report_id), None)
        if not removed:
            self.send_json({"error": "报告不存在"}, HTTPStatus.NOT_FOUND)
            return

        write_reports(keep_reports)
        file_path = UPLOAD_DIR / removed.get("filename", "")
        if file_path.exists() and file_path.is_file():
            file_path.unlink()

        self.send_json({"ok": True})

    def serve_public(self, relative_path: str) -> None:
        file_path = (PUBLIC_DIR / relative_path).resolve()
        if not str(file_path).startswith(str(PUBLIC_DIR.resolve())) or not file_path.exists() or not file_path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return

        content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8" if content_type.startswith("text/") else content_type)
        self.send_header("Content-Length", str(file_path.stat().st_size))
        self.end_headers()
        with file_path.open("rb") as file:
            shutil.copyfileobj(file, self.wfile)

    def serve_upload(self, filename: str) -> None:
        safe_name = Path(unquote(filename)).name
        file_path = (UPLOAD_DIR / safe_name).resolve()
        if not str(file_path).startswith(str(UPLOAD_DIR.resolve())) or not file_path.exists() or not file_path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/pdf")
        self.send_header("Content-Disposition", f'inline; filename="{safe_name}"')
        self.send_header("Content-Length", str(file_path.stat().st_size))
        self.end_headers()
        with file_path.open("rb") as file:
            shutil.copyfileobj(file, self.wfile)

    def report_id_from_path(self) -> str | None:
        path = urlparse(self.path).path
        match = re.fullmatch(fr"{BRAND_PREFIX}/api/reports/([A-Za-z0-9_-]+)", path)
        return match.group(1) if match else None

    def redirect(self, location: str) -> None:
        self.send_response(HTTPStatus.FOUND)
        self.send_header("Location", location)
        self.end_headers()

    def read_json_body(self) -> dict:
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0:
            return {}
        raw = self.rfile.read(content_length).decode("utf-8")
        return json.loads(raw or "{}")

    def require_admin_auth(self) -> bool:
        password = os.environ.get("ADMIN_PASSWORD", "")
        username = os.environ.get("ADMIN_USER", "shinen")
        if not password:
            self.send_text(
                "ADMIN_PASSWORD is not configured. Set ADMIN_USER and ADMIN_PASSWORD before using the admin area.",
                HTTPStatus.SERVICE_UNAVAILABLE,
            )
            return False

        auth_header = self.headers.get("Authorization", "")
        if auth_header.startswith("Basic "):
            try:
                raw = base64.b64decode(auth_header.removeprefix("Basic ").strip()).decode("utf-8")
                provided_user, provided_password = raw.split(":", 1)
                if hmac.compare_digest(provided_user, username) and hmac.compare_digest(provided_password, password):
                    return True
            except (ValueError, UnicodeDecodeError):
                pass

        self.send_response(HTTPStatus.UNAUTHORIZED)
        self.send_header("WWW-Authenticate", f'Basic realm="{ADMIN_REALM}", charset="UTF-8"')
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write("Authentication required".encode("utf-8"))
        return False

    def send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_text(self, text: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {format % args}")


def main() -> None:
    seed_storage()
    port = int(os.environ.get("PORT", "8000"))
    host = os.environ.get("HOST", "0.0.0.0")
    server = ThreadingHTTPServer((host, port), ReportServer)
    print(f"Shinen local site: http://127.0.0.1:{port}{BRAND_PREFIX}/")
    print(f"Shinen LAN site: http://<your-computer-ip>:{port}{BRAND_PREFIX}/")
    print(f"Shinen admin: http://<your-computer-ip>:{port}{ADMIN_PATH}")
    server.serve_forever()


if __name__ == "__main__":
    main()
