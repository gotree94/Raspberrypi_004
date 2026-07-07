# 4-3 도형(네모, 세모) 및 색상 검출하기

## 1. 색상 검출하기

### 4_3_1.py

```python
import mycamera
import cv2
import numpy as np

  if  __name__ =="__main__"  :
    cam = mycamera.l,lyPiCamera(640,480)
    while cam.is0penedO:
        -'  img = cam'reado
        img = 6Y2'nir(img, -1)
        hsv = cv2.cvtColor(img,  cv2.C0L0R-BGR2HSV)

        red = cv2.inRange(hsv,  (0,720,70), (10,255,255)) | cv2.inRange(hsv,  (!70,120,70),( 180,255,255) )
        blue = cv2. inRange(hsv,  (100,720,7 0), (140,255,255))

    red = cv2.medianBlu(red,  5)
    blue = cv2.medianBlu(blue,  5)

    red_view = cv2.bitwise-and(img,  img, mask=red)
    blue_view = cv2. bitwise_and(img, img, mask=blue)

    cv2.imshow("original-,  img)
    cv2. imshow("red',  red_view)
    cv2.imshow("blue", blue-view)

    if cv2.waitKey(l)  == ord( q ):
      break

cv2.destroyAllWindows()
```

## 2. 도형 인식하기

### 4_3_2.py

```python
import mycamera
import cv2
import numpy as np

def detect_shapes(f rame) :
    gray = 6v2..rtColor(f rame, cv2. COLOR-BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5,5), 0)
    edges = cv2.Canny(blur,60, !50)
    cnts, - = cv2.findContours(edges,  cv2.RETR-EXIERNAL,  cv2.CHAIN-APPR0X-SII,IPLE)
    for c in cnts:
        area = cvz.contourArea(c)
        if  area <800:
            continue
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPoly}P(c, 0.02 * peri, True)
        x, y, w, h = cv2.boundingRect(approx)
        shape ="unknown"
        if  len(approx) ==3:
            shape ="triangte"
        elif len(aPProx)  ==4,
            ratio=w/float(h)
            shape ="square"if 0.9 <= ratio <=1.1 etse "rectangle"
        elif len(approx) >6: shape ="circle"
            if shape !="unknown":
          cv2. drawContours(f rame, [approx], - 1, (0,255,0),  2)
          cv2.putText(frame, shape, (x, y -8), cv2.FONT-HERSHEY-SIMPLEX,   0.6, (0,255,0), 2)
return frame

if __name__ =="--main-":
    cam = mycamera. MyPiCamera(640,480)
    while cam.isOpened0:
        _, img = cam.read0
        img = cv2.flip(img, -1)
        result = detect-shapes(img)
        cv2. imshow("shapes", result)
        if cv2.waitKey(l  ) == sd('q'):
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
    hsv=cv2.cvtColor(frame,cv2.C0L0R-BGR2HSV)
    red = cv2.inRange(hsv,  (0,L20,70), (10,255,255)) | cv2.inRange(hsv,  (170,L?0,70), (180,255,255)  )
    blue = cv2.inRange(hsv,  (700,720,70),  (740,255,255))
    for name, mask, color in [("red", red, (0,0,255)), ("blue", blue, (255,0,0))]:
      cnts, _ = cv2.findcontours(cv2.medianBtur(mask,5),  cv2.RETR_DfiERllAL, cv2.CHAIN_APPR0X_SIMPLE)

      for c in cnts:
          if  cv2.contourArea(c) <800: continue
          peri = cv2.arclength(c, True)
          approx = cv2.approxPotyDP(c, 0.07*peri,  True)
          if  name=='red"and  len(approx)==4 .n6 0.85<=w/float(h)<=1.15:
            cv2. rectangl.e (f rame, (x, y), (x+w, y+h), cotor, 2)
            cv2.putText(frame,"red  square",(x,y-8),cv2.F0NT-HERSHEY-S$IPLEX,0.6,color,2)
            cv2. d rawContours (frame, Iapprox], -1, color, 2)
cXlc! = x+w/ 12' Y+h/12
cv2. putText(f  rame, "blue triangle", (cx-60, cy-10),cv2.  FOilT-HERSHEY-
SII.IPLEX,0  , 6, color,2)

return frame

if  __name__ =="__main__"  :
  cam = mycamera. MyPiCamera(640,480)
  while cam.isOpened():
    -, img = cam.read()
    img = cv2.flip(img, -1)
    cv2. imshow("shapes",detect(img))
    if cv2.waitKey(l  )==ord( q'): break
cv2. destroyAllWindows()
```



