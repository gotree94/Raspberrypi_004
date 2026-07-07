# ICD (Interface Control Document) — Efficient Binary Protocol
## STM32F103 ↔ Raspberry Pi 4 UART 통신 (데이터 최소화 + 전송 시간 계산)

---

## 1. 배경 및 목적

### 1.1 문제 인식

기존 ASCII 프로토콜(`S,CDS=450,HALL=320,...`)은 사람이 읽기 쉬우나
**데이터 효율이 매우 낮음**:

| 항목 | ASCII 프로토콜 | 비고 |
|------|---------------|------|
| S 패킷 1회 전송량 | ~150 bytes = **1,500 bits** | 17개 키-값 쌍 + 구분자 |
| C 패킷 1회 전송량 | ~15 bytes = **150 bits** | `C,WHEEL1=500` |
| 패킷 구분方式 | `\n` (LF, 1바이트) | 매 패킷마다 1바이트 낭비 |
| 키 이름 | `CDS`, `HALL`, `TEMP`, ... | 매 패킷마다 4~8바이트 반복 |
| 값 구분자 | `=`, `,` | 매 쌍마다 2바이트 낭비 |

### 1.2 전송 시간 문제

10Hz(100ms 간격) 전송 시, ASCII 프로토콜은 낮은 보드레이트에서 **전송 시간이 100ms를 초과**:

| 보드레이트 | 1비트 시간 | 1바이트(10비트) | ASCII S (150B) | Binary S (37B) |
|-----------|-----------|----------------|----------------|----------------|
| **9600** | 104.17 µs | **1.04 ms** | **156.3 ms ✗** | **38.5 ms ✓** |
| 19200 | 52.08 µs | 0.52 ms | 78.1 ms | 19.3 ms |
| 38400 | 26.04 µs | 0.26 ms | 39.1 ms | 9.6 ms |
| **115200** | 8.68 µs | **86.8 µs** | **13.0 ms** | **3.2 ms** |

> **9600 baud에서 ASCII 프로토콜은 10Hz 유지 불가능!**
> 한 패킷 전송에 156ms가 걸려 다음 전송 주기(100ms)를 초과함.

### 1.3 설계 목표

| 목표 | 설명 |
|------|------|
| **데이터량 최소화** | 고정 길이 바이너리 포맷, 키 이름/구분자 제거 |
| **전송 시간 계산 가능** | 각 패킷의 비트/바이트/시간을 정확히 산출 |
| **모든 보드레이트 호환** | 9600 baud에서도 10Hz 유지 < 50ms |
| **리소스 효율** | CPU/메모리 사용 최소화 (단순 struct pack/unpack) |
| **사람이 읽을 수 있는 진단** | hex dump와 매핑 테이블로 디버깅 가능 |

---

## 2. 시리얼 비트 타이밍 기초

### 2.1 UART 8N1 프레임 구조

```
1바이트 전송 = 10비트
┌─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┐
│ S   │ D0  │ D1  │ D2  │ D3  │ D4  │ D5  │ D6  │ D7  │ S   │
│ T   │     │     │     │     │     │     │     │     │ T   │
│ A   │     │     │     │     │     │     │     │     │ O   │
│ R   │     │     │     │     │     │     │     │     │ P   │
│ T   │     │     │     │     │     │     │     │     │     │
└─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┘
  1      2     3     4     5     6     7     8     9     10   비트 위치
```

| 심볼 | 의미 | 비트 수 |
|------|------|---------|
| START | 시작 비트 (0 → 1 → 0 에지 검출) | 1 |
| D0~D7 | 데이터 비트 (LSB first) | 8 |
| STOP | 정지 비트 (1) | 1 |
| **합계** | **1바이트 전송 = 10비트** | **10** |

### 2.2 비트/바이트/패킷 시간 계산 공식

```
bit_time_us   = 1,000,000 / baud_rate
byte_time_us  = bit_time_us × 10
packet_time_us = byte_time_us × packet_bytes
```

### 2.3 보드레이트별 타이밍 기준표

| 보드레이트 | 비트 시간 | 바이트 시간 | 1ms 당 바이트 |
|-----------|----------|------------|--------------|
| 2400 | 416.67 µs | 4.167 ms | 0.24 |
| 4800 | 208.33 µs | 2.083 ms | 0.48 |
| **9600** | **104.17 µs** | **1.042 ms** | **0.96** |
| 14400 | 69.44 µs | 0.694 ms | 1.44 |
| 19200 | 52.08 µs | 0.521 ms | 1.92 |
| 38400 | 26.04 µs | 0.260 ms | 3.84 |
| 57600 | 17.36 µs | 0.174 ms | 5.76 |
| **115200** | **8.68 µs** | **86.8 µs** | **11.52** |

---

## 3. 효율적 바이너리 프로토콜

### 3.1 설계 원칙

1. **고정 길이 패킷**: 각 타입별로 정해진 바이트 수, 구분자(`\n`) 불필요
2. **Little Endian**: Intel/ARM 호환 (RPi, STM32 모두 LE)
3. **위치 기반 매핑**: 키 이름 대신 바이트 오프셋으로 필드 식별
4. **1바이트 타입 식별자**: S=0x53, C=0x43, R=0x52

### 3.2 패킷 타입 요약

| 타입 | 방향 | 길이 | 전송 주기 | 설명 |
|------|------|------|----------|------|
| **S** | STM32 → RPi | **37 bytes** | 10Hz (100ms) | 센서 상태 17종 |
| **C** | RPi → STM32 | **4 bytes** (일반)<br>**34 bytes** (CLCD) | 이벤트 발생 시 | 액추에이터 명령 |
| **R** | STM32 → RPi | **2 bytes** (OK)<br>**14 bytes** (ERR) | C 수신 직후 | 명령 응답 |

### 3.3 패킷별 전송 부하량

| 패킷 | 크기 (바이트) | 비트 수 | 115200 전송 시간 | 9600 전송 시간 |
|------|-------------|---------|-----------------|---------------|
| S | 37 | **370** | **3.21 ms** | **38.5 ms** |
| C (일반) | 4 | 40 | 0.35 ms | 4.2 ms |
| C (CLCD) | 34 | 340 | 2.95 ms | 35.4 ms |
| R (OK) | 2 | 20 | 0.17 ms | 2.1 ms |
| R (ERR) | 14 | 140 | 1.22 ms | 14.6 ms |

---

## 4. S 패킷 — 센서 상태 (STM32 → RPi, 37바이트 고정)

### 4.1 바이트 맵

```
오프셋  크기  필드         타입     범위                스케일     예제 값
────── ──── ──────────── ─────── ─────────────────── ────────── ─────────
  0     1    type         uint8   0x53 ('S')          -          0x53
  1     2    CDS          uint16  0~999               raw        0x01C2 (450)
  3     2    HALL         uint16  0~999               raw        0x0140 (320)
  5     2    TEMP         uint16  0~9990              ×10       0x00FD (25.3)
  7     2    HUMI_T       uint16  0~999               raw        0x0190 (400)
  9     2    HUMI_H       uint16  0~999               raw        0x028A (650)
 11     1    ROT          uint8   0~100               raw        0x2D (45)
 12     2    US_DIST      uint16  0~999               raw        0x00B4 (180)
 14     2    JOY_X        uint16  0~999               raw        0x01F4 (500)
 16     2    JOY_Y        uint16  0~999               raw        0x01F4 (500)
 18     1    IR_RX        uint8   0~9                 raw        0x00 (0)
 19     4    GPS_LAT      int32  -900000~900000       ×10000    0x000EA3B0 (37.5600)
 23     4    GPS_LNG      int32  -1800000~1800000     ×10000    0x000F4240 (127.0000)
 27     2    FUEL         uint16  0~1000              raw        0x0398 (920)
 29     2    ACC_X        int16  -1000~1000           raw        0x0000 (0)
 31     2    ACC_Y        int16  -1000~1000           raw        0x0005 (5)
 33     2    ACC_Z        int16  -1000~1000           raw        0x03D4 (980)
 35     2    RPM          uint16  0~999               raw        0x0222 (546)
```

**총 37바이트 = 370비트**

### 4.2 인코딩 규칙

| 필드 | 규칙 |
|------|------|
| `TEMP` | 소수점 1자리 유지를 위해 값 × 10 후 uint16 저장<br>예: 25.3 → 253 → 0x00FD |
| `GPS_LAT/LNG` | 소수점 4자리 유지를 위해 × 10000 후 int32 저장<br>예: 37.5600 → 375600 → 0x0005BB70 |
| `ACC_X/Y/Z` | 부호 있는 int16, -1000~+1000 |
| `FUEL` | 0~1000, uint16 (999는 0x03E7) |
| 모든 다중바이트 | **Little Endian** (LSB first) |

### 4.3 S 패킷 전송 시간 계산

```
37 bytes × 10 bits = 370 bits

9600 baud:  370 / 9600 × 1,000,000 = 38,542 µs = 38.5 ms
19200 baud: 370 / 19200 × 1,000,000 = 19,271 µs = 19.3 ms
38400 baud: 370 / 38400 × 1,000,000 = 9,635 µs = 9.6 ms
57600 baud: 370 / 57600 × 1,000,000 = 6,424 µs = 6.4 ms
115200 baud: 370 / 115200 × 1,000,000 = 3,212 µs = 3.2 ms
921600 baud: 370 / 921600 × 1,000,000 = 401 µs = 0.4 ms
```

### 4.4 10Hz duty cycle (S 패킷만)

| 보드레이트 | S 패킷 시간 | 10Hz 주기(100ms) 대비 점유율 | 여유 대역폭 |
|-----------|------------|---------------------------|-----------|
| 2400 | 154.2 ms | **154.2% ✗ 불가능** | -54.2% |
| 4800 | 77.1 ms | 77.1% | 22.9% |
| **9600** | **38.5 ms** | **38.5%** | **61.5%** |
| 14400 | 25.7 ms | 25.7% | 74.3% |
| 19200 | 19.3 ms | 19.3% | 80.7% |
| 38400 | 9.6 ms | 9.6% | 90.4% |
| 57600 | 6.4 ms | 6.4% | 93.6% |
| **115200** | **3.2 ms** | **3.2%** | **96.8%** |

> **9600 baud 이상에서 10Hz 유지 가능!**
> ASCII 프로토콜은 9600에서 156ms(156.3%)로 불가능했던 것과 대비.

### 4.5 hex dump 예시

```
전문: 53 C2 01 40 01 FD 00 90 01 8A 02 2D B4 00 F4 01
      F4 01 00 B0 3B 0E 00 40 42 0F 00 98 03 00 00 05
      00 D4 03 22 02

해석:
0x53      → type = 'S'
0xC2 0x01 → CDS  = 0x01C2 = 450
0x40 0x01 → HALL = 0x0140 = 320
0xFD 0x00 → TEMP = 0x00FD = 253 → 25.3°C
... (이하 동일)
```

---

## 5. C 패킷 — 액추에이터 명령 (RPi → STM32)

### 5.1 액추에이터 ID 테이블

| ID (10진) | 키 이름 | 값 범위 | 바이트 수 | 비고 |
|-----------|---------|---------|----------|------|
| 1 | WHEEL1 | 0~999 | 2 | DC 모터 PWM |
| 2 | WHEEL2 | 0~999 | 2 | |
| 3 | WHEEL3 | 0~999 | 2 | |
| 4 | WHEEL4 | 0~999 | 2 | |
| 5 | SERVO1 | 0~999 | 2 | 0→0°, 500→90°, 999→180° |
| 6 | SERVO2 | 0~999 | 2 | |
| 7 | CLCD | 문자열 | **32** | UTF-8, 최대 32자 |
| 8 | LED_G | 0~999 | 2 | 2색 LED Green |
| 9 | LED_B | 0~999 | 2 | 2색 LED Blue |
| 10 | LED_RGB_R | 0~999 | 2 | |
| 11 | LED_RGB_G | 0~999 | 2 | |
| 12 | LED_RGB_B | 0~999 | 2 | |
| 13 | BUZZER | 0~1 | 2 | 0=OFF, 1=ON |
| 14 | LASER | 0~1 | 2 | |
| 15 | IR_TX | 1~9 | 2 | |

### 5.2 일반 C 패킷 구조 (액추에이터 ID 1~6, 8~15)

```
오프셋  크기  필드       타입     값
────── ──── ────────── ─────── ─────────────────
  0     1    type       uint8   0x43 ('C')
  1     1    actuator   uint8   ID (1~15)
  2     2    value      uint16  0~999 (Little Endian)
─────────────────────────────────────────────────
합계: 4 bytes = 40 bits
```

**전송 시간**:
```
115200: 40 / 115200 = 347 µs = 0.35 ms
9600:   40 / 9600   = 4,167 µs = 4.2 ms
```

### 5.3 CLCD C 패킷 구조 (액추에이터 ID 7)

```
오프셋  크기  필드       타입     값
────── ──── ────────── ─────── ─────────────────
  0     1    type       uint8   0x43 ('C')
  1     1    actuator   uint8   0x07 (CLCD)
  2    32    text       char[32] UTF-8, 미달 시 NULL 패딩
─────────────────────────────────────────────────
합계: 34 bytes = 340 bits
```

**전송 시간**:
```
115200: 340 / 115200 = 2,951 µs = 2.95 ms
9600:   340 / 9600   = 35,417 µs = 35.4 ms
```

### 5.4 hex dump 예시

```
WHEEL1=500:  43 01 F4 01
             │  │  └──┘ value = 0x01F4 = 500
             │  └──── actuator ID = 1 (WHEEL1)
             └─────── type = 'C'

SERVO1=999:  43 05 E7 03
                      └── value = 0x03E7 = 999

CLCD=Hello:  43 07 48 65 6C 6C 6F 00 ... (34 bytes)
                    └── 'H' 'e' 'l' 'l' 'o' '\0' ...
```

---

## 6. R 패킷 — 명령 응답 (STM32 → RPi)

### 6.1 구조

#### 성공 (2 bytes)

```
오프셋  크기  필드       타입     값
────── ──── ────────── ─────── ───────
  0     1    type       uint8   0x52 ('R')
  1     1    status     uint8   0x00 (OK)
─────────────────────────────────────────
합계: 2 bytes = 20 bits
```

**전송 시간**: 115200: 0.17 ms / 9600: 2.1 ms

#### 실패 (14 bytes)

```
오프셋  크기  필드       타입       값
────── ──── ────────── ───────── ─────────────────
  0     1    type       uint8     0x52 ('R')
  1     1    status     uint8     0x01 (ERR)
  2    12    err_msg    char[12]  UTF-8 에러 메시지
───────────────────────────────────────────────────
합계: 14 bytes = 140 bits
```

### 6.2 에러 코드 테이블

| 코드 (status=0x01) | err_msg | 발생 조건 |
|--------------------|---------|-----------|
| ERR_VAL_RANGE | `out of range` | 값이 0~999 범위 초과 |
| ERR_UNKNOWN_KEY | `unknown key` | 액추에이터 ID 1~15 이외 |
| ERR_BAD_VALUE | `bad value` | BUZZER/LASER가 0/1이 아님 |
| ERR_INT_REQUIRED | `int required` | 숫자 값에 문자열 입력 |

### 6.3 hex dump 예시

```
성공:  52 00
       │  └── status = OK
       └──── type = 'R'

실패(out of range):  52 01 6F 75 74 20 6F 66 20 72 61 6E 67 65
                     │  │  └── "out of range" (12 bytes)
                     │  └── status = ERR
                     └──── type = 'R'
```

---

## 7. 프로토콜 비교 분석

### 7.1 패킷 크기 비교

| 패킷 | ASCII | Binary | 절감율 |
|------|-------|--------|--------|
| S (17 sensors) | ~150 B | **37 B** | **75.3%** |
| C (WHEEL1=500) | 13 B | **4 B** | **69.2%** |
| R (OK) | 5 B | **2 B** | **60.0%** |
| R (ERR) | ~15 B | **14 B** | 6.7% |

### 7.2 초당 전송량 비교 (115200 baud, 10Hz S + α)

| 항목 | ASCII | Binary |
|------|-------|--------|
| S 패킷 10회/초 | 1,500 bytes = 15,000 bits | **370 bytes = 3,700 bits** |
| C 패킷 10회/초 | 150 bytes = 1,500 bits | **40 bytes = 400 bits** |
| 총 초당 전송량 | **1,650 bytes = 16,500 bits** | **410 bytes = 4,100 bits** |
| 대역폭 점유율 | **14.3%** | **3.6%** |
| 시간당 전송량 | **5.76 MB** | **1.44 MB** |

### 7.3 최대 S 패킷 주파수 (이론적 한계)

| 보드레이트 | ASCII 최대 Hz | Binary 최대 Hz |
|-----------|--------------|---------------|
| 2400 | 6.4 Hz | **25.9 Hz** |
| 4800 | 12.8 Hz | **51.9 Hz** |
| **9600** | **25.6 Hz** | **103.7 Hz** |
| 19200 | 51.2 Hz | 207.5 Hz |
| 38400 | 102.5 Hz | 415.0 Hz |
| 57600 | 153.8 Hz | 622.5 Hz |
| **115200** | **307.7 Hz** | **1,245.0 Hz** |

> Binary 프로토콜은 ASCII보다 **4배 높은 주파수**까지 전송 가능.

### 7.4 전송 시간 시각화 (10Hz = 100ms 주기)

```
ASCII @ 9600 baud:
├─────── S(156ms) ────────┤         ← 100ms 초과! 패킷 손실 발생
└─────────────────────────┴──────────────────────────

Binary @ 9600 baud:
├───── S(38.5ms) ────┤ ←────── 61.5ms 여유 ──────→
└────────────────────┴──────────────────────────────

ASCII @ 115200 baud:
├─── S(13ms) ──┤ ←──────── 87ms 여유 ────────────→
└──────────────┴────────────────────────────────────

Binary @ 115200 baud:
├ S(3.2ms) ┤ ←──────────── 96.8ms 여유 ──────────→
└──────────┴────────────────────────────────────────
```

---

## 8. ASCII ↔ Binary 혼용 운용

### 8.1 프로토콜 선택

`--efficient` 플래그로 모드 전환:

```
python simulator_stm32.py --efficient --serial-port COM3
python rpi_controller.py --efficient --serial-port COM4
```

### 8.2 auto-detect (향후)

첫 패킷의 타입 바이트로 자동 감지 가능:
- `0x53` ('S'): ASCII 또는 Binary (추가 바이트로 판별)
- `0x01` (SOH): Binary S 패킷

---

## 9. 권장 설정

| 상황 | 보드레이트 | 프로토콜 | 근거 |
|------|-----------|---------|------|
| **개발/디버깅** | **115200** | **ASCII** | 사람이 읽기 쉬움, 충분한 대역폭 |
| **실전 배포 (저속)** | **9600** | **Binary** | 38.5ms/S, 10Hz 유지 가능 |
| **실전 배포 (고속)** | **115200** | **Binary** | 3.2ms/S, 96.8% 대역폭 여유 |
| **고주파수 수집** | **921600** | **Binary** | S 패킷 0.4ms, 초당 2,700회 전송 가능 |

---

## 10. 전송 시간 계산 예제

### 문제 1
> 115200 baud에서 S 패킷 1회 전송 시간은?

```
1 bit = 1 / 115200 = 8.68 µs
1 byte = 8.68 × 10 = 86.8 µs
S packet = 37 bytes × 86.8 µs = 3,212 µs = 3.2 ms
```

### 문제 2
> 9600 baud, 10Hz(100ms 주기)에서 S 패킷 전송 후 남은 여유 시간은?

```
S packet @ 9600: 37 × 10 / 9600 × 1,000,000 = 38,542 µs = 38.5 ms
여유: 100 - 38.5 = 61.5 ms

→ 61.5ms 동안 C 명령 최대 14회 추가 전송 가능
  (61.5ms / 4.2ms per C = 14.6)
```

### 문제 3
> ASCII S 패킷(150바이트)이 9600 baud에서 10Hz로 동작하지 못하는 이유는?

```
150 bytes × 10 = 1,500 bits
1,500 / 9600 = 156.3 ms
156.3 ms > 100 ms (10Hz 주기)

→ 한 패킷 전송 시간이 다음 패킷 전송 시간을 초과.
→ 송신 버퍼 오버플로우, 데이터 손실 발생.
```

### 문제 4
> Binary S 패킷(37바이트)을 9600 baud의 10Hz 주기 내에 3회 전송할 수 있는가?

```
37 bytes × 10 = 370 bits
370 / 9600 = 38.5 ms
3회: 38.5 × 3 = 115.5 ms

→ 115.5 ms > 100 ms. 3회 전송 불가능.
→ 최대 2회까지 가능 (38.5 × 2 = 77 ms < 100 ms)
```

---

## 부록 A: Python 구현 레퍼런스

### A.1 BinaryProtocol 클래스

```python
import struct

class BinaryProtocol:
    S_SIZE = 37
    ACT_IDS = {
        'WHEEL1': 1, 'WHEEL2': 2, 'WHEEL3': 3, 'WHEEL4': 4,
        'SERVO1': 5, 'SERVO2': 6, 'CLCD': 7,
        'LED_G': 8, 'LED_B': 9,
        'LED_RGB_R': 10, 'LED_RGB_G': 11, 'LED_RGB_B': 12,
        'BUZZER': 13, 'LASER': 14, 'IR_TX': 15,
    }

    @staticmethod
    def encode_s(cds, hall, temp, humi_t, humi_h, rot, us_dist,
                 joy_x, joy_y, ir_rx, gps_lat, gps_lng,
                 fuel, acc_x, acc_y, acc_z, rpm):
        data = bytearray(37)
        data[0] = ord('S')
        struct.pack_into('<H', data, 1, cds)
        struct.pack_into('<H', data, 3, hall)
        struct.pack_into('<H', data, 5, int(temp * 10))
        struct.pack_into('<H', data, 7, humi_t)
        struct.pack_into('<H', data, 9, humi_h)
        data[11] = rot
        struct.pack_into('<H', data, 12, us_dist)
        struct.pack_into('<H', data, 14, joy_x)
        struct.pack_into('<H', data, 16, joy_y)
        data[18] = ir_rx
        struct.pack_into('<i', data, 19, int(gps_lat * 10000))
        struct.pack_into('<i', data, 23, int(gps_lng * 10000))
        struct.pack_into('<H', data, 27, fuel)
        struct.pack_into('<h', data, 29, acc_x)
        struct.pack_into('<h', data, 31, acc_y)
        struct.pack_into('<h', data, 33, acc_z)
        struct.pack_into('<H', data, 35, rpm)
        return bytes(data)

    @staticmethod
    def decode_s(data):
        if len(data) < 37 or data[0] != ord('S'):
            return None
        return {
            'CDS':     struct.unpack_from('<H', data, 1)[0],
            'HALL':    struct.unpack_from('<H', data, 3)[0],
            'TEMP':    struct.unpack_from('<H', data, 5)[0] / 10,
            'HUMI_T':  struct.unpack_from('<H', data, 7)[0],
            'HUMI_H':  struct.unpack_from('<H', data, 9)[0],
            'ROT':     data[11],
            'US_DIST': struct.unpack_from('<H', data, 12)[0],
            'JOY_X':   struct.unpack_from('<H', data, 14)[0],
            'JOY_Y':   struct.unpack_from('<H', data, 16)[0],
            'IR_RX':   data[18],
            'GPS_LAT': struct.unpack_from('<i', data, 19)[0] / 10000,
            'GPS_LNG': struct.unpack_from('<i', data, 23)[0] / 10000,
            'FUEL':    struct.unpack_from('<H', data, 27)[0],
            'ACC_X':   struct.unpack_from('<h', data, 29)[0],
            'ACC_Y':   struct.unpack_from('<h', data, 31)[0],
            'ACC_Z':   struct.unpack_from('<h', data, 33)[0],
            'RPM':     struct.unpack_from('<H', data, 35)[0],
        }
```

### A.2 전송 시간 계산 함수

```python
def calc_time(baud, bytes_count):
    bits = bytes_count * 10
    seconds = bits / baud
    return {
        'bits': bits,
        'seconds': seconds,
        'ms': seconds * 1000,
        'us': seconds * 1_000_000,
    }

# 사용 예
t = calc_time(115200, 37)
print(f"S packet @ 115200: {t['ms']:.2f} ms ({t['us']:.0f} µs)")
# 출력: S packet @ 115200: 3.21 ms (3212 µs)
```

### A.3 부하율 계산 함수

```python
def duty_cycle(baud, bytes_count, interval_ms=100):
    t = calc_time(baud, bytes_count)
    return (t['ms'] / interval_ms) * 100

print(f"S @ 9600, 10Hz: {duty_cycle(9600, 37):.1f}%")
# 출력: S @ 9600, 10Hz: 38.5%
```

---

## 부록 B: ASCII ↔ Binary 크기 비교표

| 필드 | ASCII 예 | ASCII bytes | Binary bytes |
|------|---------|------------|-------------|
| type | `S` | 1 | 1 |
| CDS | `CDS=450` | 7 | 2 |
| HALL | `HALL=320` | 8 | 2 |
| TEMP | `TEMP=25.3` | 9 | 2 |
| HUMI_T | `HUMI_T=400` | 10 | 2 |
| HUMI_H | `HUMI_H=650` | 10 | 2 |
| ROT | `ROT=45` | 6 | 1 |
| US_DIST | `US_DIST=180` | 11 | 2 |
| JOY_X | `JOY_X=500` | 9 | 2 |
| JOY_Y | `JOY_Y=500` | 9 | 2 |
| IR_RX | `IR_RX=0` | 7 | 1 |
| GPS_LAT | `GPS_LAT=37.5600` | 16 | 4 |
| GPS_LNG | `GPS_LNG=127.0000` | 17 | 4 |
| FUEL | `FUEL=920` | 8 | 2 |
| ACC_X | `ACC_X=0` | 7 | 2 |
| ACC_Y | `ACC_Y=5` | 7 | 2 |
| ACC_Z | `ACC_Z=980` | 9 | 2 |
| RPM | `RPM=550` | 7 | 2 |
| 구분자(`,`) | 16개 | 16 | 0 |
| 구분자(`=`) | 17개 | 17 | 0 |
| **합계** | | **~150** | **37** |

---

## 부록 C: 용어 정리

| 용어 | 설명 |
|------|------|
| **baud rate** | 초당 심볼(비트) 전송 속도. 115200 = 115,200비트/초 |
| **8N1** | 8 data bits, No parity, 1 stop bit = 10 bits per byte |
| **STX** | Start of TeXt (0x02). 본 문서에서는 'S'(0x53) 사용 |
| **Little Endian** | 하위 바이트를 먼저 저장. Intel/ARM 기본 방식 |
| **duty cycle** | 주기 내 전송 시간 비율. 10Hz(100ms)에서 3.2ms = 3.2% |
| **struct.pack** | Python 구조체 → 바이너리 직렬화 함수 |
| **throughput** | 초당 유효 데이터 전송량 (오버헤드 제외) |
