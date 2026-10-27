import os
import re
import requests
from urllib.parse import urljoin, urlparse
from flask import (
    Flask, render_template, request, Response, 
    jsonify, redirect, url_for, session as flask_session
)
from config import load_config, save_config
from browser_launcher import launch_browser
from device_manager import (
    load_device_data, track_request, set_device_name,
    set_device_block, toggle_ip_block
)

# Use /_static to avoid conflicts with website's own /static assets
app = Flask(__name__, static_url_path="/_static")
app.secret_key = "hs_economics_gateway_secret_key_darkwolf_9898"

http_session = requests.Session()

def is_admin():
    return flask_session.get("is_admin", False)

def get_target_headers(subpath=""):
    config = load_config()
    cookies = config.get("cookies", {})
    
    # Merge configured cookies with any incoming cookies from client browser
    merged_cookies = dict(cookies)
    for c_name, c_val in request.cookies.items():
        if c_name not in merged_cookies and not c_name.startswith("_hs_"):
            merged_cookies[c_name] = c_val

    cookie_str = "; ".join([f"{k}={v}" for k, v in merged_cookies.items()])
    target_base = config.get("target_url", "https://hseconomicsbd.com").rstrip("/")
    referer_url = f"{target_base}/{subpath}" if subpath else f"{target_base}/"

    return {
        "Host": "hseconomicsbd.com",
        "Origin": "https://hseconomicsbd.com",
        "Referer": referer_url,
        "User-Agent": config.get("user_agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"),
        "Cookie": cookie_str,
        "Accept": request.headers.get("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"),
        "Accept-Language": request.headers.get("Accept-Language", "en-US,en;q=0.9"),
    }

# -------------------------------------------------------------
# Admin Control Panel Routes (/admin) - Protected
# -------------------------------------------------------------

@app.route("/admin")
@app.route("/_admin")
def admin_panel():
    """Admin Control Hub with Device/IP Management and Session Controls."""
    if not is_admin():
        return render_template("login.html")
    config = load_config()
    device_data = load_device_data()
    return render_template("index.html", config=config, device_data=device_data)

@app.route("/_hub")
def hub_redirect():
    return redirect("/admin")

@app.route("/admin/login", methods=["POST"])
def admin_login():
    """Authenticates admin password."""
    password = request.form.get("password", "")
    config = load_config()
    expected_password = config.get("admin_password", "admin")

    if password == expected_password:
        flask_session["is_admin"] = True
        return redirect("/admin")
    else:
        return render_template("login.html", error="Invalid admin password. Please try again.")

@app.route("/admin/logout")
@app.route("/_hub/logout")
def admin_logout():
    """Logs out admin."""
    flask_session.pop("is_admin", None)
    return redirect("/admin")

# -------------------------------------------------------------
# Admin API: Device & IP Management
# -------------------------------------------------------------

@app.route("/api/devices", methods=["GET"])
def api_get_devices():
    if not is_admin():
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
    return jsonify(load_device_data())

@app.route("/api/device/rename", methods=["POST"])
def api_device_rename():
    if not is_admin():
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
    data = request.json or {}
    device_id = data.get("device_id")
    name = data.get("name", "")
    if set_device_name(device_id, name):
        return jsonify({"status": "success", "message": "Device renamed successfully."})
    return jsonify({"status": "error", "message": "Device not found."}), 404

@app.route("/api/device/block", methods=["POST"])
def api_device_block():
    if not is_admin():
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
    data = request.json or {}
    device_id = data.get("device_id")
    blocked = data.get("blocked", False)
    if set_device_block(device_id, blocked):
        return jsonify({"status": "success", "message": f"Device {'blocked' if blocked else 'unblocked'} successfully."})
    return jsonify({"status": "error", "message": "Device not found."}), 404

@app.route("/api/ip/block", methods=["POST"])
def api_ip_block():
    if not is_admin():
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
    data = request.json or {}
    ip = data.get("ip", "")
    blocked = data.get("blocked", False)
    if toggle_ip_block(ip, blocked):
        return jsonify({"status": "success", "message": f"IP {ip} {'blocked' if blocked else 'unblocked'} successfully."})
    return jsonify({"status": "error", "message": "Invalid IP address."}), 400

# -------------------------------------------------------------
# Admin API: Session & Browser Config
# -------------------------------------------------------------

@app.route("/api/config", methods=["GET"])
def get_config():
    if not is_admin():
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
    return jsonify(load_config())

@app.route("/api/config", methods=["POST"])
def update_config():
    if not is_admin():
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    data = request.json or {}
    config = load_config()
    if "cookies" in data:
        config["cookies"].update(data["cookies"])
    if "target_url" in data:
        config["target_url"] = data["target_url"]
    if "browser_type" in data:
        config["browser_type"] = data["browser_type"]
    if "admin_password" in data and data["admin_password"]:
        config["admin_password"] = data["admin_password"]
    save_config(config)
    return jsonify({"status": "success", "config": config})

@app.route("/api/check-session", methods=["GET"])
def check_session():
    if not is_admin():
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    config = load_config()
    target_url = config.get("target_url", "https://hseconomicsbd.com")
    headers = get_target_headers()

    try:
        resp = http_session.get(target_url, headers=headers, timeout=10, allow_redirects=True)
        html = resp.text.lower()

        student_id = str(config.get("cookies", {}).get("hseastudentId", "1035"))
        is_authenticated = (
            student_id in html 
            or "logout" in html 
            or "dashboard" in html 
            or "profile" in html
        ) and ("login" not in resp.url.lower() or "student" in resp.url.lower())

        return jsonify({
            "status": "success",
            "http_status": resp.status_code,
            "final_url": resp.url,
            "authenticated": is_authenticated,
            "title_preview": re.search(r"<title>(.*?)</title>", resp.text, re.IGNORECASE).group(1) if re.search(r"<title>(.*?)</title>", resp.text, re.IGNORECASE) else "N/A"
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route("/api/launch-browser", methods=["POST"])
def api_launch_browser():
    if not is_admin():
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    data = request.json or {}
    browser_type = data.get("browser_type")
    success, msg = launch_browser(browser_type)
    if success:
        return jsonify({"status": "success", "message": msg})
    else:
        return jsonify({"status": "error", "message": msg}), 500

# -------------------------------------------------------------
# Clean, Public Web Proxy
# Intercepts all paths, enforces IP/Device block rules,
# and proxies with full student session
# -------------------------------------------------------------

@app.route("/", defaults={"subpath": ""}, methods=["GET", "POST", "PUT", "DELETE"])
@app.route("/<path:subpath>", methods=["GET", "POST", "PUT", "DELETE"])
def proxy_all(subpath):
    # Do not intercept admin or static routes
    if subpath.startswith("admin") or subpath.startswith("_admin") or subpath.startswith("_hub") or subpath.startswith("_static") or subpath.startswith("api/"):
        return "Not found", 404

    # 1. Device and IP Tracking & Firewall Check
    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr).split(",")[0].strip()
    device_cookie = request.cookies.get("_hs_device_id")
    device_id, is_blocked = track_request(device_cookie, client_ip, request.headers.get("User-Agent", ""))

    if is_blocked:
        blocked_page = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>403 - Access Denied</title>
            <style>
                body {{ background: #0b0f17; color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, sans-serif; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; padding: 20px; box-sizing: border-box; }}
                .box {{ max-width: 480px; width: 100%; background: #131b2e; border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 16px; padding: 36px 28px; text-align: center; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }}
                .icon {{ font-size: 48px; margin-bottom: 16px; }}
                h1 {{ color: #ef4444; font-size: 22px; margin: 0 0 10px; font-weight: 700; }}
                p {{ color: #94a3b8; font-size: 14px; line-height: 1.5; margin: 0 0 20px; }}
                .badge {{ display: inline-block; background: #1e293b; color: #64748b; font-family: monospace; font-size: 12px; padding: 6px 12px; border-radius: 6px; }}
            </style>
        </head>
        <body>
            <div class="box">
                <div class="icon">🚫</div>
                <h1>Access Blocked</h1>
                <p>Your IP address or device has been blocked by the system administrator.</p>
                <div class="badge">IP: {client_ip} &bull; ID: {device_id}</div>
            </div>
        </body>
        </html>
        """
        resp = Response(blocked_page, status=403, content_type="text/html")
        resp.set_cookie("_hs_device_id", device_id, max_age=315360000, path="/")
        return resp

    config = load_config()
    target_base = config.get("target_url", "https://hseconomicsbd.com").rstrip("/")
    target_url = f"{target_base}/{subpath}" if subpath else f"{target_base}/"
    if request.query_string:
        target_url += f"?{request.query_string.decode('utf-8')}"

    headers = get_target_headers(subpath)
    if request.content_type:
        headers["Content-Type"] = request.content_type

    try:
        req_method = getattr(http_session, request.method.lower(), http_session.get)
        data = request.get_data() if request.method in ["POST", "PUT", "PATCH"] else None

        resp = req_method(
            target_url,
            headers=headers,
            data=data,
            allow_redirects=False,
            stream=True,
            timeout=20
        )

        host_url = request.host_url.rstrip("/")

        # Handle redirects (301, 302, 303, 307, 308)
        if resp.status_code in [301, 302, 303, 307, 308]:
            location = resp.headers.get("Location", "")
            if location.startswith("https://hseconomicsbd.com"):
                location = location.replace("https://hseconomicsbd.com", host_url)
            elif location.startswith("http://hseconomicsbd.com"):
                location = location.replace("http://hseconomicsbd.com", host_url)
            elif location.startswith("//hseconomicsbd.com"):
                location = location.replace("//hseconomicsbd.com", host_url.replace("http:", "").replace("https:", ""))

            flask_resp = redirect(location, code=resp.status_code)
            # Sync session cookies & device cookie
            for k, v in config.get("cookies", {}).items():
                flask_resp.set_cookie(k, str(v), path="/")
            flask_resp.set_cookie("_hs_device_id", device_id, max_age=315360000, path="/")
            return flask_resp

        # Persist updated session cookies from origin (e.g. rotated PHPSESSID)
        if resp.cookies:
            updated = False
            for c in resp.cookies:
                if config["cookies"].get(c.name) != c.value:
                    config["cookies"][c.name] = c.value
                    updated = True
            if updated:
                save_config(config)

        content_type = resp.headers.get("Content-Type", "")

        # HTML content: Clean URL rewrite without injecting any pills/badges
        if "text/html" in content_type:
            html = resp.content.decode(resp.encoding or "utf-8", errors="replace")

            # Rewrite all target domain URLs to local server URL so user stays on session
            html = html.replace("https://hseconomicsbd.com", host_url)
            html = html.replace("http://hseconomicsbd.com", host_url)
            html = html.replace("//hseconomicsbd.com", host_url.replace("http:", "").replace("https:", ""))

            flask_resp = Response(html, status=resp.status_code, content_type=content_type)
            # Sync cookies to client
            for k, v in config.get("cookies", {}).items():
                flask_resp.set_cookie(k, str(v), path="/")
            flask_resp.set_cookie("_hs_device_id", device_id, max_age=315360000, path="/")
            return flask_resp

        # Non-HTML content (images, JS, CSS, fonts, PDFs, SVGs)
        excluded_headers = [
            "content-encoding", "content-length", "transfer-encoding", "connection",
            "content-security-policy", "content-security-policy-report-only",
            "strict-transport-security", "x-frame-options"
        ]
        headers = [(k, v) for k, v in resp.raw.headers.items() if k.lower() not in excluded_headers]
        flask_resp = Response(resp.iter_content(chunk_size=8192), status=resp.status_code, headers=headers, content_type=content_type)
        flask_resp.set_cookie("_hs_device_id", device_id, max_age=315360000, path="/")
        return flask_resp

    except Exception as e:
        return f"""
        <div style="font-family:sans-serif;padding:30px;max-width:600px;margin:50px auto;background:#fff;border-radius:8px;box-shadow:0 4px 12px rgba(0,0,0,0.1);">
            <h2 style="color:#ef4444;margin-top:0;">Gateway Error</h2>
            <p>Could not connect to target page: <code>{target_url}</code></p>
            <pre style="background:#f1f5f9;padding:12px;border-radius:6px;font-size:12px;overflow-x:auto;">{str(e)}</pre>
        </div>
        """, 502

if __name__ == "__main__":
    print("=============================================================")
    print("🚀 HS Economics Gateway Active")
    print("🌐 Public Web Version (No Admin Controls): http://127.0.0.1:5000")
    print("🛡️ Admin Panel & IP/Device Manager: http://127.0.0.1:5000/admin")
    print("🔑 Default Admin Password: admin")
    print("=============================================================")
    app.run(host="0.0.0.0", port=5000, debug=True)
