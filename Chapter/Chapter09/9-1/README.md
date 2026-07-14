# 9-1 YOLOv8로 객체 검출하기

* YOLOv8 모델을 이용하여 다양한 객체를 검출하는 방법을 학습합니다.
* Ultralystics 라이브러리를 설치하고, 사전 학습된 YOLOv8 모델을 불러와 카메라 영상에서 사람, 자동차, 신호등 등의 객체를 인식합니다.

## 라이브러리 확인

* 설치된 주요 라이브러리(OpenCV, PyTorch, Ultralystic, Numpy)의 버전을 확인하른 코드를 작성합니다.

* 9_1_1.py

```Bash
pip install ultralytics
```

```python
import cv2
import torch
import ultralytics
import numpy

print("cv2:", cv2.__version__)
print("torch:", torch.__version__)
print("ultralytics:", ultralytics.__version__)
print("numpy:", numpy.__version__)
```

```
Creating new Ultralytics Settings v0.0.6 file
View Ultralytics Settings with 'yolo settings' or at 'C:\Users\Administrator\AppData\Roaming\Ultralytics\settings.json'
Update Settings with 'yolo settings key=value', i.e. 'yolo settings runs_dir=path/to/dir'. For help see https://docs.ultralytics.com/quickstart/#ultralytics-settings.
cv2: 4.11.0
torch: 2.6.0+cu124
ultralytics: 8.4.95
numpy: 1.26.4
```

## 기본 예제로 객체 검출하기

* YOLOv8 모델을 이용해 라즈베리파이 카메라로 실시간 객체 검출하고,
* 검출된 객체의 이름과 확률을 화면에 표시하는 기본 프로그램을 작성합니다.

* 9_1_2.py

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
    model = YOLO("yolov8n.pt")
    camera = mycamera.MyPiCamera(640, 480)
    try:
        while camera.isOpened():
            ok, frame = camera.read()
            if not ok:
                break
            frame = cv2.flip(frame, -1)
            results = model(frame, imgsz=320, conf=0.5, iou=0.5, device='cpu')[0]
            out = draw_detections(frame, results, model.names)
            cv2.imshow('YOLOv8 (mycamera)', out)
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
    model = YOLO("yolov8n.pt")
    #camera = mycamera.MyPiCamera(640, 480)
    camera = cv2.VideoCapture(0)
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    try:
        while camera.isOpened():
            ok, frame = camera.read()
            if not ok:
                break
            #frame = cv2.flip(frame, -1)
            results = model(frame, imgsz=320, conf=0.5, iou=0.5, device='cpu')[0]
            out = draw_detections(frame, results, model.names)
            cv2.imshow('YOLOv8 (mycamera)', out)
            if cv2.waitKey(1) == ord('q'):
                break
    finally:
        try:
            camera.release()
        except Exception:
            pass
        cv2.destroyAllWindows()
```

```
Downloading https://github.com/ultralytics/assets/releases/download/v8.4.0/yolov8n.pt to 'yolov8n.pt': 100% ━━━━━━━━━━━━ 6.2MB 7.3MB/s 0.9s
Traceback (most recent call last):

0: 256x320 (no detections), 82.7ms
Speed: 2.1ms preprocess, 82.7ms inference, 1.0ms postprocess per image at shape (1, 3, 256, 320)

0: 256x320 (no detections), 33.0ms
Speed: 1.0ms preprocess, 33.0ms inference, 0.5ms postprocess per image at shape (1, 3, 256, 320)

0: 256x320 (no detections), 28.4ms
Speed: 0.9ms preprocess, 28.4ms inference, 0.6ms postprocess per image at shape (1, 3, 256, 320)

0: 256x320 (no detections), 29.8ms
Speed: 0.7ms preprocess, 29.8ms inference, 0.6ms postprocess per image at shape (1, 3, 256, 320)
```


## 검출된 객체로 조건 설정하여 부저 울리기

* 사람이 검출되면 자동차의 부저를 울리는 코드를 작성합니다.

* 9_1_3.py

```python
import mycamera
import cv2
import torch
from ultralytics import YOLO
from gpiozero import PWMOutputDevice
import time

def beep_twice(buzzer):
    freqs = [1000, 1500]
    for f in freqs:
        buzzer.frequency = f
        buzzer.value = 0.5
        time.sleep(0.2)
        buzzer.value = 0
        time.sleep(0.1)

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
    model = YOLO('yolov8n.pt')
    camera = mycamera.MyPiCamera(640, 480)
    buzzer = PWMOutputDevice(12)
    prev_detected = False

    try:
        while camera.isOpened():
            ok, frame = camera.read()
            if not ok:
                break

            frame = cv2.flip(frame, -1)
            results = model(frame, imgsz=320, conf=0.5, iou=0.5, device='cpu')[0]
            person_detected = any(int(b.cls.item()) == 0 for b in results.boxes)

            if person_detected and not prev_detected:
                beep_twice(buzzer)

            prev_detected = person_detected
            out = draw_detections(frame, results, model.names)
            cv2.imshow('YOLOv8 (buzzer)', out)

            if cv2.waitKey(1) == ord('q'):
                break
    finally:
        buzzer.value = 0
        camera.release()
        cv2.destroyAllWindows()
```

```python
#import mycamera
import cv2
import torch
from ultralytics import YOLO
from gpiozero import PWMOutputDevice
import time

def beep_twice(buzzer):
    freqs = [1000, 1500]
    for f in freqs:
        buzzer.frequency = f
        buzzer.value = 0.5
        time.sleep(0.2)
        buzzer.value = 0
        time.sleep(0.1)

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
    model = YOLO('yolov8n.pt')
    #camera = mycamera.MyPiCamera(640, 480)
    camera = cv2.VideoCapture(0)
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    buzzer = PWMOutputDevice(12)
    prev_detected = False

    try:
        while camera.isOpened():
            ok, frame = camera.read()
            if not ok:
                break

            #frame = cv2.flip(frame, -1)
            results = model(frame, imgsz=320, conf=0.5, iou=0.5, device='cpu')[0]
            person_detected = any(int(b.cls.item()) == 0 for b in results.boxes)

            if person_detected and not prev_detected:
                beep_twice(buzzer)

            prev_detected = person_detected
            out = draw_detections(frame, results, model.names)
            cv2.imshow('YOLOv8 (buzzer)', out)

            if cv2.waitKey(1) == ord('q'):
                break
    finally:
        buzzer.value = 0
        camera.release()
        cv2.destroyAllWindows()
```

