# 4-3 도형(네모, 세모) 및 색상 검출하기

## 1. 색상 검출하기

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



