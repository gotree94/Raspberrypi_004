# 🍓 라즈베리파이4 부팅 시 자동실행 설정 가이드

부팅이 완료되면 Python 프로그램(`python test.py` 등)을 자동으로 실행하는 4가지 방법을 정리합니다.

---

## 📋 방법 비교

| 방법 | 난이도 | 안정성 | 권장 상황 | 재시작 자동복구 |
|------|--------|--------|-----------|----------------|
| ① systemd 서비스 등록 | 보통 ⭐⭐⭐ | ★★★★★ 매우 높음 | 서버/데몬 프로그램 | ✅ 가능 |
| ② crontab @reboot | 쉬움 ⭐⭐ | ★★★ 보통 | 간단한 스크립트 | ❌ 불가 |
| ③ rc.local | 매우 쉬움 ⭐ | ★★ 낮음(구식) | 레거시 호환/테스트용 | ❌ 불가 |
| ④ autostart (GUI 전용) | 쉬움 ⭐⭐ | ★★★ 보통 | 데스크탑/OpenCV GUI 앱 | ❌ 불가 |

> ⭐ **추천**: 헤드리스/센서 프로그램 → **① systemd** | GUI 앱 → **④ autostart**

---

## ① systemd 서비스 등록 ★ 가장 권장

헤드리스로 센서 읽기, 네트워크, 모니터링 등 실무 프로그램에 최적입니다.  
비정상 종료 시 **자동 재시작**까지 지원하여 운영 환경에서도 신뢰성 있게 동작합니다.

### 1-1. 서비스 파일 생성

nano editor를 이용하는 방법
```bash
sudo nano /etc/systemd/system/mai27.service
```

vi editor를 이용하는 방법
```bash
sudo vi /etc/systemd/system/mai27.service
```

또는 MobaXterm에서

```bash
cd /etc/systemd/system/
touch mai27.service
```

### 1-2. 서비스 파일 내용 작성

```ini
[Unit]
Description=MAI27 Python Service
After=network.target

[Service]
ExecStart=/usr/bin/python3 /home/gotree94/src/project_27/test.py
WorkingDirectory=/home/gotree94/src/project_27
StandardOutput=journal
StandardError=journal
Restart=always
RestartSec=5
User=gotree94

[Install]
WantedBy=multi-user.target
```

| 항목 | 설명 |
|------|------|
| `After=network.target` | 네트워크 초기화 후 실행 |
| `Restart=always` | 비정상 종료 시 자동 재시작 |
| `RestartSec=5` | 재시작 전 5초 대기 |
| `User=gotree94` | gotree94 사용자 권한으로 실행 |

### 1-3. 서비스 등록 및 활성화

```bash
# systemd 재로드
sudo systemctl daemon-reload

# 부팅 시 자동실행 등록
sudo systemctl enable mai27.service

# 지금 즉시 시작
sudo systemctl start mai27.service
```

### 1-4. 상태 확인 및 관리

```bash
# 서비스 상태 확인
sudo systemctl status mai27.service

# 실시간 로그 확인
journalctl -u mai27.service -f

# 서비스 중지
sudo systemctl stop mai27.service

# 자동실행 해제
sudo systemctl disable mai27.service
```

---

## ② crontab @reboot

간단한 스크립트를 빠르게 등록할 때 유용합니다.

### 2-1. crontab 편집

```bash
crontab -e
```

### 2-2. 맨 아래에 추가

```cron
@reboot sleep 10 && /usr/bin/python3 /home/gotree94/src/project_27/test.py >> /home/gotree94/src/project_27/mai27.log 2>&1
```

> **`sleep 10`** : 부팅 직후 네트워크, GPIO 등 주변 장치가 준비될 때까지 10초 대기  
> **`>> /home/pi/mai27.log 2>&1`** : 표준출력 및 에러를 로그 파일에 저장

### 2-3. 로그 확인

```bash
cat /home/gotree94/src/project_27/mai27.log
tail -f /home/gotree94/src/project_27/mai27.log
```

---

## ③ rc.local (전통 방식, 구식)

가장 단순하지만 최신 Raspberry Pi OS(Bookworm 이후)에서는 기본 비활성화된 경우가 있습니다.

### 3-1. rc.local 편집

nano editor를 이용하는 방법

```bash
sudo nano /etc/rc.local
```

```bash
sudo vi /etc/rc.local
```

또는 MobaXterm에서

```bash
cd /etc
touch rc.local
```

### 3-2. `exit 0` 위에 추가

```bash
#!/bin/sh -e
#
# rc.local

sleep 30 && /usr/bin/python3 /home/gotree94/test.py &

exit 0
```

> ⚠️ 맨 뒤에 **`&`** 를 반드시 붙여야 백그라운드 실행 → 부팅이 멈추지 않습니다.

### 3-3. rc-local 서비스 활성화 (Bookworm 이상)

```bash
sudo systemctl enable rc-local
sudo systemctl start rc-local
```

상태 확인
```
sudo systemctl status rc-local
```

실행권한

```
sudo chmod +x /etc/rc.local
sudo systemctl start rc-local
sudo systemctl status rc-local
```

### 3.3 확인방법

1. Python 프로그램이 실행 중인지 확인 (가장 확실)

```
ps -ef | grep test.py
```

또는

```
pgrep -af test.py
```

실행 중이라면 예를 들어

```
1234 python3 /home/gotree94/test.py
```
처럼 PID와 함께 표시됩니다.

2. 프로세스 목록 확인

```
top
```

또는

```
htop
```

에서 python3 또는 test.py를 검색합니다.

3. rc.local에서 로그 남기기 (추천)

rc.local을 다음처럼 수정하면 실제 실행 여부를 쉽게 확인할 수 있습니다.
```
#!/bin/sh -e

echo "$(date) rc.local started" >> /home/gotree94/rc.local.log

sleep 30

echo "$(date) starting python" >> /home/gotree94/rc.local.log

/usr/bin/python3 /home/gotree94/src/project_27/test.py >> /home/gotree94/main27.log 2>&1 &

exit 0
```

확인:

```
cat /home/gotree94/rc.local.log
```

4. systemd 로그 확인

```
journalctl -u rc-local.service
```

또는

```
journalctl -b | grep rc.local
```

---

## ④ autostart (GUI 창이 있는 프로그램 전용)

OpenCV 카메라 미리보기, Tkinter GUI, PyQt5 앱 등 **화면이 필요한 경우**에 사용합니다.  
데스크탑 환경(LXDE/Wayfire)이 실행된 후 동작합니다.

### 4-1. autostart 디렉토리 생성

```bash
mkdir -p ~/.config/autostart
```

### 4-2. .desktop 파일 작성

```bash
nano ~/.config/autostart/mai27.desktop
```

```ini
[Desktop Entry]
Type=Application
Name=MAI27
Exec=/usr/bin/python3 /home/gotree94/src/project_27/test.py
X-GNOME-Autostart-enabled=true
```

> **주의**: 헤드리스(모니터 없음) 환경에서는 동작하지 않습니다.

---

## 🔍 Python 경로 확인

방법에 따라 Python 경로를 정확히 지정해야 합니다.

```bash
# Python3 경로 확인
which python3
# 출력 예: /usr/bin/python3

# 가상환경 사용 시
source /home/gotree94/src/project_27/venv/bin/activate
which python
# 출력 예: /home/gotree94/src/project_27/venv/bin/python
```

> 가상환경(venv)을 사용하는 경우 `ExecStart` 또는 `Exec`에 가상환경의 Python 경로를 지정하세요.

---

## 🛠️ 문제 해결

| 증상 | 원인 | 해결 방법 |
|------|------|-----------|
| 프로그램이 실행되지 않음 | Python 경로 오류 | `which python3` 로 경로 확인 후 수정 |
| 네트워크 관련 오류 | 부팅 타이밍 문제 | `After=network-online.target` 또는 `sleep` 추가 |
| GPIO 접근 오류 | 권한 문제 | `User=root` 또는 `pi` 계정 gpio 그룹 확인 |
| 로그가 보이지 않음 | 경로 오류 | `journalctl -u 서비스명 -f` 로 에러 확인 |
| rc.local이 실행 안 됨 | 서비스 비활성화 | `sudo systemctl enable rc-local` 실행 |

---

## 📌 핵심 요약

```
센서/네트워크/모니터링 프로그램  →  ① systemd  (재시작 자동복구 ✅)
빠른 테스트용 단순 스크립트     →  ② crontab @reboot
OpenCV/Tkinter/PyQt5 GUI 앱    →  ④ autostart
레거시 환경 호환 필요           →  ③ rc.local
```

---

## 📎 참고

- Raspberry Pi OS Bookworm 기준 작성
- 테스트 환경: Raspberry Pi 4B
- Python 실행 파일 예시: `test.py`
