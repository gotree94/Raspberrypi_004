# 라즈베리파이 IR 리모컨 수신 설정 가이드

**GPIO 18** 사용, LIRC 기반, NEC 프로토콜

---

## 1단계: 하드웨어 연결

```
IR 센서 (TSOP38238 등)       라즈베리파이
┌─────────────┐
│ VCC (3.3V)  ─────  Pin 1 (3.3V)
│ GND         ─────  Pin 6 (GND)
│ OUT         ─────  Pin 12 (GPIO 18)
└─────────────┘
```

---

## 2단계: LIRC 설치 및 설정

```bash
sudo apt update
sudo apt install lirc -y
```

---

## 3단계: /boot/config.txt 수정

```bash
sudo nano /boot/config.txt
```

파일 끝에 다음을 추가하거나 수정:

```
# IR 수신기: GPIO 18
dtoverlay=gpio-ir,gpio_pin=18
```

기존에 `dtoverlay=lirc-rpi` 같은 줄이 있으면 **반드시 삭제** (구버전, 충돌 남).

---

## 4단계: 재부팅 및 확인

```bash
sudo reboot
```

재부팅 후 장치 확인:

```bash
ls -l /dev/lirc*
# /dev/lirc0 가 보여야 함

mode2 -d /dev/lirc0
```

리모컨 버튼을 누르면 pulse/space 신호가 출력되어야 함.

```
pulse 9000
space 4500
pulse 560
...
```

---

## 5단계: LIRC 데몬 중지 (Python에서 직접 접근)

LIRC 데몬이 /dev/lirc0를 점유하고 있으면 Python에서 사용 불가.

```bash
sudo systemctl stop lircd
sudo systemctl disable lircd
```

---

## 6단계: Python 프로그램 작성

```python
import RPi.GPIO as GPIO
import time

PIN = 18

GPIO.setmode(GPIO.BCM)
GPIO.setup(PIN, GPIO.IN)

# NEC 프로토콜 파라미터
TOLERANCE = 0.3
LEADER_PULSE = 9000
LEADER_SPACE = 4500
BIT_ZERO = 1125
BIT_ONE = 2250

SCANCODES = {
    # scancode -> name
    0x0007: "KPMINUS",
    0x0009: "STOP",
    0x0015: "KPPLUS",
    0x0040: "FASTFORWARD",
    0x0043: "OK",
    0x0044: "REWIND",
}

EVENT_MAP = {
    0x0007: 0x4a,   # KEY_KPMINUS
    0x0009: 0x80,   # KEY_STOP
    0x0015: 0x4e,   # KEY_KPPLUS
    0x0040: 0xd0,   # KEY_FASTFORWARD
    0x0043: 0x160,  # KEY_OK
    0x0044: 0xa8,   # KEY_REWIND
}

last_time = time.time()

def wait_for_change(pin, target, timeout=0.1):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if GPIO.input(pin) == target:
            return time.time()
    return None

def read_pulse_space():
    t = wait_for_change(PIN, 0)
    if t is None:
        return None, None
    pulse_start = t

    t = wait_for_change(PIN, 1)
    if t is None:
        return None, None
    pulse = (t - pulse_start) * 1_000_000

    t = wait_for_change(PIN, 0)
    if t is None:
        return None, None
    space = (t - pulse_start) * 1_000_000

    return pulse, space

def within(value, target):
    return abs(value - target) / target < TOLERANCE

def decode_nec():
    for _ in range(50):
        p, s = read_pulse_space()
        if p is None:
            return None
        if within(p, LEADER_PULSE) and within(s, LEADER_SPACE):
            break
    else:
        return None

    code = 0
    for i in range(32):
        p, s = read_pulse_space()
        if p is None:
            return None
        if within(s, BIT_ONE):
            code |= (1 << i)

    return code

def main():
    global last_time
    print("IR Remote Receiver - GPIO 18")
    print("Waiting for signals...")
    try:
        while True:
            code = decode_nec()
            if code is not None:
                scancode = code & 0xFFFF
                name = SCANCODES.get(scancode, "UNKNOWN")
                ev = EVENT_MAP.get(scancode, hex(scancode))
                print(f"Scancode: 0x{scancode:04X} ({name}) → Event: 0x{ev:04X}")
            time.sleep(0.01)
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        GPIO.cleanup()

if __name__ == "__main__":
    main()
```

---

## 7단계: 실행

```bash
python3 ir_receiver.py
```

리모컨 버튼을 누르면 다음과 같이 출력됨:

```
IR Remote Receiver - GPIO 18
Waiting for signals...
Scancode: 0x0043 (OK) → Event: 0x0160
Scancode: 0x0007 (KPMINUS) → Event: 0x004A
```

---

## 전체 명령어 요약

```bash
# 1. 설치
sudo apt update
sudo apt install lirc -y

# 2. config 수정
sudo nano /boot/config.txt
# → dtoverlay=gpio-ir,gpio_pin=18

# 3. 재부팅
sudo reboot

# 4. 신호 확인
mode2 -d /dev/lirc0

# 5. LIRC 데몬 중지
sudo systemctl stop lircd
sudo systemctl disable lircd

# 6. 실행
python3 ir_receiver.py
```
