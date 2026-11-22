const express = require("express");
const { readLogs } = require("./logs");

const app = express();
const PORT = 3000;
const LOG_PATH = process.env.FIREWALL_LOG_PATH || "/var/log/firewall/firewall.log";

// 브라우저가 이전 응답을 재사용하지 않도록 한다.
app.use("/api", (req, res, next) => {
    res.set("Cache-Control", "no-store");
    next();
});

// API 서버 상태 확인
app.get("/api/status", (req, res) => {
    res.json({
        status: "ONLINE",
        service: "Network Security API"
    });
});

// 최근 접근 로그 조회
app.get("/api/logs", async (req, res) => {
    const logs = await readLogs(LOG_PATH);
    res.json({
        total: logs.length,
        logs: logs.slice(-100).reverse()
    });
});

// 허용 및 차단 통계 조회
app.get("/api/statistics", async (req, res) => {
    const logs = await readLogs(LOG_PATH);
    const allowed = logs.filter(
        log => log.action === "ALLOW"
    ).length;

    const blocked = logs.filter(
        log => log.action === "BLOCK"
    ).length;

    res.json({
        total: logs.length,
        allowed: allowed,
        blocked: blocked
    });
});

app.use((error, req, res, next) => {
    console.error("Firewall log read failed:", error.code || error.message);
    res.status(503).json({ error: "방화벽 로그를 읽을 수 없습니다." });
});

// 서버 실행
app.listen(PORT, "0.0.0.0", () => {
    console.log(`API server running on port ${PORT}`);
});
