# 4-4 파란 삼각형 도형을 따라가는 자동차 만들기

## 파란 삼격형 검출하기

* 4_4_1.py

```python
import mycamera
import cv2
import numpy as np
L0w_BLUE = (t00, r20, 70)
HIGH_BLUE = (t40, 255, z5s)
HIN_TRI-AREA =1200
def find_blue_triangte(img)   :
hsv = cv2.cvtColor(img,  cv2.C0LOR_BGR2HSV)
mask = cv2.inRange(hsv,  LOI{_BLUE,  HIGH_BLUE)
mask = cv2.medianEtur(mask, 5)
contours, - = cv2.findContours(mask, cv2.RETR_EXTERNAL,   cv2.CHAIiI_APPR0X_SIiIPLE) best =l{one
for cnt in contours:
area = cv2. contourArea(cnt)
if  area < }IIN-TRI-AREA:
continue
peri = cv2.arcLength(cnt,  True)
approx = cv2.approxPolyDP(cnt,  0.04 * peri, True) if  ten(approx) ==3:
if best is None or area > besttOl: M = cv2.moments(approx)
if r["moo"1 ==s;
continue
cx =int(H["m10"f I nl"n00"]) cy =int(H["m0t"] I Al"n00'l) best = (area, approx, cx, cy)
return best, mask
if  __name__ =="__main-_" :
cam = mycamera.tlyPiCamera(640,  480)
while cam.isOpenedQ:
_, img = cam.readQ
img = 6u2.11,0, mS, -1)
vis = img.copyQ
best, mask = find_blue_triangle(img)
if best is not None:
area, approx, cx, cy = best
cv2.drawContours(vis,   lapprox], -1, (255, 0, 0), 3)
cv2.circle(vis,  (cx, cy), 5, (0, 0, 255), -1)
cv2.putText(vis,  f'area:{int(area)}", (10, 30), cv2.FONT-HERSHEY-SIMPLEX,  0.7, (0,255,0), 2)
cv2. imshow("mycamera", vis) cv2.imshow('mask',   mask) if cv2.waitKey('l) == e1d('q'):
break
cv2.destroyAllWindows0
```

## 검출된 객체를 이용하여 이동 방향 결정하기

* 4_4_2.py

```python
import mycamera
import cv2
import numpy as np

LoW_BLUE  = (100,120,70)
HIGH-BLUE = (140,255,255)
HIN_TRI-AREA = 1200

DEADBAND =20
AREA-OK_L0  = 8000
AREA_OK-HI = 18000
AREA-NEAR  = 22000

def find-btue_triangle(img) :
hsv = cv2.cvtColor(img,  cv2.COL0R_BGR2HSV)
mask = cvZ.inRange(hsv,  L0I{_BLUE, HIGH_BLUE)
mask = cv2.medianBtur(mask, 5)
contours, _ = cv2.findContours(mask, cv2.REIR_EXIERIIIAL,  cv2.CHAIiI_APPR0X_SII.|PLE) best =ltlone
for cnt in contours:
area = cv2.contourArea(cnt)
if  area < }IIN_TRI_AREA:
continue
peri = cv2.arcLength(cnt,  True)
approx = cv2.approxPolyDP(cnt,  0.04 * peri, True) if  ten(approx) ==3:
H = cv2.moments(approx)
if r["moo"] ==o:
continue
cx =int(ltl["m10"7 I Al"n00"))
cy =int(it["m01"] / M["m00"])
if best is None or area > best[O]:
6g51 = (arear approx, cx, cy)
return best, mask
def decide-direction(cx,  center-x, area):
err=cx-center_x
if  area >= AREA_]'IEAR:
return "SToP"
if  AREA-0K-10 <= area <= AREA-OK-HI:
if abs(err) <= DEADBAND:
return "F0RWARD_SLoW"
return "RIGHT"if err >0 else "LEFT"
if abs(err) <= DEADBAND:
return "FORWARD_FAST"
return "RIGHT"if err >0 else "LEFT"
if  __name__ =="-_main__" :
cam = mycamera.l{yPicamera(640,   480)
while cam.is0penedO:
-'  itttg = cam'reado
img = 6Y2'nir(img' -1)
h, w = img.shapel:2]
center_x = w //2
vis = img.copyo
best, mask = find_btue_triangle(img)
if best is not None:
area, aPPrOx, Cx, CY = best
decision = decide-direction(cx,  center-x, area) cv2.drawContours(vis,   [approxl, -1, (255, 0, 0), 3) cv2.circle(vis,  (cx, cy), 5, (0, 0, 255), -1)
cv2.line(vis, (center-x,0), (center-x, h), (0, 255,255), 1) cv2.putText(vis,  f ' a rea  : {i nt(are6)} err:{cx-ce  n ter-x}',  (1 0, 30),
cv2. FONT_H  EHSH EY_SI  M PLEX, 0. 7, (0,255,0), 2) cv2. putText(vis,  f ' decis ion :{decis ion}", (1 0, 60),
cv2. FONT-HERSHEY-SIMPLEX,  0.7, (0,255,255),  2) print(decision)
else:
decision ='TARGET_LOST"
cv2.putText(vis, decision, (1 0, 30),
cv2. FONT-H EBSH EY_SI  M PLEX, 0. 7, (0,0,255), 2) print(decision)
cv2.imshow("mycamera',  vis) cv2.imshow('mask',   mask) if cv2.waitKey(1)  == epfl('q'):
break
cv2.destroyAllWindows0
```


## 실제 자동차를 움직여 파란 세모 도형을 따라가기

* 4_4_3.py

```python
import mycamera
import cv2
import numpy as np
import myservo
import time
from gpiozero inport Pl$.l0utputDevice, Digital0utputDevice
PWITIA = Pl{MOutputDevice(t8)
AIN1 = Digital0utputDevice(22)
AIN2 = Digital0utputDevice(27)
PtIMB = Pt$l0utputDevice(23)
BIN1 = Digital0utputDevice(25)
BIN2 = Digital0utputDevice(24)
def motor_go(speed):
AIN1,value  =0; AIN2.value  =1; PWl,lA.vatue = speed BIN1.value =0; BIN2.value =1; P$.lB.value = speed
def motor_back(speed)  :
AINI.value =1; AIN2.value  =0; Pl{}lA.value = speed BIN1.value =1; BIN2.value =0; PIflqB.value = speed
def motor_stopO:
AIN1.value  =0; AIN2.value  =1; Pl{lilA.vatue =0.0 BIN1.value =1; BIN2.value =0; PW?,lB.value  =0.0
pca9685 = myservo.PCA9685o SERVO-CH  =0
LEFT-ANGLE =45
RIGHT-ANGLE =13s
CENTER-ANGLE  =90
BASE-SPEED   =0.s
SLOW-SPEED =0.3
TURN-DEADBAND =20
MIN_TRI_AREA  =1200
AREA-0K_10  =8000
AREA_OK_HI =L8000
AREA-NEAR  =22000
Lo|{_BLUE = (700, 120, 70)
HIGH_BLUE = (740, 255, 255) KP-AiJGLE =30.0 /320.0
def clamp(v, 1o, hi):

return hi if v > hi else to if v < 1o else v
def find_btue_triangle(img)  :
hsv = cv2.cvtColor(img,  cv2.CoLoR_BGR2HSV)
mask = cv2.inRange(hsv,  LOII_BLUE,  HIGH_BLUE)
mask = cv2.medianBlur(mask, 5)
contours, _ = cv2.findContours(mask, cv2. RETR_Dfi ERNAL,  cv2. CHAIN_APPR0X_SIIIPLE) best =None
for cnt in contours:
area = cv2.contourArea(cnt) if  area < I{IIi_TRI_AREA:
continue
peri = cv2.arcLength(cnt,  True)
approx = cv2.approxPolyDP(cnt,  0.04 * peri, True) if  ten(approx) ==3:
Il = cv2.moments(approx)
if l'l["m00"] ==0r
continue
cx =int(M["m10"] I Al"n00"))
cy =int(H["mo1"] / H["m00"])
if  best is None or area > best[O]: 5951 = (arear approx, cx, cy)
return best, mask
if  __name__ =="__main__"  :
camera = mycamera.HyPicamera(640,  480)
pca9685. set_servo_angle(SERVO_CH,    CENTER-ANGLE)
t ry:
while camera. isOpenedO :
-'  img = camera'reado
img = sY2'6i'(img' -1)
h, w = img.shape[:2]
cx-nid = w //2
best, mask = find_btue_triangle(img)
vis = img.copyo
if best is not None:
area, approx, CX, Cy = best
cv2.drawContours(vis, [approx], -1, (255, 0, 0), 3)
cv2,circle(vis, (cx, cy),5, (0,0,255), -1) err=cx-cx_mid
if abs(err) <= TURN-DEADBAND:
target_angle = CENTER_ANGLE
else:
target_angle = CENTER_ANGLE + KP_ANGLE * err
target_angle = clamp(target_angle, LEFT_ANGLE,  RIGHT_Ai{GLE) pca9685.set-servo-angle(SERvo-CH, int(target-angIe))
if  area >= AREA_NEAR:
motor_stopo
etif AREA_0K_10 <= area <= AREA_0K_HI:
motor_go (SLoW_SPEED)
else:
motor-go(BASE_SPEED)
else:
pca9685.set-servo-angle(SERVO_CH,    CENTER_ANG LE) motor-stop0
cv2. imshow('view",  vis)
cv2.imshow("mask",  mask)
if cv2.waitKeY(1)  == ord( q')'
break
time.sleep(0.0'1)
finally:
motor-stopQ
pca9685.set_servo_angle(SE RVO_CH,  CE NTE B_ANG LE)
cv2.destroyAllWindows()
```



