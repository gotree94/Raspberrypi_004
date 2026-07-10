# Case3: DIY 레이싱 휠 + STM32 — 실제 조향 GT 수집 시스템

## 목표

레이싱 휠을 직접 제작하여, 사람이 운전하는 **실제 조향각 GT**와
카메라 영상을 동기화하여 기록하는 데이터 수집 시스템 구축.

---

## 1. 시스템 구성

```
[레이싱 휠 (로터리 엔코더)]
        ↓ 회전 각도
[STM32 (Timer Encoder Mode)]
        ↓ USB CDC (Serial)
[PC  Python (pySerial + OpenCV)]
        ↓
[np.save: frame.npy, metadata.json]
```

### 데이터 흐름

```python
while cap.isOpened():
    ret, frame = cap.read()
    steering = ser.readline()             # STM32 → "-512\n"
    np.save(f"frames/frame_{n:06d}.npy", frame)
    metadata[n] = {
        "steering": float(steering),
        "timestamp": time.time()
    }
    n += 1
```

---

## 2. 하드웨어 부품

| 부품 | 모델 | 예상 가격 | 역할 |
|:---|---:|---:|:---|
| MCU | **STM32F103C8T6 (Blue Pill)** | ~4,000원 | Timer Encoder Mode, USB CDC |
| Encoder | **EC11** (30 P/R, 120 detent) | ~1,000원 | 회전 각도 감지 |
| Encoder (대안) | **KY-040** (20 P/R) | ~1,500원 | 더 큰 노브, 장착 용이 |
| 3D 프린팅 | PLA 필라멘트 | ~2,000원 | 휠, 하우징, 베어링 마운트 |
| 베어링 | 608ZZ (x2) | ~1,000원 | 회전축 지지 |
| 복원 스프링 | 토션 스프링 or 고무밴드 | ~500원 | **센터링 (필수)** |
| USB 케이블 | Micro USB | ~1,000원 | PC 연결 |
| **합계** | | **~10,500원** | |

### 권장 구성도

```
        [레이싱 휠] ← PLA 3D 프린팅, 지름 25~30cm
            │
        [회전축] ← 608ZZ 베어링 2개
            │
        [EC11 엔코더] ← 토션 스프링으로 센터링
            │ VCC/GND/A/B
        [STM32F103] ← USB → PC
```

### EC11 핀맵

| EC11 핀 | 연결 |
|:---:|:---|
| A | TIM2_CH1 (PA0) |
| B | TIM2_CH2 (PA1) |
| C (common) | GND |
| SW | GND (버튼, 옵션) |

---

## 3. STM32 펌웨어 (HAL)

### Timer Encoder Mode 설정 (STM32CubeIDE)

```
TIM2: Combined Channels → Encoder Mode TI1 and TI2
    Prescaler = 0
    Period = 65535 (16-bit auto-reload)
    Polarity: Rising Edge both
```

### 메인 코드

```c
#include "main.h"
#include "stdio.h"

TIM_HandleTypeDef htim2;
UART_HandleTypeDef huart2;  // USB CDC

int main(void) {
    HAL_Init();
    SystemClock_Config();
    MX_GPIO_Init();
    MX_TIM2_Init();   // Encoder Mode
    MX_USB_DEVICE_Init();  // USB CDC

    int16_t prev_angle = 0;

    while (1) {
        int16_t angle = (int16_t)__HAL_TIM_GET_COUNTER(&htim2);
        if (angle != prev_angle) {
            char buf[16];
            int len = snprintf(buf, sizeof(buf), "%d\n", angle);
            CDC_Transmit_FS((uint8_t*)buf, len);
            prev_angle = angle;
        }
        HAL_Delay(5);  // 200Hz 전송
    }
}
```

### 데이터 포맷

```
-1024 ~ +1024  (12비트 분해능, 2048 스텝)
양수 = 우회전, 음수 = 좌회전
```

---

## 4. Python 수집 코드

### 의존성

```powershell
pip install pyserial opencv-python numpy
```

### 수집 스크립트 (collect_data.py)

```python
import cv2
import numpy as np
import serial
import time
import json
import os
from pathlib import Path

VIDEO_SOURCE = 0  # USB 카메라 or "Self-driving.mp4"
SERIAL_PORT = "COM3"
OUT_DIR = "collected_data"

ser = serial.Serial(SERIAL_PORT, 115200, timeout=0.01)
cap = cv2.VideoCapture(VIDEO_SOURCE)
Path(OUT_DIR).mkdir(exist_ok=True)

metadata = {}
frame_idx = 0

print("Recording... Press SPACE to start, ESC to stop.")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # 시리얼에서 조향값 읽기 (최신값 1개)
    steering = 0.0
    while ser.in_waiting:
        line = ser.readline().strip()
        if line:
            try:
                steering = int(line) / 1024.0    # -1.0 ~ +1.0
            except:
                pass

    # 저장
    h, w = frame.shape[:2]
    frame_small = cv2.resize(frame[:, w//4:3*w//4], (160, 80))
    np.save(f"{OUT_DIR}/frame_{frame_idx:06d}.npy", frame_small)

    metadata[frame_idx] = {
        "steering": round(steering, 4),
        "timestamp": time.time()
    }

    # 디스플레이
    cv2.putText(frame, f"S: {steering:+.3f}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    cv2.imshow("Recording", frame)

    key = cv2.waitKey(1) & 0xFF
    if key == 27:  # ESC
        break
    elif key == 32:  # SPACE — pause/resume
        cv2.waitKey(-1)

    frame_idx += 1

# 메타데이터 저장
with open(f"{OUT_DIR}/metadata.json", "w") as f:
    json.dump(metadata, f, indent=2)

cap.release()
ser.close()
cv2.destroyAllWindows()
print(f"Saved {frame_idx} frames to {OUT_DIR}/")
```

---

## 5. 레이싱 휠 3D 프린팅 설계

### 휠 규격

| 항목 | 권장값 | 비고 |
|:---|---:|:---|
| 외경 | **250~300 mm** | 실제 차량 대비 1:2 스케일 |
| 림 두께 | 20~25 mm | 잡기 편하게 |
| 그립 | 고무 코팅 or 열수축 튜브 | 미끄럼 방지 |
| 중심축 | 8mm 강봉 or M8 볼트 | 베어링 608ZZ 내경 8mm |
| 무게 | 300~500g | 너무 가벼우면 감각 없음 |

### 센터링 메커니즘

```ascii
    [휠] ← 중심각 ±90° (180° 전체 회전)
     │
    [축] ← 608ZZ 베어링
     │
    [토션 스프링] ← 양단 고정 (0°에서 복원력 최대)
     │
   [EC11 ENCODER] ← 축에 직접 체결
```

**Spring Return 설계 포인트:**
- 토션 스프링은 **0°(중앙)에서 최대 복원력**
- 스프링 상수: 너무 약하면 센터링 안 됨, 너무 강하면 피로
- 권장: **0.5~1.0 N·m/rad** (EC11 회전 토크의 5~10배)

---

## 6. 데이터 품질 비교

| 방식 | GT 정확도 | 샘플 수 | 비용 | 노력 |
|:---|---:|:---:|:---:|:---:|
| Lane Detection (현재) | ❌ 낮음 (합성) | 많음 | 0원 | 낮음 |
| **DIY 레이싱 휠** | **✅ 높음 (실제)** | **많음** | **~1만원** | **중간** |
| 게임패드 (대안) | ✅ 높음 | 많음 | 2~5만원 | 낮음 |
| Logitech G29 | ✅ 높음 | 많음 | 20~30만원 | 낮음 |

---

## 7. 권장 개발 순서

### Phase 1 (개념 증명) — 게임패드로 시작

```python
pip install pygame
# → 게임패드 조이스틱 → steering 값 → 수집
```

### Phase 2 (하드웨어 제작) — DIY 휠

1. STM32 CubeMX 프로젝트 생성 (Encoder Mode)
2. EC11 + STM32 배선, 시리얼 출력 확인
3. 3D 프린팅: 휠 + 하우징 설계 (Fusion360 / TinkerCAD)
4. 조립 → 센터링 스프링 장착
5. Python 수집 스크립트와 연동

### Phase 3 (학습 및 주행)

1. 수집된 데이터로 `prepare_data.py` 실행 (동기화 + 전처리)
2. `train_model.py`로 모델 학습
3. `simulator.py`로 실시간 주행 테스트

---

## 8. 파일 목록 (case3)

| 파일 | 설명 |
|:---|:---|
| `README.md` | 본 문서 |
| `collect_data.py` | Python 수집 스크립트 (예정) |
| `stm32_encoder.ioc` | STM32CubeMX 설정 (예정) |
| `stm32_encoder.c` | STM32 펌웨어 (예정) |
| `wheel_3d_model.stl` | 3D 프린팅 휠 모델 (예정) |
