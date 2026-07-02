# USB CAM Test

## 1. 설치 및 실행
```bash
# OpenCV 설치 (Debian 13 권장 방법)
sudo apt install python3-opencv

# 또는 pip 사용 시
pip install opencv-python --break-system-packages

# 카메라 연결 확인
ls /dev/video*

# 실행
python usb_camera.py
```

## 2. 주요 옵션

```bash
python usb_camera.py --device 0              # /dev/video0 (기본값)
python usb_camera.py --width 1280 --height 720 --fps 30
python usb_camera.py --save                  # 바로 녹화 시작
```

## 3. 키 조작
| 키 | 기능 | 
|----|----|
| q | 종료 | 
| s | 스냅샷 저장 (snapshot_0000.jpg) | 
| r | 녹화 시작 / 중지 | 
| g | 그레이스케일 토글 | 
| f | 좌우 반전 토글| 

## 4. RPi 주의사항
   * 라즈베리파이에서 cv2.imshow()를 사용하려면 데스크탑 환경(X11) 이 필요합니다. SSH로 접속 중이라면 아래를 추가하세요.
```bash
# SSH X11 포워딩
ssh -X user@raspberrypi

# 또는 헤드리스 환경에서는 imshow 대신 파일 저장 모드만 사용
python usb_camera.py --save
```
