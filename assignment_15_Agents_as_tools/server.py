#!/usr/bin/env python3
import json
import os
import smtplib
from email.message import EmailMessage
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_PATH = os.path.join(BASE_DIR, "index.html")

HARDCODED_TO = "22dsyndergaard@gmail.com"


def _read_body(handler):
    length = int(handler.headers.get("Content-Length", "0"))
    return handler.rfile.read(length) if length > 0 else b""


def _json_response(handler, status, payload):
    data = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def _get_env(name, default=None):
    value = os.getenv(name)
    if value is None:
        return default
    return value


def _send_email(name, email, message, subject=None):
    smtp_host = _get_env("SMTP_HOST")
    smtp_port = int(_get_env("SMTP_PORT", "587"))
    smtp_user = _get_env("SMTP_USERNAME")
    smtp_pass = _get_env("SMTP_PASSWORD")
    smtp_from = _get_env("SMTP_FROM", smtp_user)
    use_tls = _get_env("SMTP_USE_TLS", "true").lower() in ("1", "true", "yes")

    if not smtp_host or not smtp_user or not smtp_pass or not smtp_from:
        raise RuntimeError("SMTP settings missing. Set SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD, SMTP_FROM.")

    msg = EmailMessage()
    msg["From"] = smtp_from
    msg["To"] = HARDCODED_TO
    msg["Subject"] = subject or f"Website request from {name}"
    if email:
        msg["Reply-To"] = email

    body_lines = [
        "New request submitted from the website:",
        "",
        f"Name: {name}",
        f"Email: {email or 'Not provided'}",
        "",
        "Message:",
        message,
    ]
    msg.set_content("\n".join(body_lines))

    with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
        if use_tls:
            server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            try:
                with open(INDEX_PATH, "rb") as f:
                    data = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            except FileNotFoundError:
                _json_response(self, 404, {"error": "index.html not found"})
                return

        if self.path == "/api/health":
            _json_response(self, 200, {"ok": True})
            return

        _json_response(self, 404, {"error": "Not found"})

    def do_POST(self):
        if self.path != "/api/send-email":
            _json_response(self, 404, {"error": "Not found"})
            return

        body = _read_body(self)
        content_type = (self.headers.get("Content-Type") or "").lower()

        payload = {}
        if "application/json" in content_type:
            try:
                payload = json.loads(body.decode("utf-8") or "{}")
            except json.JSONDecodeError:
                _json_response(self, 400, {"error": "Invalid JSON"})
                return
        elif "application/x-www-form-urlencoded" in content_type:
            parsed = parse_qs(body.decode("utf-8"))
            payload = {k: v[0] for k, v in parsed.items()}
        else:
            _json_response(self, 415, {"error": "Unsupported Content-Type"})
            return

        name = (payload.get("name") or "").strip()
        email = (payload.get("email") or "").strip()
        message = (payload.get("message") or "").strip()
        subject = (payload.get("subject") or "").strip() or None

        if not name or not message:
            _json_response(self, 400, {"error": "Name and message are required"})
            return

        try:
            _send_email(name, email, message, subject=subject)
        except Exception as exc:
            _json_response(self, 500, {"error": str(exc)})
            return

        _json_response(self, 200, {"ok": True})


if __name__ == "__main__":
    host = _get_env("HOST", "0.0.0.0")
    port = int(_get_env("PORT", "8000"))
    httpd = HTTPServer((host, port), Handler)
    print(f"Server running on http://{host}:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
