# 8-3 모델 불러와 테스트하기

*  라즈베리파이에서 학습된 모델을 불러와 예측 결과를 테스트 합니다.
*  카메라 영상을 입력으로 받아 모델의 출력 결과를 화면에 표시합니다.

## 모델 불러오기

* 저장왼 PyTorch모델을 불러와 정상적으로 동작하는지 테스트하는 코드를 작성합니다.
* 모델을 불러온 되 더미 입력을 넣어 출력을 확인함으로써 모델 로드가 성공했는지 검증합니다.

* 8_3_1.py

``` python
import torch

MODEL_PATH = "/home/pi/AI_CAR/model/lane_navigation_final.torchscript"

def main():
    model = torch.jit.load(MODEL_PATH, map_location="cpu")
    model.eval()
    torch.set_num_threads(1)
    x = torch.zeros(1, 3, 66, 200, dtype=torch.float32)
    with torch.no_grad():
        y = model(x)
    print('model_loaded:', type(model).__name__)
    print("dry_run_output: ", float(y.view(-1)[0].item()))

if __name__ == "__main__":
    main()
```

```python
import torch

MODEL_PATH = "model-20260714_231443\\lane_navigation_final.torchscript"

def main():
    model = torch.jit.load(MODEL_PATH, map_location="cpu")
    model.eval()
    torch.set_num_threads(1)
    x = torch.zeros(1, 3, 66, 200, dtype=torch.float32)
    with torch.no_grad():
        y = model(x)
    print('model_loaded:', type(model).__name__)
    print("dry_run_output: ", float(y.view(-1)[0].item()))

if __name__ == "__main__":
    main()
```

```
(base) C:\Users\Administrator\Desktop\recordings>python 8_3_1.py
model_loaded: RecursiveScriptModule
dry_run_output:  -35.81206130981445
```

## 불로온 모델을 이용해서 각도 예측하기

* 8_3_2.py

```python
import mycamera
import torch
import cv2
import numpy as np

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

            angle = int(float(y.item()))
            print('predict angle:', angle)

            cv2.imshow("camera", image)
            cv2.imshow('preprocess', pre)

    finally:
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
```

```python
#import mycamera
import torch
import cv2
import numpy as np

MODEL_PATH = "model-20260714_231443\\lane_navigation_final.torchscript"

clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

def img_preprocess(image):
    h, w, c = image.shape
    image = image[:h//2, :, :]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray_eq = clahe.apply(gray)
    inv = 255 - gray_eq
    inv_eq = clahe.apply(inv)
    blurred = cv2.GaussianBlur(inv_eq, (3, 3), 0)
    resized = cv2.resize(blurred, (200, 66))
    img = resized.astype(np.float32) / 255.0
    return img

def main():
    #camera = mycamera.MyPiCamera(640, 480)
    camera = cv2.VideoCapture(0)
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
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
            x = pre.transpose(2, 0, 1)
            x = np.expand_dims(x, axis=0)
            x_tensor = torch.from_numpy(x).float()

            with torch.no_grad():
                y = model(x_tensor)

            angle = int(float(y.item()))
            print('predict angle:', angle)

            cv2.imshow("camera", image)
            cv2.imshow('preprocess', (pre * 255).astype(np.uint8))

    finally:
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
```





