# 3-5 시리얼 블루투스 통신으로 자동차 제어하기

블루투스 모듈을 이용하여 스마트폰 등 외부 기기와 자동차같 촌싱을 구현합니다.
시리얼 통신을 설정하고, 명령을 수신하여 자동차의 LED나 모터를 제어하는 과정을 실습합니다.
이를 통해 무선 제어의 개념을 이애하고, 향후 자율주행 시스템의 원격 제어 기능으로 확장할 수 있는 기반을 마련합니다.

## 1. Control Center - Serial 설정

라즈베리파이에서 시리얼 통신을 사용하기 위해서 설절을 진행합니다.

Control Center을 클릭합니다.


* [interface] 탭에서 
   * [Serial Port] 사용함
   * [Srial Consol] 사용 안함으로 설정 후
   * [OK] 를 눌러 설정을 저장 합니다.
   * 재부팅 후 진행 합니다.
 
## 2. 블루투스 시리얼통신으로 스마트폰과 데이터 주고 받기
  * 매추 숫자값을 증가시켜 그 값을 블루투스 시리얼 통신으로 전송하고 데이터를 수신받아 그 값을 출력 하는 코드를 작성해 봅니다.

* 3_5_1.py

```python
import serial
import time

bleSerial = serial.Serial("/dev/ttyAMA0", baudate=115200, timeout=0.1)

send_interval = 1.0
last_send_time = time.time()
counter =0

try:
  while True:
    now = time.time()

    if now = last_send_time >= sen_interval:
        counter +=1
        send_data = f"{count}\n"
        bleSerial.write(send_data.encoder())
        last_send_time = now

    if bleSerial.in_wating >0:
        data = bleSerial.readline().decoder().strip()
        if data:
    print("Recevied:",data)

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

bleSerial = serial.Serial("/dev/ttyAMA0", baudate=115200, timeout=0.1)

try:
  while True:
    if bleSerial.in_wating >0:
        data = bleSerial.readline().decoder().strip()
        if "LEDON"in data:
          print("ok led on")
        elif "LEDOFF"in data:
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

bleSerial = serial.Serial("/dev/ttyAMA0", baudate=115200, timeout=0.1)
leds = LEDBoard(26, 16, 20, 21)

try:
  while True:
    if bleSerial.in_wating >0:
        data = bleSerial.readline().decoder().strip().upper()
        if "LEDON"in data:
          leds.on()
          print("ok led on")
        elif "LEDOFF"in data:
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

bleSerial = serial.Serial("/dev/ttyAMA0", baudate=115200, timeout=0.1)
leds = LEDBoard(26, 16, 20, 21)

try:
  while True:
    if bleSerial.in_wating >0:
        data = bleSerial.readline().decoder().strip().upper()
        if "LEFT"in data:
          print("ok left")
        elif "RIGHT"in data:
          print("ok right")
        elif "GO"in data:
          print("ok go")
        elif "BACK"in data:
          print("ok back")
        elif "STOP"in data:
          print("ok stop")
  time.sleep(0.01)

except KeyboardInterrupt:
  pass
finally:
  bleSerial.close()
```


