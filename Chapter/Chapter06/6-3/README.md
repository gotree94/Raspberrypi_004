## 데이터수집하기

* 자율주행 학습을 위한 실제 이미지 데이터를 수집하는 과정을 실습합니다.
* 주행 중 카메라로 활용한 영상을 프레임 단위로 저장하고, 각 이미지에 해당 주행 상태(좌회전, 직진 등)의 라벨을 함께 기록합니다.
* 이를 통해 인공지능 학습에 활용할 수 있는 체계적인 데이터셋을 구축할 수 있습니다.

## 조종 화면과 이미지 처리 코드 합치기

* 6_3_1.py

```python
import cv2
import numpy as np
import mycamera
import time
import threading
import myservo
import os
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

    cap = mycamera.MyPiCamera(640, 480)

    cv2.namedWindow('Controls')
    cv2.resizeWindow('Controls', 500, 100)

    cv2.createTrackbar('Steering','Controls', 90, 180, nothing)
    cv2.createTrackbar('Speed','Controls', 40, 100, nothing)

    while True:
        _, frame = cap.read()
        frame = cv2.flip(frame, -1)

        height, width, channels = frame.shape
        save_image = frame[int(height/2):, :, :]
        save_image = cv2.cvtColor(save_image, cv2.COLOR_BGR2YUV)
        save_image = cv2.GaussianBlur(save_image, (3,3), 0)
        save_image = cv2.resize(save_image, (200, 66))
        cv2.imshow('Save', save_image)

        steering_value = cv2.getTrackbarPos('Steering','Controls')
        speed_value = cv2.getTrackbarPos('Speed','Controls')

        servo_angle = pca9685.set_servo_angle(channel, steering_value)

        controls_image = np.zeros((100, 500, 3), dtype=np.uint8)
        cv2.putText(controls_image, f'Steering: {servo_angle}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(controls_image, f'Speed: {speed_value}', (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        if space_pressed:
            cv2.circle(controls_image, (250, 30), 15, (0, 255, 0), -1)
            cv2.putText(controls_image, 'GO', (235, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            motor_go(speed_value / 100)
        else:
            cv2.circle(controls_image, (250, 30), 15, (0, 0, 255), -1)
            cv2.putText(controls_image, 'STOP', (225, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            motor_go(0)

        cv2.imshow('Controls', controls_image)
        cv2.imshow('Camera', frame)

        key = cv2.waitKey(10) & 0xFF
        if key == ord('q'):
            break
        elif key == 32:  # Space key
            space_pressed = not space_pressed

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
```



## 이미지 저장하기

* 학습할 이미지를 저장하는 코드를 작성하여 데이터 수집 코드를 환성하도록 합니다.

* 6_3_2.py

```python
import cv2
import numpy as np
import mycamera
import time
import threading
import myservo
import os
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

    save_path = "/home/pi/AI_CAR/video"
    file_path = save_path + '/train'
    image_count = 0
    space_pressed = False

    if not os.path.exists(save_path):
        os.makedirs(save_path)

    cap = mycamera.MyPiCamera(640, 480)

    cv2.namedWindow('Controls')
    cv2.resizeWindow('Controls', 500, 100)

    cv2.createTrackbar('Steering','Controls', 90, 180, nothing)
    cv2.createTrackbar('Speed','Controls', 40, 100, nothing)

    while True:
        _, frame = cap.read()
        frame = cv2.flip(frame, -1)

        height, width, channels = frame.shape
        save_image = frame[int(height/2):, :, :]
        save_image = cv2.cvtColor(save_image, cv2.COLOR_BGR2YUV)
        save_image = cv2.GaussianBlur(save_image, (3, 3), 0)
        save_image = cv2.resize(save_image, (200, 66))
        cv2.imshow('Save', save_image)

        steering_value = cv2.getTrackbarPos('Steering','Controls')
        speed_value = cv2.getTrackbarPos('Speed','Controls')
        servo_angle = pca9685.set_servo_angle(channel, steering_value)

        controls_image = np.zeros((100, 500, 3), dtype=np.uint8)
        cv2.putText(controls_image, f'Steering: {servo_angle}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(controls_image, f'Speed: {speed_value}', (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        if space_pressed:
            cv2.imwrite("%s_%05d_%03d.png" % (file_path, image_count, servo_angle), save_image)
            image_count = image_count + 1
            cv2.circle(controls_image, (250, 30), 15, (0, 255, 0), -1)
            cv2.putText(controls_image, 'GO', (235, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            motor_go(speed_value / 100)
        else:
            cv2.circle(controls_image, (250, 30), 15, (0, 0, 255), -1)
            cv2.putText(controls_image, 'STOP', (225, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            motor_go(0)

        cv2.imshow('Controls', controls_image)
        cv2.imshow('Camera', frame)

        key = cv2.waitKey(10) & 0xFF
        if key == ord('q'):
            break
        elif key == 32:  # Space key
            space_pressed = not space_pressed

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
```

## 데이터 학습




