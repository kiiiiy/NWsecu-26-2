# A 담당 — 컨테이너 방화벽

## 구성

```text
사용자 → 호스트:80 → firewall 172.28.10.2 → web 172.28.20.10:80
관리자 → 호스트:2222 → firewall:22 (ADMIN_CIDRS에 등록한 출발지만)

outside 172.28.10.0/24: firewall .2 / 허용 테스트 클라이언트 .100 / 차단 클라이언트 .101
inside  172.28.20.0/24: firewall .2 / web .10 (기본 경로 → firewall)
```

### 컨테이너 시작

`entrypoint.sh`는 설정 검사와 관리자 계정 생성을 먼저 한다. INPUT(방화벽 자체 접속)과 FORWARD(웹서버로 전달하는 접속)를 기본 차단한 다음 로그 수집기를 켠다. 수집기가 준비됐다는 파일을 만들면 규칙을 적용하고 SSH 서버를 시작한다. 이후 두 프로세스가 살아 있는지 확인한다.

### 웹 요청과 관리자 접속

웹 요청은 `PREROUTING의 DNAT → FORWARD의 허용·로그 → POSTROUTING의 SNAT → 웹서버` 순서로 처리한다. DNAT는 목적지를 웹서버로 바꾸고, SNAT는 출발지를 방화벽 내부 IP로 바꾼다. 응답은 연결 추적(conntrack)에 의해 반대 방향으로 주소가 복원된다.

SSH 요청은 웹서버로 전달하지 않고 INPUT에서 검사한다. 관리자 IP의 TCP 22만 허용하며, 이후 SSH 서버가 ID/PW를 검사한다. `AUDIT_ALLOW`와 `AUDIT_BLOCK`은 각각 NFLOG로 기록할 정보를 보낸 다음 ACCEPT 또는 DROP을 실행하는 공통 체인이다.

### 로그 저장

`logger.py`의 `main()`은 파일을 열고, NFLOG 그룹 10에 연결한 뒤 수신을 반복한다. 그룹 번호는 `rules.sh`와 같아야 한다.

| 함수 | 하는 일 |
|---|---|
| `open_log()` | 로그 파일과 파일 회전 설정 |
| `open_nflog()` | 커널 로그 수신 소켓 생성·그룹 등록 |
| `send_config()` | 커널에 설정을 보내고 응답 확인 |
| `read_events()` | 한 버퍼에서 메시지를 하나씩 분리 |
| `read_attributes()` | 메시지에서 패킷과 ALLOW/BLOCK 표시 추출 |
| `decode()` | IPv4 헤더와 TCP/UDP 헤더에서 IP·포트 추출 |

Netlink는 커널과 프로그램이 메시지를 주고받는 통신 방식이고, NFLOG는 방화벽에서 그 통신으로 패킷 정보를 전달하는 기능이다. 이 메시지가 바이너리이므로 `struct`로 정해진 위치의 숫자를 읽는다. `logger.py` 상단의 상수는 그 메시지 규격에 정해진 번호다.

| 경로 | 역할 |
|---|---|
| `compose.yaml` | 컨테이너, 고정 IP, 포트 공개, 내부 네트워크 |
| `firewall/rules.sh` | 기본 차단, HTTP 전달, 관리자 SSH 제한, NFLOG |
| `firewall/logger.py` | 커널 NFLOG 수신 → JSON Lines 로그, 파일 회전 |
| `firewall/entrypoint.sh` | 관리자 계정, SSH, 로그 수집기 시작·감시 |
| `firewall/validate.py` | 관리자 계정·비밀번호·IP 설정 검증 |
| `web/` | B 담당이 교체할 최소 Nginx 연결 확인용 서버 |
| `tests/check.py` | 서로 다른 출발지에서 HTTP/SSH/우회 접근 검증 |
| `logs/firewall.log` | 실제 접속 결정 로그 |
| `logs/active-rules.txt` | 적용된 방화벽 규칙 |

## 관리자 설정

현재 `.env`의 허용 IP는 테스트 관리자 `172.28.10.100/32`이다. 실서버로 옮길 때 실제 관리자 IP를 추가해야 한다.

## 실행

Linux 컨테이너를 사용하는 Docker Engine + Compose가 필요하다. Linux VM에서 최종 시연을 권장한다.

현재 Windows 작업 폴더에서는 `powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1 -Check`로 빌드·실행·검사를 한 번에 수행한다. `.env`가 없으면 테스트 관리자 IP와 랜덤 비밀번호로 생성한다. 실제 관리자 IP는 별도로 추가한다.

```sh
cp .env.example .env
# .env의 ADMIN_CIDRS, ADMIN_PASSWORD 수정
docker compose up -d --build
docker compose ps
curl http://localhost/
ssh -p 2222 fwadmin@localhost
```

SSH 접속 후 `sudo iptables -nvL`로 규칙을 확인·관리한다(관리자 비밀번호 입력). 관리자 계정에는 iptables/iptables-save에 한정한 sudo 권한을 준다. SSH TCP 포워딩은 비활성화했다. SSH에서 임시 변경한 규칙은 컨테이너 재시작 시 `rules.sh` 내용으로 다시 적용되므로 영구 변경은 파일에 반영한다.

PowerShell에서는 `Copy-Item .env.example .env`를 사용한다. 이미 생성된 `.env`가 있으면 덮어쓰지 말고 수정한다. 비밀번호는 `.env`에서 확인하며 Git에 올리지 않는다. 호스트 80/2222가 사용 중이면 `.env`의 HTTP_PORT/SSH_PORT를 바꾼다. 과제 최종 웹서비스 포트는 80을 사용한다.

`ADMIN_CIDRS`는 공백으로 구분한 IPv4 CIDR 목록이다. 예: `192.168.0.25/32 192.168.0.26/32`. 기본 샘플 IP는 실제 관리자 주소가 아니다. 최초 구성의 `172.28.10.100/32`는 자동 테스트용 클라이언트만 허용한다. 실제 관리자 PC에서 SSH를 한 번 시도한 뒤 BLOCK 로그의 `src_ip`를 확인해 관리 IP를 추가한다. `docker compose up -d --force-recreate firewall`로 적용한다. 방화벽 재생성 시 기존 TCP 연결은 다시 연결한다.

**Docker Desktop/공유기 NAT를 거치면 서로 다른 PC가 같은 출발지 IP로 보일 수 있다.** 이때 게이트웨이 IP 허용만으로 PC별 접근 통제를 증명할 수 없다. 최종 시연은 출발지 IP가 보존되는 Linux VM LAN에서 하거나 아래 두 테스트 컨테이너를 사용한다. 도커 호스트의 root/관리자는 이 실습 방화벽의 보호 범위에 포함하지 않는다.

## 로그 확인

```sh
docker compose exec firewall tail -f /var/log/firewall/firewall.log
docker compose exec firewall iptables -nvL
docker compose exec firewall iptables -t nat -nvL
```

호스트에서는 `logs/firewall.log`를 열거나 PowerShell의 `Get-Content .\logs\firewall.log -Wait`를 사용한다.

```json
{"timestamp":"<UTC 시각>","action":"ALLOW","src_ip":"172.28.10.100","dst_ip":"172.28.20.10","dst_port":80,"protocol":"TCP"}
{"timestamp":"<UTC 시각>","action":"BLOCK","src_ip":"172.28.10.101","dst_ip":"172.28.10.2","dst_port":22,"protocol":"TCP"}
```

위 두 줄은 형식 예시이며 실제 로그가 아니다. 시간은 UTC이다. HTTP 목적지는 DNAT 이후 웹서버 주소, SSH 목적지는 컨테이너 내부 포트 22로 기록한다(호스트의 2222가 아님). 포트가 없는 ICMP/일부 IP 조각은 `dst_port: null`이다.

ALLOW는 새 HTTP/SSH 연결을 허용한 결정, BLOCK은 차단한 패킷을 기록한다. 이미 성립된 연결의 후속 패킷과 정상 응답은 중복 로깅하지 않는다. SYN 재전송은 여러 줄이 생길 수 있다. SSH의 ALLOW는 네트워크 통과를 의미하며 비밀번호 인증 성공을 의미하지 않는다. 비밀번호 인증 관련 내용은 `docker compose logs firewall`의 sshd 출력을 확인한다. 10MiB마다 회전하며 이전 파일 5개를 보관한다. NFLOG/커널 소켓 버퍼는 유한하므로 대량 트래픽에서 모든 이벤트 보존을 보장하는 감사 시스템은 아니다.

내부 Docker bridge의 격리 규칙과 호환되도록 HTTP 전달 시 SNAT를 사용한다. 방화벽 로그는 SNAT 전 FORWARD에서 수집하므로 방화벽이 받은 원래 출발지 IP가 남고, Nginx access log에는 방화벽 내부 IP가 보인다. 호스트/공유기에서 이미 변경된 출발지 IP는 복원하지 않는다.

## 자동 연결 검사

`.env`의 ADMIN_CIDRS에 `172.28.10.100/32`를 포함하고 `.101`은 포함하지 않는다.

```sh
docker compose --profile test run --rm test-allowed
docker compose --profile test run --rm test-blocked
```

PowerShell에서는 `powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1`로 전체 검사(실제 로그 대조 포함)를 실행한다.

검사 항목: 두 출발지의 HTTP 성공, .100의 SSH 및 올바른 비밀번호 허용, 잘못된 비밀번호 거절, .101의 SSH 타임아웃, 81번 차단, 외부망에서 내부 웹서버 직접 접근 실패. `sshpass`는 이 자동 인증 검사에 사용한다.

호스트에서 공개하지 않은 포트로 접속하면 패킷이 방화벽 컨테이너까지 도달하지 않아 해당 시도는 firewall.log에 남지 않는다. 81번 BLOCK 검사는 외부망 테스트 컨테이너가 방화벽 컨테이너의 81번으로 직접 보내서 검증한다. 웹서버 직접 접근 실패는 도커 내부망 격리도 함께 검증하며, 우회 시도가 방화벽을 지나지 않으면 방화벽 로그에는 남지 않는다.


## 종료

```sh
docker compose down
```

로그는 호스트 `logs/`에 남는다. `.env` 수정은 재생성 후 적용한다. SSH 호스트 키는 동일 컨테이너 재시작에서는 유지되나 컨테이너 재생성 시 바뀐다. 재생성 사실을 확인한 뒤 SSH known_hosts 항목을 갱신한다.
