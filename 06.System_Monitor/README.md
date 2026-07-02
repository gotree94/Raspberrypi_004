# 📊 Raspberry Pi Monitoring System

라즈베리파이 기반 시스템 리소스, 네트워크, 센서, 카메라 및 하드웨어 상태를 모니터링하기 위한 데이터 수집 항목 정리입니다.

---

## 🖥️ 시스템 리소스

| 항목 | 데이터 수집 방법 |
|------|----------------|
| CPU 온도 | `vcgencmd measure_temp` 또는 `/sys/class/thermal` |
| CPU 사용률 (%) | `psutil.cpu_percent()` |
| CPU 주파수 | `psutil.cpu_freq()` |
| CPU 코어별 사용률 | `psutil.cpu_percent(percpu=True)` |
| 메모리 사용량 / 여유 | `psutil.virtual_memory()` |
| 스왑 메모리 | `psutil.swap_memory()` |
| 디스크 사용량 | `psutil.disk_usage('/')` |
| 디스크 I/O 속도 | `psutil.disk_io_counters()` |
| 업타임 / 부팅 시간 | `psutil.boot_time()` |
| 프로세스 목록 | `psutil.pids()` |

---

## 🌐 네트워크

| 항목 | 데이터 수집 방법 |
|------|----------------|
| 네트워크 송수신 속도 | `psutil.net_io_counters()` |
| IP 주소 | `psutil.net_if_addrs()` |
| WiFi 신호 강도 (RSSI) | `iwconfig` / `iwgetid` |
| 연결된 장치 목록 | `arp -a` |
| 열린 포트 | `psutil.net_connections()` |

---

## 📡 GPIO / 센서 (외부 연결)

| 항목 | 데이터 수집 방법 |
|------|----------------|
| 온습도 (DHT11/DHT22) | `Adafruit_DHT` |
| 거리 (HC-SR04) | `gpiozero.DistanceSensor` |
| 조도 (BH1750, LDR) | `smbus2 (I2C)` |
| 기압 / 고도 (BMP280) | `smbus2 (I2C)` |
| CO2 / 공기질 (MQ-135) | `ADC (MCP3008)` |
| 토양 습도 | `ADC (MCP3008)` |
| 적외선 감지 (PIR) | `gpiozero.MotionSensor` |
| 가속도 / 자이로 (MPU-6050) | `smbus2 (I2C)` |

---

## 📷 카메라

| 항목 | 데이터 수집 방법 |
|------|----------------|
| 실시간 영상 스트리밍 | `picamera2 + MJPEG` |
| 사진 캡처 | `picamera2` |
| 영상 처리 결과 | `OpenCV (cv2)` |
| 모션 감지 여부 | `cv2 프레임 차이` |

---

## ⚡ 전력 / 하드웨어 상태

| 항목 | 데이터 수집 방법 |
|------|----------------|
| GPU 온도 | `vcgencmd measure_temp` |
| GPU 메모리 | `vcgencmd get_mem gpu` |
| 전압 상태 (Under-voltage) | `vcgencmd get_throttled` |
| SD카드 읽기/쓰기 속도 | `dd 명령어` |

---

* 모니터링 서버 구현

* 실행 방법
```bash
# 1. Node.js 설치 (없는 경우)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# 2. 프로젝트 폴더 구성
mkdir -p ~/pi-monitor/public
# server.js → ~/pi-monitor/
# package.json → ~/pi-monitor/
# index.html → ~/pi-monitor/public/

# 3. 의존성 설치 및 실행
cd ~/pi-monitor
npm install
node server.js
```

<img width="1254" height="1115" alt="126" src="https://github.com/user-attachments/assets/eff722b9-d426-4f94-b941-4f707435b8f0" />
