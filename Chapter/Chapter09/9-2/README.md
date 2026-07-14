# 9-2 신호등, 보행자, 횡단보도 학습하여 사용자 모델만들기

* 자율주행 환경에 특화된 사용자 정의 객체 인식 모델(Custom Model)을 제작합니다.
* 신호등, 보항자, 횡단보도 등 교통 관련 객체를 중심으로 데이터를 수집하고 라벨링 한 후, <br>
  YOLOv8을 이용해 직접 학습을 진행합니다.
* 이를 통해 학습자는 데이터셋 준비, 학습 파아미터 설정, 모델 평가 등의 과정을 체계적으로 경함하고, <br>
  자신만의 인공지능 모델으 완성할 수 있습니다.

## 라즈베리파이에서 버튼을 눌러 사진 찍어 저장하기

* 라즈베리파이 카메라로 실시간 영상을 표시하고,
* 사용자가 's'키를 누르면 이미지를 저장. 'q'키를 누르면 종료하는 프로그램을 작서합니다.

* 9_2_1.py

```python
import os
from datetime import datetime
import cv2
import mycamera

SAVE_DIR = os.path.join(os.path.dirname(__file__), "pictures")
os.makedirs(SAVE_DIR, exist_ok=True)

if __name__ == "__main__":
    camera = mycamera.MyPiCamera(640, 480)
    while camera.isOpened():
        ok, image = camera.read()
        if not ok:
            break
        image = cv2.flip(image, -1)
        cv2.imshow("mycamera", image)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('s'):
            filename = datetime.now().strftime("%Y%m%d_%H%M%S_%f") + ".png"
            path = os.path.join(SAVE_DIR, filename)
            cv2.imwrite(path, image)
            print(f'saved: {path}')
        elif key == ord('q'):
            break

    cv2.destroyAllWindows()
```

```python
import os
from datetime import datetime
import cv2
#import mycamera

SAVE_DIR = os.path.join(os.path.dirname(__file__), "pictures")
os.makedirs(SAVE_DIR, exist_ok=True)

if __name__ == "__main__":
    #camera = mycamera.MyPiCamera(640, 480)
    camera = cv2.VideoCapture(0)
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)    
    while camera.isOpened():
        ok, image = camera.read()
        if not ok:
            break
        #image = cv2.flip(image, -1)
        cv2.imshow("mycamera", image)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('s'):
            filename = datetime.now().strftime("%Y%m%d_%H%M%S_%f") + ".png"
            path = os.path.join(SAVE_DIR, filename)
            cv2.imwrite(path, image)
            print(f'saved: {path}')
        elif key == ord('q'):
            break

    cv2.destroyAllWindows()
```

## 압축하기

* 9_2_2.py

```python
import os
import zipfile

def zip_pictures_folder():
    base_dir = os.path.dirname(__file__)
    pictures_dir = os.path.join(base_dir, "pictures")
    zip_path = os.path.join(base_dir, "pictures.zip")

    if not os.path.exists(pictures_dir):
        print("pictures folder not found.")
        return

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(pictures_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, pictures_dir)
                zipf.write(file_path, arcname)

    print(f"zip created: {zip_path}")

if __name__ == "__main__":
    zip_pictures_folder()

```

## 데이터 라벨링 : Page 331 ~ 

* 저장된 사진에서 객체를 라벨링 합니다. 라벨링 작업은 객체의 정잡을 부여하는 과정으로 사람이 수작업으로 진행합니다.
* https://github.com/HumanSignal/labelImg
* https://github.com/HumanSignal/labelImg/releases
* https://github.com/HumanSignal/labelImg/archive/refs/tags/v1.8.1.zip

* predefined_classes.tx

```
person
crosswalk
traffic_lights_red
traffic_lights_yellow
traffic-lights-greenl
```

---

## 로컬 학습 방법

```
from ultralytics import YOLO

# 1. 사전 학습된 모델 로드
model = YOLO('yolov8n.pt')

# 2. 나만의 데이터셋으로 학습
model.train(data='my_dataset.yaml', epochs=50, imgsz=640)
```

* 데이터셋 준비 : /path/to/dataset 업데이트 후 사용

```
my_dataset.yaml:

path: /path/to/dataset
train: images/train
val: images/val
names:
  0: car
  1: person
  2: lane
```

```
디렉토리 구조:

dataset/
├── images/
│   ├── train/
│   └── val/
├── labels/
│   ├── train/
│   └── val/
└── my_dataset.yaml
```

* 라벨링 도구 (무료)
   * LabelImg	간편, 바운딩박스
   * CVAT	고급, 다양한 어노테이션
   * Roboflow	웹에서 라벨링 + 학습

* 추천 순서
   * 이미지 수집 (200장 이상)
   * LabelImg으로 라벨링
   * 로컬에서 model.train() 실행


## 최종목표

  * ai_car_model.pt 모델 만들기

---

## Google Colab에서 YOLO 학습하기

### 1. Colab 접속

https://colab.research.google.com

### 2. GPU 설정

런타임 → 런타임 유형 변경 → GPU 선택

### 3. 학습 코드

```
# 1. ultralytics 설치
!pip install ultralytics

# 2. Google Drive 마운트
from google.colab import drive
drive.mount('/content/drive')

# 3. 데이터셋 경로 설정
%cd /content/drive/MyDrive/yolo_dataset

# 4. 학습 실행
from ultralytics import YOLO

model = YOLO('yolov8n.pt')
model.train(
    data='my_dataset.yaml',
    epochs=50,
    imgsz=640,
    batch=16
)
```

### 4. 학습 결과 확인

```
# 학습 결과 폴더 확인
!ls runs/detect/train/

# 학습 그래프 보기
from IPython.display import Image
Image(filename='runs/detect/train/results.png')
```

### 5. 모델 다운로드

```
# Google Drive로 복사
!cp runs/detect/train/weights/best.pt /content/drive/MyDrive/
Google Drive 디렉토리 구조
MyDrive/
└── yolo_dataset/
    ├── my_dataset.yaml
    ├── images/
    │   ├── train/
    │   └── val/
    └── labels/
        ├── train/
        └── val/
```

---

## 사용 이미지


![](Slide1.PNG)

![](Slide2.PNG)

![](Slide3.PNG)

---

# 라즈베리파이 4용 YOLOv8 Nano + NCNN 실시간 객체 인식 가이드

이 가이드는 라즈베리파이 4(Raspberry Pi 4) 환경에서 '사람'과 '신호등'을 실시간으로 감지하기 위해 **YOLOv8 Nano** 모델을 고성능 ARM CPU 최적화 엔진인 **NCNN** 포맷으로 변환하고 실행하는 전체 과정을 다룹니다.

---

## 📋 전체 작업 흐름도

```text
[1단계: 64비트 OS 확인] ──> [2단계: 패키지 설치] ──> [3단계: NCNN 변환] ──> [4단계: 추론 코드 작성] ──> [5단계: 최적화 실행]
```

---

## 1단계: OS 환경 확인 (64비트 필수)

라즈베리파이 4의 CPU 성능을 최대한 끌어올리려면 반드시 **64비트(64-bit) OS**를 사용해야 합니다. 32비트 OS 환경에서는 연산 속도가 매우 느리며 라이브러리 호환성 문제가 발생할 수 있습니다.

1. 라즈베리파이 터미널을 열고 아래 명령어를 입력합니다.
   ```bash
   uname -m
   ```
2. 출력 결과가 **`aarch64`**이면 64비트 OS입니다. 
   *(만약 `armv7l` 등 32비트 환경으로 나온다면, Raspberry Pi OS 64-bit 버전을 새로 설치하는 것을 강력하게 권장합니다.)*

---

## 2단계: 가상환경 생성 및 패키지 설치

시스템 라이브러리와의 충돌을 방지하기 위해 파이썬 가상환경(venv)을 구성하고, 필수 인공지능 패키지를 설치합니다.

```bash
# 1. 시스템 패키지 업데이트
sudo apt update && sudo apt upgrade -y

# 2. 작업 폴더 생성 및 이동
mkdir ~/yolo_project && cd ~/yolo_project

# 3. 파이썬 가상환경 생성 및 활성화
python3 -m venv venv
source venv/bin/activate

# 4. 필수 라이브러리 및 추론 엔진 설치
pip install --upgrade pip
pip install ultralytics ncnn opencv-python
```

---

## 3단계: YOLOv8 Nano -> NCNN 모델 변환

파이토치 기본 포맷(`.pt`) 모델을 라즈베리파이 CPU에서 빠르게 동작하는 **NCNN** 포맷으로 변환합니다. 이 작업은 라즈베리파이에서 직접 수행하거나 성능이 좋은 PC에서 변환 후 파일만 복사해 와도 됩니다.

터미널에서 가상환경이 활성화된 상태로 파이썬 대화형 인터프리터나 스크립트를 통해 아래 코드를 실행합니다.

```python
# python3 실행 후 아래 코드 입력
from ultralytics import YOLO

# 1. 온라인에서 기본 YOLOv8n 가중치 파일 다운로드
model = YOLO("yolov8n.pt")

# 2. NCNN 포맷으로 최적화 변환 진행
model.export(format="ncnn")
```

* **결과물:** 변환이 완료되면 작업 디렉토리에 **`yolov8n_ncnn_model/`** 이라는 이름의 폴더가 생성됩니다. 이 폴더 통째로 추론 코드와 같은 위치에 두어야 합니다.

---

## 4단계: 실시간 카메라 인식 코드 작성 (`detect.py`)

카메라로부터 실시간 영상을 입력받아 NCNN 모델로 추론하고, '사람(ID: 0)'과 '신호등(ID: 9)'만 골라 화면에 박스를 쳐주는 핵심 파이썬 코드입니다.

`~/yolo_project` 폴더 안에 **`detect.py`** 파일을 생성하고 아래 코드를 저장하세요.

```python
import cv2
from ultralytics import YOLO

# 1. NCNN으로 경량 변환된 모델 폴더 로드
model = YOLO("yolov8n_ncnn_model")

# 2. 카메라 연결 (일반 USB 웹캠: 0, 라즈베리파이 전용 카메라 모듈: 환경에 맞게 인덱스 조정)
cap = cv2.VideoCapture(0)

# 프레임 저하를 방지하기 위해 카메라 입력 해상도를 낮게 설정 (기본 해상도는 너무 무거움)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# COCO 데이터셋 클래스 필터링 (0: person, 9: traffic light)
TARGET_CLASSES = [0, 9]

print("=========================================")
print("실시간 객체 인식을 시작합니다... (종료: 'q' 키)")
print("=========================================")

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        print("카메라에서 영상을 읽을 수 없습니다.")
        break

    # 추론 속도 극대화를 위해 모델 입력 크기(imgsz)를 320x320으로 설정
    # conf(임계값)를 조절하여 인식 민감도 제어 가능
    results = model(
        frame, 
        imgsz=320, 
        conf=0.25, 
        classes=TARGET_CLASSES, 
        verbose=False
    )

    # 인식된 객체 바운딩 박스가 렌더링된 프레임 가져오기
    annotated_frame = results[0].plot()

    # 결과 화면 출력
    cv2.imshow("RPi4 - YOLOv8 NCNN Object Detection", annotated_frame)

    # 'q' 키를 누르면 루프 탈출 및 종료
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# 자원 해제
cap.release()
cv2.destroyAllWindows()
```

---

## 5단계: 실행 및 성능 최적화 꿀팁

### 실행하기
가상환경이 활성화된 상태에서 아래 명령어로 실시간 검출을 구동합니다.
```bash
python detect.py
```

### ⚡ 프레임률(FPS) 향상을 위한 팁
라즈베리파이 4의 물리적 한계를 극복하기 위한 몇 가지 세부 설정법입니다.

1. **모델 해상도 축소 (`imgsz` 조정):**
   * 코드 내 `imgsz=320`을 `imgsz=256` 혹은 `imgsz=192`로 줄여보세요. 화면 왜곡은 생기지만 연산량이 대폭 감소해 FPS가 비약적으로 올라갑니다.
2. **라즈베리파이 오버클러킹 (선택):**
   * 방열판과 쿨링팬이 장착되어 있다면 CPU 클럭을 기본 `1.5GHz`에서 `1.8GHz` ~ `2.0GHz`로 오버클러킹하여 추론 속도를 20~30% 더 높일 수 있습니다.
3. **OpenCV 버퍼 관리:**
   * 실시간성이 중요하므로 카메라 큐 버퍼 사이즈를 제한하거나 프레임을 1~2개씩 건너뛰며 추론(Skip-Frame)하는 구조를 추가하면 화면이 밀리는 현상을 원천 방지할 수 있습니다.
