# USB Webcam + OpenCV Python 프로젝트 20선

## 사전 준비

```bash
# OpenCV 설치
pip install opencv-python opencv-contrib-python numpy

# USB 웹캠 연결 확인
lsusb
ls /dev/video*
v4l2-ctl --list-devices
```

```
gotree94@rp4ros-nwk:~ $ pip install opencv-python
error: externally-managed-environment

× This environment is externally managed
╰─> To install Python packages system-wide, try apt install
    python3-xyz, where xyz is the package you are trying to
    install.

    If you wish to install a non-Debian-packaged Python package,
    create a virtual environment using python3 -m venv path/to/venv.
    Then use path/to/venv/bin/python and path/to/venv/bin/pip. Make
    sure you have python3-full installed.

    For more information visit http://rptl.io/venv

note: If you believe this is a mistake, please contact your Python installation or OS distribution provider. You can override this, at the risk of breaking your Python installation or OS, by passing --break-system-packages.
hint: See PEP 668 for the detailed specification.
```

* 의미: Debian Bookworm/Trixie부터 시스템 파이썬 패키지를 pip으로 설치하면 OS 패키지 관리자(apt)와 충돌하는 걸 막기 위해 이 에러가 발생합니다.

* 해결 방법 3가지:
1. (권장) apt로 설치 — 시스템 패키지와 충돌 없음

```
sudo apt install python3-opencv
```

2. (권장) venv 가상환경 사용 — 프로젝트마다 독립 환경

```
python3 -m venv myenv
source myenv/bin/activate
pip install opencv-python
```

3. 강제 설치 (--break-system-packages) — 시스템 패키지 깨질 위험 있음

```
pip install opencv-python --break-system-packages로 넘어간다면,
```
향후 apt upgrade할 때 OpenCV 관련 의존성 충돌이 날 수 있습니다. 가상환경(venv) 또는 apt 추천합니다.


> 라즈베리파이 전용 카메라(CSI)는 `picamera2` 패키지 사용

---

## 1. 기본 웹캠 실시간 보기

```python
import cv2

cap = cv2.VideoCapture(0)  # 0: 첫 번째 USB 카메라
if not cap.isOpened():
    print("카메라를 열 수 없습니다")
    exit()

while True:
    ret, frame = cap.read()
    if not ret:
        break
    cv2.imshow("USB Camera", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
```

---

## 2. 카메라 화면 상하 뒤집기 (Flip)

```python
import cv2

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break
    flipped = cv2.flip(frame, 0)  # 0: 상하 뒤집기
    cv2.imshow("Flipped", flipped)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
```

---

## 3. 카메라 화면 좌우 반전 (Mirror)

```python
import cv2

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break
    mirrored = cv2.flip(frame, 1)  # 1: 좌우 반전
    cv2.imshow("Mirrored", mirrored)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
```

---

## 4. 그레이스케일 변환

```python
import cv2

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    cv2.imshow("Grayscale", gray)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
```

---

## 5. 스냅샷 저장하기

```python
import cv2
from datetime import datetime

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break
    cv2.imshow("Press SPACE to capture", frame)
    key = cv2.waitKey(1) & 0xFF
    if key == ord(' '):  # 스페이스바
        filename = f"snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        cv2.imwrite(filename, frame)
        print(f"저장됨: {filename}")
    elif key == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
```

---

## 6. 비디오 녹화하기

```python
import cv2
from datetime import datetime

cap = cv2.VideoCapture(0)
fps = 20.0
w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

filename = f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.avi"
fourcc = cv2.VideoWriter_fourcc(*'XVID')
out = cv2.VideoWriter(filename, fourcc, fps, (w, h))

recording = False

while True:
    ret, frame = cap.read()
    if not ret:
        break

    if recording:
        out.write(frame)
        cv2.circle(frame, (30, 30), 10, (0, 0, 255), -1)  # 녹화 표시
        cv2.putText(frame, "REC", (50, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

    cv2.imshow("Video Record", frame)
    key = cv2.waitKey(1) & 0xFF
    if key == ord('r'):
        recording = not recording
        print(f"녹화 {'시작' if recording else '중지'}")
    elif key == ord('q'):
        break

cap.release()
out.release()
cv2.destroyAllWindows()
```

---

## 7. Canny 에지 검출

```python
import cv2

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    cv2.imshow("Canny Edges", edges)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
```

---

## 8. 가우시안 블러 (노이즈 제거)

```python
import cv2

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break
    blurred = cv2.GaussianBlur(frame, (15, 15), 0)
    cv2.imshow("Blurred", blurred)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
```

---

## 9. 얼굴 검출 (Haar Cascade)

```bash
# Haar XML은 opencv 패키지에 포함되어 있음
# (haarcascade_frontalface_default.xml)
```

```python
import cv2

face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)
cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.1, 5)

    for (x, y, w, h) in faces:
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(frame, "Face", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, (0, 255, 0), 2)

    cv2.imshow("Face Detection", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
```

---

## 10. 프레임에 도형/텍스트 그리기

```python
import cv2

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    h, w = frame.shape[:2]

    # 사각형
    cv2.rectangle(frame, (50, 50), (w - 50, h - 50), (0, 255, 0), 2)
    # 원 (중앙)
    cv2.circle(frame, (w // 2, h // 2), 50, (0, 0, 255), 3)
    # 선 (십자)
    cv2.line(frame, (w // 2, 0), (w // 2, h), (255, 0, 0), 1)
    cv2.line(frame, (0, h // 2), (w, h // 2), (255, 0, 0), 1)
    # 텍스트
    cv2.putText(frame, "OpenCV Camera", (30, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)

    cv2.imshow("Draw", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
```

---

## 11. 색상 공간 변환 (HSV, LAB)

```python
import cv2

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    hsv_display = cv2.resize(hsv, (0, 0), fx=0.5, fy=0.5)
    lab_display = cv2.resize(lab, (0, 0), fx=0.5, fy=0.5)
    cv2.imshow("HSV", hsv_display)
    cv2.imshow("LAB", lab_display)
    cv2.imshow("Original", cv2.resize(frame, (0, 0), fx=0.5, fy=0.5))
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
```

---

## 12. 특정 색상 추적 (HSV 범위)

```python
import cv2
import numpy as np

cap = cv2.VideoCapture(0)

# 파란색 HSV 범위
lower_blue = np.array([100, 50, 50])
upper_blue = np.array([140, 255, 255])

while True:
    ret, frame = cap.read()
    if not ret:
        break
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, lower_blue, upper_blue)
    result = cv2.bitwise_and(frame, frame, mask=mask)

    cv2.imshow("Mask", mask)
    cv2.imshow("Result", result)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
```

---

## 13. 움직임 감지 (프레임 차이)

```python
import cv2

cap = cv2.VideoCapture(0)
ret, prev = cap.read()
prev_gray = cv2.cvtColor(prev, cv2.COLOR_BGR2GRAY)

while True:
    ret, frame = cap.read()
    if not ret:
        break
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    diff = cv2.absdiff(prev_gray, gray)
    thresh = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)[1]

    motion = cv2.countNonZero(thresh)
    cv2.putText(frame, f"Motion: {motion}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

    cv2.imshow("Motion Detection", frame)
    cv2.imshow("Diff", diff)

    prev_gray = gray
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
```

---

## 14. FPS 카운터 표시

```python
import cv2
import time

cap = cv2.VideoCapture(0)
prev_time = time.time()

while True:
    ret, frame = cap.read()
    if not ret:
        break

    curr_time = time.time()
    fps = 1 / (curr_time - prev_time)
    prev_time = curr_time

    cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
    cv2.imshow("FPS Counter", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
```

---

## 15. 카메라 전환 (여러 USB 카메라)

```python
import cv2

caps = [cv2.VideoCapture(i) for i in range(4)]
current = 0

while True:
    ret, frame = caps[current].read()
    if ret:
        cv2.imshow(f"Camera {current}", frame)

    key = cv2.waitKey(1) & 0xFF
    if ord('0') <= key <= ord('3'):
        current = key - ord('0')
        print(f"Camera {current} 선택됨")
    elif key == ord('q'):
        break

for c in caps:
    c.release()
cv2.destroyAllWindows()
```

---

## 16. 프레임 리사이즈

```python
import cv2

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break
    small = cv2.resize(frame, (320, 240))
    big = cv2.resize(frame, None, fx=1.5, fy=1.5)
    cv2.imshow("Original", cv2.resize(frame, (640, 480)))
    cv2.imshow("Small", small)
    cv2.imshow("Big", big)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
```

---

## 17. ROI 영역 자르기 (Crop)

```python
import cv2

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break
    h, w = frame.shape[:2]
    roi = frame[h // 4: 3 * h // 4, w // 4: 3 * w // 4]
    cv2.rectangle(frame, (w // 4, h // 4), (3 * w // 4, 3 * h // 4),
                  (0, 255, 0), 2)
    cv2.imshow("Frame", frame)
    cv2.imshow("ROI", roi)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
```

---

## 18. 이진화 처리 (Threshold)

```python
import cv2

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
    adaptive = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                     cv2.THRESH_BINARY, 11, 2)

    cv2.imshow("Binary", binary)
    cv2.imshow("Adaptive", adaptive)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
```

---

## 19. 컨투어 검출

```python
import cv2

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)

    cv2.drawContours(frame, contours, -1, (0, 255, 0), 2)
    cv2.putText(frame, f"Contours: {len(contours)}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    cv2.imshow("Contours", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
```

---

## 20. 히스토그램 평활화 (명암 보정)

```python
import cv2

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    equalized = cv2.equalizeHist(gray)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    clahe_result = clahe.apply(gray)

    cv2.imshow("Original", gray)
    cv2.imshow("Equalized", equalized)
    cv2.imshow("CLAHE", clahe_result)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
```

---

## 21. 크로마키 배경 합성

```python
import cv2
import numpy as np

cap = cv2.VideoCapture(0)
bg = cv2.imread("background.jpg")  # 배경 이미지 준비

while True:
    ret, frame = cap.read()
    if not ret:
        break
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    lower_green = np.array([40, 40, 40])
    upper_green = np.array([80, 255, 255])
    mask = cv2.inRange(hsv, lower_green, upper_green)
    mask_inv = cv2.bitwise_not(mask)

    fg = cv2.bitwise_and(frame, frame, mask=mask_inv)
    bg_resized = cv2.resize(bg, (frame.shape[1], frame.shape[0]))
    bk = cv2.bitwise_and(bg_resized, bg_resized, mask=mask)
    result = cv2.add(fg, bk)

    cv2.imshow("Chroma Key", result)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
```

---

## 22. PiCamera2 (라즈베리파이 CSI 카메라)

```bash
# picamera2 설치 (라즈베리파이 OS 전용)
sudo apt install python3-picamera2
```

```python
from picamera2 import Picamera2
import cv2
import numpy as np

picam = Picamera2()
picam.configure(picam.create_preview_configuration(
    main={"format": 'RGB888', "size": (640, 480)}))
picam.start()

while True:
    frame = picam.capture_array()
    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    cv2.imshow("PiCamera", frame)
    cv2.imshow("PiCamera Gray", gray)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

picam.stop()
cv2.destroyAllWindows()
```

## 22. PiCamera2 라이브러리를 이용해 opencv로 변환하는 코드 (라즈베리파이 CSI 카메라)

```python
from picamera2 import Picamera2 
import numpy as np

class MyPiCamera():

    def __init__(self,width,height):
        self.cap = Picamera2()

        self.width = width;
        self.height = height
        self.is_open = True

        try:
            self.config = self.cap.create_video_configuration(main={"format":"RGB888","size":(width,height)})
            self.cap.align_configuration(self.config)
            self.cap.configure(self.config)

            self.cap.start()
        except:
            self.is_open = False
        return
    
    def read(self,dst=None):
        if dst is  None:
            dst = np.empty((self.height, self.width, 3), dtype=np.uint8)

        if self.is_open:
            dst = self.cap.capture_array()
    
        return self.is_open,dst
    def isOpened(self):
        return self.is_open
    def release(self): 
        if self.is_open is True:
             self.cap.close()
        self.is_open = False
        return

if __name__ == "__main__":
    import cv2
    camera = MyPiCamera(640,480)

    while camera.isOpened():
        _, image = camera.read()
        cv2.imshow("mycamera", image)
        
        if cv2.waitKey(1) == ord('q'):
            break

    cv2.destroyAllWindows()

```

---

## 예제 요약표

| # | 예제 | 설명 |
|---|------|------|
| 1 | 기본 웹캠 보기 | 가장 기본적인 실시간 카메라 출력 |
| 2 | 상하 뒤집기 | `cv2.flip(frame, 0)` |
| 3 | 좌우 반전 | `cv2.flip(frame, 1)` 셀카 모드 |
| 4 | 그레이스케일 | `cv2.cvtColor(frame, COLOR_BGR2GRAY)` |
| 5 | 스냅샷 저장 | 스페이스바로 JPEG 저장 |
| 6 | 비디오 녹화 | `VideoWriter`로 AVI 저장 |
| 7 | Canny 에지 | 엣지 검출 기초 |
| 8 | 가우시안 블러 | 노이즈 제거 스무딩 |
| 9 | 얼굴 검출 | Haar Cascade 분류기 |
| 10 | 도형/텍스트 그리기 | 사각형, 원, 선, 글자 |
| 11 | HSV/LAB 변환 | 색상 공간 이해 |
| 12 | 색상 추적 | 특정 색상만 마스킹 |
| 13 | 움직임 감지 | 프레임 차이 기반 |
| 14 | FPS 표시 | 초당 프레임 수 |
| 15 | 카메라 전환 | 여러 USB 카메라 전환 |
| 16 | 리사이즈 | 프레임 확대/축소 |
| 17 | ROI 자르기 | 관심 영역 추출 |
| 18 | 이진화 | Threshold / Adaptive |
| 19 | 컨투어 검출 | 객체 외곽선 찾기 |
| 20 | 히스토그램 평활화 | 명암 대비 개선 (CLAHE) |
| 21 | 크로마키 합성 | 그린 스크린 배경 합성 |
| 22 | PiCamera2 | CSI 카메라 연동 |
