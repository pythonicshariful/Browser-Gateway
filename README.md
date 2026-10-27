# Browser-Gateway ⚡

A Flask-powered web gateway and browser automation platform designed to access authenticated domains (such as `hseconomicsbd.com`) with session persistence, device/IP firewall controls, and custom naming.

---

## 🌟 Key Features

1. **Clean Public Web Version (No Admin Controls Visible)**
   - Access the complete website at **`http://127.0.0.1:5000/`**.
   - Zero pills, banners, or admin badges are displayed anywhere. Regular users see only the authentic website.
   - **No Session Drop**: All tabs, courses, navigation links, forms, and AJAX assets retain your student session cookies automatically.
   - **Account Protection Shield**: The "Logout" and "Password Change" options are completely removed from the profile menu, and `/logout` / `/dashboard/profile-password` routes are intercepted to prevent visitors from logging out or altering account credentials.

2. **Admin Panel & Device Manager (`/admin`)**
   - Access at **`http://127.0.0.1:5000/admin`**.
   - **Password Protected**: Default password is `admin` (can be updated directly from the panel).
   - **Connected Devices Tracking**: View every connected device (IP address, OS, Browser, Hits, and Last Active timestamp).
   - **Custom Device Names**: Give any device a custom label (e.g., "Friend's Laptop", "Rahim's Phone", "Suspicious User").
   - **Device & IP Firewall**:
     - 1-Click **Block Device**: Instantly blocks the specific visitor device.
     - 1-Click **Block IP**: Blocks the entire IP address.
     - Manual IP input to block any custom IP range or address.
     - Blocked users immediately receive a clean `403 Access Denied` screen.
   - **Session Cookie Editor**: Modify or refresh `PHPSESSID` and student tokens without touching code.
   - **Live Health Check & Native Browser Launcher**: Test target session or launch in Chrome/Edge.

3. **Bunny Stream Video Proxy (Fixes 403 Forbidden on Hosted Domains)**
   - Academy videos are delivered via **Bunny.net (mediadelivery.net)**, which checks the HTTP `Referer` domain whitelist.
   - When hosted on custom domains like `hs.pythonicshariful.tech`, the video player area previously showed `403 Forbidden`.
   - The built-in `/bunny/...` video proxy injects `Referer: https://hseconomicsbd.com/` into all player and video chunk requests, allowing full playback anywhere without 403 errors.

---

## 🔑 Default Session Configuration

The system comes pre-configured with:
- **Domain**: `hseconomicsbd.com`
- **Target URL**: `https://hseconomicsbd.com`
- **Cookies**:
  - `hseastudentId`: `1035`
  - `hseastudentToken`: `9155c8fca455c876a3266861b5da1d96`
  - `PHPSESSID`: `7q5m2juk8qmd1ci0ai046v1slg`

---

## 🚀 How to Run

### Option 1: One-Click Runner (Windows)
Double-click `run.bat` in the project root:
- Automatically creates a Python virtual environment (`.venv`).
- Installs all dependencies from `requirements.txt`.
- Starts the Flask server and opens `http://127.0.0.1:5000` in your default browser.

### Option 2: Manual Terminal
```powershell
# In project folder
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python app.py
```
- **Public Web Portal**: Open [http://127.0.0.1:5000/](http://127.0.0.1:5000/)
- **Admin Control Panel**: Open [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin) (Password: `admin`)

---

## 📁 Project Structure

```
Browser-Gateway/
├── app.py                  # Main Flask application, proxy router & firewall
├── config.py               # Cookie configuration & storage loader
├── device_manager.py       # Visitor device/IP tracking, blocking & naming
├── browser_launcher.py     # Selenium / Edge / Chrome launcher with cookie injection
├── requirements.txt        # Python package dependencies
├── run.bat                 # One-click Windows starter script
├── README.md               # Project documentation
├── static/
│   ├── css/
│   │   └── style.css       # Dark glassmorphism dashboard UI styles
│   └── js/
│       └── main.js         # Frontend controller & API handlers
└── templates/
    ├── index.html          # Admin panel template
    └── login.html          # Admin login screen
```