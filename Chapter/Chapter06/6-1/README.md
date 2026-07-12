# 6-1 OpenCV를 활용해 자동차 조종 화면 만들기

* OpenCV를 이용해 자동차의 주행 상황을 실시간으로 확일할 수 있는 조종 화면을 구성합니다.
* 카메라에서 입력된 영상을 화면에 출력하고, 키보드 입력을 통해 자동차의 전진, 좌우 조향 등을 제어 합니다.


## 조향과 속도를 위한 슬라이드 추가하기

* 조향과 속도 조절을 위한 슬라이드를 OpenCV의 기능을 이용하여 추가해 보도록 합니다.
* 또한 슬라이드 조향 서보를 제어해 앞바퀴를 움직여 보도록 합니다.

* 6_1_1.py

```python
import cv2
import numpy as np
import time
import myservo
from gpiozero import DigitalOutputDevice
from gpiozero import PWMOutputDevice

def nothing(x):
    pass

def main():
    pca9685 = myservo.PCA9685()
    channel = 0

    cv2.namedWindow('Controls')
    cv2.resizeWindow('Controls', 500, 100)

    cv2.createTrackbar('steering','Controls', 90, 180, nothing)
    cv2.createTrackbar('Speed','Controls',  40, 700, nothing)

    while True:
        steering_value = cv2.getTrackbarPos('steering','Controls')
        speed_value = cv2.getTrackbarPos('Speed','Controls')

        servo_angle = pca9685.set_servo_angle(channel, steering_value)

        controls_image = np.zeros((100, 500, 3), dtype=np.uint8)
        cv2.putText(controls_image, f'Steering: {servo_angle}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(controls_image, f'Speed: {speed_value}', (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        cv2.imshow('Controls', controls_image)

        key = cv2.waitKey(10) & 0xFF
        if key == ord('q'):
            break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()

```

```python
import cv2
import numpy as np
import time
#import myservo
#from gpiozero import DigitalOutputDevice
#from gpiozero import PWMOutputDevice

def nothing(x):
    pass

def main():
    #pca9685 = myservo.PCA9685()
    channel = 0

    cv2.namedWindow('Controls')
    cv2.resizeWindow('Controls', 500, 100)

    cv2.createTrackbar('steering','Controls', 90, 180, nothing)
    cv2.createTrackbar('Speed','Controls',  40, 700, nothing)

    while True:
        steering_value = cv2.getTrackbarPos('steering','Controls')
        speed_value = cv2.getTrackbarPos('Speed','Controls')

        servo_angle = pca9685.set_servo_angle(channel, steering_value)

        controls_image = np.zeros((100, 500, 3), dtype=np.uint8)
        cv2.putText(controls_image, f'Steering: {servo_angle}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(controls_image, f'Speed: {speed_value}', (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        cv2.imshow('Controls', controls_image)

        key = cv2.waitKey(10) & 0xFF
        if key == ord('q'):
            break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()

```

## 자동차 이동, 멈춤 기능 구현하기

* 스페이스바를 한번 누르면 Go, 다시 한번 누르면 STOP이 되도록 이동, 멈춤 기능을 구현해 보도록 합니다.

* 6_1_2.py

```python
import cv2
import numpy as np
import time
import myservo
from gpiozero import DigitalOutputDevice
from gpiozero import PWMOutputDevice

def nothing(x):
    pass

def main():
    pca9685 = myservo.PCA9685()
    channel = 0

    space_pressed = False

    cv2.namedWindow('Controls')
    cv2.resizeWindow('Controls', 500, 100)

    cv2.createTrackbar('Steering','Controls', 90, 180, nothing)
    cv2.createTrackbar('Speed','Controls', 40, 100, nothing)

    while True:
        steering_value = cv2.getTrackbarPos('Steering','Controls')
        speed_value = cv2.getTrackbarPos('Speed','Controls')

        servo_angle = pca9685.set_servo_angle(channel, steering_value)

        controls_image = np.zeros((100, 500, 3), dtype=np.uint8)
        cv2.putText(controls_image, f'Steering: {servo_angle}', (10,30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
        cv2.putText(controls_image, f'Speed: {speed_value}', (10,70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)

        if space_pressed:
            cv2.circle(controls_image, (250, 30), 15, (0,255,0), -1)
            cv2.putText(controls_image, 'GO', (235, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
        else:
            cv2.circle(controls_image, (250, 30), 15, (0,0,255), -1)
            cv2.putText(controls_image, 'STOP', (235, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)

        cv2.imshow('Controls', controls_image)

        key = cv2.waitKey(10) & 0xFF
        if key == ord('q'):
            break
        elif key == 32:  # Space key
            space_pressed = not space_pressed

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()

```



## 실제 자동차 움직임 구현하여 조종하기

* 모터를 제어하는 실제 자동차를 움직여 조종해보도록 합니다.

* 6_1_3.py

```python
import cv2
import numpy as np
import time
import myservo
from gpiozero import DigitalOutputDevice
from gpiozero import PWMOutputDevice

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

def nothing(x):
    pass

def main():
    pca9685 = myservo.PCA9685()
    channel = 0

    space_pressed = False

    cv2.namedWindow('Controls')
    cv2.resizeWindow('Controls', 500, 100)

    cv2.createTrackbar('Steering','Controls', 90, 180, nothing)
    cv2.createTrackbar('Speed','Controls', 40, 100, nothing)

    while True:
        steering_value = cv2.getTrackbarPos('Steering','Controls')
        speed_value = cv2.getTrackbarPos('Speed','Controls')

        servo_angle = pca9685.set_servo_angle(channel, steering_value)

        controls_image = np.zeros((100, 500, 3), dtype=np.uint8)

        cv2.putText(controls_image, f'Steering: {servo_angle}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(controls_image, f'Speed: {speed_value}', (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)

        if space_pressed:
            cv2.circle(controls_image, (250, 30), 15, (0, 255, 0), -1)
            cv2.putText(controls_image, 'GO', (235, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
            motor_go(speed_value / 100)
        else:
            cv2.circle(controls_image, (250, 30), 15, (0, 0, 255), -1)
            cv2.putText(controls_image, 'STOP', (225, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
            motor_go(0)

        cv2.imshow('Controls', controls_image)

        key = cv2.waitKey(10) & 0xFF
        if key == ord('q'):
            break
        elif key == 32:  # Space key
            space_pressed = not space_pressed

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()

```


