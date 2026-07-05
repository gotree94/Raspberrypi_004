# 2-2 카메라 라이브러리 활용하여 OpenCV로 활용하기

## 1. mycamera 라이브러리를 불러와 사용하기

```python
import mycamera
import cv2

if __name__ == "__main__":
    camera = mycamera.MyPiCamera(640,480)

    while camera.isOpened():
        _, image = camera.read()
        cv2.imshow("mycamera", image)
        
        if cv2.waitKey(1) == ord('q'):
            break

    cv2.destroyAllWindows()
```


## 2. 카메라 화면 뒤집기

```python
import mycamera
import cv2

if __name__ == "__main__":
    camera = mycamera.MyPiCamera(640,480)

    while camera.isOpened():
        _, image = camera.read()
        image = cv2.flip(image,-1)
        cv2.imshow("mycamera", image)
        
        if cv2.waitKey(1) == ord('q'):
            break

    cv2.destroyAllWindows()
```
