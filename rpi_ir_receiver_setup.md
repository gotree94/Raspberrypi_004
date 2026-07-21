# 라즈베리파이 IR 리모컨 수신 설정 (GPIO 18)

---

## 1단계: 하드웨어 연결

```
IR 센서 (TSOP38238 등)       라즈베리파이
VCC (3.3V)  ─────  Pin 1 (3.3V)
GND         ─────  Pin 6 (GND)
OUT         ─────  Pin 12 (GPIO 18)
```

---

## 2단계: /boot/firmware/config.txt 수정

```bash
sudo nano /boot/firmware/config.txt
```

파일 끝에 다음 한 줄 추가:

```
dtoverlay=gpio-ir,gpio_pin=18
```

`dtoverlay=lirc-rpi` 같은 줄이 있으면 삭제.

---

## 3단계: 재부팅

```bash
sudo reboot
```

---

## 4단계: IR 장치 확인

```bash
ir-keytable
```

출력에서 `gpio_ir_recv` 항목의 rc 번호(예: `rc2`)와 event 번호(예: `/dev/input/event4`)를 확인.

---

## 5단계: NEC 프로토콜 영구 활성화

```bash
sudo tee /etc/systemd/system/ir-keytable-nec.service << 'EOF'
[Unit]
Description=Enable NEC IR protocol

[Service]
Type=oneshot
ExecStart=/usr/bin/ir-keytable -s rc2 -p nec
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now ir-keytable-nec.service
```

> 위 service 파일의 `-s rc2` 부분은 4단계에서 확인한 rc 번호로 바꾸세요.

---

## 6단계: evdev Python 패키지 설치

```bash
pip install evdev
```

---

## 7단계: Python 테스트 코드

```python
import evdev

device = evdev.InputDevice('/dev/input/event4')
print(f"Listening on {device.name}")

for event in device.read_loop():
    if event.type == evdev.ecodes.EV_MSC and event.code == evdev.ecodes.MSC_SCAN:
        scancode = event.value & 0xFFFF
        print(f"Scancode: 0x{scancode:04X}")
```

> `/dev/input/event4`는 4단계에서 확인한 event 번호로 바꾸세요.

---

## 전체 명령어 한 번에

```bash
# 1. config 수정
echo "dtoverlay=gpio-ir,gpio_pin=18" | sudo tee -a /boot/firmware/config.txt

# 2. 재부팅
sudo reboot

# 3. rc 번호 확인
ir-keytable

# 4. NEC 서비스 등록 (rc2 기준, 필요시 번호 수정)
sudo tee /etc/systemd/system/ir-keytable-nec.service << 'EOF'
[Unit]
Description=Enable NEC IR protocol

[Service]
Type=oneshot
ExecStart=/usr/bin/ir-keytable -s rc2 -p nec
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now ir-keytable-nec.service

# 5. Python 패키지 설치
pip install evdev

# 6. event 번호 확인 후 Python 실행
python3 -c "
import evdev
d = evdev.InputDevice('/dev/input/event4')
for e in d.read_loop():
    if e.type == evdev.ecodes.EV_MSC and e.code == evdev.ecodes.MSC_SCAN:
        print(f'Scancode: 0x{e.value & 0xFFFF:04X}')
"
```
