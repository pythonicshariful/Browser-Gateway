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

def get_host_url():
    """Detects current host URL correctly even behind reverse proxy / SSL."""
    scheme = request.headers.get("X-Forwarded-Proto", request.scheme)
    host = request.headers.get("X-Forwarded-Host", request.host)
    return f"{scheme}://{host}"

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
# Video Streaming Proxy for Bunny Stream (mediadelivery.net / b-cdn.net)
# Bypasses 403 Forbidden domain restrictions by injecting whitelisted Referer
# -------------------------------------------------------------

ACTIVE_BUNNY_ZONE = "bcdn_vz-0f119c07-b5a"

# Direct route for /assets/... requested by player.es.js & player.es.css
@app.route("/assets/<path:subpath>", methods=["GET", "OPTIONS"])
def proxy_assets(subpath):
    return proxy_bunny("player", f"assets/{subpath}")

# Direct route for /video/... requested by Bunny player for thumbnails, captchas, VTT, etc.
@app.route("/video/<path:subpath>", methods=["GET", "POST", "OPTIONS"])
def proxy_bunny_video(subpath):
    return proxy_bunny("video", subpath)

# Mock responder for Bunny infra latency/geo pings (edgezone-*.bunnyinfra.net)
@app.route("/bunny/infra/", defaults={"subpath": ""}, methods=["GET", "OPTIONS"])
@app.route("/bunny/infra/<path:subpath>", methods=["GET", "OPTIONS"])
def mock_bunny_infra(subpath):
    if request.method == "OPTIONS":
        resp = Response("", status=200)
    else:
        dummy_jpg = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9"
        resp = Response(dummy_jpg, status=200, content_type="image/jpeg")
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, HEAD, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "*"
    return resp

@app.route("/bunny/<service>/", defaults={"subpath": ""}, methods=["GET", "POST", "OPTIONS"])
@app.route("/bunny/<service>/<path:subpath>", methods=["GET", "POST", "OPTIONS"])
def proxy_bunny(service, subpath):
    global ACTIVE_BUNNY_ZONE
    if service.startswith("bcdn_"):
        ACTIVE_BUNNY_ZONE = service

    if request.method == "OPTIONS":
        resp = Response("", status=200)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, HEAD, OPTIONS"
        resp.headers["Access-Control-Allow-Headers"] = "*"
        return resp

    # Map service name to actual Bunny CDN origin host
    if service == "player":
        target_origin = "https://player.mediadelivery.net"
    elif service == "iframe":
        target_origin = "https://iframe.mediadelivery.net"
    elif service == "video":
        target_origin = "https://video.mediadelivery.net"
    elif service.startswith("bcdn_"):
        zone = service[5:]
        target_origin = f"https://{zone}.b-cdn.net"
    else:
        target_origin = f"https://{service}"

    target_url = f"{target_origin}/{subpath}" if subpath else f"{target_origin}/"
    if request.query_string:
        target_url += f"?{request.query_string.decode('utf-8')}"

    # Crucial: Bunny CDN requires Referer of the licensed customer domain
    headers = {
        "User-Agent": request.headers.get("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"),
        "Referer": "https://hseconomicsbd.com/",
        "Origin": "https://hseconomicsbd.com",
        "Accept": request.headers.get("Accept", "*/*"),
        "Accept-Language": request.headers.get("Accept-Language", "en-US,en;q=0.9"),
    }

    # Pass Range header for video seeking & chunk buffering
    if "Range" in request.headers:
        headers["Range"] = request.headers["Range"]
    if request.content_type:
        headers["Content-Type"] = request.content_type

    try:
        data = request.get_data() if request.method in ["POST", "PUT", "PATCH"] else None
        resp = requests.request(
            method=request.method,
            url=target_url,
            headers=headers,
            data=data,
            stream=True,
            timeout=25,
            allow_redirects=True
        )

        content_type = resp.headers.get("Content-Type", "")
        host_url = get_host_url()

        # 1. HTML Embed Player Page Rewriting
        if "text/html" in content_type:
            html = resp.content.decode(resp.encoding or "utf-8", errors="replace")

            # Rewrite root-relative assets so player.es.js and player.es.css load through /bunny/player/
            html = html.replace('="/assets/', f'="{host_url}/bunny/player/assets/')
            html = html.replace("='/assets/", f"='{host_url}/bunny/player/assets/")
            html = html.replace('="/css/', f'="{host_url}/bunny/player/css/')
            html = html.replace('="/js/', f'="{host_url}/bunny/player/js/')

            # Inject base tag so any remaining relative paths resolve under /bunny/player/
            base_tag = f'<base href="{host_url}/bunny/player/">'
            if "<head>" in html:
                html = html.replace("<head>", f"<head>{base_tag}")
            elif "<head " in html:
                html = re.sub(r'(<head[^>]*>)', r'\1' + base_tag, html, count=1, flags=re.IGNORECASE)

            # Rewrite all internal CDN endpoints so subsequent JS/video calls route through our proxy
            html = re.sub(r'https?://player\.mediadelivery\.net', f'{host_url}/bunny/player', html)
            html = re.sub(r'https?://iframe\.mediadelivery\.net', f'{host_url}/bunny/iframe', html)
            html = re.sub(r'https?://video\.mediadelivery\.net', f'{host_url}/bunny/video', html)
            html = re.sub(r'https?://([a-zA-Z0-9_\-\.]+)\.b-cdn\.net', rf'{host_url}/bunny/bcdn_\1', html)

            html = re.sub(r'//player\.mediadelivery\.net', f'{host_url}/bunny/player', html)
            html = re.sub(r'//iframe\.mediadelivery\.net', f'{host_url}/bunny/iframe', html)
            html = re.sub(r'//video\.mediadelivery\.net', f'{host_url}/bunny/video', html)
            html = re.sub(r'//([a-zA-Z0-9_\-\.]+)\.b-cdn\.net', rf'{host_url}/bunny/bcdn_\1', html)

            flask_resp = Response(html, status=resp.status_code, content_type=content_type)
            flask_resp.headers["Access-Control-Allow-Origin"] = "*"
            flask_resp.headers["Access-Control-Allow-Headers"] = "*"
            return flask_resp

        # 2. JavaScript Rewriting (player.es.js)
        if "javascript" in content_type:
            js_text = resp.content.decode(resp.encoding or "utf-8", errors="replace")
            js_text = re.sub(r'https?://video\.mediadelivery\.net', f'{host_url}/bunny/video', js_text)
            js_text = re.sub(r'https?://iframe\.mediadelivery\.net', f'{host_url}/bunny/iframe', js_text)
            js_text = re.sub(r'https?://([a-zA-Z0-9_\-\.]+)\.b-cdn\.net', rf'{host_url}/bunny/bcdn_\1', js_text)
            js_text = re.sub(r'//video\.mediadelivery\.net', f'{host_url}/bunny/video', js_text)
            js_text = re.sub(r'//([a-zA-Z0-9_\-\.]+)\.b-cdn\.net', rf'{host_url}/bunny/bcdn_\1', js_text)
            # Rewrite bunnyinfra geo/latency probes to our mock responder
            js_text = re.sub(r'https?://[a-zA-Z0-9_\-\.]+\.bunnyinfra\.net', f'{host_url}/bunny/infra', js_text)
            js_text = re.sub(r'//[a-zA-Z0-9_\-\.]+\.bunnyinfra\.net', f'{host_url}/bunny/infra', js_text)

            flask_resp = Response(js_text, status=resp.status_code, content_type=content_type)
            flask_resp.headers["Access-Control-Allow-Origin"] = "*"
            flask_resp.headers["Access-Control-Allow-Headers"] = "*"
            return flask_resp

        # 3. HLS Playlist (.m3u8) Rewriting
        if ".m3u8" in subpath or "mpegurl" in content_type:
            playlist_text = resp.content.decode("utf-8", errors="replace")
            # Rewrite absolute CDN URLs
            playlist_text = re.sub(r'https?://([a-zA-Z0-9_\-\.]+)\.b-cdn\.net', rf'{host_url}/bunny/bcdn_\1', playlist_text)
            playlist_text = re.sub(r'https?://video\.mediadelivery\.net', f'{host_url}/bunny/video', playlist_text)
            
            # Rewrite AES encryption key URI: URI="/fefd803e-.../key/..." -> URI="http://.../bunny/<service>/fefd803e-.../key/..."
            playlist_text = re.sub(
                r'URI=["\']/(.*?)["\']',
                rf'URI="{host_url}/bunny/{service}/\1"',
                playlist_text
            )
            # Rewrite any root-relative segment paths (lines starting with /)
            rewritten_lines = []
            for line in playlist_text.splitlines():
                stripped = line.strip()
                if stripped.startswith("/") and not stripped.startswith("//"):
                    rewritten_lines.append(f"{host_url}/bunny/{service}{stripped}")
                else:
                    rewritten_lines.append(line)
            playlist_text = "\n".join(rewritten_lines)

            flask_resp = Response(playlist_text, status=resp.status_code, content_type=content_type)
            flask_resp.headers["Access-Control-Allow-Origin"] = "*"
            flask_resp.headers["Access-Control-Allow-Headers"] = "*"
            return flask_resp

        # 4. Video Segments (.ts, .dts, .m4s, .mp4, keys, CSS, images, fonts)
        forward_headers = {}
        for h in ["Content-Type", "Content-Length", "Content-Range", "Accept-Ranges", "ETag", "Last-Modified"]:
            if h in resp.headers:
                forward_headers[h] = resp.headers[h]

        forward_headers["Access-Control-Allow-Origin"] = "*"
        forward_headers["Access-Control-Allow-Methods"] = "GET, POST, HEAD, OPTIONS"
        forward_headers["Access-Control-Allow-Headers"] = "*"

        return Response(
            resp.iter_content(chunk_size=65536),
            status=resp.status_code,
            headers=forward_headers,
            content_type=content_type
        )

    except Exception as e:
        return f"Video Gateway Error: {str(e)}", 502

# -------------------------------------------------------------
# Clean, Public Web Proxy
# Intercepts all paths, enforces IP/Device block rules,
# and proxies with full student session
# -------------------------------------------------------------

@app.route("/", defaults={"subpath": ""}, methods=["GET", "POST", "PUT", "DELETE"])
@app.route("/<path:subpath>", methods=["GET", "POST", "PUT", "DELETE"])
def proxy_all(subpath):
    # Do not intercept admin, static, assets, or video proxy routes
    if (subpath.startswith("admin") or subpath.startswith("_admin") or 
        subpath.startswith("_hub") or subpath.startswith("_static") or 
        subpath.startswith("api/") or subpath.startswith("bunny/") or
        subpath.startswith("assets/") or subpath.startswith("video/")):
        return "Not found", 404

    # Catch any UUID-prefixed video asset or encryption key mistakenly requested from root
    # e.g. /fefd803e-9221-414f-87fc-0b0b976f5586/key/...
    if re.match(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}/', subpath):
        return proxy_bunny(ACTIVE_BUNNY_ZONE, subpath)

    # Intercept logout and password change to protect student account from being altered/destroyed
    if subpath.startswith("logout") or "profile-password" in subpath or "password-change" in subpath:
        return redirect("/dashboard/profile")

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

        host_url = get_host_url()

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

        # HTML content: Clean URL rewrite
        if "text/html" in content_type:
            html = resp.content.decode(resp.encoding or "utf-8", errors="replace")

            # 1. Rewrite all target domain URLs to current host URL
            html = html.replace("https://hseconomicsbd.com", host_url)
            html = html.replace("http://hseconomicsbd.com", host_url)
            html = html.replace("//hseconomicsbd.com", host_url.replace("http:", "").replace("https:", ""))

            # 2. Rewrite Bunny Stream video iframes to route through our /bunny proxy
            # This fixes the 403 Forbidden on videos when hosted on external domains/localhost!
            html = re.sub(r'https?://player\.mediadelivery\.net/embed/', f'{host_url}/bunny/player/embed/', html)
            html = re.sub(r'//player\.mediadelivery\.net/embed/', f'{host_url}/bunny/player/embed/', html)
            html = re.sub(r'https?://iframe\.mediadelivery\.net/embed/', f'{host_url}/bunny/iframe/embed/', html)
            html = re.sub(r'//iframe\.mediadelivery\.net/embed/', f'{host_url}/bunny/iframe/embed/', html)

            # 3. Disable and remove Logout and Password Change buttons from the student profile dropdown
            html = re.sub(
                r'<li[^>]*>\s*<a[^>]*href=["\'][^"\']*(?:logout|profile-password)[^"\']*["\'][^>]*>.*?</a>\s*</li>',
                '',
                html,
                flags=re.IGNORECASE | re.DOTALL
            )

            # 4. Inject CSS shield to hide any logout or password change links/buttons across all pages
            account_shield = """
            <style id="__hs_account_shield">
                a[href*="logout"], 
                a[href*="Logout"], 
                a[href*="profile-password"],
                a[href*="password-change"],
                .dropdown-item[href*="logout"],
                .dropdown-item[href*="profile-password"],
                li:has(a[href*="logout"]),
                li:has(a[href*="profile-password"]) {
                    display: none !important;
                    visibility: hidden !important;
                    pointer-events: none !important;
                }
            </style>
            """
            if "</head>" in html:
                html = html.replace("</head>", f"{account_shield}</head>")
            elif "<body" in html:
                html = re.sub(r'(<body[^>]*>)', r'\1' + account_shield, html, count=1, flags=re.IGNORECASE)

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
    print("🚀 HS Economics Gateway Active with Video Stream Proxy")
    print("🌐 Public Web Version (No Admin Controls): http://127.0.0.1:5000")
    print("🛡️ Admin Panel & IP/Device Manager: http://127.0.0.1:5000/admin")
    print("🎥 Video Stream Proxy Enabled: /bunny/player/... -> mediadelivery.net")
    print("🔑 Default Admin Password: admin")
    print("=============================================================")
    app.run(host="0.0.0.0", port=5000, debug=True)
