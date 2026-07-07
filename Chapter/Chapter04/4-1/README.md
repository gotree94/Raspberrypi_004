# 4-1 OpenCV 영상 처리 기초

* OpenCV를 사용하여 영상 데이터를 다루는 기본 개념을 학습합니다.
* 이밎 읽기, 화면 출력, 색상 변환, 블러링, 에지 검출 등 주요 함수의 사용법을 익힙니다.
* 이를 통해 영상 데이터가 디지털 형태로 어떻게 처리되는지 이해하고, 이후 인식 알고리즘 구현의 기토를 마련 합니다.

## 1. 이미지 불러와 뒤집어 출력하기

* 4_1_1.py

```python
import mycamera
import cv2

if __name__ = "__main__":
  camera = mycamera.MyPiCamera(640,480)

while camera.isOpenedO:
  _, image = camera.readQ
  image = cv2.flip(image,-1  )
  cv2.imshow("mycamera',  image)

  if cv2.waitKey('l) == q1fl('q'):
    break

cv2. destroyAllWindows()
```

## 이미지 자르기
* 4_1_2.py

```python
import mycamera
import cv2

if  __name__ =="__main_":
  camera = mycamera.HyPiCamera(640,480)

  while camera. is0penedO  :
    _, image = camera.reado
    image = cv2.flip(image,  -1)
  height, width, _ = image.shape
  roi = image[int(height/2):,  :]
  cv2.imshow("Origrna1",  image)
  cv2. imshow("Cropped", roi)

  if cv2.waitKey(l)  == ord('q')'
    break

cv2. destroyAllWindows()
```

## 이미지 색상 변환
* 4_1_3.py

```python
import mycamera
import cv2

if  --name-- =="-_main__" :
  camera = mycamera.l,{yPiCamera(640,480)

  while camera.isOpenedO :
    _, image = camera.reado
    image = cv2.flip(image, -1)
    gra! = sv2..rtCotor(image,  cv2. COL0R-BGR2GRAY)
  hsv = cv2.cvtColo(image,  cv2.COLOR-BGB2HSV)
  yuv = cv2.cvtColo(image,  cv2.COLOR-BGR2YUV)
  cv2.imshow("Original", image)
  cv2.imshow('Gray-, gray) cv2.imshow("HSV", hsv) cv2. imshow("YUV', yuv)

if cv2.waitKey('l) == efi( q ):
  break

cv2. destroyAllWindows()
```

## 이미지 블러링

* 4_1_4.py

```python
import mycamera
import cv2

if  __name__ =="-_mai-n__"  :
  camera = mycamera.llyPiCamera(640,480)

  white camera.isOpenedO r
    _, image = camera.reado
  image = cv2.flip(image, -1)
  blurl = cv2.GaussianBlu(image, (3,3), 0)
  blu12 = cv2.GaussianBlu(image, (7,7), 0)
  blur3 = cv2.GaussianBlu(image,  (1 5,15),0)
  cv2.imshow("Original", image)
  cv2.imshow("Blur Lrght', blurl )
  cv2.imshow("Blur Medium-, blur2)
  cv2.imshow("Blur Strong', blur3)

  if cv2.waitKey(l)  == ord('q')
    break

cv2. destroyAllWindows()
```

## 이미지 저장하기

* 4_1_5.py

```python
import mycamera
import cv2
import os

if  __name-- =="__main__":
    camera = mycamera.l,lyPiCamera(640,480)
  save-dir ="captured"
  os. makedirs(save-dir, exist_ok=True)
  count =0

while camera. isOpenedQ:
    _, image = camera.readQ
    image = cv2.flip(image, -1)
    cv2. imshow('Camera", image)

  key = cv2.waitKey(l)
  if key == ord('s'):
    filename = os.path.join(save_dir,  f"c_{count:04d}. jpg')
    cv2. imwrite(filename, image)
    print("save image :",count) count +=1
  elif key == ord('q'):
    break

cv2. destroyAllWindows()
```






