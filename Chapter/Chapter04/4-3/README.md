# 4-3 도형(네모, 세모) 및 색상 검출하기

* 영상 내 다양한 기본 도형을 인식하는 방법을 학습합니다.
* 에지 검출과 윤곽선 분석을 통해 사각형, 원, 삼각형 등의 형태를 구분하고 표시합니다.
* 도형 인식을 통해 형태 기반 영상 분석의 원리를 이해하며, 객체 탐지의 기초 개념을 실습니다.


## 1. 색상 검출하기

* 영상에서 빨간색과 파란색 영역을 HSV 색 공간을 이요해 검출하고 시각적으로 표시하는 프로그램을 작성합니다.

### 4_3_1.py

```python
import mycamera
import cv2
import numpy as np

if __name__ == "__main__":
    cam = mycamera.MyPiCamera(640, 480)
    while cam.isOpened():
        _, img = cam.read()
        img = cv2.flip(img, -1)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        red = cv2.inRange(hsv, (0, 120, 70), (10, 255, 255)) | cv2.inRange(hsv, (170, 120, 70), (180, 255, 255))
        blue = cv2.inRange(hsv, (100, 120, 70), (140, 255, 255))

        red = cv2.medianBlur(red, 5)
        blue = cv2.medianBlur(blue, 5)

        red_view = cv2.bitwise_and(img, img, mask=red)
        blue_view = cv2.bitwise_and(img, img, mask=blue)

        cv2.imshow("original", img)
        cv2.imshow("red", red_view)
        cv2.imshow("blue", blue_view)

        if cv2.waitKey(1) == ord('q'):
            break

cv2.destroyAllWindows()
```

```python
import cv2
import numpy as np

if __name__ == "__main__":
    cam = cv2.VideoCapture(0)
    cam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    while cam.isOpened():
        _, img = cam.read()
        img = cv2.flip(img, 1)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        red = cv2.inRange(hsv, (0, 120, 70), (10, 255, 255)) | cv2.inRange(hsv, (170, 120, 70), (180, 255, 255))
        blue = cv2.inRange(hsv, (100, 120, 70), (140, 255, 255))

        red = cv2.medianBlur(red, 5)
        blue = cv2.medianBlur(blue, 5)

        red_view = cv2.bitwise_and(img, img, mask=red)
        blue_view = cv2.bitwise_and(img, img, mask=blue)

        cv2.imshow("original", img)
        cv2.imshow("red", red_view)
        cv2.imshow("blue", blue_view)

        if cv2.waitKey(1) == ord('q'):
            cam.release()
            break

cv2.destroyAllWindows()
```

## 2. 도형 인식하기

### 4_3_2.py

```python
import mycamera
import cv2
import numpy as np

def detect_shapes(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 60, 150)
    cnts, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for c in cnts:
        area = cv2.contourArea(c)
        if area < 800:
            continue
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        x, y, w, h = cv2.boundingRect(approx)
        shape = "unknown"
        if len(approx) == 3:
            shape = "triangle"
        elif len(approx) == 4:
            ratio = w / float(h)
            shape = "square" if 0.9 <= ratio <= 1.1 else "rectangle"
        elif len(approx) > 6:
            shape = "circle"
        if shape != "unknown":
            cv2.drawContours(frame, [approx], -1, (0, 255, 0), 2)
            cv2.putText(frame, shape, (x, y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    return frame

if __name__ == "__main__":
    cam = mycamera.MyPiCamera(640, 480)
    while cam.isOpened():
        _, img = cam.read()
        img = cv2.flip(img, -1)
        result = detect_shapes(img)
        cv2.imshow("shapes", result)
        if cv2.waitKey(1) == ord('q'):
            break
cv2.destroyAllWindows()
```

```python
import cv2
import numpy as np

def detect_shapes(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 60, 150)
    cnts, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for c in cnts:
        area = cv2.contourArea(c)
        if area < 800:
            continue
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        x, y, w, h = cv2.boundingRect(approx)
        shape = "unknown"
        if len(approx) == 3:
            shape = "triangle"
        elif len(approx) == 4:
            ratio = w / float(h)
            shape = "square" if 0.9 <= ratio <= 1.1 else "rectangle"
        elif len(approx) > 6:
            shape = "circle"
        if shape != "unknown":
            cv2.drawContours(frame, [approx], -1, (0, 255, 0), 2)
            cv2.putText(frame, shape, (x, y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    return frame

if __name__ == "__main__":
    cam = cv2.VideoCapture(0)
    cam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    while cam.isOpened():
        _, img = cam.read()
        img = cv2.flip(img, 1)
        result = detect_shapes(img)
        cv2.imshow("shapes", result)
        if cv2.waitKey(1) == ord('q'):
            break
cv2.destroyAllWindows()
```

## 3. 도형 및 색상 인식하기

### 4_3_3.py

```python
import mycamera
import cv2
import numpy as np

def detect(frame):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    red = cv2.inRange(hsv, (0, 120, 70), (10, 255, 255)) | cv2.inRange(hsv, (170, 120, 70), (180, 255, 255))
    blue = cv2.inRange(hsv, (100, 120, 70), (140, 255, 255))
    for name, mask, color in [("red", red, (0, 0, 255)), ("blue", blue, (255, 0, 0))]:
        cnts, _ = cv2.findContours(cv2.medianBlur(mask, 5), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in cnts:
            if cv2.contourArea(c) < 800:
                continue
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.07 * peri, True)
            x, y, w, h = cv2.boundingRect(approx)
            if name == "red" and len(approx) == 4 and 0.85 <= w / float(h) <= 1.15:
                cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                cv2.putText(frame, "red square", (x, y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                cv2.drawContours(frame, [approx], -1, color, 2)
            if name == "blue" and len(approx) == 3:
                cx = x + w // 2
                cy = y + h // 2
                cv2.putText(frame, "blue triangle", (cx - 60, cy - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                cv2.drawContours(frame, [approx], -1, color, 2)
    return frame

if __name__ == "__main__":
    cam = mycamera.MyPiCamera(640, 480)
    while cam.isOpened():
        _, img = cam.read()
        img = cv2.flip(img, -1)
        cv2.imshow("shapes", detect(img))
        if cv2.waitKey(1) == ord('q'):
            break
cv2.destroyAllWindows()
```

```python
import cv2
import numpy as np

def detect(frame):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    red = cv2.inRange(hsv, (0, 120, 70), (10, 255, 255)) | cv2.inRange(hsv, (170, 120, 70), (180, 255, 255))
    blue = cv2.inRange(hsv, (100, 120, 70), (140, 255, 255))
    for name, mask, color in [("red", red, (0, 0, 255)), ("blue", blue, (255, 0, 0))]:
        cnts, _ = cv2.findContours(cv2.medianBlur(mask, 5), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in cnts:
            if cv2.contourArea(c) < 800:
                continue
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.07 * peri, True)
            x, y, w, h = cv2.boundingRect(approx)
            if name == "red" and len(approx) == 4 and 0.85 <= w / float(h) <= 1.15:
                cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                cv2.putText(frame, "red square", (x, y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                cv2.drawContours(frame, [approx], -1, color, 2)
            if name == "blue" and len(approx) == 3:
                cx = x + w // 2
                cy = y + h // 2
                cv2.putText(frame, "blue triangle", (cx - 60, cy - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                cv2.drawContours(frame, [approx], -1, color, 2)
    return frame

if __name__ == "__main__":
    cam = cv2.VideoCapture(0)
    cam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    while cam.isOpened():
        _, img = cam.read()
        img = cv2.flip(img, 1)
        cv2.imshow("shapes", detect(img))
        if cv2.waitKey(1) == ord('q'):
            break
cv2.destroyAllWindows()
```

---

## HSV 색 공간(Hue, Saturation, Value)

> HSV 색 공간(Hue, Saturation, Value)은 색을 색상(H), 채도(S), 명도(V)라는 세 가지 요소로 표현하는 색 공간(Color Space)입니다. >
> RGB보다 사람이 색을 인식하는 방식에 더 가깝기 때문에 이미지 처리와 컴퓨터 비전에서 널리 사용됩니다.

### HSV의 세 요소
1. H (Hue, 색상)
   * 어떤 색인지 나타냅니다.
   * 일반적으로 **0° ~ 360°**의 각도로 표현됩니다.
      * 0° : 빨강
      * 60° : 노랑
      * 120° : 초록
      * 180° : 시안
      * 240° : 파랑
      * 300° : 자홍
   * 일부 라이브러리(예: OpenCV)는 8비트 표현을 위해 0~179 범위를 사용합니다.
2. S (Saturation, 채도)
   * 색이 얼마나 선명한지를 나타냅니다.
   * 범위: 0~1 또는 0~100%
   * 예시
      * S = 0 → 회색(무채색)
      * S = 1 → 가장 선명한 색

3. V (Value, 명도)
   * 색의 밝기를 나타냅니다.
   * 범위: 0~1 또는 0~100%
   * 예시
      * V = 0 → 검정
      * ㅜV = 1 → 가장 밝은 상태

* 예시

| HSV	|  결과 |
|:------:|:------:|
| (0°, 100%, 100%)	 |선명한 빨강 | 
| (120°, 100%, 100%)	 |선명한 초록 | 
| (240°, 100%, 100%)	 |선명한 파랑 | 
| (0°, 0%, 100%)	 |흰색 | 
| (0°, 0%, 50%)	 |회색 |
| (아무 색상, 아무 채도, 0%)	 |검정 |

### RGB와의 차이

| RGB	| HSV | 
|:------:|:------:|
| 빨강, 초록, 파랑의 양으로 색 표현	| 색상, 채도, 명도로 표현 | 
| 컴퓨터가 표현하기 쉬움	| 사람이 이해하기 쉬움 | 
| 밝기 변화에 민감	| 색상(H)과 밝기(V)가 분리되어 처리하기 편리 | 

* 예를 들어 빨간색 물체만 찾고 싶다면 RGB에서는 세 채널(R, G, B)을 모두 고려해야 하지만,
* HSV에서는 Hue(색상) 범위만 지정하면 되므로 색상 검출이 훨씬 간단합니다.
* 그래서 컴퓨터 비전 라이브러리인 OpenCV에서도 HSV를 이용한 색상 분할(color segmentation)이 매우 흔합니다.

### HSV를 사용하는 대표적인 분야
   * 📷 영상 처리 및 컴퓨터 비전
   * 🎨 그래픽 편집 프로그램의 색상 선택기
   * 🤖 로봇의 색상 인식
   * 🚗 자율주행에서 신호등·차선 색상 검출
   * 📸 특정 색상 객체 추적

### 요약하면, 
   * HSV 색 공간은 "어떤 색(H)", "얼마나 선명한가(S)", "얼마나 밝은가(V)"를 각각 독립적으로 표현하는 색 공간이며,
   * 사람의 색 인식 방식과 유사해 색상 분석과 영상 처리에 매우 유용합니다.

