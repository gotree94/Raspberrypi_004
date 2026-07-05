# 3-5 시리얼 블루투스 통신으로 자동차 제어하기

블루투스 모듈을 이용하여 스마트폰 등 외부 기기와 자동차간 통신을 구현합니다.
시리얼 통신을 설정하고, 명령을 수신하여 자동차의 LED나 모터를 제어하는 과정을 실습합니다.
이를 통해 무선 제어의 개념을 이해하고, 향후 자율주행 시스템의 원격 제어 기능으로 확장할 수 있는 기반을 마련합니다.

## 1. Control Center - Serial 설정

라즈베리파이에서 시리얼 통신을 사용하기 위해서 설정을 진행합니다.

Raspberry Pi Configuration(환경설정)을 실행합니다.


* [interface] 탭에서 
   * [Serial Port] 사용함
   * [Serial Console] 사용 안함으로 설정 후
   * [OK] 를 눌러 설정을 저장 합니다.
   * 재부팅 후 진행 합니다.
 
## 2. 블루투스 시리얼통신으로 스마트폰과 데이터 주고 받기
  * 매초 숫자값을 증가시켜 그 값을 블루투스 시리얼 통신으로 전송하고 데이터를 수신받아 그 값을 출력 하는 코드를 작성해 봅니다.

* 3_5_1.py

```python
import serial
import time

bleSerial = serial.Serial("/dev/ttyAMA0", baudrate=115200, timeout=0.1)

send_interval = 1.0
last_send_time = time.time()
counter = 0

try:
    while True:
        now = time.time()

        if now - last_send_time >= send_interval:
            counter += 1
            send_data = f"{counter}\n"
            bleSerial.write(send_data.encode())
            last_send_time = now

        if bleSerial.in_waiting > 0:
            data = bleSerial.readline().decode().strip()
            if data:
                print("Received:", data)

except KeyboardInterrupt:
    pass
finally:
    bleSerial.close()
```

* 스마트폰의 "시리얼통신"을 검색 후 "Serial Bluetooth Terminal 앱을 설치한 다음 실행 합니다."



## 3. 데이터 수신 받아 LED 제어 조건 설정하기
  * 데이터를 수신받는 조건을 설정하여 자율주행 자동차의 LED 제어를 위한 조건을 설정해 보도록 합니다.

* 3_5_2.py

```python
import serial
import time

bleSerial = serial.Serial("/dev/ttyAMA0", baudrate=115200, timeout=0.1)

try:
    while True:
        if bleSerial.in_waiting > 0:
            data = bleSerial.readline().decode().strip()
            if "LEDON" in data:
                print("ok led on")
            elif "LEDOFF" in data:
                print("ok led off")
        time.sleep(0.01)

except KeyboardInterrupt:
    pass
finally:
    bleSerial.close()
```


## 4. 데이터 수신받아 LED 제어 완성하기
  * 실제 자율주행 자동차의 LED를 켜고 끄는 코드를 넣어 LED를 제어해보도록 합니다.

* 3_5_3.py

```python
import serial
import time
from gpiozero import LEDBoard

bleSerial = serial.Serial("/dev/ttyAMA0", baudrate=115200, timeout=0.1)
leds = LEDBoard(26, 16, 20, 21)

try:
    while True:
        if bleSerial.in_waiting > 0:
            data = bleSerial.readline().decode().strip().upper()
            if "LEDON" in data:
                leds.on()
                print("ok led on")
            elif "LEDOFF" in data:
                leds.off()
                print("ok led off")
        time.sleep(0.01)

except KeyboardInterrupt:
    pass
finally:
    bleSerial.close()
```


## 5. 데이터 수신받아 자동차 조종조건 설정하기
  * 자동차 조종을 위해 left, right, go, back, stop 명령어를 받아 조건을 확인하는 코드를 작성해 봅니다.
  * 대소문자 상관없이 코드에서 모두 대문자로 변경하여 조건에 만족하도록 합니다.   

* 3_5_4.py

```python
import serial
import time
from gpiozero import LEDBoard

bleSerial = serial.Serial("/dev/ttyAMA0", baudrate=115200, timeout=0.1)
leds = LEDBoard(26, 16, 20, 21)

try:
    while True:
        if bleSerial.in_waiting > 0:
            data = bleSerial.readline().decode().strip().upper()
            if "LEFT" in data:
                print("ok left")
            elif "RIGHT" in data:
                print("ok right")
            elif "GO" in data:
                print("ok go")
            elif "BACK" in data:
                print("ok back")
            elif "STOP" in data:
                print("ok stop")
        time.sleep(0.01)

except KeyboardInterrupt:
    pass
finally:
    bleSerial.close()
```


## 6. 데이터 수신받아 자동차 조종 완성하기
  * 이제 실제 자동차를 움직이는 부분을 넣어 코드를 완성하여 자동차를 앱으로 조종하는 코드를 만들어 완성합니다.

* 3_5_5.py

```python
import serial
import time
import myservo
from gpiozero import DigitalOutputDevice, PWMOutputDevice

bleSerial = serial.Serial("/dev/ttyAMA0", baudrate=115200, timeout=0.1)

PWMA = PWMOutputDevice(18)
AIN1 = DigitalOutputDevice(22)
AIN2 = DigitalOutputDevice(27)

PWMB = PWMOutputDevice(23)
BIN1 = DigitalOutputDevice(25)
BIN2 = DigitalOutputDevice(24)

def motor_go(speed):
    AIN1.value = 0
    AIN2.value = 1
    PWMA.value = speed
    BIN1.value = 0
    BIN2.value = 1
    PWMB.value = speed

def motor_back(speed):
    AIN1.value = 1
    AIN2.value = 0
    PWMA.value = speed
    BIN1.value = 1
    BIN2.value = 0
    PWMB.value = speed

def motor_stop():
    AIN1.value = 0
    AIN2.value = 1
    PWMA.value = 0.0
    BIN1.value = 0
    BIN2.value = 1
    PWMB.value = 0.0

pca9685 = myservo.PCA9685()
servo_channel = 0
LEFT_ANGLE = 45
RIGHT_ANGLE = 135
CENTER_ANGLE = 90
speedSet = 0.5

try:
    pca9685.set_servo_angle(servo_channel, CENTER_ANGLE)
    while True:
        if bleSerial.in_waiting > 0:
            data = bleSerial.readline().decode().strip().upper()
            if "LEFT" in data:
                pca9685.set_servo_angle(servo_channel, LEFT_ANGLE)
                print("ok left")
            elif "RIGHT" in data:
                pca9685.set_servo_angle(servo_channel, RIGHT_ANGLE)
                print("ok right")
            elif "GO" in data:
                pca9685.set_servo_angle(servo_channel, CENTER_ANGLE)
                motor_go(speedSet)
                print("ok go")
            elif "BACK" in data:
                pca9685.set_servo_angle(servo_channel, CENTER_ANGLE)
                motor_back(speedSet)
                print("ok back")
            elif "STOP" in data:
                motor_stop()
                print("ok stop")
        time.sleep(0.01)

except KeyboardInterrupt:
    pass
finally:
    motor_stop()
    pca9685.set_servo_angle(servo_channel, CENTER_ANGLE)
    bleSerial.close()
```






























