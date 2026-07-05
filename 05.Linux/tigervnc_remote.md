# TigerVNC — 라즈베리파이 고속 원격 데스크톱

> TigerVNC는 RealVNC보다 가볍고 빠른 오픈소스 VNC 구현체입니다. <br>
> 로컬 네트워크에서 직접 연결하므로 클라우드 중계 방식보다 지연시간이 훨씬 짧습니다.

---

## 1. 개요

| 항목 | RealVNC | TigerVNC |
|------|---------|----------|
| 연결 방식 | 클라우드 중계 (외부 서버 경유) | 직접 연결 (로컬 네트워크) |
| 속도 | 상대적으로 느림 | **빠름** (압축/인코딩 최적화) |
| 라이선스 | Home plan 제한 (무료 판도 변화) | **완전 무료 오픈소스** |
| Bookworm 지원 | Wayland 미지원 | **WayVNC + TigerVNC 조합 권장** |

---

## 2. 라즈베리파이 설정 (서버)

Raspberry Pi OS Bookworm/Trixie에는 **WayVNC**가 기본 포함되어 있습니다.

### 2.1. VNC 활성화

```bash
# 방법 1: raspi-config
sudo raspi-config
# → Interface Options → VNC → Enable

# 방법 2: GUI
# 메뉴 → Preferences → Raspberry Pi Configuration → Interfaces → VNC → Enable
```

### 2.2. WayVNC 상태 확인

```bash
systemctl --user status wayvnc
```

### 2.3. (선택) RealVNC 제거 — 충돌 방지

```bash
sudo apt purge realvnc-vnc-server
```

---

## 3. PC 클라이언트 설치

### Linux (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install tigervnc-viewer
```

### Windows

1. [TigerVNC GitHub Releases](https://github.com/TigerVNC/tigervnc/releases) 접속
2. 최신 `vncviewer64-<버전>.exe` 다운로드
3. 실행 → 라즈베리파이 IP 입력

### macOS

```bash
brew install tigervnc-viewer
# 또는 https://github.com/TigerVNC/tigervnc/releases 에서 .dmg 다운로드
```

---

## 4. 연결

```bash
# Linux 터미널
vncviewer 192.168.xxx.xxx

# 또는
vncviewer raspberrypi.local
```

**연결 정보 입력:**
- **VNC Server:** `192.168.xxx.xxx` (라즈베리파이 IP)
- **Options:** 기본값 유지
- **암호:** 라즈베리파이 사용자 계정 비밀번호

> ✅ 연결 성공 시 제목 표시줄에 `WayVNC - TigerVNC` 가 표시됩니다.

---

## 5. 성능 최적화 팁

| 설정 | 권장값 | 설명 |
|------|--------|------|
| 연결 방식 | **유선 이더넷** | WiFi보다 대역폭 안정적, 지연시간 감소 |
| GPU 메모리 | **128MB 이상** | `sudo raspi-config → Performance Options → GPU Memory` |
| 화면 해상도 | **720p ~ 1080p** | 4K는 VNC에 불필요, 대역폭만 낭비 |
| 색상 깊이 | **16비트** | `vncviewer -PreferredEncoding=raw -PixelFormat=rgb16` |
| 압축 방식 | **Tight / ZRLE** | TigerVNC 기본값, 낮은 대역폭에 최적 |

### 고급: 다른 해상도로 가상 세션 열기

```bash
# 라즈베리파이에서 가상 디스플레이 생성 (물리 모니터 없이 접속)
wayvnc --max-fps 30 --max-viewports 2
```

---

## 6. 문제 해결

### 연결 거부됨 (Connection refused)

```bash
# WayVNC 실행 확인
systemctl --user status wayvnc

# 수동 시작
systemctl --user start wayvnc
```

### 검은 화면만 보임

```bash
# 최신 패키지로 업데이트
sudo apt update
sudo apt upgrade
```

### 인증 실패

`raspi-config`에서 VNC를 활성화한 후 **반드시 재부팅**하세요.

```bash
sudo reboot
```

---

> **참고:** TigerVNC 공식 문서는 [tigervnc.org](https://tigervnc.org/) 에서 확인할 수 있습니다.
>
> *마지막 업데이트: 2026년 7월*
