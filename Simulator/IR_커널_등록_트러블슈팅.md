# IR 리모컨 커널 등록 트러블슈팅 정리

라즈베리파이4에서 IR 리모컨 수신부를 커널에 등록하는 과정에서 막혔던 지점을 순서대로 정리합니다. 하드웨어 배선이나 파이썬 코드 문제가 아니라, **"오버레이 설정 누락 → 장치 번호 오배정 → 명령어 버전 차이 → 키맵 미적용"이 순서대로 겹쳐서 각 단계마다 다른 원인으로 막힌 것**이었습니다.

---

## 1) `config.txt`에 오버레이 줄 자체가 빠져있었음 (근본 원인)

`/boot/firmware/config.txt`에 아래 두 줄만 있고 IR 관련 줄이 없었음:
```
enable_uart=1
dtoverlay=disable-bt
```

**빠져있던 줄:**
```
dtoverlay=gpio-ir,gpio_pin=18
```

### 증상
- 커널이 IR 리시버용 드라이버(`gpio_ir_recv`)를 로드할 이유가 없었음
- `/dev/lirc0` 자체가 생성되지 않음
  ```bash
  $ ls /dev/lirc*
  ls: cannot access '/dev/lirc*': No such file or directory
  ```
- 그 이후 단계(ir-keytable, evtest 등)는 시도할 대상 자체가 없는 상태였음

### 해결
```bash
sudo nano /boot/firmware/config.txt
```
```
enable_uart=1
dtoverlay=disable-bt
dtoverlay=gpio-ir,gpio_pin=18
```
저장 후 **반드시 재부팅** (디바이스 트리 오버레이는 부팅 시점에만 적용됨):
```bash
sudo reboot
```
재부팅 후 `/dev/lirc0`가 정상 생성됨을 확인.

---

## 2) rc 장치 번호가 기본값(`rc0`)이 아니라 `rc2`로 등록됨

`dmesg` 로그 확인:
```bash
$ dmesg | grep -i "ir-rx\|gpio_ir\|lirc"
rc rc2: gpio_ir_recv as /devices/platform/ir-receiver@12/rc/rc2
rc rc2: lirc_dev: driver gpio_ir_recv registered at minor = 0, raw IR receiver, no transmitter
input: gpio_ir_recv as /devices/platform/ir-receiver@12/rc/rc2/input4
```

### 증상
`ir-keytable` 대부분의 예제/문서는 `rc0`을 기본 가정하는데, 라즈베리파이4는 HDMI-CEC 등 다른 rc 장치가 먼저 rc0~rc1을 차지해서 IR 리시버가 **rc2**로 밀려 등록됨. 이걸 모르고 기본값으로 명령을 치면 엉뚱한(또는 존재하지 않는) 장치를 보게 되어 계속 헷갈림.

### 해결
이후 모든 `ir-keytable` 명령에 `-s rc2`를 명시:
```bash
sudo ir-keytable -t -s rc2
sudo ir-keytable -r -s rc2
sudo ir-keytable -c -w /etc/rc_keymaps/mycar.toml -s rc2
```

---

## 3) `ir-keytable -d` 옵션이 이 버전에는 없었음

```bash
$ sudo ir-keytable -t -d /dev/lirc0
ir-keytable: invalid option -- 'd'
```

### 원인
처음 시도한 명령은 `-d /dev/lirc0`(lirc 디바이스 경로 지정) 방식이었는데, 설치된 `v4l-utils` 버전은 그 옵션이 없고 **`-s SYSDEV`(sysfs rc 장치명, 예: `rc2`)** 방식만 지원함.

### 해결
```bash
ir-keytable --help
```
로 실제 지원 옵션 확인:
```
-s, --sysdev=SYSDEV   rc device to control, defaults to rc0 if not specified
```
`-d` 대신 `-s rc2`로 정정:
```bash
sudo ir-keytable -t -s rc2
```

---

## 4) 기본 키맵(`rc-rc6-mce`)이 이미 깔려 있어서, 매핑이 안 먹은 것처럼 보였음

```bash
$ sudo ir-keytable -s rc2
Found /sys/class/rc/rc2/ with:
        Name: gpio_ir_recv
        Default keymap: rc-rc6-mce
        Enabled kernel protocols: lirc nec
```

### 증상
raw scancode(`ir-keytable -t`)는 처음부터 정상적으로 잡히고 있었지만(`nec` 프로토콜 디코딩 자체는 항상 됨), **evdev 레벨(`KEY_STOP` 같은 이름 붙은 키)** 로는 우리가 원하는 매핑이 아직 없는 상태였음. 그래서 "raw scancode는 잘 나오는데 파이썬 코드에서는 아무 반응이 없다"는 혼란으로 이어짐.

### 해결
커스텀 키맵 파일 작성 후, 기존 매핑을 지우고 새로 적용:
```bash
sudo ir-keytable -c -w /etc/rc_keymaps/mycar.toml -s rc2
```
- `-c`: 기존(rc6-mce 기본) 매핑 삭제
- `-w`: 새 매핑 적용

적용 확인:
```bash
$ sudo ir-keytable -r -s rc2
scancode 0x0007 = KEY_KPMINUS (0x4a)
scancode 0x0009 = KEY_STOP (0x80)
scancode 0x0015 = KEY_KPPLUS (0x4e)
scancode 0x0040 = KEY_FASTFORWARD (0xd0)
scancode 0x0043 = KEY_OK (0x160)
scancode 0x0044 = KEY_REWIND (0xa8)
Enabled kernel protocols: lirc nec
```

### 참고 — 이 적용은 재부팅하면 초기화됨
`ir-keytable -c -w`는 디스크 설정을 바꾸는 게 아니라 **커널 메모리 상의 매핑 테이블**에 값을 써넣는 것이라, 재부팅하면 다시 기본 키맵(`rc-rc6-mce`)으로 돌아감. 영구 적용하려면:
```bash
sudo nano /etc/rc_maps.cfg
# 맨 위에 추가: *	gpio_ir_recv	mycar.toml

sudo cp /etc/rc_keymaps/mycar.toml /lib/udev/rc_keymaps/mycar.toml
```
등록해두면 udev가 부팅 시 `gpio_ir_recv` 장치 인식 시 자동으로 키맵을 적용해줌.

---

## 단계별 진단 도구 정리

| 레벨 | 명령어 | 확인 내용 |
|---|---|---|
| 1. 오버레이 로딩 | `ls /dev/lirc*` | `/dev/lirc0` 생성 여부 |
| 2. 커널 드라이버 등록 | `dmesg \| grep -i "gpio_ir\|lirc"` | 드라이버 등록 여부, rc 장치 번호(rc0/rc2 등) |
| 3. raw scancode 디코딩 | `sudo ir-keytable -t -s rc2` | NEC 프로토콜 디코딩 자체가 되는지 (키맵 적용 전에도 항상 보임) |
| 4. 현재 매핑 확인 | `sudo ir-keytable -r -s rc2` | scancode→KEY_* 매핑이 실제로 적용됐는지 |
| 5. evdev 이벤트 | `sudo evtest` → 장치 선택 → 버튼 누름 | 이름 붙은 `KEY_STOP` 등 이벤트가 실제로 뜨는지 |
| 6. 파이썬 최종 검증 | `python3 test_control_ir.py` | `armed`/`speed`/`steer` 값이 버튼에 따라 실시간 갱신되는지 |

> **주의**: `sudo evtest` 실행 후 `Testing ... (interrupt to exit)` 상태에서 반드시 **실제로 버튼을 눌러야** 이벤트가 출력됨. 그냥 Ctrl+C로 나가면 "장치 지원 이벤트 목록"만 보고 끝나서 검증이 안 된 상태로 착각하기 쉬움.

---

## 요약 표

| 막힌 지점 | 증상 | 근본 원인 | 해결 |
|---|---|---|---|
| 1 | `/dev/lirc0` 없음 | config.txt에 오버레이 줄 누락 | `dtoverlay=gpio-ir,gpio_pin=18` 추가 + 재부팅 |
| 2 | 명령어가 장치를 못 찾음 | rc0이 아니라 rc2로 등록됨 | 모든 명령에 `-s rc2` 명시 |
| 3 | `-d` 옵션 에러 | 설치 버전이 `-d` 대신 `-s` 사용 | `--help`로 옵션 확인 후 `-s`로 교체 |
| 4 | 코드에서 반응 없음 | 커스텀 키맵 미적용(기본 rc6-mce 키맵만 존재) | `-c -w mycar.toml -s rc2`로 키맵 적용 |
