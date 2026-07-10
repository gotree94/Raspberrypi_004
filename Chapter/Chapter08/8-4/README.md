# 8-4 차선 유지 자율주행 실습

* 학습된 모델을 이요하여 실제 차선 유지 자율주행을 구현합니다.
* 카메라로부터 입력된 영상 데이터를 모델이 실시간으로 분석하여 자동차의 조향을 자동으로 제어합니다.
* 직진, 커브, 차선 변경 등의 상황에서 자동차가 스스로 판단하여 주행하는 모습을 관창할 수 있습니다.
* 이 실습을 통해 학습자는 인공지능 기반 자율주행의 완성된 형태를 경험하게 됩니다.


## 조향각에 따라 서보모터 움직이기

* 8_4_1.py

```python
import mycamera
import myservo
import cv2
import numpy as np
import torch

MODEL_PATH = "/home/pi/AI_CAR/model/lane_navigation_final.torchscript"

def img_preprocess(image):
    h, w, c = image.shape
    image = image[h//2:, :, :]
    image = cv2.cvtColor(image, cv2.COLOR_BGR2YUV)
    image = cv2.GaussianBlur(image, (3, 3), 0)
    image = cv2.resize(image, (200, 66))
    image = image.astype(np.float32) / 255.0
    return image

def main():
    camera = mycamera.MyPiCamera(640, 480)
    pca9685 = myservo.PCA9685()
    channel = 0
    model = torch.jit.load(MODEL_PATH, map_location="cpu")
    model.eval()
    torch.set_num_threads(1)

    try:
        while camera.isOpened():
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break

            ok, image = camera.read()
            if not ok:
                continue

            image = cv2.flip(image, -1)

            pre = img_preprocess(image)
            x = np.transpose(pre, (2, 0, 1))
            x = np.expand_dims(x, axis=0)
            x_tensor = torch.from_numpy(x).float()

            with torch.no_grad():
                y = model(x_tensor)

            angle = int(float(y.view(-1)[0].item()))
            pca9685.set_servo_angle(channel, angle)
            print('predict angle:', angle)

            cv2.imshow('camera', image)
            cv2.imshow('preprocess', pre)

    finally:
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
```


## 모터 구동하여 자율주행 완성하기

* 8_4_2.py

```python
import mycamera
import myservo
import cv2
import numpy as np
import torch
from gpiozero import DigitalOutputDevice, PWMOutputDevice

SET_MOTOR_SPEED = 0.4

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

def motor_stop():
    AIN1.value = 0
    AIN2.value = 1
    PWMA.value = 0.0
    BIN1.value = 1
    BIN2.value = 0
    PWMB.value = 0.0

def img_preprocess(image):
    h, w, c = image.shape
    image = image[h//2:, :, :]
    image = cv2.cvtColor(image, cv2.COLOR_BGR2YUV)
    image = cv2.GaussianBlur(image, (3, 3), 0)
    image = cv2.resize(image, (200, 66))
    image = image.astype(np.float32) / 255.0
    return image

def main():
    camera = mycamera.MyPiCamera(640, 480)
    pca9685 = myservo.PCA9685()
    channel = 0

    model_path = "/home/pi/AI_CAR/model/lane_navigation_final.torchscript"
    model = torch.jit.load(model_path, map_location="cpu")
    model.eval()
    torch.set_num_threads(1)

    drive = False
    angle_smooth = None
    alpha = 0.8

    try:
        while camera.isOpened():
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == 32:
                drive = not drive
                print('DRIVE:', "ON" if drive else "OFF")

            ok, image = camera.read()
            if not ok:
                continue

            image = cv2.flip(image, -1)

            pre = img_preprocess(image)
            x = np.transpose(pre, (2, 0, 1))
            x = np.expand_dims(x, axis=0)
            x_tensor = torch.from_numpy(x).float()

            with torch.no_grad():
                y = model(x_tensor)

            angle = int(float(y.view(-1)[0].item()))
            pca9685.set_servo_angle(channel, angle)
            print("angle: ", angle)

            cv2.imshow('camera', image)
            cv2.imshow('preprocess', pre)

            if drive:
                motor_go(SET_MOTOR_SPEED)
            else:
                motor_stop()

    finally:
        motor_stop()
        PWMA.value = 0.0
        PWMB.value = 0.0
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
```

