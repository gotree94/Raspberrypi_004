# Raspberry Pi 4 Camera Setup Guide

> **Camera 1.3(OV5647)**과 **Camera 2.1(IMX219)**은 config.txt 설정이 다르므로,
> 각각 전용 스크립트로 분리되어 있습니다.


![](V1.3.png)

![](v2.1.png)

Raspberry Pi 4에서 Camera 1.3 / 2.1 연결 및 동작 확인 가이드


---

## 1. 호환성

| 카메라 | 센서 | 해상도 | config.txt 설정 |
|--------|------|--------|----------------|
| Camera Module 1.3 | OmniVision OV5647 | 5MP (2592x1944) | `dtoverlay=ov5647` |
| Camera Module 2.1 | Sony IMX219 | 8MP (3280x2464) | `camera_auto_detect=1` |

> 두 카메라는 **동시에 연결 불가**. 각각 단독으로만 사용합니다.

---

## 2. 하드웨어 연결

```
1. sudo poweroff  (전원 완전히 끄기)
2. CSI 포트 래치(검은색 걸쇠)를 위로 열기
3. 리본 케이블 삽입
   - 파란색 접촉면이 Pi 바깥쪽을 향하도록
   - Pi 4: micro HDMI 포트와 오디오 잭 사이, "CAMERA" 라벨 위치
4. 래치를 양쪽 균등하게 눌러 닫기
5. 전원 연결 후 부팅
```

---

## 3. 카메라별 설정 및 테스트

### Camera 1.3 (OV5647)

```bash
# 1) 설정 적용 (재부팅 필수)
sudo bash setup_camera_v13.sh
sudo reboot

# 2) 재부팅 후 테스트
python3 test_camera_v13.py
# 또는
bash quick_test_v13.sh
```

**config.txt 변경 내용:**
```ini
#camera_auto_detect=1
dtoverlay=ov5647
gpu_mem=128
```

### Camera 2.1 (IMX219)

```bash
# 1) 설정 적용 (재부팅 필수)
sudo bash setup_camera_v21.sh
sudo reboot

# 2) 재부팅 후 테스트
python3 test_camera_v21.py
# 또는
bash quick_test_v21.sh
```

**config.txt 변경 내용:**
```ini
camera_auto_detect=1
```

---

## 4. 카메라 전환 방법

카메라를 교체할 때마다 **반드시 전원을 끄고** 케이블을 교체한 뒤, 해당 스크립트를 실행하고 재부팅합니다.

```
Camera 1.3 사용 시 → setup_camera_v13.sh → reboot → test_camera_v13.py
Camera 2.1 사용 시 → setup_camera_v21.sh → reboot → test_camera_v21.py
```

---

## 5. CLI 빠른 명령어

```bash
# 카메라 목록 확인
rpicam-hello --list-cameras

# 사진 촬영
rpicam-still -o test.jpg

# 영상 녹화 (3초)
rpicam-vid -t 3000 -o test.h264
```

---

## 6. rpicam-apps 명령어 참조

| 명령어 | 기능 |
|--------|------|
| `rpicam-hello` | 프리뷰 (테스트용) |
| `rpicam-still` | 사진 촬영 |
| `rpicam-jpeg` | 빠른 JPEG 촬영 |
| `rpicam-vid` | 영상 녹화 |

### 유용한 옵션

| 옵션 | 설명 |
|------|------|
| `-o file` | 출력 파일명 |
| `-t ms` | 실행 시간 (밀리초) |
| `--rotation 0/90/180/270` | 회전 |
| `--hflip` / `--vflip` | 수평/수직 뒤집기 |
| `--list-cameras` | 연결된 카메라 목록 |

---

## 7. 트러블슈팅

| 증상 | 원인 | 해결 |
|------|------|------|
| `no cameras available` | 케이블 연결 불량 | 전원 off 후 케이블 재연결 |
| `Camera frontend has timed out` | OV5647 타임아웃 | `dtoverlay=ov5647` 수동 지정 |
| overlay 불일치 | 카메라 교체 후 설정 미변경 | 해당 카메라 setup 스크립트 재실행 + 재부팅 |
| `rpicam-hello: not found` | rpicam-apps 미설치 | `sudo apt install rpicam-apps` |
| 이미지 회전됨 | 카메라 장착 방향 | `--rotation 180` |
| Picamera2 import 에러 | 미설치 | `sudo apt install python3-picamera2` |

---

## 8. 파일 목록

| 파일 | 설명 |
|------|------|
| `setup_camera_v13.sh` | Camera 1.3용 설치 스크립트 (OV5647 overlay) |
| `setup_camera_v21.sh` | Camera 2.1용 설치 스크립트 (auto_detect) |
| `test_camera_v13.py` | Camera 1.3 Python 테스트 |
| `test_camera_v21.py` | Camera 2.1 Python 테스트 |
| `quick_test_v13.sh` | Camera 1.3 셸 빠른 테스트 |
| `quick_test_v21.sh` | Camera 2.1 셸 빠른 테스트 |
| `README.md` | 이 문서 |

---

## 참고 링크

- [공식 카메라 문서](https://www.raspberrypi.com/documentation/accessories/camera.html)
- [카메라 소프트웨어 문서](https://www.raspberrypi.com/documentation/computers/camera_software.html)
