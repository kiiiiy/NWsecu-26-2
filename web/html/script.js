let allowedCount = 0;
let blockedCount = 0;
let logs = [];

// ========================================
// Clock
// ========================================
function updateClock() {
    const now = new Date();

    document.getElementById("clock").textContent =
        now.toLocaleTimeString("ko-KR", {
            hour12: false
        });
}

updateClock();
setInterval(updateClock, 1000);

// ========================================
// Traffic Statistics
// ========================================
function updateStatistics() {
    const total = allowedCount + blockedCount;

    const allowedPercent =
        total === 0 ? 0 : (allowedCount / total) * 100;

    const blockedPercent =
        total === 0 ? 0 : (blockedCount / total) * 100;

    document.getElementById("total-count").textContent =
        total.toLocaleString();

    document.getElementById("traffic-allowed").textContent =
        allowedCount.toLocaleString();

    document.getElementById("traffic-blocked").textContent =
        blockedCount.toLocaleString();

    document.getElementById("allowed-percent").textContent =
        allowedPercent.toFixed(1) + "%";

    document.getElementById("blocked-percent").textContent =
        blockedPercent.toFixed(1) + "%";

    document.getElementById("allowed-bar").style.width =
        allowedPercent + "%";

    document.getElementById("blocked-bar").style.width =
        blockedPercent + "%";
}

// ========================================
// Access Logs
// ========================================
function renderLogs() {
    const logBody = document.getElementById("log-body");

    logBody.innerHTML = "";

    logs.slice(0, 10).forEach((log) => {
        const row = document.createElement("tr");

        const timestamp = log.timestamp
            ? new Date(log.timestamp).toLocaleTimeString(
                "ko-KR",
                { hour12: false }
            )
            : "-";

        const actionClass =
            log.action === "ALLOW" ? "allow" : "block";

        const cells = [
            timestamp,
            log.source_ip,
            log.destination_ip || "-",
            log.destination_port,
            log.protocol,
            log.action
        ];

        cells.forEach((value) => {
            const cell = document.createElement("td");
            cell.textContent = value ?? "-";
            row.appendChild(cell);
        });

        const actionCell = row.lastElementChild;
        actionCell.innerHTML = "";

        const actionLabel = document.createElement("span");
        actionLabel.className = `action ${actionClass}`;
        actionLabel.textContent = log.action;

        actionCell.appendChild(actionLabel);
        logBody.appendChild(row);
    });

    document.getElementById("log-count").textContent =
        `Showing ${logs.length} events`;
}

// ========================================
// API: Traffic Statistics
// ========================================
async function fetchStatistics() {
    try {
        const response = await fetch("/api/statistics");

        if (!response.ok) {
            throw new Error("Statistics API request failed");
        }

        const data = await response.json();

        console.log("API Statistics:", data);

        allowedCount = data.allowed;
        blockedCount = data.blocked;

        updateStatistics();

    } catch (error) {
        console.error("Statistics API Error:", error);
    }
}

// ========================================
// API: Access Logs
// ========================================
async function fetchLogs() {
    try {
        const response = await fetch("/api/logs");

        if (!response.ok) {
            throw new Error("Logs API request failed");
        }

        const data = await response.json();

        logs = data.logs || [];

        renderLogs();

    } catch (error) {
        console.error("Logs API Error:", error);
    }
}

// ========================================
// Refresh
// ========================================
async function refreshData() {
    await Promise.all([
        fetchStatistics(),
        fetchLogs()
    ]);
}

// ========================================
// Initialization
// ========================================
document.getElementById("refresh-btn")
    .addEventListener("click", refreshData);

// 최초 데이터 조회
refreshData();

// 5초마다 API 데이터 갱신
setInterval(refreshData, 5000);