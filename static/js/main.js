document.addEventListener("DOMContentLoaded", () => {
    const btnLaunchBrowser = document.getElementById("btnLaunchBrowser");
    const browserChoice = document.getElementById("browserChoice");
    const btnCheckSession = document.getElementById("btnCheckSession");
    const sessionStatusText = document.getElementById("sessionStatusText");
    const cookieForm = document.getElementById("cookieForm");
    const toastContainer = document.getElementById("toastContainer");

    function showToast(message, type = "info") {
        const toast = document.createElement("div");
        toast.className = `toast ${type}`;
        toast.textContent = message;
        toastContainer.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = "0";
            toast.style.transition = "opacity 0.3s ease";
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }

    // ---------------------------------------------------------
    // Tab Switching
    // ---------------------------------------------------------
    window.switchTab = function(tabId, btnElement) {
        document.querySelectorAll(".tab-content").forEach(el => el.classList.remove("active"));
        document.querySelectorAll(".tab-btn").forEach(el => el.classList.remove("active"));
        
        const targetTab = document.getElementById(tabId);
        if (targetTab) targetTab.classList.add("active");
        if (btnElement) btnElement.classList.add("active");
    };

    // ---------------------------------------------------------
    // Device & IP Management
    // ---------------------------------------------------------
    function getOsIcon(os) {
        const lower = (os || "").toLowerCase();
        if (lower.includes("windows")) return "🪟";
        if (lower.includes("android")) return "📱";
        if (lower.includes("iphone") || lower.includes("ipad")) return "🍏";
        if (lower.includes("mac")) return "💻";
        if (lower.includes("linux")) return "🐧";
        return "🌐";
    }

    window.loadDevices = async function() {
        const container = document.getElementById("deviceListContainer");
        const blockedIpsContainer = document.getElementById("blockedIpsContainer");
        const badge = document.getElementById("deviceCountBadge");

        try {
            const resp = await fetch("/api/devices");
            if (!resp.ok) {
                container.innerHTML = `<p class="text-muted" style="text-align:center;padding:20px;">Could not load devices (Unauthorized).</p>`;
                return;
            }
            const data = await resp.json();
            const devices = Object.values(data.devices || {});
            const blockedIps = data.blocked_ips || [];

            if (badge) badge.textContent = devices.length;

            // Render Blocked IPs Chips
            if (blockedIps.length === 0) {
                blockedIpsContainer.innerHTML = `<span class="text-muted" style="font-size:12px;">No IPs blocked.</span>`;
            } else {
                blockedIpsContainer.innerHTML = blockedIps.map(ip => `
                    <div class="ip-chip">
                        <span>${ip}</span>
                        <button class="ip-chip-remove" onclick="toggleIpBlock('${ip}', false)" title="Unblock IP">&times;</button>
                    </div>
                `).join("");
            }

            // Render Devices List
            if (devices.length === 0) {
                container.innerHTML = `<p class="text-muted" style="text-align:center;padding:30px;">No devices connected yet. Open the website at <a href="/" target="_blank" style="color:#60a5fa;">http://127.0.0.1:5000/</a> to record visitor devices.</p>`;
                return;
            }

            container.innerHTML = devices.map(dev => {
                const isBlocked = dev.blocked || blockedIps.includes(dev.ip);
                const isIpBlocked = blockedIps.includes(dev.ip);
                const icon = getOsIcon(dev.os);

                return `
                <div class="device-item ${isBlocked ? 'is-blocked' : ''}">
                    <div class="device-main">
                        <div class="device-icon-box">${icon}</div>
                        <div class="device-details">
                            <div class="device-title-row">
                                <span class="custom-name-text">${escapeHtml(dev.custom_name || dev.id)}</span>
                                <button onclick="promptRename('${dev.id}', '${escapeHtml(dev.custom_name || '')}')" class="btn btn-outline btn-xs" style="padding:2px 8px;font-size:11px;">
                                    ✏️ Rename
                                </button>
                                ${isBlocked ? '<span style="color:#ef4444;font-size:11px;font-weight:700;background:rgba(239,68,68,0.15);padding:2px 6px;border-radius:4px;">BLOCKED</span>' : '<span style="color:#10b981;font-size:11px;font-weight:700;background:rgba(16,185,129,0.15);padding:2px 6px;border-radius:4px;">ACTIVE</span>'}
                            </div>
                            <div class="device-meta-row">
                                <span>IP: <strong>${dev.ip}</strong></span>
                                <span>OS: ${dev.os} &bull; Browser: ${dev.browser}</span>
                                <span>Last Active: ${dev.last_seen}</span>
                                <span>Hits: ${dev.requests_count || 1}</span>
                            </div>
                        </div>
                    </div>

                    <div class="device-actions">
                        ${dev.blocked ? `
                            <button onclick="toggleDeviceBlock('${dev.id}', false)" class="btn btn-success btn-xs">
                                🟢 Unblock Device
                            </button>
                        ` : `
                            <button onclick="toggleDeviceBlock('${dev.id}', true)" class="btn btn-danger btn-xs">
                                🚫 Block Device
                            </button>
                        `}

                        ${isIpBlocked ? `
                            <button onclick="toggleIpBlock('${dev.ip}', false)" class="btn btn-success btn-xs">
                                🟢 Unblock IP
                            </button>
                        ` : `
                            <button onclick="toggleIpBlock('${dev.ip}', true)" class="btn btn-outline btn-xs" style="border-color:#ef4444;color:#f87171;">
                                🚫 Block IP (${dev.ip})
                            </button>
                        `}
                    </div>
                </div>
                `;
            }).join("");

        } catch (err) {
            container.innerHTML = `<p class="text-muted" style="text-align:center;padding:20px;">Error loading devices: ${err.message}</p>`;
        }
    };

    function escapeHtml(str) {
        return (str || "").replace(/[&<>"']/g, function(m) {
            return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m];
        });
    }

    window.promptRename = async function(deviceId, currentName) {
        const newName = prompt("Enter a custom name for this device/user (e.g. 'Friend's Laptop', 'My Phone'):", currentName);
        if (newName === null) return;
        const cleanName = newName.trim();
        if (!cleanName) return;

        try {
            const resp = await fetch("/api/device/rename", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ device_id: deviceId, name: cleanName })
            });
            const data = await resp.json();
            if (resp.ok && data.status === "success") {
                showToast("Device name updated to: " + cleanName, "success");
                loadDevices();
            } else {
                showToast(data.message || "Failed to rename device.", "error");
            }
        } catch (err) {
            showToast("Network error: " + err.message, "error");
        }
    };

    window.toggleDeviceBlock = async function(deviceId, blocked) {
        try {
            const resp = await fetch("/api/device/block", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ device_id: deviceId, blocked: blocked })
            });
            const data = await resp.json();
            if (resp.ok && data.status === "success") {
                showToast(data.message, blocked ? "error" : "success");
                loadDevices();
            } else {
                showToast(data.message || "Operation failed", "error");
            }
        } catch (err) {
            showToast("Network error: " + err.message, "error");
        }
    };

    window.toggleIpBlock = async function(ip, blocked) {
        try {
            const resp = await fetch("/api/ip/block", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ ip: ip, blocked: blocked })
            });
            const data = await resp.json();
            if (resp.ok && data.status === "success") {
                showToast(data.message, blocked ? "error" : "success");
                loadDevices();
            } else {
                showToast(data.message || "Operation failed", "error");
            }
        } catch (err) {
            showToast("Network error: " + err.message, "error");
        }
    };

    window.blockManualIp = function() {
        const input = document.getElementById("manualIpInput");
        const ip = (input.value || "").trim();
        if (!ip) {
            showToast("Please enter a valid IP address", "error");
            return;
        }
        toggleIpBlock(ip, true);
        input.value = "";
    };

    // Auto-load devices on initial start
    loadDevices();

    // ---------------------------------------------------------
    // Browser Launch & Session Checker Handlers
    // ---------------------------------------------------------
    if (btnLaunchBrowser) {
        btnLaunchBrowser.addEventListener("click", async () => {
            const selectedBrowser = browserChoice.value;
            const originalText = btnLaunchBrowser.innerHTML;
            btnLaunchBrowser.disabled = true;
            btnLaunchBrowser.innerHTML = `<span class="btn-text">Opening ${selectedBrowser.toUpperCase()}...</span>`;

            try {
                const resp = await fetch("/api/launch-browser", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ browser_type: selectedBrowser })
                });
                const data = await resp.json();

                if (resp.ok && data.status === "success") {
                    showToast(data.message || "Browser launched successfully!", "success");
                } else {
                    showToast("Failed to launch browser: " + (data.message || "Unknown error"), "error");
                }
            } catch (err) {
                showToast("Connection error: " + err.message, "error");
            } finally {
                btnLaunchBrowser.disabled = false;
                btnLaunchBrowser.innerHTML = originalText;
            }
        });
    }

    if (btnCheckSession) {
        btnCheckSession.addEventListener("click", async () => {
            const originalText = btnCheckSession.innerHTML;
            btnCheckSession.disabled = true;
            btnCheckSession.innerHTML = `Checking...`;
            sessionStatusText.textContent = "Testing connection and session response...";
            sessionStatusText.style.color = "#94a3b8";

            try {
                const resp = await fetch("/api/check-session");
                const data = await resp.json();

                if (resp.ok && data.status === "success") {
                    if (data.authenticated) {
                        sessionStatusText.innerHTML = `<span style="color:#10b981;font-weight:700;">● Active & Logged In</span> (HTTP ${data.http_status})`;
                        showToast("Session is valid & authenticated on target server!", "success");
                    } else {
                        sessionStatusText.innerHTML = `<span style="color:#f59e0b;font-weight:700;">▲ Connected, Login may be required</span> (HTTP ${data.http_status})`;
                        showToast("Target reached, but session cookies might be expired or need update.", "info");
                    }
                } else {
                    sessionStatusText.innerHTML = `<span style="color:#ef4444;font-weight:700;">✕ Target Server Error</span>`;
                    showToast("Server check error: " + (data.message || "Error"), "error");
                }
            } catch (err) {
                sessionStatusText.innerHTML = `<span style="color:#ef4444;font-weight:700;">✕ Check Failed</span>`;
                showToast("Network error checking session: " + err.message, "error");
            } finally {
                btnCheckSession.disabled = false;
                btnCheckSession.innerHTML = originalText;
            }
        });
    }

    if (cookieForm) {
        cookieForm.addEventListener("submit", async (e) => {
            e.preventDefault();

            const studentId = document.getElementById("cookieStudentId").value.trim();
            const studentToken = document.getElementById("cookieStudentToken").value.trim();
            const phpSessId = document.getElementById("cookiePhpSessId").value.trim();
            const adminPassword = document.getElementById("adminPassword") ? document.getElementById("adminPassword").value.trim() : "";

            try {
                const resp = await fetch("/api/config", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        admin_password: adminPassword,
                        cookies: {
                            hseastudentId: studentId,
                            hseastudentToken: studentToken,
                            PHPSESSID: phpSessId
                        }
                    })
                });
                const data = await resp.json();

                if (resp.ok && data.status === "success") {
                    showToast("Cookies and settings updated successfully!", "success");
                } else {
                    showToast("Failed to save cookies: " + (data.message || "Error"), "error");
                }
            } catch (err) {
                showToast("Network error saving configuration: " + err.message, "error");
            }
        });
    }
});
