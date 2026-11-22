const express = require("express");

const app = express();
const PORT = 3000;

app.use(express.json());

// 임시 로그 데이터
// 추후 실제 ulogd2 로그 파일로 교체
const logs = [
    {
        timestamp: "2026-11-20 18:30:00",
        source_ip: "192.168.0.10",
        destination_port: 80,
        protocol: "TCP",
        action: "ALLOW"
    },
    {
        timestamp: "2026-11-20 18:31:00",
        source_ip: "192.168.0.20",
        destination_port: 22,
        protocol: "TCP",
        action: "BLOCK"
    },
    {
        timestamp: "2026-11-20 18:32:00",
        source_ip: "192.168.0.30",
        destination_port: 80,
        protocol: "TCP",
        action: "ALLOW"
    }
];

// API 서버 상태 확인
app.get("/api/status", (req, res) => {
    res.json({
        status: "ONLINE",
        service: "Network Security API"
    });
});

// 최근 접근 로그 조회
app.get("/api/logs", (req, res) => {
    res.json({
        total: logs.length,
        logs: [...logs].reverse()
    });
});

// 허용 및 차단 통계 조회
app.get("/api/statistics", (req, res) => {
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

// 서버 실행
app.listen(PORT, "0.0.0.0", () => {
    console.log(`API server running on port ${PORT}`);
});