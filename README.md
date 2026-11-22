# NWsecu-26-2

네트워크 보안 팀 프로젝트


## 1. 프로젝트 구성

```text
network-security/
├── compose.yaml
├── README.md
│
├── firewall/
│   ├── Dockerfile
│   ├── firewall.sh
│   ├── entrypoint.sh
│   └── sshd_config
│
├── web/
│   ├── Dockerfile
│   └── html/
│       ├── index.html
│       ├── style.css
│       └── script.js
│
└── api/
    ├── Dockerfile
    ├── package.json
    └── server.js
```

### 주요 구성 요소

| 구성 요소 | 역할 |
|---|---|
| Firewall | 네트워크 접근 제어, NAT 및 트래픽 전달 |
| Nginx Web | 웹서비스 제공 및 정적 파일 호스팅 |
| Node.js API | 트래픽 통계 및 접근 로그 데이터 제공 |
| Dashboard | 네트워크 트래픽 및 보안 정책 모니터링 |

## 2. 네트워크 구성

### 네트워크 구조

```text
                 External User
                       |
                       | HTTP : 80
                       v
              +------------------+
              |     Firewall     |
              |                  |
              |  External:       |
              |  172.28.10.2     |
              |                  |
              |  Internal:       |
              |  172.28.20.2     |
              +------------------+
                       |
                       | TCP : 80
                       v
              +------------------+
              |   Nginx Web      |
              |  172.28.20.10    |
              +------------------+
                       |
                       | API Request
                       v
              +------------------+
              |   Node.js API    |
              |  172.28.20.20    |
              +------------------+
```

### 네트워크 IP 구성

| 구성 요소 | IP 주소 | 역할 |
|---|---|---|
| Firewall 외부 | 172.28.10.2 | 외부 요청 수신 |
| Firewall 내부 | 172.28.20.2 | 내부 웹서버 연결 |
| Nginx Web | 172.28.20.10 | 웹서비스 제공 |
| Node.js API | 172.28.20.20 | API 데이터 제공 |

### 네트워크 대역

- External Network: `172.28.10.0/24`
- Internal Network: `172.28.20.0/24`

External Network와 Internal Network를 분리하여 외부에서 내부 서비스로 직접 접근하는 것을 제한합니다.

### 서비스 포트

| 서비스 | 포트 | 설명 |
|---|---|---|
| Web | TCP 80 | 외부 웹서비스 |
| SSH | TCP 2222 | 관리자 접속용 호스트 포트 |
| API | TCP 3000 | 내부 API 통신 |

- 웹서버와 API 서버는 호스트에 직접 포트를 공개하지 않습니다.
- 외부 사용자의 웹 요청은 방화벽을 통해 웹서버로 전달됩니다.
- API 서버는 내부 네트워크에서 웹서버의 요청을 처리합니다.
- 관리자 SSH 접속은 지정된 관리자만 허용하도록 구성합니다.

## 3. 실행 환경

- Linux 서버 또는 VM
- Docker
- Docker Compose

Docker 및 Docker Compose가 설치되어 있어야 합니다.

## 4. 실행 방법

프로젝트 최상위 디렉터리에서 실행합니다.

### 4-1. 설정 파일 검사

```bash
docker compose config
```

### 4-2. 컨테이너 빌드 및 실행

```bash
docker compose up -d --build
```

### 4-3. 실행 상태 확인

```bash
docker compose ps
```

### 4-4. 전체 로그 확인

```bash
docker compose logs
```

특정 컨테이너의 로그만 확인하려면 다음 명령어를 사용합니다.

```bash
docker compose logs firewall
docker compose logs web
docker compose logs api
```

## 5. 종료 방법

실행 중인 컨테이너를 종료하고 네트워크를 정리합니다.

```bash
docker compose down
```

컨테이너와 네트워크가 종료되며, 이미지와 소스 파일은 삭제되지 않습니다.

## 6. 재실행 방법

프로젝트 최상위 디렉터리에서 다음 명령어를 실행합니다.

```bash
docker compose up -d
```

코드를 수정하여 이미지를 다시 빌드해야 하는 경우 다음 명령어를 사용합니다.

```bash
docker compose up -d --build
```

## 7. 웹서비스 및 API 확인

### 7-1. 웹서비스 접속

브라우저에서 다음 주소로 접속합니다.

```text
http://<Linux 서버 IP>
```

웹서비스는 TCP 80을 사용하고, 
외부 사용자의 HTTP 요청은 Firewall을 거쳐 Nginx Web Server로 전달됩니다.

### 7-2. 웹서버 응답 확인

```bash
docker compose exec web wget -qO- http://localhost
```

정상적으로 HTML 내용이 출력되면 Nginx 웹서버가 동작하는 것입니다.

### 7-3. API 서버 확인

API 서버의 상태를 확인하려면 다음 주소를 사용합니다.

```text
http://<Linux 서버 IP>/api/status
```

API는 Nginx의 Reverse Proxy를 통해 전달되며, API 컨테이너의 포트 3000은 외부에 직접 공개하지 않습니다.

## 8. 보안 테스트

다음 항목을 확인합니다.

- 외부에서 방화벽을 경유한 웹 접속 성공
- 웹서비스 TCP 80 이외의 불필요한 접근 차단
- 지정된 관리자 IP에서만 관리 접속 허용
- 관리자 인증(ID/PW) 정상 동작
- 웹서버 직접 접근 및 방화벽 우회 차단
- API 서버 외부 직접 접근 차단
- 웹서버 응답 트래픽의 방화벽 경유 여부 확인

## 9. 참고 사항

- 방화벽의 NAT 및 접근 제어 규칙은 별도의 초기화 스크립트에서 관리합니다.
- 웹서버의 외부 포트 공개는 방화벽을 통해서만 이루어지도록 구성합니다.
- API 서버는 내부 네트워크에서만 접근할 수 있도록 구성합니다.
- 관리자 SSH 접속 방식과 포트는 최종 통합 설정에 따라 확정합니다.
- 대시보드의 트래픽 및 접근 로그는 실제 방화벽 연동 전까지 샘플 데이터로 표시합니다.
- 실제 방화벽 경유 및 우회 차단 여부는 통합 테스트를 통해 확인해야 합니다.