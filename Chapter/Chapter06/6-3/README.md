## 데이터수집하기

## 조종 화면과 이미지 처리 코드 합치기

* 6_3_1.py

```python
import cv2
import numpy as np
import mycamera
import time
import threading
import myservo
import os
from gpiozero import DigitalOutputDevice
from gpiozero import PWi,l0utputDevice

PWMA = PWMOutputDevice(18)
AIN1 = DigitatOutputDevice(22)
AIN2 = Digitat0utputDevice(27)

PWMB = PWM0utputDevice(23)
BIN1 = Digital0utputDevice(25)
BIN2 = Digital0utputDevice(24)

def motor_go(speed):
    AIN1.value  =0
    Alltl2.value  =1
    Pl{}lA.value  = speed
    BIN1.value  =0
    BIN2.value  =L
    PW.IB.value  = speed

def nothing(x):
    pass

def main():
    pca9685 = myservo.PCA96850
    channel =0

    space_Pressed =False

    cap = mycamera.MyPicamera(640,480)

    cv2. namedwindovY('  Cont rols ')
    cv2.resizeWindow('Controls',  5A0, L00)

    cv2.createTrackbar('Steering','Controls',    90, L80, nothing)
    cv2.createTrackbar('Speed','Controls',   40, 100, nothing)

    white True:
        _, frame = cap.reado
        frame = cv2.flip(frame,-1)

        height, -, - = frame.shape
        save_image = framelint(height/2):,  :, : l
        save_image = cv2.cvtColor(save_image,   cv2.C0LOR_BGR2YUV)
        save_image = cv2.GaussianBlur(save_image, (3,3), 0)
        save_image = cv2.resize(save_image,   (200,66))
        cv2.imshow('Save', save_image)

        steering_value = cv2.getTrackbarPos('Steering','Controls')
        speed_value  = cv2.getTrackbarPos('Speed','Controls')

        servo_angte = pca9685.set_servo_angle(channel,  steering_vaIue)

        controts_image  = np.zeros((700,  500, 3), dtype=np.uint8)
        cv2.putText(controls_image, f'steering: {servo_angle}' , (10, 30), cv2.FONT_HERSHEY_
255 255),7)
, 2ss), 2)

    if  space_pressed:
        cv2.circle(controls_image, (250, 30), 15, (0, 255, 0), -1)
        cv2.putText(controls_image, f'G0', (235, 70), cv2.F0NT-HERSHEY_SIHPLEX,    0.7, (255,
        motor-go (speed_va tue/ 100)
    else:
        cv2.circle(controls_image, (250, 30),15, (0, 0, 255), -1)
        cv2.putText(controls_image, f'5T0P', (225, 70), cv2.F0NT_HERSHEY_S$IPLEX,    0.7, (255,
        motor_go(0)

    cv2.imshow(' Controts', controls_image)

    cv2.imshow('  Camera', frame)

    key = su2.*rttKey(10) &oxFF
    if key == ord('q'):
        break
    elif key ==32: #S SPace key
        if not space_pressed:
            space_pressed  =True
        else:
            space_pressed  =FaIse

cap.release()
cv2.destroyAllWindows()

if __name__ =="__main__"
  main()
```



## 조종 화면과 이미지 처리 코드 합치기

* 6_3_2.py

```python
import cv2
import numpy as np
import mycamera
import time
import threading
import myservo
import os
from gpiozero import DigitalOutputDevice
from gpiozero import PtillOutputDevice

PWMA = PWMOutputDevice(18)
AIN1 = Digital0utputDevice(22)
AIN2 = Digitat0utputDevice(27)

PWMB = PWM0utputDevice(23)
BIN1 = DiSitalOutputDevice(25)
BIN2 = DigitatOutputDevice(24)

def motor_go(speed):
    AII{1.vatue  =0
    AIN2.value  =1
    PWMA.value  = speed
    BIN1.value  =0
    BIN2.value  =1
    PWMB.value = speed

def nothing(x)
    pass

def main():
    pca9685 = myservo.PCA9685o
    channet =0

    save_path =" I hone / pi / Al_CAR/video'
    file_path = save path +'ltrain"
    image-count =0
    space_pressed  =Fatse

    if not os.path.exists(save_path) :
        os. makedirs (save-path)

    cap = 6y66r..a.HyPiCamera(640,   480)

    cv2. namedl{indow( ' Contro ts' )
    cv2. resizel{indow(' Controls', 500, 100)

    cv2.createTrackbar('Steering','Controts',    90, 180, nothing)
    cv2.createTrackbar('Speed','Controls',  40, !00, nothing)

  while True:
      _, frame = cap.reado
      frame = cv2.flip(frame,-1)

      height, -, - = frame.shape save_image = framelint(height/2):, 
:,:l
srl,lPLEx, 0.7, (255, 255, 255), 2)
068         cv2.putText(controls_image, f'Speed: {speed_vatue}',  (10, 70), cv2.F0NT_HERSHEY_SII{PLEX, 0.7, (255, 255, 255), 2)
069
save_image = cv2.cvtCotor(save-image, cv2,COL0R-BGR2YUV)
save_image = cv2.GaussianBlur(save-image,  (3,3), 0)
save_image = cv2.resize(save_imageJ  (204,66))
cv2.imshow('Save', save_image)
steering_value = cv2.getTrackbarPos('Steering','Controls')
speed_value  = cv2.getTrackbarPos('Speed','Controls')
servo_angle = pca9685.set_servo_angle(channe1, steering_value)
controls_image  = np.zeros((100,  500, 3), dtype=np.uint8)
cv2.putText(controls_image, f'Steering: {servo_angte}', (10,30), cv2.F0NT-HERSHEY-

if  space_pressed:
, 255),2)
cv2.imwrite("%s_%05d_%03d.png'   % (fite_path, image_count, servo-angle), save-image) image_count = image_count  +1
cv2.circte(controls_image,   (250, 30), 15, (0, 255, 0), -7)
cv2.putText(controls-image,  f'G0', (235,70),  cv2.F0I'|T-HERSHEY-SI}|PLEX,0.7, (255, motor_go (speed-value/ 100)
else
, 255), 2)
cv2,circle(controls_image, (250, 30), 15, (0, 0, 255), -1)
cv2.putText(controls_image, f'SToP', (225, 70), cv2.F0NT-HERSHEY-SIHPLEX, 0,7, (255, motor_go(0)
cv2.imshow(' Controls', controls-image) cv2.imshow('  Camera', frame)
key = 6v2.*.itKey(10) &oxFF if  key == ord('q'):
elif keY ==32; # SPace keY if not space-pressed:
space_pressed  =True etse:
space_pressed  =False

cap.release0
cv2. destroyAllWindows0

ii _name- =="-main-"
main0
```

