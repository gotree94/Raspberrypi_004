# ICD (Interface Control Document) 
# STM32F103 ↔ Raspberry Pi 4 UART 통신

---

RPi 4B 설정 방법:

1. /boot/firmware/config.txt (Bookworm) 또는 /boot/config.txt 에 추가:
```
enable_uart=1
dtoverlay=disable-bt
```

  * 블루투스를 비활성화해서 UART0(TXD0/RXD0 on GPIO 14/15)가 Bluetooth에 할당되지 않도록 풀어주는 장치 트리 오버레이입니다.

  * dtoverlay=disable-bt → 블루투스 끄고, PL011 UART0를 GPIO 14/15로 완전히 사용 가능
  * enable_uart=1 → mini UART 활성화
  * 두 줄 다 없으면 RPi 4B에서는 UART0가 Bluetooth에 점유되어 GPIO 14/15를 serial console로 쓰기 어렵습니다.
  * 블루투스를 계속 써야 한다면 dtoverlay=disable-bt를 빼고 enable_uart=1만 넣으면 되지만, mini UART는 속도가 불안정할 수 있습니다.


2. GPIO 핀 연결 (USB-시리얼 어댑터 필요):

```
GPIO 14 (TXD) → USB-시리얼 RX
GPIO 15 (RXD) → USB-시리얼 TX
GND          → GND
```

3. PC에서 PuTTY 등으로 115200 baud 연결
> 참고: 그냥 부팅 후 로그만 확인하려면 journalctl -b 또는 dmesg 명령어로도 충분합니다. serial 콘솔은 부팅 과정 전체를 실시간으로 볼 때 필요합니다.

---


## 시스템 개요

```
┌─────────────────────────┐         UART 115200         ┌──────────────────────┐
│  NUCLEO STM32F103       │ ◄═══════════════════════►   │  Raspberry Pi 4      │
│  (차량 시뮬레이터)       │     8N1, ASCII 패킷        │  (메인 컨트롤러)      │
│                         │                             │                      │
│  • 센서 17개 키 (10Hz)  │                             │  • 데이터 수신/처리    │
│  • 액추에이터 7종 제어   │                             │  • 명령 전송          │
│  • GPS 궤적 이동        │                             │  • 지도 매핑 (예정)    │
│  • 연료 탱크 시뮬레이션  │                             │                      │
└─────────────────────────┘                             └──────────────────────┘
```

---

## 통신 규격

| 항목 | 값 |
|------|------|
| Interface | UART (via ST-LINK VCP → USB) |
| Baud Rate | 115200 |
| Data Bits | 8 |
| Parity | None |
| Stop Bits | 1 |
| Flow Control | None |
| 물리 계층 | USB 케이블 (NUCLEO ST-LINK USB Mini-B → RPi USB-A) |
| RPi 장치 경로 | `/dev/ttyACM0` (VCP 드라이버 자동 매핑) |
| 패킷 구분 | `\n` (newline, LF, 0x0A) |

---

## 패킷 프로토콜

### 공통 형식

```
<type>,<key1>=<value1>,<key2>=<value2>,...\n
```

| 필드 | 설명 |
|------|------|
| `<type>` | 패킷 종류 (`S` = Status 주기, `C` = Command, `R` = Response) |
| `<key>=<value>` | 콤마로 구분된 키-값 쌍 |
| `\n` | 패킷 종료 (LF, 0x0A) |

### Type S — 주기적 상태 보고 (STM32 → RPi)

**전송 주기**: 10Hz (100ms 간격)

```
S,CDS=450,HALL=320,TEMP=25.3,HUMI_T=400,HUMI_H=650,ROT=45,US_DIST=180,JOY_X=500,JOY_Y=500,IR_RX=0,GPS_LAT=37.56,GPS_LNG=127.0,FUEL=920,ACC_X=0,ACC_Y=5,ACC_Z=980,RPM=550\n
```

| Key | 설명 | 범위 | 변화율 | 시뮬레이션 |
|-----|------|------|--------|-----------|
| `CDS` | 조도 센서 | 0~999 | 분당 ±10 | 랜덤 워크 |
| `HALL` | 홀 센서 | 0~999 | 분당 ±15 | 랜덤 워크 |
| `TEMP` | 온도 센서 (NTC) | 0~999 | 분당 ±5 | 랜덤 워크 |
| `HUMI_T` | 온습도 온도값 | 0~999 | 분당 ±7 | 랜덤 워크 |
| `HUMI_H` | 온습도 습도값 | 0~999 | 분당 ±11 | 랜덤 워크 |
| `ROT` | 로터리 엔코더 | 0~100 | 수동 조작 | GUI 다이얼 |
| `US_DIST` | 초음파 거리 | 0~999 cm | 분당 ±18 | 랜덤 워크 |
| `JOY_X` | 조이스틱 X | 0~999 | 중앙 500, ±7 왕복 | 자동 시뮬레이션 |
| `JOY_Y` | 조이스틱 Y | 0~999 | 중앙 500, ±11 왕복 | 자동 시뮬레이션 |
| `IR_RX` | IR 수신값 | 0~9 | 버튼 입력 | GUI 버튼 |
| `GPS_LAT` | GPS 위도 | -90~90 | 중심점 기준 궤적 | 원형 궤도 |
| `GPS_LNG` | GPS 경도 | -180~180 | 중심점 기준 궤적 | 원형 궤도 |
| `FUEL` | 연료 잔량 | 0~1000 | 시간당 감소 | 사용시 -1, Refill시 1000 |
| `ACC_X` | 가속도 X | -1000~1000 | 자동 시뮬 | 진동 + 선회 |
| `ACC_Y` | 가속도 Y | -1000~1000 | 자동 시뮬 | 진동 + 선회 |
| `ACC_Z` | 가속도 Z | -1000~1000 | 자동 시뮬 | 중력 980 기준 |
| `RPM` | 엔진 RPM | 0~999 | 자동 변동 | 랜덤 + 주행 연동 |

#### 조이스틱 시뮬레이션 패턴
- 기준값: 500
- X: 5회 증가(500→535) → 5회 감소(535→500) 무한 반복, 1틱당 ±7
- Y: 5회 증가(500→555) → 5회 감소(555→500) 무한 반복, 1틱당 ±11
- 10Hz에서 5+5 = 10틱 = 1초 주기 (분당 60사이클)

#### GPS 궤적 시뮬레이션
- 사용자가 설정한 중심점(lat0, lng0) 기준
- 반경 R (기본 0.001°) 의 원형 궤도
- `lat = lat0 + R × cos(θ)`, `lng = lng0 + R × sin(θ)`
- θ는 시간에 따라 증가 (1분에 1바퀴)

#### 연료 소모
- 주행 중: 10Hz마다 FUEL -= 1 (약 16.7분 만에 1000→0)
- 정차 시: 10Hz마다 FUEL -= 0.1 (약 167분 만에 0)
- GUI "Refill" 버튼: FUEL = 1000으로 초기화

#### IR_RX (IR 수신값)
- GUI 버튼 0~9 중 하나를 누르면 `sensors['IR_RX']['val']` 이 해당 값으로 설정됨
- 다음 10Hz S 패킷에 `IR_RX=n` 형태로 즉시 반영
- IR_TX(송신)와 별개: IR_RX는 STM32가 외부 리모컨으로부터 수신한 값을 시뮬레이션

#### 연료 주행/정차 모드 전환
- GUI "연료 모드: 주행/정차" 버튼으로 `fuel_driving` 플래그 토글
  - 주행(Driving): 10Hz마다 FUEL -= 1
  - 정차(Stopped): 10Hz마다 FUEL -= 0.1 (10배 느림)
- "연료 채움" 버튼: FUEL = 1000 초기화

#### 액추에이터 슬라이더
- WHEEL1~4, SERVO1~2 슬라이더를 움직이면 즉시 `C,WHEELn=value` 명령 전송
- LED_G, LED_B, LED_RGB_R/G/B 슬라이더도 동일하게 명령 전송
- 시뮬레이터 내부 엔진이 명령을 수신·처리하여 `engine.act` 갱신

---

### Type C — 명령 (RPi → STM32)

```
C,WHEEL1=500,WHEEL2=500,WHEEL3=500,WHEEL4=500,SERVO1=90,SERVO2=45,CLCD=Hello World!,LED_G=255,LED_B=0,LED_RGB_R=128,LED_RGB_G=64,LED_RGB_B=32,BUZZER=1,LASER=0,IR_TX=5\n
```

| Key | 설명 | 범위 | 비고 |
|-----|------|------|------|
| `WHEEL1`~`WHEEL4` | DC 모터 PWM (바퀴 1~4) | 0~999 | 0=정지, 500=중속, 999=최고속 |
| `SERVO1`~`SERVO2` | 서보모터 각도 | 0~999 | 0→0°, 500→90°, 999→180° |
| `CLCD` | I2C CLCD 16x2 문자 | 문자열 (최대 32자) | 16자 + `\n` + 16자 |
| `LED_G` | 2색 LED Green | 0~999 | PWM 밝기 |
| `LED_B` | 2색 LED Blue | 0~999 | PWM 밝기 |
| `LED_RGB_R` | 3색 LED Red | 0~999 | PWM 밝기 |
| `LED_RGB_G` | 3색 LED Green | 0~999 | PWM 밝기 |
| `LED_RGB_B` | 3색 LED Blue | 0~999 | PWM 밝기 |
| `BUZZER` | 부저 | 0 또는 1 | 0=OFF, 1=ON |
| `LASER` | 레이저 | 0 또는 1 | 0=OFF, 1=ON |
| `IR_TX` | IR 송신 버튼값 | 1~9 | GUI 버튼으로 송신 (IR_RX와 별개) |

#### 서보모터 각도 매핑

```
angle_deg = value × 180 / 1000
```

| 입력값 | 각도 | 위치 |
|--------|------|------|
| 0 | 0° | 최좌측 |
| 250 | 45° | 45도 |
| 500 | 90° | 중앙 |
| 750 | 135° | 135도 |
| 999 | ~180° | 최우측 |

#### CLCD 표시 규칙
- 1행: 16자, `\n`로 행 구분
- 예: `CLCD=Hello World!` → 1행에 "Hello World!   "
- 예: `CLCD=Line1\nLine2` → 1행 "Line1", 2행 "Line2"
- 16자 초과 시 trim

---

### Type R — 응답 (STM32 → RPi)

```
R,OK\n                    ← 명령 성공
R,ERR=Invalid value\n     ← 명령 실패 (값 범위 오류)
R,ERR=Unknown key: LED4\n ← 명령 실패 (미지정 키)
```

명령 수신 시 즉시 응답. 지연 없음.

---

## 전송 예시

### 정상 통신 흐름

```
[STM32] ─── S,CDS=450,HALL=320,...\n ──────────────────────────► [RPi]   (10Hz 주기)
[STM32] ─── S,CDS=451,HALL=321,...\n ──────────────────────────► [RPi]
[RPi]   ─── C,WHEEL1=999,WHEEL2=999,...\n ────────────────────► [STM32] (명령)
[STM32] ─── R,OK\n ◄────────────────────────────────────────────── [RPi]
[STM32] ─── S,CDS=452,HALL=322,...\n ──────────────────────────► [RPi]   (계속)
```

### 파이썬 코드 예시 (RPi 측 수신)

```python
import serial

ser = serial.Serial('/dev/ttyACM0', 115200, timeout=1)

while True:
    line = ser.readline().decode('utf-8', errors='ignore').strip()
    if not line:
        continue
    if line.startswith('S,'):
        parts = line[2:].split(',')
        data = {}
        for p in parts:
            if '=' in p:
                k, v = p.split('=', 1)
                data[k] = v
        print(f"CDS={data.get('CDS')}, JOY_X={data.get('JOY_X')}")
```

### 파이썬 코드 예시 (RPi 측 송신)

```python
cmd = "C,WHEEL1=500,WHEEL2=500,SERVO1=90,BUZZER=0\n"
ser.write(cmd.encode())
resp = ser.readline().decode().strip()
print(resp)  # R,OK
```

---

## 하드웨어 핀맵

### NUCLEO STM32F103 핀 연결

| STM32 핀 | 기능 | 연결 대상 |
|----------|------|-----------|
| PA2 (UART2_TX) | UART 송신 | ST-LINK VCP (내부) |
| PA3 (UART2_RX) | UART 수신 | ST-LINK VCP (내부) |
| PB6 (I2C1_SCL) | I2C CLCD SCL | CLCD 모듈 |
| PB7 (I2C1_SDA) | I2C CLCD SDA | CLCD 모듈 |
| PA0 | 조도 센서 (ADC) | CDS |
| PA1 | 홀 센서 (ADC) | HALL |
| PA4 | 온도 NTC (ADC) | TEMP |
| PA5 | 온습도 센서 | DHT11/22 |
| PB0 | 초음파 Trig | HC-SR04 |
| PB1 | 초음파 Echo | HC-SR04 |
| PA6 | 로터리 엔코더 CLK | Rotary Encoder |
| PA7 | 로터리 엔코더 DT | Rotary Encoder |
| PB3 | Joystick X (ADC) | 조이스틱 |
| PB4 | Joystick Y (ADC) | 조이스틱 |
| PA8~PA11 | PWM 바퀴 1~4 | L298N 모터 드라이버 |
| PA15, PB5 | 서보모터 1, 2 | 서보 PWM |
| PB12 | 부저 | Buzzer |
| PB13 | 레이저 | Laser Module |
| PB14 | IR 수신 | IR Receiver |
| PB15 | IR 송신 | IR LED |
| PC0 | 2색 LED Green | 2색 LED |
| PC1 | 2색 LED Blue | 2색 LED |
| PC2~PC4 | 3색 LED R/G/B | RGB LED |
| VCC | 3.3V or 5V | 쉴드 보드 전원 |
| GND | Ground | 공통 GND |

---

## 시뮬레이터 사용법

### 파일 구조

```
1-2/
├── README.md              ← 기존 하드웨어 조립 문서
├── ICD_SIMULATOR.md       ← 본 문서 (통신 명세 + 시뮬레이터 설명)
├── simulator_stm32.py     ← STM32F103 차량 시뮬레이터 (GUI)
├── rpi_controller.py      ← RPi 컨트롤러 시뮬레이터 검증 도구
└── 1-2-F*.png             ← 기존 이미지
```

### 실행

```bash
# GUI 실행 (포트 선택 드롭다운)
python simulator_stm32.py

# 시리얼 포트 직접 지정
python simulator_stm32.py --serial-port COM3
python simulator_stm32.py --serial-port /dev/ttyACM0

# 헤드리스 모드 (GUI 없이)
python simulator_stm32.py --headless --serial-port COM3
```

### 연결 설정

시뮬레이터 실행 시 상단에 연결 설정 바가 표시됩니다.

| 항목 | 설명 |
|------|------|
| **COM 포트** | 시스템 시리얼 포트 자동 검색 후 드롭다운에서 선택 |
| **새로고침** 🔄 | 현재 시스템의 COM 포트 목록 재검색 |
| **연결/종료** | 클릭으로 시리얼 연결 시작 또는 종료 |

#### 포트 자동 검색
- Windows: `COM1` ~ `COM256` 스캔 (pyserial 설치 시 상세 정보 표시)
- Linux: `/dev/ttyUSB*`, `/dev/ttyACM*`, `/dev/ttyAMA*`, `/dev/ttyS*` 검색
- pyserial 선택사항 (미설치 시 기본 검색으로 동작)

#### 보드레이트
- 기본값: **115200 bps** (고정, ICD 규격 준수)

### 시리얼 통신 테스트 (RPi 측)

```bash
# minicom으로 직접 확인
minicom -b 115200 -D /dev/ttyACM0

# 또는 Python
python -c "
import serial
ser = serial.Serial('/dev/ttyACM0', 115200, timeout=1)
while True:
    line = ser.readline().decode().strip()
    if line:
        print(line)
"
```

시뮬레이터가 RPi의 `/dev/ttyACM0` (또는 `/dev/ttyUSB0`)에 연결되면
STM32F103이 전송하는 `S,CDS=...` 패킷을 수신할 수 있습니다.

---

## RPi Controller — 시뮬레이터 검증 도구

`rpi_controller.py`는 실제 라즈베리파이에서 실행될 코드를 모사한 **테스트/검증 도구**입니다.
STM32F103 시뮬레이터와 동일한 시리얼 포트로 연결하여 모든 기능을 검증합니다.

### 실행

```bash
# 포트 선택 후 인터랙티브 모드
python rpi_controller.py

# 포트 직접 지정
python rpi_controller.py --serial-port COM3

# 자동 테스트 (전체 명령 검증)
python rpi_controller.py --serial-port COM3 --auto-test
```

### 기능

| 모드 | 설명 |
|------|------|
| **인터랙티브** | 실시간 센서 데이터 표시 + 명령 입력 |
| **자동 테스트** | 22개 정상 명령 + 4개 오류 명령 자동 검증 |

### 자동 테스트 검증 항목 (26 tests)

| # | 명령 | 예상 응답 |
|---|------|-----------|
| 1 | `WHEEL1=500` | `R,OK` |
| 2 | `WHEEL2=300` | `R,OK` |
| 3 | `WHEEL3=700` | `R,OK` |
| 4 | `WHEEL4=999` | `R,OK` |
| 5 | `WHEEL1=0` | `R,OK` |
| 6 | `SERVO1=0` | `R,OK` |
| 7 | `SERVO1=500` | `R,OK` |
| 8 | `SERVO1=999` | `R,OK` |
| 9 | `SERVO2=250` | `R,OK` |
| 10 | `CLCD=Hello World!` | `R,OK` |
| 11 | `CLCD=Line1\nLine2` | `R,OK` |
| 12 | `LED_G=500` | `R,OK` |
| 13 | `LED_B=800` | `R,OK` |
| 14 | `LED_RGB_R=999` | `R,OK` |
| 15 | `LED_RGB_G=500` | `R,OK` |
| 16 | `LED_RGB_B=200` | `R,OK` |
| 17 | `BUZZER=1` | `R,OK` |
| 18 | `BUZZER=0` | `R,OK` |
| 19 | `LASER=1` | `R,OK` |
| 20 | `LASER=0` | `R,OK` |
| 21 | `IR_TX=5` | `R,OK` |
| 22 | `IR_TX=9` | `R,OK` |
| 23 | `WHEEL1=1000` (범위초과) | `R,ERR=...` |
| 24 | `SERVO3=500` (없는키) | `R,ERR=Unknown key: SERVO3` |
| 25 | `BUZZER=2` (잘못된값) | `R,ERR=BUZZER must be 0 or 1` |
| 26 | `INVALID_KEY=1` (알수없는키) | `R,ERR=Unknown key: INVALID_KEY` |

### 테스트 절차

```
1. 터미널 1: python simulator_stm32.py      # 시뮬레이터 실행
2. 터미널 2: python rpi_controller.py        # 컨트롤러 실행, 같은 COM 포트 선택
3. 컨트롤러에서 명령 입력 또는 test 입력
```

---

## 추후 확장 예정

| 기능 | 설명 |
|------|------|
| 지도 매핑 | GPS 좌표를 folium/leaflet으로 실시간 지도 표시 |
| CAN bus 시뮬레이션 | OBD-II 프로토콜 에뮬레이션 |
| 웹 대시보드 | Flask 기반 원격 모니터링 |
| 데이터 로깅 | CSV 저장 + replay 기능 |
| 고장 모드 | 센서 고장/통신 끊김 시나리오 시뮬레이션 |
