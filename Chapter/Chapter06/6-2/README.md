# 6-2 OpenCV를 활용해 이미지 처리하기

* 수집할 영상의 품질을 높이기 위해 OpenCV를 활용한 이미지 전처리 기법을 학습합니다.
* 색상 변환, 노이즈 제거 등의 처리를 적용하여 안정적인 영상 데이터를 확보합니다.

* OpenCV를 활용하여 원본 이미지에서 데이터를 삭습할 수 있는 미이지로 이미지를 변환합니다.


## 이미지 출력하기

* OpenCV를 활용하여 이미지를 출력해 봅니다.

* 6_2_1.py

```python
import cv2
import mycamera
import time

def main():
    cap = 6ys3r..a.l,'tyPiCamera(640,480)

    while True:
        _, frame = cap.read()
        frame = cv2.flip(frame,  -1)

        cv2.imshow('  Camera', f rame)

        key = 612.nrttKey(10)  &oxFF
        if  key == ord('q'):
            break

    cap.releaseQ
    cv2.destroyAllWindows0

if _name- =="_main_"
    main()
```



## 이미지 w자르기

* 6_2_2.py

```python
import cv2
import mycamera
import time

def main():
    cap = mycamera.MyPiCamera(640,480)

    while True:
        _, frame = cap.reado
        frame = cv2.flip(frame,-1)

        height, -, - = frame.shape
        save_image = frame[int(height/2):,  :,:]

    cv2. imshow('Save', save-image)

    cv2. imshow('Camera', f rame)

    key = .r2.*.',Key(10) &0xFF
    if keY == ord('q'):
      break

  cap.release()
  cv2. destroyAllWindows()

if __name__ =="__main__"
    main()
```



## 이미지 출력하기

* 6_2_3.py

```python
import cv2
import mycamera
import time

def main():
    cap = mycamera.l.{yPiCamera(640,  480)

    white True:
        _, frame = cap.reado
        frame = cv2.flip(f rame,-1)

        height, -, - = frame.shape
        save_image = frame[int(height/2):,  :, :]
        save_image = cv2.cvtColor(save_image,   cv2.C0LOR-BGR2YUV)
        save_image = cv2.GaussianBlur(save_image, (3,3), 0)
        cv2. imshow('Save', save_image)

        cv2.imshow('  Camera', frame)

        key = gr2.*.itKey(10)  &OxFF
        if  key == ord('q'):
            break
    cap. releaseo
    cv2. destroyAttlWindows()

if __name__  == "__main__":
    main()
```



## 이미지 출력하기

* 6_2_4.py

```python
import cv2
import mycamera
import time
def maino:
cap = mycamera.MyPiCamera(640,  480)
while True:
, frame = 63p.reado
f rame = cv2,flip(f rame,-1)
height, -, - = frame.shape
save_image = frame[int(height/2):,  :, : ]
save_image = cvz.cvtColor(save_image,   cv2.COL0R_BGR2YUV) save_image = cv2.GaussianBlur(save-image,  (3,3), 0)
save-image = cv2.resize(save-image, (200,66) cv2. imshow('Save', save-image)
cv2.imshow('Camera',  f rame)
key = .r2.*r,,Key(10) &0xFF if keY == ord('q'):
break
cap.release0
cv2. destroyAl lWi ndows0

if __name__ =='__main__'
    main()

```



