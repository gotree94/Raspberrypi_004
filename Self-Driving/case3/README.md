# Case3: DIY 레이싱 휠 + STM32 + RPi — End-to-End Self-Driving 데이터 수집 시스템

## 목표

레이싱 휠(STM32 엔코더)로 조향하고, **Raspberry Pi + USB 카메라**를 통해
영상을 취득하여 PC에서 실시간 모니터링 + 녹화하는 원격 데이터 수집 시스템.

---

## 1. 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────────────┐
│  [STM32]     ───Serial──→  [PC Controller]  ←──Keyboard(WASDX)──  │
│  EC11 Encoder              python pc_controller.py                  │
│  -1024~+1024                 │          │                           │
│                              │ TCP cmd  │ TCP video                 │
│                              ▼          ▼                           │
│                         [Raspberry Pi]                              │
│                         python rpi_streamer.py                      │
│                              │                                      │
│                         [USB Camera]  [Motor Driver ← GPIO PWM]    │
└─────────────────────────────────────────────────────────────────────┘
```

### 2개의 프로그램

| 프로그램 | 실행 위치 | 역할 |
|:---|---:|:---|
| **rpi_streamer.py** | Raspberry Pi | 카메라 영상 TCP 스트리밍 + 명령 수신 + 모터 제어 |
| **pc_controller.py** | PC | 영상 수신/디스플레이 + STM32 엔코더 입력 + WASDX 전송 + 녹화 |

---

## 2. 통신 프로토콜

### 영상 스트림 (TCP port 8000)

```
[RPi → PC]  4바이트(payload length, uint32 big-endian) + JPEG bytes
            320x240, JPEG quality 70, ~20fps
```

### 명령 채널 (TCP port 8001)

| 명령 | 포맷 | 설명 |
|:---|:---|:---|
| 전진 | `CMD:W\n` | 양쪽 모터 +speed |
| 후진 | `CMD:S\n` | 양쪽 모터 -speed |
| 좌회전 | `CMD:A\n` | 감속 회전 |
| 우회전 | `CMD:D\n` | 감속 회전 |
| 정지 | `CMD:X\n` | 모든 모터 0 |
| 연속 조향 | `STEER:left,right\n` | -1.0~+1.0 각 모터 속도 |

> **STEER 명령**은 엔코더 연결 시 사용. `pc_controller.py`가 엔코더 값으로
> `left = speed * (1 - steering)`, `right = speed * (1 + steering)` 계산 후 전송.

### STM32 → PC Serial 포맷

```
-1024 ~ +1024  (12비트 분해능, 2048 스텝)
양수 = 우회전, 음수 = 좌회전
115200 baud, USB CDC
```

---

## 3. 프로그램 상세

### 3.1 `rpi_streamer.py` — Raspberry Pi

```bash
python rpi_streamer.py [--cam 0] [--video-port 8000] [--cmd-port 8001]
                       [--width 320] [--height 240] [--fps 20] [--speed 0.5]
```

**내부 구조 (Threaded):**

```
┌─ Main Thread ─────────────────────────┐
│  KeyboardInterrupt 대기                │
└────────────────────────────────────────┘

┌─ Capture Thread ──────────────────────┐
│  cv2.VideoCapture(0)                  │
│  → JPEG encode → frame_queue          │
└────────────────────────────────────────┘

┌─ Stream Thread ───────────────────────┐
│  TCP Server (port 8000)               │
│  ← frame_queue → send(len + data)     │
└────────────────────────────────────────┘

┌─ Command Thread ──────────────────────┐
│  TCP Server (port 8001)               │
│  "CMD:W" → MotorController.set()       │
│  "STEER:-0.5,0.8" → set_speeds()      │
└────────────────────────────────────────┘
```

**MotorController (GPIO):**

| 핀 | BCM | 기능 |
|:---:|:---:|:---|
| ENA | 18 | 좌측 PWM |
| IN1 | 23 | 좌측 방향 1 |
| IN2 | 24 | 좌측 방향 2 |
| IN3 | 25 | 우측 방향 1 |
| IN4 | 12 | 우측 방향 2 |
| ENB | 13 | 우측 PWM |

> RPi.GPIO가 없으면 simulation mode로 동작 (명령어만 print)

### 3.2 `pc_controller.py` — PC

```bash
python pc_controller.py --rpi 192.168.1.100 [--com COM3] [--record]
                        [--video-port 8000] [--cmd-port 8001]
                        [--out collected_data] [--baud 115200]
```

**내부 구조 (Threaded):**

```
┌─ Main Thread ─────────────────────────────┐
│  cv2.imshow + cv2.waitKey (keyboard)      │
│  → frame display + HUD overlay            │
│  → recorder.record()                      │
└────────────────────────────────────────────┘

┌─ Video Thread ────────────────────────────┐
│  TCP Client → RPi:8000                    │
│  recv(len + JPEG) → decode → latest_frame │
└────────────────────────────────────────────┘

┌─ Cmd Thread ──────────────────────────────┐
│  TCP Client → RPi:8001                    │
│  send_queue → sendall(cmd + "\n")         │
└────────────────────────────────────────────┘

┌─ Encoder Thread ──────────────────────────┐
│  serial.Serial(COM3, 115200)              │
│  readline → int → /1024 → value (-1~+1)  │
└────────────────────────────────────────────┘
```

**Keyboard Controls:**

| 키 | 기능 | 비고 |
|:---:|:---|---:|
| W/S | 전진/후진 속도 조절 | 0.1씩 증감 |
| A/D | 키보드 좌/우회전 | 엔코더 없을 때만 |
| X | 정지 | 속도 0 |
| +/- | 기본 속도 조절 | |
| SPACE | 녹화 토글 | ON/OFF |
| ESC | 종료 | |

**HUD Display:**

```
┌─ top-left ─────────────────────┐
│ FPS: 19                         │
│ Speed: 0.50                    │
│ Enc: +0.325                    │
│ Cmd: S +0.33                   │
│ REC: ● (or ○)                  │
└─────────────────────────────────┘
           ┌── Steering Bar ──┐
           │████████░░░░░░░░░│ -0.25
           └──────────────────┘
```

### 3.3 데이터 저장 포맷

`train_model.py`와 **완벽 호환**:

```
collected_data/
├── frame_000000.npy     # 160×80 RGB, uint8
├── frame_000001.npy
├── ...
└── metadata.json         # {frame_idx: {steering, timestamp}}
```

```python
# 저장 로직 (pc_controller.py)
frame_small = cv2.resize(frame, (160, 80))
np.save(f"{out_dir}/frame_{idx:06d}.npy", frame_small)
metadata[idx] = {"steering": steering, "timestamp": t}
```

---

## 4. 하드웨어

### 부품 목록

| 부품 | 모델 | 예상 가격 | 역할 |
|:---|---:|---:|:---|
| MCU | **STM32F103C8T6 (Blue Pill)** | ~4,000원 | 엔코더 읽기 → Serial |
| Encoder | **EC11** (30 P/R, 120 detent) | ~1,000원 | 조향 각도 감지 |
| SBC | **Raspberry Pi 3/4/Zero 2 W** | ~50,000원 | 카메라 + 스트리밍 + 모터 |
| 카메라 | **USB Webcam** | ~15,000원 | 영상 취득 |
| 모터 드라이버 | **L298N** | ~4,000원 | DC모터 2채널 PWM |
| DC모터 | **N20 Micro Metal Gearmotor** | ~6,000원 × 2 | 구동 |
| 전원 | **5V 3A Power Bank** | ~10,000원 | RPi + 모터 전원 |
| 3D 프린팅 | PLA 필라멘트 | ~2,000원 | 휠, 하우징 |
| 베어링 | 608ZZ (x2) | ~1,000원 | 회전축 |
| SPRING | 토션 스프링 | ~500원 | 센터링 |
| **합계** | | **~100,000원** | (휠 제외 시 ~13,000원) |

### 구성도

```
     ┌───[RPi]───┐        ┌───[PC]───┐
     │ USB Cam   │        │ Controller│
     │ GPIO→L298N│─TCP──→ │ STM32←USB│
     │ DC Motors │        │ Display  │
     └───────────┘        │ Record   │
                          └──────────┘
```

---

## 5. 설치 및 실행

### Raspberry Pi

```bash
# 의존성 설치
sudo apt update
sudo apt install python3-opencv python3-pip
pip3 install RPi.GPIO

# 실행
python3 rpi_streamer.py
```

### PC

```powershell
# 의존성 설치
pip install opencv-python numpy pyserial

# 실행 (STM32 연결)
python pc_controller.py --rpi 192.168.1.100 --com COM3

# 실행 (키보드만)
python pc_controller.py --rpi 192.168.1.100

# 실행 (녹화 자동 시작)
python pc_controller.py --rpi 192.168.1.100 --com COM3 --record
```

### STM32 (CubeIDE)

1. STM32CubeMX: TIM2 → Combined Channels → Encoder Mode TI1 and TI2
2. USB_DEVICE → Communication Device Class (CDC)
3. Generate code + add main loop (README 섹션 3 코드 참조)
4. Flash to STM32F103

---

## 6. 데이터 흐름 예시

```
STM32 엔코더: +512  ← 휠을 우측으로 50% 회전
      ↓
PC Serial read: 512 → steering = 512/1024 = +0.5
      ↓
left  = 0.5 * (1 - 0.5) = 0.25  (우측)
right = 0.5 * (1 + 0.5) = 0.75  (더 빠르게)
      ↓
TCP send: "STEER:0.250,0.750\n"
      ↓
RPi receive → L298N PWM: left=25%, right=75% → 우회전
      ↓
PC display HUD + record (frame + 0.5)
```

---

## 7. 학습 파이프라인 연동

```
수집 → 전처리 → 학습 → 시뮬레이션
  │        │        │        │
  │  [pc_controller.py]        │
  │  → frame_*.npy            │
  │  → metadata.json          │
  ▼        ▼        ▼        ▼
  [prepare_data.py]  (바로 사용 가능, 이미 동일 포맷)
  [train_model.py]   (--data collected_data)
  [simulator.py]     (--model steering_model.keras)
```

---

## 8. 파일 목록 (case3)

| 파일 | 설명 |
|:---|:---|
| `README.md` | 시스템 전체 문서 |
| `rpi_streamer.py` | **Program 1** — RPi 영상 스트리밍 + 모터 제어 |
| `pc_controller.py` | **Program 2** — PC 모니터링 + 엔코더 입력 + 녹화 |
| `stm32_encoder.ioc` | STM32CubeMX 설정 (예정) |
| `stm32_encoder.c` | STM32 펌웨어 (예정) |
| `wheel_3d_model.stl` | 3D 프린팅 휠 모델 (예정) |
