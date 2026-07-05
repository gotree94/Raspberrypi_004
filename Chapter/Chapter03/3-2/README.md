# 3-2 버튼 입력 받기

* 물리적인 버튼을 이용하여 사용자 입력을 처리하는 방법을 다룹니다.
* 입력 핀을 설정하고, 버튼 상태를 감지하여 프로그램이 반응하도록 구성합니다.
* 하드웨어 입력과 소프트웨어 제어가 상호작용하는 과정을 이해함으로써, 이벤트 기반 제어의 기초를 학습합니다.


## 버튼 상태 확인하기

* 3_2_1.py
    * 버튼 상태를 출력하는 코드를 작성

```python
from gpiozero import Button
import time

SW1 = Button(5, pull_up=False, bounce_time=0.05)
SW2 = Button(6, pull_up=False, bounce_time=0.05)
SW3 = Button(13, pull_up=False, bounce_time=0.05)
SW4 = Button(19, pull_up=False, bounce_time=0.05)

try :
    while True:
      sw1_value = SW1.is_pressed
      sw2_value = SW2.is_pressed
      sw3_value = SW3.is_pressed
      sw4_value = SW4.is_pressed
      print("1:",sw1_value,"2:",sw2_value,"3:",sw3_value,"3:",sw4_value)
      time.sleep(0.5)

except KeyboardInterrupt:
  print("code end")
```

* 3_2_1.py
    * 조건문을 이용하여 버튼을 누르고 있을 때만 값이 출력하도록 코드를 작성.

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
