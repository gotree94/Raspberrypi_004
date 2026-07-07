# 4-4 파란 삼각형 도형을 따라가는 자동차 만들기

## 파란 삼격형 검출하기

* 4_4_1.py

```python
import mycamera
import cv2
import numpy as np

LOW_BLUE = (100, 120, 70)
HIGH_BLUE = (140, 255, 255)
MIN_TRI_AREA = 1200

def find_blue_triangle(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, LOW_BLUE, HIGH_BLUE)
    mask = cv2.medianBlur(mask, 5)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    best = None
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < MIN_TRI_AREA:
            continue
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.04 * peri, True)
        if len(approx) == 3:
            M = cv2.moments(approx)
            if M["m00"] == 0:
                continue
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            if best is None or area > best[0]:
                best = (area, approx, cx, cy)
    return best, mask

if __name__ == "__main__":
    cam = mycamera.MyPiCamera(640, 480)
    while cam.isOpened():
        _, img = cam.read()
        img = cv2.flip(img, -1)
        vis = img.copy()
        best, mask = find_blue_triangle(img)
        if best is not None:
            area, approx, cx, cy = best
            cv2.drawContours(vis, [approx], -1, (255, 0, 0), 3)
            cv2.circle(vis, (cx, cy), 5, (0, 0, 255), -1)
            cv2.putText(vis, f'area:{int(area)}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.imshow("mycamera", vis)
        cv2.imshow("mask", mask)
        if cv2.waitKey(1) == ord('q'):
            break
    cv2.destroyAllWindows()
```

```python
import cv2
import numpy as np

LOW_BLUE = (100, 120, 70)
HIGH_BLUE = (140, 255, 255)
MIN_TRI_AREA = 1200

def find_blue_triangle(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, LOW_BLUE, HIGH_BLUE)
    mask = cv2.medianBlur(mask, 5)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    best = None
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < MIN_TRI_AREA:
            continue
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.04 * peri, True)
        if len(approx) == 3:
            M = cv2.moments(approx)
            if M["m00"] == 0:
                continue
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            if best is None or area > best[0]:
                best = (area, approx, cx, cy)
    return best, mask

if __name__ == "__main__":
    cam = cv2.VideoCapture(0)
    cam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    while cam.isOpened():
        _, img = cam.read()
        img = cv2.flip(img, 1)
        vis = img.copy()
        best, mask = find_blue_triangle(img)
        if best is not None:
            area, approx, cx, cy = best
            cv2.drawContours(vis, [approx], -1, (255, 0, 0), 3)
            cv2.circle(vis, (cx, cy), 5, (0, 0, 255), -1)
            cv2.putText(vis, f'area:{int(area)}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.imshow("mycamera", vis)
        cv2.imshow("mask", mask)
        if cv2.waitKey(1) == ord('q'):
            break
    cv2.destroyAllWindows()
```

## 검출된 객체를 이용하여 이동 방향 결정하기

* 4_4_2.py

```python
import mycamera
import cv2
import numpy as np

LOW_BLUE = (100, 120, 70)
HIGH_BLUE = (140, 255, 255)
MIN_TRI_AREA = 1200

DEADBAND = 20
AREA_OK_LO = 8000
AREA_OK_HI = 18000
AREA_NEAR = 22000

def find_blue_triangle(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, LOW_BLUE, HIGH_BLUE)
    mask = cv2.medianBlur(mask, 5)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    best = None
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < MIN_TRI_AREA:
            continue
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.04 * peri, True)
        if len(approx) == 3:
            M = cv2.moments(approx)
            if M["m00"] == 0:
                continue
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            if best is None or area > best[0]:
                best = (area, approx, cx, cy)
    return best, mask

def decide_direction(cx, center_x, area):
    err = cx - center_x
    if area >= AREA_NEAR:
        return "STOP"
    if AREA_OK_LO <= area <= AREA_OK_HI:
        if abs(err) <= DEADBAND:
            return "FORWARD_SLOW"
        return "RIGHT" if err > 0 else "LEFT"
    if abs(err) <= DEADBAND:
        return "FORWARD_FAST"
    return "RIGHT" if err > 0 else "LEFT"

if __name__ == "__main__":
    cam = mycamera.MyPiCamera(640, 480)
    while cam.isOpened():
        _, img = cam.read()
        img = cv2.flip(img, -1)
        h, w = img.shape[:2]
        center_x = w // 2
        vis = img.copy()
        best, mask = find_blue_triangle(img)
        if best is not None:
            area, approx, cx, cy = best
            decision = decide_direction(cx, center_x, area)
            cv2.drawContours(vis, [approx], -1, (255, 0, 0), 3)
            cv2.circle(vis, (cx, cy), 5, (0, 0, 255), -1)
            cv2.line(vis, (center_x, 0), (center_x, h), (0, 255, 255), 1)
            cv2.putText(vis, f'area:{int(area)} err:{cx - center_x}', (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(vis, f'decision:{decision}', (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            print(decision)
        else:
            decision = "TARGET_LOST"
            cv2.putText(vis, decision, (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            print(decision)
        cv2.imshow("mycamera", vis)
        cv2.imshow("mask", mask)
        if cv2.waitKey(1) == ord('q'):
            break
    cv2.destroyAllWindows()
```

```python
import cv2
import numpy as np

LOW_BLUE = (100, 120, 70)
HIGH_BLUE = (140, 255, 255)
MIN_TRI_AREA = 1200

DEADBAND = 20
AREA_OK_LO = 8000
AREA_OK_HI = 18000
AREA_NEAR = 22000

def find_blue_triangle(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, LOW_BLUE, HIGH_BLUE)
    mask = cv2.medianBlur(mask, 5)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    best = None
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < MIN_TRI_AREA:
            continue
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.04 * peri, True)
        if len(approx) == 3:
            M = cv2.moments(approx)
            if M["m00"] == 0:
                continue
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            if best is None or area > best[0]:
                best = (area, approx, cx, cy)
    return best, mask

def decide_direction(cx, center_x, area):
    err = cx - center_x
    if area >= AREA_NEAR:
        return "STOP"
    if AREA_OK_LO <= area <= AREA_OK_HI:
        if abs(err) <= DEADBAND:
            return "FORWARD_SLOW"
        return "RIGHT" if err > 0 else "LEFT"
    if abs(err) <= DEADBAND:
        return "FORWARD_FAST"
    return "RIGHT" if err > 0 else "LEFT"

if __name__ == "__main__":
    cam = cv2.VideoCapture(0)
    cam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    while cam.isOpened():
        _, img = cam.read()
        img = cv2.flip(img, 1)
        h, w = img.shape[:2]
        center_x = w // 2
        vis = img.copy()
        best, mask = find_blue_triangle(img)
        if best is not None:
            area, approx, cx, cy = best
            decision = decide_direction(cx, center_x, area)
            cv2.drawContours(vis, [approx], -1, (255, 0, 0), 3)
            cv2.circle(vis, (cx, cy), 5, (0, 0, 255), -1)
            cv2.line(vis, (center_x, 0), (center_x, h), (0, 255, 255), 1)
            cv2.putText(vis, f'area:{int(area)} err:{cx - center_x}', (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(vis, f'decision:{decision}', (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            print(decision)
        else:
            decision = "TARGET_LOST"
            cv2.putText(vis, decision, (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            print(decision)
        cv2.imshow("mycamera", vis)
        cv2.imshow("mask", mask)
        if cv2.waitKey(1) == ord('q'):
            break
    cv2.destroyAllWindows()
```

## 실제 자동차를 움직여 파란 세모 도형을 따라가기

* 4_4_3.py

```python
import mycamera
import cv2
import numpy as np
import myservo
import time
from gpiozero import PWMOutputDevice, DigitalOutputDevice

PWMA = PWMOutputDevice(18)
AIN1 = DigitalOutputDevice(22)
AIN2 = DigitalOutputDevice(27)

PWMB = PWMOutputDevice(23)
BIN1 = DigitalOutputDevice(25)
BIN2 = DigitalOutputDevice(24)

def motor_go(speed):
    AIN1.value = 0; AIN2.value = 1; PWMA.value = speed
    BIN1.value = 0; BIN2.value = 1; PWMB.value = speed

def motor_back(speed):
    AIN1.value = 1; AIN2.value = 0; PWMA.value = speed
    BIN1.value = 1; BIN2.value = 0; PWMB.value = speed

def motor_stop():
    AIN1.value = 0; AIN2.value = 0; PWMA.value = 0.0
    BIN1.value = 0; BIN2.value = 0; PWMB.value = 0.0

pca9685 = myservo.PCA9685()
SERVO_CH = 0
LEFT_ANGLE = 45
RIGHT_ANGLE = 135
CENTER_ANGLE = 90

BASE_SPEED = 0.5
SLOW_SPEED = 0.3
TURN_DEADBAND = 20
MIN_TRI_AREA = 1200
AREA_OK_LO = 8000
AREA_OK_HI = 18000
AREA_NEAR = 22000

LOW_BLUE = (100, 120, 70)
HIGH_BLUE = (140, 255, 255)
KP_ANGLE = 30.0 / 320.0

def clamp(v, lo, hi):
    return hi if v > hi else lo if v < lo else v

def find_blue_triangle(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, LOW_BLUE, HIGH_BLUE)
    mask = cv2.medianBlur(mask, 5)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    best = None
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < MIN_TRI_AREA:
            continue
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.04 * peri, True)
        if len(approx) == 3:
            M = cv2.moments(approx)
            if M["m00"] == 0:
                continue
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            if best is None or area > best[0]:
                best = (area, approx, cx, cy)
    return best, mask

if __name__ == "__main__":
    camera = mycamera.MyPiCamera(640, 480)
    pca9685.set_servo_angle(SERVO_CH, CENTER_ANGLE)
    try:
        while camera.isOpened():
            _, img = camera.read()
            img = cv2.flip(img, -1)
            h, w = img.shape[:2]
            cx_mid = w // 2
            best, mask = find_blue_triangle(img)
            vis = img.copy()
            if best is not None:
                area, approx, cx, cy = best
                cv2.drawContours(vis, [approx], -1, (255, 0, 0), 3)
                cv2.circle(vis, (cx, cy), 5, (0, 0, 255), -1)
                err = cx - cx_mid
                if abs(err) <= TURN_DEADBAND:
                    target_angle = CENTER_ANGLE
                else:
                    target_angle = CENTER_ANGLE + KP_ANGLE * err
                target_angle = clamp(target_angle, LEFT_ANGLE, RIGHT_ANGLE)
                pca9685.set_servo_angle(SERVO_CH, int(target_angle))
                if area >= AREA_NEAR:
                    motor_stop()
                elif AREA_OK_LO <= area <= AREA_OK_HI:
                    motor_go(SLOW_SPEED)
                else:
                    motor_go(BASE_SPEED)
            else:
                pca9685.set_servo_angle(SERVO_CH, CENTER_ANGLE)
                motor_stop()
            cv2.imshow("view", vis)
            cv2.imshow("mask", mask)
            if cv2.waitKey(1) == ord('q'):
                break
            time.sleep(0.01)
    finally:
        motor_stop()
        pca9685.set_servo_angle(SERVO_CH, CENTER_ANGLE)
        cv2.destroyAllWindows()
```

```python
import cv2
import numpy as np
import time
from gpiozero import PWMOutputDevice, DigitalOutputDevice

PWMA = PWMOutputDevice(18)
AIN1 = DigitalOutputDevice(22)
AIN2 = DigitalOutputDevice(27)

PWMB = PWMOutputDevice(23)
BIN1 = DigitalOutputDevice(25)
BIN2 = DigitalOutputDevice(24)

def motor_go(speed):
    AIN1.value = 0; AIN2.value = 1; PWMA.value = speed
    BIN1.value = 0; BIN2.value = 1; PWMB.value = speed

def motor_back(speed):
    AIN1.value = 1; AIN2.value = 0; PWMA.value = speed
    BIN1.value = 1; BIN2.value = 0; PWMB.value = speed

def motor_stop():
    AIN1.value = 0; AIN2.value = 0; PWMA.value = 0.0
    BIN1.value = 0; BIN2.value = 0; PWMB.value = 0.0

#pca9685 = myservo.PCA9685()
SERVO_CH = 0
LEFT_ANGLE = 45
RIGHT_ANGLE = 135
CENTER_ANGLE = 90

BASE_SPEED = 0.5
SLOW_SPEED = 0.3
TURN_DEADBAND = 20
MIN_TRI_AREA = 1200
AREA_OK_LO = 8000
AREA_OK_HI = 18000
AREA_NEAR = 22000

LOW_BLUE = (100, 120, 70)
HIGH_BLUE = (140, 255, 255)
KP_ANGLE = 30.0 / 320.0

def clamp(v, lo, hi):
    return hi if v > hi else lo if v < lo else v

def find_blue_triangle(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, LOW_BLUE, HIGH_BLUE)
    mask = cv2.medianBlur(mask, 5)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    best = None
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < MIN_TRI_AREA:
            continue
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.04 * peri, True)
        if len(approx) == 3:
            M = cv2.moments(approx)
            if M["m00"] == 0:
                continue
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            if best is None or area > best[0]:
                best = (area, approx, cx, cy)
    return best, mask

if __name__ == "__main__":
    cam = cv2.VideoCapture(0)
    cam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    #pca9685.set_servo_angle(SERVO_CH, CENTER_ANGLE)
    try:
        while cam.isOpened():
            _, img = cam.read()
            img = cv2.flip(img, 1)
            h, w = img.shape[:2]
            cx_mid = w // 2
            best, mask = find_blue_triangle(img)
            vis = img.copy()
            if best is not None:
                area, approx, cx, cy = best
                cv2.drawContours(vis, [approx], -1, (255, 0, 0), 3)
                cv2.circle(vis, (cx, cy), 5, (0, 0, 255), -1)
                err = cx - cx_mid
                if abs(err) <= TURN_DEADBAND:
                    target_angle = CENTER_ANGLE
                else:
                    target_angle = CENTER_ANGLE + KP_ANGLE * err
                target_angle = clamp(target_angle, LEFT_ANGLE, RIGHT_ANGLE)
                #pca9685.set_servo_angle(SERVO_CH, int(target_angle))
                if area >= AREA_NEAR:
                    motor_stop()
                elif AREA_OK_LO <= area <= AREA_OK_HI:
                    motor_go(SLOW_SPEED)
                else:
                    motor_go(BASE_SPEED)
            else:
                #pca9685.set_servo_angle(SERVO_CH, CENTER_ANGLE)
                motor_stop()
            cv2.imshow("view", vis)
            cv2.imshow("mask", mask)
            if cv2.waitKey(1) == ord('q'):
                break
            time.sleep(0.01)
    finally:
        motor_stop()
        pca9685.set_servo_angle(SERVO_CH, CENTER_ANGLE)
        cv2.destroyAllWindows()
```

