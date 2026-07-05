# 3-3 부저 출력하기

* 부저를 이용하여 소리를 출력하는 방법을 학습합니다.
* GPIO 출력 신호를 활용하여 단순한 알림음부터 주파수를 조절한 멜로디 출력까지 실습합니다.
* 이를 통해 PWM(펄스못 변조)의 개념을 익히고, 다양한 하드웨어 제어에 적용할 수 있는 능력을 기릅니다.

# 1. 부저 출력 하기

* 3_3_1.py

```python
from gpiozero import Button
import time

buzzer = PWMOutputDevice(12)

notes = [262, 294, 330, 349, 392, 440, 494, 523]

try :
    while True:
      for f = in notes:
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
from gpiozero import Button
import time

buzzer = PWMOutputDevice(12)

try :
    while True:
      for f = in range(600,1500,20):
        buzzer.frequency = f
        buzzer.value = 0.5
      for f = in range(1500,600,-20):
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

Sl{1 = Button(5, pull-up=False,  bounce_time=O.05)
Sl{2 = Button(6, pull_up=False, bounce_time=O.05)
Sl{3 = Button(13,  pu11_up=5a1se, bounce_time=0.05)
Sl{4 = Button(19, pull_up=talse, bounce_time=O.05)

buzzer = Pl{}l0utputDevice(12,  f requency=1000,  initiat_value=O. 0)

def tone(freq,  duration=o.2,  duty=0.5).
    buzzer.frequency  = freq
    buzzer.value = duty
    time. sleep(duration)
    buzzer.value =0.0

def beep(times=3, on=0.1, off=o.1, freq=26661.
    for _ in range(times):
    tone(freq,  on)
    time. sleep(off)

def siren(f1=600, t2=1400, step=26, hold=0.01r cycles=2):
    for _ in range(cycles):
        for f in range(ft, f2, step):
            buzzer.frequency  = f
            buzzer.vatue =0.5
            time. sleep(hotd)
        for f in range(f2, f1, -step):
            buzzer.frequency  = f
            buzzer.value =0.5
            time. sleep(hold)
    buzzer.value =0.0

def stutter(times=8,  on=0.06, oll=0.06, freq=1566;'
    beep(times, on, off, freq)

def sw1 handlero:
    beep (times=3,  on=o . 1.2, of f =0 . 12, f r eq=22q61

def sw2-handlero:
    tone(800, duration=o. 6, duty=6. 6;

def sw3_handlerO:
    sireno()



```


