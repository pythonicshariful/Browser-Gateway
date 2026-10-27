import os
import json
import time
import uuid
from datetime import datetime

DEVICES_FILE = os.path.join(os.path.dirname(__file__), "devices.json")

def load_device_data():
    if os.path.exists(DEVICES_FILE):
        try:
            with open(DEVICES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"devices": {}, "blocked_ips": []}

def save_device_data(data):
    with open(DEVICES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def parse_user_agent(ua_string):
    """Simple, dependency-free OS & Browser detector."""
    ua = (ua_string or "").lower()
    os_name = "Unknown OS"
    browser_name = "Unknown Browser"

    # Detect OS
    if "windows" in ua:
        os_name = "Windows"
    elif "android" in ua:
        os_name = "Android"
    elif "iphone" in ua or "ipod" in ua:
        os_name = "iPhone"
    elif "ipad" in ua:
        os_name = "iPad"
    elif "macintosh" in ua or "mac os" in ua:
        os_name = "macOS"
    elif "linux" in ua:
        os_name = "Linux"

    # Detect Browser
    if "edg" in ua:
        browser_name = "Edge"
    elif "chrome" in ua and "safari" in ua and "edg" not in ua:
        browser_name = "Chrome"
    elif "firefox" in ua:
        browser_name = "Firefox"
    elif "safari" in ua and "chrome" not in ua:
        browser_name = "Safari"
    elif "opera" in ua or "opr" in ua:
        browser_name = "Opera"

    return os_name, browser_name

def track_request(device_id, ip_address, user_agent):
    """
    Records or updates a device interaction.
    Returns (device_id, is_blocked)
    """
    data = load_device_data()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # If IP is explicitly blocked
    if ip_address in data.get("blocked_ips", []):
        return device_id, True

    if not device_id or device_id not in data["devices"]:
        device_id = device_id or f"dev_{uuid.uuid4().hex[:8]}"
        os_name, browser_name = parse_user_agent(user_agent)
        data["devices"][device_id] = {
            "id": device_id,
            "ip": ip_address,
            "user_agent": user_agent or "Unknown",
            "os": os_name,
            "browser": browser_name,
            "custom_name": f"{os_name} ({browser_name})",
            "blocked": False,
            "first_seen": now_str,
            "last_seen": now_str,
            "requests_count": 1
        }
    else:
        dev = data["devices"][device_id]
        dev["ip"] = ip_address
        dev["last_seen"] = now_str
        dev["requests_count"] = dev.get("requests_count", 0) + 1
        # Update user agent/browser if changed
        if user_agent and user_agent != dev.get("user_agent"):
            dev["user_agent"] = user_agent
            os_name, browser_name = parse_user_agent(user_agent)
            dev["os"] = os_name
            dev["browser"] = browser_name

    save_device_data(data)
    is_blocked = data["devices"][device_id].get("blocked", False)
    return device_id, is_blocked

def set_device_name(device_id, new_name):
    data = load_device_data()
    if device_id in data["devices"]:
        data["devices"][device_id]["custom_name"] = new_name.strip()
        save_device_data(data)
        return True
    return False

def set_device_block(device_id, blocked_state):
    data = load_device_data()
    if device_id in data["devices"]:
        data["devices"][device_id]["blocked"] = bool(blocked_state)
        save_device_data(data)
        return True
    return False

def toggle_ip_block(ip_address, blocked_state):
    data = load_device_data()
    ip = ip_address.strip()
    if not ip:
        return False
    blocked_ips = data.setdefault("blocked_ips", [])
    if blocked_state:
        if ip not in blocked_ips:
            blocked_ips.append(ip)
    else:
        if ip in blocked_ips:
            blocked_ips.remove(ip)
    save_device_data(data)
    return True
