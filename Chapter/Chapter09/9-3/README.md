# 9-3 자율주행 + 객체 검출 적용하기

* 기존의 자율주행 코드에 객체 검출 기능을 토합하여 지능형 주행 시스템을 구현합니다.
* 카메라로 인식한 신호들이나 보행자 등의 정보를 기반으로 자도차가 정지하거나 주행을 결정하도록 제어 로직을 구성합니다.
* 이 실습으로 단순한 차선 주행을 넘어, 주변 환경을 인식하고 반응하는 AI 기반 자율주행을 완성하게 됩니다.
* 겱과적으로 학습자는 인공지능 모델을 실제 하드웨어에 적용하고, 자율주행의 핵십 기술이 실시간으로 작동하는 과정을 직접 확인할 수 있습니다.

## 모델 파일 라즈베리파이로 이동

* PC 다운로드 폴더늬 [ai_car_model.pt] 파일을 라즈베리파이의 AI_CAR 폴더로 이동합니다.


## 내가 만든 모델로 객체 인식하기

* 라즈베리파이 카메라로 실시간 영상을 받아, 내가 만든 YOLO 모델을 이ㅛㅇ해 객체를 검출하고 화면에 표시하는 프로그램을 작성합니다.

* 9_3_1.py

```python
import mycamera
import cv2
from ultralytics import YOLO

def draw_detections(frame, results, names):
    if results is None:
        return frame
    for b in results.boxes:
        cls_id = int(b.cls.item())
        conf = float(b.conf.item())
        x1, y1, x2, y2 = map(int, b.xyxy[0].tolist())
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        label = f"{names[cls_id]} {conf:.2f}"
        cv2.putText(frame, label, (x1, max(10, y1 - 6)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    return frame

if __name__ == "__main__":
    model = YOLO("ai_car_model.pt")
    camera = mycamera.MyPiCamera(640, 480)
    try:
        while camera.isOpened():
            ok, frame = camera.read()
            if not ok:
                break
            frame = cv2.flip(frame, -1)
            results = model(frame, imgsz=320, conf=0.5, iou=0.5, device='cpu')[0]
            out = draw_detections(frame, results, model.names)
            cv2.imshow("YOLOv8 (mycamera)", out)
            if cv2.waitKey(1) == ord('q'):
                break
    finally:
        try:
            camera.release()
        except Exception:
            pass
        cv2.destroyAllWindows()

```

```python
#import mycamera
import cv2
from ultralytics import YOLO

def draw_detections(frame, results, names):
    if results is None:
        return frame
    for b in results.boxes:
        cls_id = int(b.cls.item())
        conf = float(b.conf.item())
        x1, y1, x2, y2 = map(int, b.xyxy[0].tolist())
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        label = f"{names[cls_id]} {conf:.2f}"
        cv2.putText(frame, label, (x1, max(10, y1 - 6)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    return frame

if __name__ == "__main__":
    model = YOLO("ai_car_model.pt")
    #camera = mycamera.MyPiCamera(640, 480)
    camera = cv2.VideoCapture(0)
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)  
    try:
        while camera.isOpened():
            ok, frame = camera.read()
            if not ok:
                break
            frame = cv2.flip(frame, -1)
            results = model(frame, imgsz=320, conf=0.5, iou=0.5, device='cpu')[0]
            out = draw_detections(frame, results, model.names)
            cv2.imshow("YOLOv8 (mycamera)", out)
            if cv2.waitKey(1) == ord('q'):
                break
    finally:
        try:
            camera.release()
        except Exception:
            pass
        cv2.destroyAllWindows()
```

## 자율주행에 객체 인식 모델 적용해서 주행하기

* 차선 각도 예측 모델(TorchScript)로 서보를 조향하고, 주기적으로 YOLO로 객체를 검출해 화면에 표시하는 코드를 작성합니다.

* 9_3_2.py

```python
import mycamera
import myservo
import cv2
import numpy as np
import torch
from ultralytics import YOLO
from gpiozero import DigitalOutputDevice, PWMOutputDevice

SET_MOTOR_SPEED = 0.2
DETECT_EVERY_N = 3
YOLO_IMG_SIZE = 224

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

def draw_detections(frame, results, names):
    if results is None:
        return frame
    for b in results.boxes:
        cls_id = int(b.cls.item())
        conf = float(b.conf.item())
        x1, y1, x2, y2 = map(int, b.xyxy[0].tolist())
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        label = f"{names[cls_id]} {conf:.2f}"
        cv2.putText(frame, label, (x1, max(10, y1 - 6)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    return frame

def main():
    cv2.setUseOptimized(True)
    camera = mycamera.MyPiCamera(640, 480)
    pca9685 = myservo.PCA9685()
    channel = 0

    model_path = "/home/pi/AI_CAR/model/lane_navigation_final.torchscript"
    lane_model = torch.jit.load(model_path, map_location="cpu")
    lane_model.eval()
    torch.set_num_threads(1)

    det_model = YOLO("ai_car_model.pt")
    drive = False
    angle = 90
    det_results = None
    frame_count = 0

    try:
        while camera.isOpened():
            ok, frame = camera.read()
            if not ok:
                continue

            frame = cv2.flip(frame, -1)

            pre = img_preprocess(frame)
            x = np.transpose(pre, (2, 0, 1))[None, :, :]
            x_tensor = torch.from_numpy(x).float()

            with torch.no_grad():
                y = lane_model(x_tensor)
            angle = int(float(y.view(-1)[0].item()))
            pca9685.set_servo_angle(channel, angle)

            if frame_count % DETECT_EVERY_N == 0:
                det_results = det_model(frame, imgsz=YOLO_IMG_SIZE, conf=0.55, iou=0.5,
                                        device='cpu')[0]

            out = frame
            out = draw_detections(out, det_results, det_model.names)
            status = f"DRIVE: {'ON' if drive else 'OFF'} ANGLE: {angle}"
            cv2.putText(out, status, (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 2)
            cv2.imshow("camera", out)
            cv2.imshow("preprocess", pre)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == 32:
                drive = not drive
                print("DRIVE:", 'ON' if drive else 'OFF')

            if drive:
                motor_go(SET_MOTOR_SPEED)
            else:
                motor_stop()

            frame_count += 1

    finally:
        motor_stop()
        PWMA.value = 0.0
        PWMB.value = 0.0
        try:
            camera.release()
        except Exception:
            pass
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()

```

## 사람이 검출되면 멈추기

* 차선 추론으로 서보 각도를 제어하고, YOLO로 사람(person)을 감지하면 즉시 정지하는 코드를 작성합니다.

* 9_3_3.py

```python
import mycamera
import myservo
import cv2
import numpy as np
import torch
from ultralytics import YOLO
from gpiozero import DigitalOutputDevice, PWMOutputDevice

SET_MOTOR_SPEED = 0.2
DETECT_EVERY_N = 3
YOLO_IMG_SIZE = 224

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

def draw_detections(frame, results, names):
    if results is None:
        return frame, False
    stop_flag = False
    for b in results.boxes:
        cls_id = int(b.cls.item())
        conf = float(b.conf.item())
        x1, y1, x2, y2 = map(int, b.xyxy[0].tolist())
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        label = f"{names[cls_id]} {conf:.2f}"
        cv2.putText(frame, label, (x1, max(10, y1 - 6)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        if names[cls_id].lower() == "person" and conf > 0.5:
            stop_flag = True
    return frame, stop_flag

def main():
    cv2.setUseOptimized(True)
    camera = mycamera.MyPiCamera(640, 480)
    pca9685 = myservo.PCA9685()
    channel = 0

    model_path = "/home/pi/AI_CAR/model/lane_navigation_final.torchscript"
    lane_model = torch.jit.load(model_path, map_location="cpu")
    lane_model.eval()
    torch.set_num_threads(1)

    det_model = YOLO("ai_car_model.pt")
    drive = False
    angle = 90
    det_results = None
    frame_count = 0
    stop_due_to_person = False

    try:
        while camera.isOpened():
            ok, frame = camera.read()
            if not ok:
                continue

            frame = cv2.flip(frame, -1)

            pre = img_preprocess(frame)
            x = np.transpose(pre, (2, 0, 1))[None, :, :]
            x_tensor = torch.from_numpy(x).float()

            with torch.no_grad():
                y = lane_model(x_tensor)
            angle = int(float(y.view(-1)[0].item()))
            pca9685.set_servo_angle(channel, angle)

            if frame_count % DETECT_EVERY_N == 0:
                det_results = det_model(frame, imgsz=YOLO_IMG_SIZE, conf=0.55, iou=0.5,
                                        device='cpu')[0]

            out, person_detected = draw_detections(frame.copy(), det_results, det_model.names)
            if person_detected:
                stop_due_to_person = True

            if stop_due_to_person:
                drive = False

            status = f"DRIVE: {'ON' if drive else 'OFF'} ANGLE: {angle}"
            if stop_due_to_person:
                status += ' - PERSON DETECTED'

            cv2.putText(out, status, (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            cv2.imshow("camera", out)
            cv2.imshow("preprocess", pre)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == 32:
                if stop_due_to_person:
                    stop_due_to_person = False
                else:
                    drive = not drive
                print("DRIVE:", 'ON' if drive else 'OFF')

            if drive and not stop_due_to_person:
                motor_go(SET_MOTOR_SPEED)
            else:
                motor_stop()

            frame_count += 1

    finally:
        motor_stop()
        PWMA.value = 0.0
        PWMB.value = 0.0
        try:
            camera.release()
        except Exception:
            pass
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
```

