# 6-1 OpenCV를 활용해 자동차 조종 화면 만들기


## 조향과 속도를 위한 슬라이드 추가하기

* 6_1_1.py

```python
import cv2
import numpy as np
import time
import myservo
from gpiozero import DigitalOutputDevice
f rom gpiozero import niH0utputDevice

def nothing(x):
    pass

def main():
    pca9685 = myservo.PCA9685()
    channel =0

    cv2 . namedWindow(  ' Cont rots ' )
    cv2. resizeWindow(' Controls', 500, 100)

    cv2.createTrackbar('steering','Controls', 90, 180, nothing)
    cv2.createTrackbar('Speed','Controls',  40, 700, nothing)

    while True:
        steering_value = cv2.getTrackbarPos('Steering','Controts')
        speed-vatue = cv2,getTrackbarPos('Speed','Controls')

        servo_angle = pca9685,set_servo-angle(channe1,  steering-value)

    controls-image = np.zeros((1 00, 500, 3), dtype=np.uint8)
    cv2.putText(controls-image, f'Steerrng: {servo-angle}', (10, 30), cv2.FONT-HERSHEY-SIMPLEX,   0.7,(255, 255, 255), 2)
    cv2.putText(controls-image, f'Speed: {speed-value}', (10, 70), cv2.FONT-HERSHEY-SIMPLEX,  0.7, (255 255,255),2)

    cv2. imshow('Controls', controls-image)

    key = .r2.*u,,*ey(1  0) &OxFF
    if keY == ord('q'):
        break

    cv2.destroyAllWindows0

if _name- =="_main_'
  main()
```


## 자동차 이동, 멈춤 기능 구현하기

* 6_1_2.py

```python
import cv2
import numpy as np
import time
import myservo
from gpiozero import Digital0utputDevice
from gpiozero import PWMOutputDevice

def nothing(x):
    pass

def main():
        pca9685 = myservo.PCA9685Q
        channel =0

        space_pressed  =False

        cv2. namedWindow('  Cont rols' )
        cv2. resizeWindow('Controls',  500, 100)

        cv2.createTrackbar('Steering','Controls',    90, !80, nothing)
        cv2.createTrackbar('Speed','Controls',  40, 100, nothing)

        while True:
                steering_value = cv2.getTrackbarPos('Steering','ControIs'    )
                speed_value  = cv2.getTrackbarPos('Speed','Controls'   )

                servo_angIe = pca9685.set_servo_angle(channel,  steering_value)

                controls_image  = np.zeros((100,  500, 3), dtype=np.uint8)
                cv2.putText(controls_image, f'Steering: {servo_angle}', (10,30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255),2)
                cv2.putText(controls_image, f'Speed: {speed_value}', (10,70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255),2)

                if space_pressed:
                    cv2.circle(controls_image, (250, 30), 15, (0,255,0), -1)
                    cv2.putText(contros_imag, f'GO', (235, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
                else:
                    cv2.circle(controls_image, (250, 30), 15, (0,255,0), -1)
                    cv2.putText(contros_imag, f'STOP', (235, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)

                cv2.imshow('Controls', controls_image)

                key = cv2.waitKey(10)&OxFF
                if  key == ord('q'):
                    break
                etif key ==32; # SPace keY
                if not space_pressed:
                    space_pressed  =True
                else:
                    space_pressed  =False

    cv2. destroyAl lWi ndows0

if __name__ =="__main__":
    main()
```



## 실제 자동차 움직임 구현하여 조종하기

* 6_1_3.py

```python

import cv2
import numpy as np
import tinre
import myservo
from gpiozero import Digital0utputDevice
f rorn gpiozero import PliltOutputDevice
B{l'tA = PWMOutputDevice(18)
AIN1 = Digitat0utputDevice(22)
AIN2 = DigitalOutputDevice(27)
PI{MB = PWll0utputDevice(23)
BIN1 = Disitat0utput0evice(25)
BIN2 = Digital0utputDevice(24)
def motor_g0(speed):
AIN1.value  =0
AII'I2.value  =1
PWfi.value = speed
BINl.value  =0
BIN2,value  =1
P|{I'IB.value = speed
def nothing(x)
pass
def maino:
pca9685 = myservo.PCA9685Q
channel =0
space_pressed  =False
cv2, namedliindow('  Cont rols' )
cv2. resizeWindow(' Controls', 500, 100)
cv2.createTrackbar('Steering','Controls',    90, 780, nothing)
cv2.createTrackbar('Speed','Controts',  40, I00, nothing)
while True:
steering_value = cv2.getTrackbarPos('Steering','Controls') speed_value  = cv2,getTrackbarPos('Speed','Controls') servo_angIe = pca9685.set_servo_angle(channet,  steering_value) controls_image  = np.zeros((700,  500, 3), dtype=np.uint8)

cv2.putText(controts_image, f'Steering: {servo_angte}', (L0, 30), cv2.F0ilT_HERSHEy_ SIMPLEX, 0.7, (255, 255, 255), 2)
47            cv2.putText(controts_image, f'Speed: {speed_value}',  (!0, 70), cv2.F0IIT_HERSHEY_Sil{PLEX, 0.7, (255,255,255),2)
48
49
50
51
255, 255), 2)
5? s3 54 55

, 255), 2)
if  space_pressed:
cv2.circle(controls_image, (250, 30), 15, (0, 255, 0), -1,)
cv2.putText(controls_image, f'G0', (235, 70), cv2.F0NT_HERSHEY_S$,IPLEX,   0.7, (255,
moto r_go ( speed_va Iue/ 100)
else:
cv2.circle(controls_image, (250, 30), !5, (0, 0, 255), -1)
cv2.putText(controls_image, f'STOP', (225,70),  cv2.F0NT_HERSHEY_S$IPLEX,    0.7, (?55, motor_go(0)
cv2.imshow('Controls',  controls_image)
key = 6v2.*ritKey(10) &0xFF if  key == ord('q'):
elif keY ==32; # S,ace ke, if not space_pressed:
space_pressed  =True else:
space_pressed  =False cv2. destroyAllWindowso
break
72    if _name- =="__main_ main0

```


