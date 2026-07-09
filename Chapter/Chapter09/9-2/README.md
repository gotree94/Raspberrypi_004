# 9-2 신호등, 보행자, 횡단보도 학습하여 사용자 모델만들기

* 자율주행 환경에 특화된 사용자 정의 객체 인식 모델(Custom Model)을 제작합니다.
* 신호등, 보항자, 횡단보도 등 교ㅕ통 관련 객체를 중심으로 데이터를 수집하고 라벨링 한 후, <br>
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
SAVE_DIR = os.path. join(os.path.dirname(__fite__), "pi-ctures")
os.makedirs(SAVE_DIR, exist_ok=True)
if
__name-- =="__main-_" :
camera = mycamera.l,lyPicamera(640, 480)
while camera. isOpenedO :
ok, image = camera.reado
if not ok:
break
image = cv2.flip(image, -1)
cv2. imshow("mycamera", image)
key = 6v2."ritKey(1) &0xFF
if keY == ord('s'):
f ilename = datetime.nowO.strftime("%Y% mohd_okHo/olttlo/oS_%f ") +". png"
path = os.path.ioin(SAVE_DlR, filename)
cv2.imwrite(path, image)
print(f'saved : {path}')
elif key == ord('q'):
break
```


## 압축하기

* 9_2_2.py

```python
import os
import zipfile
def zip_pictures_folderO :
base_dir = os. path. dirname(__fite--)
pictures_dir = os.path. join(base-dir, "pictures")
zip_path = os.path.join(base-dir, "pictures.zip")
if not os.path.exists(pictures-dir) :
print("pictures folder not found.")
return
with zipfile.ZipFile(zip-path, rv', zipfile.ZlP-DEFLATED) as zipf:
for root, dirs, files in os.walk(pictures-dir):
for file in files:
file_path = os.path.join(root, file)
arcnam e = os. path. relpath(f ile-path, pictures-dir)
zipf .write(f i le-path, arcname)
print(f" zip created: {zip-path}")
if _name_ =="__main_
zip-pictures-folderQ
```

## 데이터 라벨링

* 저장된 사진에서 객체를 라벨링 합니다. 라벨링 작업은 객체의 정잡을 부여하는 과정으로 사람이 수작업으로 진행합니다.

* 9_2_2.py

```python

```

