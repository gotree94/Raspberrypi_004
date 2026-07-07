# 4-2 바코드 및 QR코드 검출하기

* 카메라 영상을 이용하여 바코드와 QR 코드를 인식하는 방법을 다룹니다.
* OpenCV와 외부 라이브러리를 활용해 코드 영역을 검출하고, 인식된 데이터를 출력 합니다.

## 1. 라이브러리 설치하기

```
pip install pyzbar
```

## 2. 바토드 QR 코드 만들기

* 구글에서 barcode genetaotr 또는 Qrcode Generator로 검색하면 많은 사이트에서 바코드 및 qr코드의 생성이 가능합니다.
* https://barcode.tec-it.com/en

### 2.1 바코드 및 QR코드 인식하기

* 4_2_1.py

```python
import mycamera
import cv2
from pyzbar import pyzbar

def read_barcodes(frame):
    barcodes = pyzbar.decode(frame)
    for barcode in barcodes:
        x, y, w, h = barcode.rect
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        barcode_data = barcode.data.decode('utf-8')
        barcode_type = barcode.type
        text = f"{barcode_data} ({barcode_type})"
        cv2.putText(frame, text, (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        print("Detected : ", text)
    return frame

if __name__ == "__main__":
    camera = mycamera.MyPiCamera(640, 480)

    while camera.isOpened():
        _, image = camera.read()
        image = cv2.flip(image, -1)
        image = read_barcodes(image)
        cv2.imshow("mycamera", image)

        if cv2.waitKey(1) == ord('q'):
            break

    cv2.destroyAllWindows()
```

```python
import cv2
from pyzbar import pyzbar

def read_barcodes(frame):
    barcodes = pyzbar.decode(frame)
    for barcode in barcodes:
        x, y, w, h = barcode.rect
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        barcode_data = barcode.data.decode('utf-8')
        barcode_type = barcode.type
        text = f"{barcode_data} ({barcode_type})"
        cv2.putText(frame, text, (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        print("Detected : ", text)
    return frame

if __name__ == "__main__":
    cam = cv2.VideoCapture(0)
    cam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    while cam.isOpened():
        _, image = cam.read()
        image = cv2.flip(image, -1)
        image = read_barcodes(image)
        cv2.imshow("mycamera", image)

        if cv2.waitKey(1) == ord('q'):
            break

    cv2.destroyAllWindows()
```

### 2.2 인식한 조건으로 LED 제어하기

* 4_2_2.py

```python
import mycamera
import cv2
from pyzbar import pyzbar
from gpiozero import LEDBoard

leds = LEDBoard(26, 16, 20, 27)

def read_barcodes(frame):
    barcodes = pyzbar.decode(frame)
    for barcode in barcodes:
        x, y, w, h = barcode.rect
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        data = barcode.data.decode('utf-8')
        cv2.putText(frame, data, (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        print("Detected : ", data)
        if data.lower() == "ledon":
            leds.on()
        elif data.lower() == "ledoff":
            leds.off()
    return frame

if __name__ == "__main__":
    camera = mycamera.MyPiCamera(640, 480)
    while camera.isOpened():
        _, image = camera.read()
        image = cv2.flip(image, -1)
        image = read_barcodes(image)
        cv2.imshow("mycamera", image)

        if cv2.waitKey(1) == ord('q'):
            break

    cv2.destroyAllWindows()
    leds.off()
```

```python
import cv2
from pyzbar import pyzbar
from gpiozero import LEDBoard

leds = LEDBoard(26, 16, 20, 27)

def read_barcodes(frame):
    barcodes = pyzbar.decode(frame)
    for barcode in barcodes:
        x, y, w, h = barcode.rect
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        data = barcode.data.decode('utf-8')
        cv2.putText(frame, data, (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        print("Detected : ", data)
        if data.lower() == "ledon":
            leds.on()
        elif data.lower() == "ledoff":
            leds.off()
    return frame

if __name__ == "__main__":
    cam = cv2.VideoCapture(0)
    cam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    while cam.isOpened():
        _, image = cam.read()
        image = cv2.flip(image, -1)
        image = read_barcodes(image)
        cv2.imshow("mycamera", image)

        if cv2.waitKey(1) == ord('q'):
            break

    cv2.destroyAllWindows()
    leds.off()
```



