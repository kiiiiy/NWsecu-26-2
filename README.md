# Docker 기반 안전한 Linux 웹서버

방화벽과 웹서버를 서로 다른 컨테이너로 구성한 네트워크 보안 팀 프로젝트다. 웹 요청은 방화벽을 거쳐 Nginx로 전달하고, 관리 접속은 지정한 IP와 관리자 계정으로 제한한다. 방화벽에서 생성한 실제 허용·차단 로그는 API를 통해 대시보드에 표시한다.

## 1. 과제 요구사항 적용

| 요구사항 | 적용 방법 | 확인 위치 |
|---|---|---|
| 방화벽과 웹서버 분리 | `firewall`, `web`을 별도 컨테이너로 실행 | `compose.yaml` |
| TCP 80 웹서비스 | 호스트 80번을 방화벽 80번에 연결하고 Nginx 80번으로 전달 | `compose.yaml`, `firewall/rules.sh` |
| 웹서비스 외 접근 차단 | INPUT·FORWARD 기본 정책을 DROP으로 설정하고 필요한 접속만 허용 | `firewall/entrypoint.sh`, `firewall/rules.sh` |
| 관리자 IP 접근통제 | 허용된 출발지 IP의 SSH만 통과 | `.env`의 `ADMIN_CIDRS`, `firewall/rules.sh` |
| 관리자 ID/PW | 전용 계정을 만들고 SSH 비밀번호 인증 적용, root 직접 로그인 금지 | `.env`, `firewall/entrypoint.sh` |
| 공개 이미지 사용 | Debian·Nginx·Node.js 이미지를 기반으로 필요한 설정 추가 | 각 서비스의 `Dockerfile` |

관리자 SSH는 관리 기능을 위한 예외다. 일반 사용자는 웹서비스만 이용할 수 있다. 웹·API 컨테이너에는 호스트 공개 포트를 설정하지 않는다. 로그 수집과 대시보드는 과제 조건에 추가한 기능이며, 발표와 시연 영상 녹화·LMS 제출은 별도로 진행한다.

## 2. 아키텍처

```text
사용자 ── HTTP :80 ──▶ Linux 호스트 ──▶ 방화벽 ──▶ Nginx 웹·대시보드
                                          │               │
관리자 ── SSH :2222 ──────────────────────▶│               └─ /api/ ──▶ API :3000
              허용 IP + 관리자 ID/PW       │                              │
                                          └─ NFLOG → Python → firewall.log
                                                                         ▲
                                                API가 공유 로그를 읽음 ───┘
```

컨테이너는 Linux 호스트 한 대에서 Docker Compose로 실행한다. `outside`는 요청 수신용 네트워크이고, `inside`는 `internal: true`로 외부 연결을 제한한 내부 네트워크다.

| 구성 | 네트워크 / IP | 포트 |
|---|---|---|
| 방화벽 외부 | outside / `172.28.10.2` | HTTP 80, SSH 22 |
| 방화벽 내부 | inside / `172.28.20.2` | 웹서버 전달 경로 |
| Nginx | inside / `172.28.20.10` | 내부 TCP 80 |
| Node.js API | inside / `172.28.20.20` | 내부 TCP 3000 |
| 허용 테스트 클라이언트 | outside / `172.28.10.100` | 관리자 IP 역할 |
| 차단 테스트 클라이언트 | outside / `172.28.10.101` | 비관리자 IP 역할 |

네트워크 대역은 `172.28.10.0/24`, `172.28.20.0/24`다. 호스트의 기본 공개 포트는 **80과 2222**이며, 호스트 2222는 방화벽 컨테이너의 SSH 22로 연결한다. 실제 관리자 PC의 IP와 위 컨테이너 IP는 구분해야 한다.

## 3. 파일 구성

```text
NWsecu-26-2/
├── compose.yaml           # 서비스, 네트워크, 포트, 공유 디렉터리
├── .env.example           # 실행 설정 예시
├── firewall/
│   ├── Dockerfile
│   ├── entrypoint.sh      # 관리자 계정 생성 및 프로세스 시작
│   ├── validate.py        # 환경변수 검사
│   ├── rules.sh           # 접근 제어와 NAT 규칙
│   └── logger.py          # NFLOG 수신 및 로그 파일 기록
├── web/
│   ├── Dockerfile
│   ├── nginx.conf         # 정적 페이지 및 /api/ 프록시
│   ├── route.sh           # 기본 경로를 방화벽으로 설정
│   └── html/              # 대시보드 HTML, CSS, JavaScript
├── api/
│   ├── Dockerfile
│   ├── package.json
│   ├── server.js          # 로그·통계 API
│   └── logs.js            # 실제 로그 읽기와 필드 변환
├── scripts/
│   ├── start.ps1          # Windows 실행 스크립트
│   └── check.ps1          # 전체 검사 스크립트
├── tests/                 # 접속·차단·로그·API 검사
└── logs/                  # 실행 시 생성되는 로그와 적용 규칙 사본
```

실행에는 `compose.yaml`을 사용한다. `.env`와 `logs/`의 실행 결과는 Git 업로드 대상에서 제외하며, 설정 예시인 `.env.example`은 공유한다.

## 4. 처음 실행하기

### 준비

- Docker Engine과 Docker Compose가 설치된 Linux 서버 또는 VM
- Windows에서는 Linux 컨테이너 모드의 Docker Desktop
- 호스트의 80·2222번 포트를 사용할 수 있는 환경

이후 명령은 `compose.yaml`이 있는 프로젝트 최상위 디렉터리에서 실행한다.

### 4-1. 환경설정 만들기

Linux / WSL:

```bash
test -f .env || cp .env.example .env
```

PowerShell:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

기존 `.env`가 있으면 그대로 수정한다. 다음은 설정 형식 예시다. 실제 IP와 비밀번호로 바꿔야 한다.

```dotenv
ADMIN_CIDRS="172.28.10.100/32 192.168.0.25/32"
ADMIN_USER=fwadmin
ADMIN_PASSWORD=CHANGE_TO_STRONG_PASSWORD
HTTP_PORT=80
SSH_PORT=2222
```

| 변수 | 설정 방법 |
|---|---|
| `ADMIN_CIDRS` | 관리자 출발지 IPv4 CIDR. 여러 개는 공백으로 구분하며, 한 IP만 허용할 때 `/32` 사용 |
| `ADMIN_USER` | 소문자로 시작하는 관리자 계정 이름 |
| `ADMIN_PASSWORD` | 직접 정한 12자 이상 비밀번호. 줄바꿈과 `:`는 사용하지 않음 |
| `HTTP_PORT` | 호스트 웹 포트. 과제 시연에서는 80 사용 |
| `SSH_PORT` | 호스트 관리 포트. 기본값 2222 |

`172.28.10.100/32`는 자동 검사에 사용하는 관리자 컨테이너 주소다. `192.168.0.25/32`는 실제 관리자 PC 주소를 넣을 자리의 예시다. `.env.example`을 복사한 경우에도 관리자 IP·비밀번호를 수정해야 하며, `CHANGE_ME` 비밀번호로는 실행되지 않는다. 모든 IP를 허용하는 `0.0.0.0/0`도 허용하지 않는다.

### 4-2. 빌드 및 실행

```bash
docker compose config --quiet
docker compose up -d --build --wait
docker compose ps
```

`firewall`, `web`, `api`가 실행되면 브라우저에서 `http://localhost/`를 연다. 다른 PC에서 접속할 때는 `http://<서버 IP>/`를 사용한다. 호스트 웹 포트를 변경했다면 주소에 해당 포트를 붙인다.

PowerShell에서는 다음 명령으로 빌드·실행·전체 검사를 한 번에 할 수 있다.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1 -Check
```

이 스크립트는 `.env`가 없을 때만 테스트 관리자 IP와 랜덤 비밀번호로 생성한다. 실제 관리자 PC 주소는 별도로 추가해야 한다. `-Check`를 사용하려면 `ADMIN_CIDRS`에 `172.28.10.100/32`를 포함하고 `172.28.10.101`은 포함하지 않는다.

### 4-3. API 확인

```bash
curl http://localhost/api/status
curl http://localhost/api/logs
curl http://localhost/api/statistics
```

PowerShell에서는 `curl` 대신 `curl.exe`를 사용해도 된다. API 포트 3000은 외부에 직접 공개하지 않으며, 위 요청은 방화벽과 Nginx를 거친다.

## 5. 관리자 접속 적용

1. 관리자 PC에서 `ssh -p 2222 fwadmin@<서버 IP>`로 접속을 시도한다.
2. 차단됐다면 서버에서 `logs/firewall.log`의 SSH BLOCK 기록을 확인한다.
3. 그 기록의 `src_ip`를 `.env`의 `ADMIN_CIDRS`에 `/32`로 등록한다.
4. 다음 명령으로 설정을 적용하고 다시 접속한다.

```bash
docker compose up -d --force-recreate firewall
ssh -p 2222 fwadmin@<서버 IP>
```

계정과 포트를 바꿨다면 SSH 명령에도 반영한다. 로그인 후에는 다음과 같이 관리자 비밀번호를 입력해 규칙을 확인한다.

```bash
sudo iptables -nvL
sudo iptables -t nat -nvL
```

관리자 계정에는 `iptables`, `iptables-save` 실행을 위한 sudo 권한을 부여했다. SSH에서 임시로 바꾼 규칙은 재시작하면 `rules.sh` 내용으로 돌아가므로, 영구 변경은 해당 파일에 반영하고 다시 빌드한다.

Docker Desktop이나 공유기 NAT를 거치면 서로 다른 PC가 같은 출발지 IP로 보일 수 있다. PC별 IP 통제를 시연할 때는 출발지가 구분되는 Linux VM LAN 환경이나 아래 테스트 컨테이너를 사용한다. 호스트 관리자 자체의 접근은 이 컨테이너 방화벽의 보호 범위에 포함하지 않는다.

## 6. 방화벽 동작 설명

### 시작 순서

`entrypoint.sh`는 설정을 검사하고 관리자 계정을 만든다. INPUT·FORWARD 기본 정책을 DROP으로 설정한 뒤 로그 수집기를 시작한다. 수집기 준비가 끝나면 규칙을 적용하고 SSH 서버를 실행한다. 로그 수집기나 SSH 프로세스가 종료되면 컨테이너도 종료한다.

### 웹 요청

1. 호스트 80번으로 들어온 요청이 방화벽 컨테이너 80번에 도착한다.
2. PREROUTING의 **DNAT**가 목적지를 `172.28.20.10:80`으로 바꾼다.
3. FORWARD에서 웹서버 TCP 80 요청을 허용하고 NFLOG로 기록한다.
4. POSTROUTING의 **SNAT**가 출발지를 방화벽 내부 IP로 바꿔 내부망으로 전달한다.
5. 정상 연결의 응답은 conntrack의 `ESTABLISHED,RELATED` 규칙으로 허용하고 NAT 주소를 복원한다.

Nginx의 `/api/` 요청은 내부 API `api:3000`으로 전달한다. 웹과 API 사이 통신은 같은 내부망에서 이루어지므로 방화벽 FORWARD를 경유하지 않는다. 그 외 방화벽으로 들어오는 새 접속과 허용되지 않은 전달 트래픽은 차단한다. 방화벽 자체의 OUTPUT은 허용하고, 웹서버가 시작한 외부 연결은 FORWARD에서 차단한다. 이 구성은 IPv4 기준이며 방화벽의 IPv6는 비활성화했다.

### 관리 요청

호스트 2222번 요청은 방화벽의 22번으로 연결된다. INPUT에서 관리자 출발지 IP를 검사한 뒤 SSH 서버가 ID/PW를 확인한다. 따라서 IP 허용과 비밀번호 인증은 별개의 단계다.

## 7. 실제 로그와 대시보드

```text
iptables → NFLOG 그룹 10 → logger.py → logs/firewall.log
                                            │
                                            └→ API 읽기 → Nginx → 대시보드
```

API는 공유 로그 디렉터리를 읽기 전용으로 연결한다. 대시보드는 가짜 데이터 대신 실제 로그를 조회하며 5초마다 갱신한다. 로그는 한 줄에 JSON 하나씩 저장한다. 아래는 형식 예시다.

```json
{"timestamp":"<UTC 시각>","action":"BLOCK","src_ip":"172.28.10.101","dst_ip":"172.28.10.2","dst_port":22,"protocol":"TCP"}
```

| 로그 필드 | 의미 | API 응답 필드 |
|---|---|---|
| `timestamp` | 기록 시각, UTC | `timestamp` |
| `src_ip` | 방화벽이 받은 출발지 IP | `source_ip` |
| `dst_ip` | 목적지 IP | `destination_ip` |
| `dst_port` | 목적지 포트 | `destination_port` |
| `protocol` | TCP, UDP, ICMP 등 | `protocol` |
| `action` | 허용 ALLOW / 차단 BLOCK | `action` |

로그를 확인하는 명령:

```bash
docker compose exec firewall tail -f /var/log/firewall/firewall.log
```

PowerShell에서는 `Get-Content .\logs\firewall.log -Wait`를 사용한다.

로그를 해석할 때는 다음을 구분한다.

- ALLOW는 새 연결의 네트워크 허용 결정이다. SSH 비밀번호 인증 성공 여부는 `docker compose logs firewall`에서 확인한다.
- 차단 패킷은 기록하고, 정상 연결의 후속 패킷과 응답은 중복 기록하지 않는다. 재전송은 여러 건으로 남을 수 있으므로 건수는 고유 사용자 수나 HTTP 요청 수와 다르다.
- 웹 요청은 DNAT 후·SNAT 전에 기록한다. 방화벽 로그에는 받은 출발지 IP가 남고, Nginx 로그에는 방화벽 내부 IP가 보인다. 호스트 NAT로 이미 바뀐 출발지는 복원하지 않는다.
- SSH 목적지 포트는 호스트 2222가 아닌 컨테이너 22로 기록한다. 포트가 없는 패킷은 `null`이다.
- `/api/logs`는 최근 100개를 최신순으로 반환하며 화면 표에는 최근 10개를 표시한다. 통계는 현재 파일 전체의 유효한 ALLOW/BLOCK 건수다.
- 로그는 10MiB마다 회전하고 이전 파일 5개를 보관한다. API는 현재 파일만 읽으므로 회전하면 통계도 새 파일 기준이 된다.
- 파일이 없거나 비어 있으면 빈 목록·0을 반환한다. 미완성 줄과 잘못된 JSON 줄은 제외하고, 다른 읽기 오류는 HTTP 503으로 알린다.

`logs/active-rules.txt`는 적용한 규칙의 사본이며 접속 로그와 구분한다. 호스트에서 공개하지 않은 포트의 요청이나 방화벽을 경유하지 않은 우회 시도는 이 로그에 남지 않을 수 있다.

## 8. 기능 검사 및 시연 순서

자동 검사에서는 `172.28.10.100`을 관리자, `172.28.10.101`을 비관리자로 사용한다. `.env`에서 전자는 허용하고 후자는 허용하지 않아야 한다. 먼저 컨테이너를 실행한 후 다음 명령을 수행한다.

Linux / WSL:

```bash
docker compose --profile test run --rm test-allowed
docker compose --profile test run --rm test-blocked
```

PowerShell 전체 검사:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1
```

| 검사 | 예상 결과 |
|---|---|
| 두 출발지에서 HTTP 80과 `/api/status` 접속 | 성공 |
| 관리자 IP에서 올바른 ID/PW로 SSH 접속 및 sudo 규칙 조회 | 성공 |
| 관리자 IP에서 잘못된 비밀번호 사용 | 인증 거절 |
| 비관리자 IP에서 SSH 접속 | 타임아웃으로 차단 |
| 외부망 클라이언트에서 방화벽 81·3000번 접속 | 타임아웃으로 차단 |
| 외부망에서 내부 웹·API IP로 직접 접속 | 실패 |
| API에서 이번 차단 요청의 IP·포트·BLOCK 조회 | 실제 기록 표시 |
| API 통계의 허용 건수 + 차단 건수 | 전체 건수와 일치 |

PowerShell 전체 검사에는 새로 생성된 로그 6개 조합 대조, Python 로그 파서 검사, Node.js 로그 읽기 검사도 포함된다. 테스트 클라이언트는 검사 후 자동 삭제된다.

시연 영상은 다음 순서로 녹화하면 된다.

1. `docker compose ps`로 방화벽·웹·API 분리 구성을 보여준다.
2. 브라우저로 서버의 80번 웹서비스와 대시보드를 연다.
3. 허용·차단 클라이언트 검사를 실행해 SSH·포트 접근 결과를 보여준다.
4. `firewall.log`의 출발지 IP·목적지 포트·ALLOW/BLOCK을 확인한다.
5. 대시보드 새로고침으로 실제 차단 기록과 통계를 보여준다.
6. `iptables -nvL`과 NAT 규칙으로 각 과제 조건을 설명한다.

81번 차단 검사는 테스트 컨테이너에서 **방화벽 IP**로 직접 요청한다. 호스트의 공개하지 않은 81번으로 접속하는 것만으로는 방화벽 컨테이너의 차단 규칙을 검증할 수 없다. 시연 영상을 녹화해 14주차 수업 시작 전 LMS에 제출한다.

## 9. 설정 변경과 종료

코드 수정 후:

```bash
docker compose up -d --build --wait
```

`.env` 수정 후에는 `docker compose up -d`로 변경된 서비스를 재생성한다. `docker compose restart`만으로는 새 환경변수가 반영되지 않는다.

오류 확인:

```bash
docker compose logs --tail 50 firewall web api
```

종료:

```bash
docker compose down
```

종료해도 소스·이미지와 호스트 `logs/`의 기록은 남는다. 컨테이너 재생성 시 SSH 호스트 키는 바뀌므로, 키 경고가 발생하면 재생성 사실을 확인하고 기존 known_hosts 항목을 정리한다. 네트워크 대역을 변경할 때는 Compose와 `rules.sh`, `route.sh`, 테스트의 고정 IP도 함께 수정한다.
