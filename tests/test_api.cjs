const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const os = require("node:os");
const path = require("node:path");
const { readLogs } = require("../api/logs");

test("실제 로그 필드 변환, 미완성 줄 제외, 파일 교체 반영", async () => {
    const directory = await fs.mkdtemp(path.join(os.tmpdir(), "firewall-api-"));
    const file = path.join(directory, "firewall.log");
    try {
        assert.deepEqual(await readLogs(file), []);
        const event = { timestamp: new Date().toISOString(), src_ip: "172.28.10.101",
            dst_ip: "172.28.10.2", dst_port: 81, protocol: "TCP", action: "BLOCK" };
        await fs.writeFile(file, JSON.stringify(event) + '\ninvalid\nnull\n{"action":');
        const logs = await readLogs(file);
        assert.equal(logs.length, 1);
        assert.equal(logs[0].source_ip, event.src_ip);
        assert.equal(logs[0].destination_ip, event.dst_ip);
        assert.equal(logs[0].destination_port, 81);
        assert.equal(logs[0].action, "BLOCK");
        await fs.rename(file, file + ".1");
        await fs.writeFile(file, "");
        assert.deepEqual(await readLogs(file), []);
        await assert.rejects(readLogs(directory), { code: "EISDIR" });
    } finally {
        await fs.rm(directory, { recursive: true, force: true });
    }
});
