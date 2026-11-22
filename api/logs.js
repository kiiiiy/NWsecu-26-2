const fs = require("node:fs/promises");

// 수집기 로그를 화면에서 사용하는 필드 이름으로 바꾼다.
async function readLogs(filePath) {
    let content;
    try {
        content = await fs.readFile(filePath, "utf8");
    } catch (error) {
        if (error.code === "ENOENT") return [];
        throw error;
    }
    const logs = [];
    // 수집기가 쓰고 있는 마지막 줄은 다음 요청에서 읽는다.
    const lines = content.split("\n");
    lines.pop();
    for (const line of lines) {
        if (!line.trim()) continue;
        let event;
        try {
            event = JSON.parse(line);
        } catch {
            continue;
        }
        if (!event || !["ALLOW", "BLOCK"].includes(event.action)) continue;
        logs.push({ timestamp: event.timestamp, source_ip: event.src_ip,
            destination_ip: event.dst_ip, destination_port: event.dst_port,
            protocol: event.protocol, action: event.action });
    }
    return logs;
}

module.exports = { readLogs };
