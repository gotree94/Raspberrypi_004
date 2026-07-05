# 3-3 부저 출력하기

* 부저를 이용하여 소리를 출력하는 방법을 학습합니다.
* GPIO 출력 신호를 활용하여 단순한 알림음부터 주파수를 조절한 멜로디 출력까지 실습합니다.
* 이를 통해 PWM(펄스폭 변조)의 개념을 익히고, 다양한 하드웨어 제어에 적용할 수 있는 능력을 기릅니다.

# 1. 부저 출력 하기

* 3_3_1.py

```python
from gpiozero import PWMOutputDevice
import time

buzzer = PWMOutputDevice(12)

notes = [262, 294, 330, 349, 392, 440, 494, 523]

try:
    while True:
        for f in notes:
            buzzer.frequency = f
            buzzer.value = 0.5
            time.sleep(0.3)
            buzzer.value = 0
            time.sleep(0.1)

except KeyboardInterrupt:
    print("code end")
```

# 2. 긴급음 출력하기

* 3_3_2.py

```python
from gpiozero import PWMOutputDevice
import time

buzzer = PWMOutputDevice(12)

try:
    while True:
        for f in range(600, 1500, 20):
            buzzer.frequency = f
            buzzer.value = 0.5
            time.sleep(0.005)
        for f in range(1500, 600, -20):
            buzzer.frequency = f
            buzzer.value = 0.5
            time.sleep(0.005)

except KeyboardInterrupt:
    print("code end")
```

# 3. 버튼을 눌러 다양한 소리 출력하기

* 3_3_3.py

```python
from gpiozero import Button, PWMOutputDevice
import time

SW1 = Button(5, pull_up=False, bounce_time=0.05)
SW2 = Button(6, pull_up=False, bounce_time=0.05)
SW3 = Button(13, pull_up=False, bounce_time=0.05)
SW4 = Button(19, pull_up=False, bounce_time=0.05)

buzzer = PWMOutputDevice(12, frequency=1000, initial_value=0.0)

def tone(freq, duration=0.2, duty=0.5):
    buzzer.frequency = freq
    buzzer.value = duty
    time.sleep(duration)
    buzzer.value = 0.0

def beep(times=3, on=0.1, off=0.1, freq=2000):
    for _ in range(times):
        tone(freq, on)
        time.sleep(off)

def siren(f1=600, f2=1400, step=26, hold=0.01, cycles=2):
    for _ in range(cycles):
        for f in range(f1, f2, step):
            buzzer.frequency = f
            buzzer.value = 0.5
            time.sleep(hold)
        for f in range(f2, f1, -step):
            buzzer.frequency = f
            buzzer.value = 0.5
            time.sleep(hold)
    buzzer.value = 0.0

def stutter(times=8, on=0.06, off=0.06, freq=1500):
    beep(times, on, off, freq)

def sw1_handler():
    beep(times=3, on=0.12, off=0.12, freq=2200)

def sw2_handler():
    tone(800, duration=0.6, duty=0.6)

def sw3_handler():
    siren()

def sw4_handler():
    stutter()

SW1.when_pressed = sw1_handler
SW2.when_pressed = sw2_handler
SW3.when_pressed = sw3_handler
SW4.when_pressed = sw4_handler

try:
    while True:
        time.sleep(0.1)

except KeyboardInterrupt:
    buzzer.value = 0.0
```


