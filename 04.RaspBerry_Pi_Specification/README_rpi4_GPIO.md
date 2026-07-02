# Raspberry Pi 3B+ GPIO 테스트 가이드

**보드**: Raspberry Pi 3B+ (BCM2837B0, rev 1.3)  
**OS**: Debian GNU/Linux 13 (Trixie)  
**도구**: libgpiod 2.2.1 (`gpiod` 패키지)

---

## 목차

1. [환경 확인](#1-환경-확인)
2. [패키지 설치](#2-패키지-설치)
3. [GPIO 칩 확인](#3-gpio-칩-확인)
4. [외부 GPIO 제어 (gpioset)](#4-외부-gpio-제어-gpioset)
5. [내장 LED 제어](#5-내장-led-제어)
6. [외부 GPIO vs 내장 LED 비교](#6-외부-gpio-vs-내장-led-비교)

---

## 1. 환경 확인

```bash
$ cat /etc/os-release
PRETTY_NAME="Debian GNU/Linux 13 (trixie)"
NAME="Debian GNU/Linux"
VERSION_ID="13"
VERSION="13 (trixie)"
VERSION_CODENAME=trixie
DEBIAN_VERSION_FULL=13.2
ID=debian
HOME_URL="https://www.debian.org/"
SUPPORT_URL="https://www.debian.org/support"
BUG_REPORT_URL="https://bugs.debian.org/"


$ uname -r
6.12.47+rpt-rpi-v8    # 커널

$ gpiodetect
gpiochip0 [pinctrl-bcm2711] (58 lines)
gpiochip1 [raspberrypi-exp-gpio] (8 lines)
```

---

## 2. 패키지 설치

### ⚠️ Debian 13 패키지명 주의

Debian 13 Trixie에서는 패키지명이 변경되었습니다.

| 잘못된 이름 (오류 발생) | 올바른 이름 |
|----------------------|-----------|
| `libgpiod2` | `libgpiod3` |
| `libgpiod3t64` | `libgpiod3` |

```bash
# 올바른 설치 명령
sudo apt update
sudo apt install -y libgpiod3 libgpiod-dev gpiod gcc make

# 설치 확인
dpkg -l | grep gpiod
```

```
ii  gpiod                                2.2.1-2+deb13u1                      arm64        Tools for interacting with Linux GPIO character device - binary
ii  libgpiod-dev:arm64                   2.2.1-2+deb13u1                      arm64        C library for interacting with Linux GPIO device - static libraries and headers
ii  libgpiod3:arm64                      2.2.1-2+deb13u1                      arm64        C library for interacting with Linux GPIO device - shared libraries
ii  python3-libgpiod                     2.2.1-2+deb13u1                      arm64        Python bindings for libgpiod (Python 3)

```

---

## 3. GPIO 칩 확인

### ⚠️ libgpiod 2.x 문법 변경

libgpiod 2.x부터 옵션 체계가 전면 변경되었습니다.

| 구분 | 1.x (구버전) | 2.x (현재) |
|------|------------|-----------|
| 칩 정보 | `gpioinfo gpiochip0` | `gpioinfo --chip gpiochip0` |
| 출력 | `gpioset gpiochip0 18=1` | `gpioset --chip gpiochip0 18=1` |
| 입력 | `gpioget gpiochip0 18` | `gpioget --chip gpiochip0 18` |
| 모니터 | `gpiomon gpiochip0 17` | `gpiomon --chip gpiochip0 17` |

```bash
# GPIO 칩 목록
gpiodetect

# gpiochip0 전체 핀 정보
gpioinfo --chip gpiochip0

# 특정 핀 정보
gpioinfo --chip gpiochip0 18
```

---

## 4. 외부 GPIO 제어 (gpioset)

> 외부 핀 헤더(40핀)에 LED, 버튼 등 부품을 연결해서 사용합니다.

### 핀 배치 (사용 핀)

```
   3.3V  [ 1] [ 2]  5V
  GPIO2  [ 3] [ 4]  5V
  GPIO3  [ 5] [ 6]  GND
  GPIO4  [ 7] [ 8]  GPIO14
    GND  [ 9] [10]  GPIO15
 GPIO17  [11] [12]  GPIO18   ← LED/버튼 테스트 핀
 GPIO27  [13] [14]  GND
 GPIO22  [15] [16]  GPIO23
```

| BCM | 물리 핀 | 용도 |
|-----|--------|------|
| GPIO17 | Pin 11 | 버튼 입력 |
| GPIO18 | Pin 12 | LED 출력 |

### 4-1. LED 출력 (gpioset)

#### gpioset 기본 동작

> `gpioset`은 **프로세스가 살아있는 동안 GPIO 값을 유지**합니다.  
> 실행 후 화면이 멈춘 것처럼 보이는 것이 **정상**입니다.  
> `Ctrl+C`로 종료하면 GPIO가 해제됩니다.

```bash
# LED ON (Ctrl+C 전까지 유지)
gpioset --chip gpiochip0 18=1

# LED OFF
gpioset --chip gpiochip0 18=0

# 지정 시간 후 자동 종료
gpioset --chip gpiochip0 --hold-period 1s 18=1   # 1초 후 종료
gpioset --chip gpiochip0 --hold-period 500ms 18=1 # 0.5초 후 종료

# 백그라운드 유지 (데몬)
gpioset --chip gpiochip0 --daemonize 18=1
```

#### 블링크 (--toggle)

```bash
# 500ms 간격 반복 토글 (Ctrl+C로 종료)
gpioset --chip gpiochip0 --toggle 500ms 18=1

# 횟수 지정 후 종료 (마지막 0 = 종료)
gpioset --chip gpiochip0 --toggle 500ms,500ms,500ms,0 18=1
```

#### 여러 핀 동시 제어

```bash
gpioset --chip gpiochip0 17=0 18=1 22=0 23=1
```

### 4-2. 버튼 입력 (gpioget / gpiomon)

```bash
# 현재 값 1회 읽기
gpioget --chip gpiochip0 17

# 연속 모니터링
gpiomon --chip gpiochip0 17

# 하강 엣지만 감지 (버튼 누름)
gpiomon --falling-edge --chip gpiochip0 17

# 상승 엣지만 감지 (버튼 뗌)
gpiomon --rising-edge --chip gpiochip0 17

# 5회 감지 후 자동 종료
gpiomon --num-events=5 --chip gpiochip0 17
```

### 4-3. 주요 옵션 요약

| 옵션 | 설명 | 예시 |
|------|------|------|
| `--chip` | GPIO 칩 지정 | `--chip gpiochip0` |
| `--hold-period` | 유지 시간 후 종료 | `--hold-period 1s` |
| `--toggle` | 토글 주기 설정 | `--toggle 500ms` |
| `--daemonize` | 백그라운드 실행 | `--daemonize` |
| `--bias` | 풀업/풀다운 | `--bias pull-up` |
| `--active-low` | 액티브 로우 설정 | `--active-low` |

> **시간 단위**: `us`(마이크로초) · `ms`(밀리초) · `s`(초) · `m`(분)

---

## 5. 내장 LED 제어 (전원관리 IC에 연결된 핀)

<img width="589" height="641" alt="125" src="https://github.com/user-attachments/assets/5805f0a3-b881-46c6-b17e-c02f1e2f9391" />

> 외부 회로 없이 보드에 내장된 LED 2개를 바로 제어할 수 있습니다.

### LED 위치 확인

```bash
$ ls /sys/class/leds/
ACT   PWR   default-on   mmc0
```

| LED | 색상 | 위치 | 기본 역할 |
|-----|------|------|---------|
| `ACT` | 🟢 녹색 | SD카드 슬롯 옆 | SD카드 활동 표시 |
| `PWR` | 🔴 빨간색 | ACT LED 옆 | 전원 표시 (항상 ON) |

### 5-1. ACT (녹색) LED

```bash
# 끄기
echo 0 | sudo tee /sys/class/leds/ACT/brightness

# 켜기
echo 1 | sudo tee /sys/class/leds/ACT/brightness

# 원래대로 복구 (SD카드 활동 표시)
echo mmc0 | sudo tee /sys/class/leds/ACT/trigger
```

### 5-2. PWR (빨간) LED

```bash
# 끄기
echo 0 | sudo tee /sys/class/leds/PWR/brightness

# 켜기
echo 1 | sudo tee /sys/class/leds/PWR/brightness

# 원래대로 복구 (항상 켜짐)
echo default-on | sudo tee /sys/class/leds/PWR/trigger
```

### 5-3. 블링크 (쉘 루프)

```bash
# ACT LED 블링크 (Ctrl+C로 종료)
while true; do
  echo 1 | sudo tee /sys/class/leds/ACT/brightness
  sleep 0.5
  echo 0 | sudo tee /sys/class/leds/ACT/brightness
  sleep 0.5
done
```

### 5-4. 사용 가능한 trigger 목록 확인

```bash
cat /sys/class/leds/ACT/trigger
# [none] rc-feedback kbd-scrolllock kbd-numlock ... mmc0 ...
# [ ] 안에 있는 것이 현재 설정된 trigger
```

---

## 6. 외부 GPIO vs 내장 LED 비교

| 항목 | 내장 LED | 외부 GPIO |
|------|---------|----------|
| 제어 경로 | `/sys/class/leds/` | `/dev/gpiochip0` |
| 제어 명령 | `echo` + `tee` | `gpioset` |
| 외부 회로 | ❌ 불필요 | ✅ 필요 |
| `gpioset` 사용 | ❌ 불가 | ✅ 가능 |

### 내장 LED에 gpioset을 사용하면?

내장 LED는 BCM2835 GPIO에 연결되어 있지만, 부팅 시 커널 LED 드라이버가 먼저 점유합니다.  
`gpioset`으로 접근하면 아래 오류가 발생합니다.

```bash
$ gpioset --chip gpiochip0 47=1
gpioset: error setting the GPIO line values: Device or resource busy
```

내장 LED는 반드시 `/sys/class/leds/` 경로로만 제어해야 합니다.

### ACT LED는 gpio42에 연결이 되어 있다면, gpio42는 gpioset으로 제어 할 수 있지 않을까?

* ACT LED는 GPIO42에 연결되어 있지만, gpioset으로는 제어할 수 없습니다.
* 이유는 앞서 설명한 것과 동일합니다. 부팅 시 커널의 LED 드라이버(leds-gpio.c)가 GPIO42를 먼저 request(점유)해버리기 때문입니다.

```bash
# 시도하면
gpioset --chip gpiochip0 42=1

# 결과
gpioset: error setting the GPIO line values: Device or resource busy
```

* 실제로 점유 상태를 확인할 수 있습니다.
```bash
gpioinfo --chip gpiochip0 | grep -E "42|43|44"
# line 42: "ACT"  output  consumer="led0"  [used]
```

* consumer="led0" 으로 이미 LED 드라이버가 잡고 있는 것이 보입니다.



---

## 참고

- [libgpiod 공식 문서](https://libgpiod.readthedocs.io/)
- [BCM2837 데이터시트](https://datasheets.raspberrypi.com/bcm2837/bcm2837-peripherals.pdf)
- [Raspberry Pi 3B+ 핀아웃](https://pinout.xyz/)
