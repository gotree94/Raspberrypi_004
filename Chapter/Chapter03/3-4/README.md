# 3-4 DC 모터 구동하기

* 자동차의 구동을 담당하는 DC 모터를 제어하는 방법을 다룹니다.
* 모터 드라이버를 통해 방향 제어와 속도 조절을 수행하며, PWM 신로를 뢀용한 모터 구동 원리를 학습합니다.
* 이 실습은 자동차의 실제 주행 기능을 구현하기 위한 핵심 단계로, 이후 자율주행 제어의 기초가 됩니다.

### 1. 모터 속도 제어하기

* 모터의 속도를 제어하는 PWM핀의 PWM값을 변경하여 모터 속도를 변경하는 코드를 작성

* 3_4_1.py

```python
from gpiozero import DigitlaOutputDevice
from gpiozero import PWMOutputDevice
import time

PWMA = PWMOutputDevice(18)
AIN1 = DigitlaOutputDevice(22)
AIN2 = DigitlaOutputDevice(27)

PWMB = PWMOutputDevice(23)
BIN1 = DigitlaOutputDevice(25)
BIN2 = DigitlaOutputDevice(24)


try :
    while True:
      AIN1.value = 0
      AIN2.value = 0
      PWMA.value = 0.3
      BIN1.value = 0
      BIN2.value = 0
      PWMB.value = 0.3
      print("0.3")
      time.sleep(2.0)

      AIN1.value = 0
      AIN2.value = 1
      PWMA.value = 0.5
      BIN1.value = 0
      BIN2.value = 1
      PWMB.value = 0.5
      print("0.3")
      time.sleep(2.0)

      AIN1.value = 0
      AIN2.value = 0
      PWMA.value = 1.0
      BIN1.value = 0
      BIN2.value = 0
      PWMB.value = 1.0
      print("1.0")
      time.sleep(2.0)

      AIN1.value = 0
      AIN2.value = 1
      PWMA.value = 0.0
      BIN1.value = 0
      BIN2.value = 1
      PWMB.value = 0.0
      print("0.0")
      time.sleep(10.0)

except KeyboardInterrupt:
  print("code end")
```

### 2. 모터의 방향 제어하기

* 모터의 방향을 제어하는 디지털핀의 출력을 변경하여 자동차를 전진, 후진하는 코드를 작성.

* 3_4_2.py

```python
from gpiozero import Button
import time

SW1 = Button(5, pull_up=False, bounce_time=0.05)
SW2 = Button(6, pull_up=False, bounce_time=0.05)
SW3 = Button(13, pull_up=False, bounce_time=0.05)
SW4 = Button(19, pull_up=False, bounce_time=0.05)

try :
    while True:
      if SW1.is_pressed == True:
            print("sw1")

      if SW2.is_pressed == True:
            print("sw2")

      if SW3.is_pressed == True:
            print("sw3")

      if SW4.is_pressed == True:
            print("sw4")

      time.sleep(0.5)

except KeyboardInterrupt:
  print("code end")
```

### 3. 함수 만들어 모터 제어하기

* 함수를 만들어 코드를 직관적으로 변경하여 동작해보도록 코드를 작성합니다.

* 3_4_3.py

```python
from gpiozero import Button
import time

SW1 = Button(5, pull_up=False, bounce_time=0.05)
SW2 = Button(6, pull_up=False, bounce_time=0.05)
SW3 = Button(13, pull_up=False, bounce_time=0.05)
SW4 = Button(19, pull_up=False, bounce_time=0.05)

def sw1_pressed():
    print("Button 1 predded")

def sw2_pressed():
    print("Button 2 predded")

def sw3_pressed():
    print("Button 3 predded")

def sw4_pressed():
    print("Button 4 predded")

SW1.when_pressed = sw1_pressed
SW2.when_pressed = sw2_pressed
SW3.when_pressed = sw3_pressed
SW4.when_pressed = sw4_pressed

      time.sleep(0.5)

except KeyboardInterrupt:
  print("code end")
```



### 4. InputDevice 사용해서 GPIO 상태 확인하기 

* InputDevice 라이브러리를 사용하여  GPIO 상태를 확인하는 코드를 작성.

* 3_4_3.py

```python
from gpiozero import Button
import time

SW1 = InputDevice(5, pull_up=False)
SW2 = InputDevice(6, pull_up=False)
SW3 = InputDevice(13, pull_up=False)
SW4 = InputDevice(19, pull_up=False)

try :
    while True:
      if SW1.is_active == True:
            print("sw1")

      if SW2.is_active == True:
            print("sw2")

      if SW3.is_active == True:
            print("sw3")

      if SW4.is_active == True:
            print("sw4")

      time.sleep(0.5)

except KeyboardInterrupt:
  print("code end")
```


