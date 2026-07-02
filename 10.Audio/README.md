# 🎵 Raspberry Pi 4 오디오 재생 & 시각화 프로젝트

> **환경: Raspberry Pi 4B · Debian GNU/Linux 13 (Trixie) · Kernel 6.12 · bcm2835 Headphones card 2**

3.5mm 이어폰 잭을 통한 WAV / MP3 재생과  
파형(Waveform) · FFT 스펙트럼 · Waterfall 시각화를 Python으로 구현하는 실습 프로젝트입니다.

---

## 📋 목차

1. [하드웨어 & 오디오 아키텍처](#1-하드웨어--오디오-아키텍처)
2. [시스템 환경 확인](#2-시스템-환경-확인)
3. [ALSA 설정](#3-alsa-설정)
4. [Python 환경 구성](#4-python-환경-구성)
5. [프로젝트 구조](#5-프로젝트-구조)
6. [소스코드](#6-소스코드)
7. [실행 방법](#7-실행-방법)
8. [트러블슈팅](#8-트러블슈팅)

---

## 1. 하드웨어 & 오디오 아키텍처

### 1.1 실제 확인된 하드웨어 환경

```
admin@rp4-nwk:~ $ cat /etc/os-release
```
```
PRETTY_NAME="Debian GNU/Linux 13 (trixie)"
NAME="Debian GNU/Linux"
VERSION_ID="13"
VERSION="13 (trixie)"
VERSION_CODENAME=trixie
DEBIAN_VERSION_FULL=13.4
ID=debian
HOME_URL="https://www.debian.org/"
SUPPORT_URL="https://www.debian.org/support"
BUG_REPORT_URL="https://bugs.debian.org/"
```
```
admin@rp4-nwk:~ $ uname -a
```
```
Linux rp4-nwk 6.12.75+rpt-rpi-v8 #1 SMP PREEMPT Debian 1:6.12.75-1+rpt1 (2026-03-11) aarch64 GNU/Linux
```

```
admin@rp4-nwk:~ $ aplay -l
```

```
**** List of PLAYBACK Hardware Devices ****
card 0: vc4hdmi0 [vc4-hdmi-0], device 0: MAI PCM i2s-hifi-0 [MAI PCM i2s-hifi-0] device 0  ← HDMI 0
  Subdevices: 1/1
  Subdevice #0: subdevice #0
card 1: vc4hdmi1 [vc4-hdmi-1], device 0: MAI PCM i2s-hifi-0 [MAI PCM i2s-hifi-0] device 1  ← HDMI 1
  Subdevices: 1/1
  Subdevice #0: subdevice #0
card 2: Headphones [bcm2835 Headphones], device 0: bcm2835 Headphones [bcm2835 Headphones] device 2  ← 3.5mm 잭 ✅
  Subdevices: 8/8
  Subdevice #0: subdevice #0
  Subdevice #1: subdevice #1
  Subdevice #2: subdevice #2
  Subdevice #3: subdevice #3
  Subdevice #4: subdevice #4
  Subdevice #5: subdevice #5
  Subdevice #6: subdevice #6
  Subdevice #7: subdevice #7
```

### 1.2 Pi 4B 오디오 신호 경로

```
┌──────────────────────────────────────────────────────────┐
│                    BCM2711 SoC (Pi 4B)                   │
│                                                          │
│   PWM0 (GPIO 40) ──┐                                     │
│   PWM1 (GPIO 41) ──┴──► RC 저역통과 필터 ──► 3.5mm TRRS  │
│                                                          │
│   ALSA 드라이버: snd_bcm2835                              │
│   카드명: bcm2835 Headphones  (card 2)                    │
│                                                          │
│   ※ 3.5mm 잭은 출력 전용 — 마이크 입력 없음              │
└──────────────────────────────────────────────────────────┘
```

### 1.3 구버전 vs 현재 버전 비교

| 항목 | 구버전 (Bullseye 이전) | **현재 (Trixie, Kernel 6.12)** |
|------|----------------------|-------------------------------|
| ALSA 모드 | `compat_alsa=1` (단일 card 0) | `compat_alsa=0` (카드 분리) |
| 헤드폰 잭 | card 0: bcm2835 ALSA | **card 2: bcm2835 Headphones** |
| HDMI 오디오 | card 0의 device 1/2 | card 0/1: vc4-hdmi 별도 카드 |
| 출력 전환 | `amixer cset numid=3 1` | ❌ 더 이상 유효하지 않음 |
| 올바른 설정 | — | `~/.asoundrc` 에서 card 2 고정 |
| 마이크 입력 | — | ❌ 출력 전용 (USB 마이크 별도 필요) |

> ⚠️ **`sudo amixer cset numid=3 1` → `Operation not permitted`**  
> Trixie / Kernel 6.12 에서는 `numid=3 (PCM Playback Route)` 컨트롤이 더 이상 존재하지 않습니다.  
> `~/.asoundrc` 로 기본 출력 장치를 card 2 로 고정하는 것이 현재의 올바른 방법입니다.

### 1.4 소프트웨어 스택

```
Python 애플리케이션
  ├── pyaudio  ──► PortAudio ──► ALSA ──► snd_bcm2835 ──► 3.5mm 잭
  ├── pygame   ──► SDL_mixer ──► ALSA ──► snd_bcm2835 ──► 3.5mm 잭
  └── subprocess(mpg123) ──────► ALSA ──► snd_bcm2835 ──► 3.5mm 잭
```

---

## 2. 시스템 환경 확인

### 2.1 ALSA 드라이버 로드 확인

```bash
lsmod | grep snd_bcm2835
# snd_bcm2835   24576  1  ← 이 줄이 있어야 정상
```

```
snd_bcm2835            24576  1
snd_pcm               151552  5 snd_bcm2835,snd_soc_hdmi_codec,snd_compress,snd_soc_core,snd_pcm_dmaengine
snd                   114688  12 snd_seq,snd_seq_device,snd_bcm2835,snd_soc_hdmi_codec,snd_timer,snd_compress,snd_soc_core,snd_pcm
```

### 2.2 오디오 장치 확인

```bash
# 재생 장치 목록
aplay -l
```
```
**** List of PLAYBACK Hardware Devices ****
card 0: vc4hdmi0 [vc4-hdmi-0], device 0: MAI PCM i2s-hifi-0 [MAI PCM i2s-hifi-0] device 0  ← HDMI 0
  Subdevices: 1/1
  Subdevice #0: subdevice #0
card 1: vc4hdmi1 [vc4-hdmi-1], device 0: MAI PCM i2s-hifi-0 [MAI PCM i2s-hifi-0] device 1  ← HDMI 1
  Subdevices: 1/1
  Subdevice #0: subdevice #0
card 2: Headphones [bcm2835 Headphones], device 0: bcm2835 Headphones [bcm2835 Headphones] device 2  ← 3.5mm 잭 ✅
  Subdevices: 8/8
  Subdevice #0: subdevice #0
  Subdevice #1: subdevice #1
  Subdevice #2: subdevice #2
  Subdevice #3: subdevice #3
  Subdevice #4: subdevice #4
  Subdevice #5: subdevice #5
  Subdevice #6: subdevice #6
  Subdevice #7: subdevice #7
```
```
# 카드 2 컨트롤 확인
amixer -c 2 contents
```

### 2.3 CLI 재생 테스트 (Python 전 기본 동작 확인)

```bash
# ① ALSA 내장 WAV 재생 — 카드 직접 지정
aplay -D plughw:CARD=Headphones,DEV=0 /usr/share/sounds/alsa/Front_Center.wav
```
```
# ② 사인파 톤 테스트 (440Hz)
speaker-test -D plughw:2,0 -t sine -f 440 -c 2 -s 1
```
```
speaker-test 1.2.14

Playback device is plughw:2,0
Stream parameters are 48000Hz, S16_LE, 2 channels
Sine wave rate is 440.0000Hz
Rate set to 48000Hz (requested 48000Hz)
Buffer size range from 480 to 32768
Period size range from 480 to 32768
Periods = 4
was set period_size = 12000
was set buffer_size = 32768
  - Front Left
```

```
# ② 사인파 톤 테스트 (440Hz)
speaker-test -D plughw:2,0 -t sine -f 440 -c 2 -s 2
```
```
speaker-test 1.2.14

Playback device is plughw:2,0
Stream parameters are 48000Hz, S16_LE, 2 channels
Sine wave rate is 440.0000Hz
Rate set to 48000Hz (requested 48000Hz)
Buffer size range from 480 to 32768
Period size range from 480 to 32768
Periods = 4
was set period_size = 12000
was set buffer_size = 32768
  - Front Right
```

```
# ③ MP3 재생 테스트
mpg123 -a plughw:2,0 beat-it.mp3
```

---

## 3. ALSA 설정

### 3.1 ~/.asoundrc — 기본 출력 장치 고정

```bash
nano ~/.asoundrc
```

```
# ~/.asoundrc
# Raspberry Pi 4B / Debian Trixie / Kernel 6.12
# 기본 재생 장치: card 2 = bcm2835 Headphones (3.5mm 잭)

pcm.!default {
    type plug
    slave.pcm "hw:2,0"
}

ctl.!default {
    type hw
    card 2
}
```

적용 확인:

```bash
# 재시작 없이 즉시 적용 — 카드 지정 없이 재생되면 성공
aplay /usr/share/sounds/alsa/Front_Center.wav
```

### 3.2 볼륨 설정

```bash
# 카드 2 볼륨 조절 (0~100%)
amixer -c 2 set PCM 85%

# 터미널 믹서 실행 → F6 으로 카드 2 선택
alsamixer

# 설정 영구 저장
sudo alsactl store
```

### 3.3 /boot/firmware/config.txt 확인

```bash
sudo nano /boot/firmware/config.txt
```

```ini
# 내장 오디오 활성화 (기본값)
dtparam=audio=on

# vc4-kms-v3d 드라이버 (Trixie 기본)
dtoverlay=vc4-kms-v3d
```

> `dtparam=audio=on` 이 없으면 추가 후 `sudo reboot`

---

## 4. Python 환경 구성

### 4.1 시스템 패키지 설치

```bash
sudo apt update

sudo apt install -y \
    portaudio19-dev \
    libportaudio2 \
    python3-dev \
    python3-pip \
    python3-venv \
    python3-pygame \
    mpg123 \
    ffmpeg \
    alsa-utils
```

### 4.2 가상환경 생성

```bash
mkdir ~/pi4-audio && cd ~/pi4-audio

# --system-site-packages: apt 설치된 python3-pygame 공유
python3 -m venv venv --system-site-packages

source venv/bin/activate
# 프롬프트가 (venv) 로 바뀌면 성공
```

### 4.3 Python 패키지 설치

```bash
pip install --upgrade pip

pip install pyaudio --break-system-packages        # PortAudio 바인딩 (WAV 재생)
pip install numpy --break-system-packages          # 신호 처리 (FFT, STFT)
pip install matplotlib --break-system-packages     # 파형 / FFT / Waterfall 시각화
pip install pydub --break-system-packages          # MP3 메타데이터 (ffmpeg 필요)
```

> **pygame** 은 `python3-pygame` (apt) 으로 설치한 것을 가상환경에서 공유합니다.  
> Trixie 에서 `pip install pygame` 은 빌드 오류가 발생할 수 있으므로 apt 버전을 권장합니다.

### 4.4 설치 확인

```bash
python -c "import pyaudio, pygame, numpy, matplotlib; print('모두 정상')"
```

### 4.5 requirements.txt

```
pyaudio>=0.2.14
numpy>=1.24.0
matplotlib>=3.7.0
pydub>=0.25.1
# pygame 은 apt 패키지 사용 (python3-pygame)
```

---

## 5. 프로젝트 구조

```
pi4-audio/
│
├── README.md
├── requirements.txt
│
└── src/
    ├── 01_device_list.py     # ALSA 장치 열거
    ├── 02_play_wav.py        # WAV 재생 (pyaudio)
    ├── 03_play_pygame.py     # WAV / MP3 재생 (pygame)
    ├── 04_play_mpg123.py     # MP3 재생 (mpg123 subprocess)
    ├── 05_waveform.py        # 파형 시각화
    ├── 06_fft_spectrum.py    # FFT 주파수 스펙트럼
    ├── 07_waterfall.py       # Waterfall 스펙트로그램
    └── 08_player.py          # 통합 플레이어 (재생 + 시각화)
```

---

## 6. 소스코드

### 6.1 오디오 장치 목록 — `01_device_list.py`

```python
#!/usr/bin/env python3
"""
01_device_list.py
ALSA / pyaudio 오디오 장치 목록 출력
Pi 4B Trixie 환경에서 card 2 = bcm2835 Headphones 확인용
"""
import pyaudio


def list_devices():
    pa    = pyaudio.PyAudio()
    count = pa.get_device_count()

    print(f"\n{'─'*70}")
    print(f"  총 오디오 장치 수: {count}")
    print(f"{'─'*70}")
    print(f"  {'IDX':^4}  {'장치명':<40}  {'입력':^4}  {'출력':^4}")
    print(f"{'─'*70}")

    try:
        default_in = pa.get_default_input_device_info()["index"]
    except OSError:
        default_in = -1   # 입력 장치 없음 (Pi 4B 기본 상태)

    default_out = pa.get_default_output_device_info()["index"]

    for i in range(count):
        info = pa.get_device_info_by_index(i)
        tag  = ""
        if i == default_in:
            tag += " ◀ 기본입력"
        if i == default_out:
            tag += " ◀ 기본출력"
        print(
            f"  [{i:2d}]  "
            f"{info['name']:<40}  "
            f"{int(info['maxInputChannels']):^4}  "
            f"{int(info['maxOutputChannels']):^4}"
            f"{tag}"
        )

    print(f"{'─'*70}")
    print(f"  기본 출력 인덱스: {default_out}")
    print(f"{'─'*70}\n")
    pa.terminate()


if __name__ == "__main__":
    list_devices()
```

---

### 6.2 WAV 파일 재생 — `02_play_wav.py`

```python
#!/usr/bin/env python3
"""
02_play_wav.py
WAV 파일을 pyaudio로 재생합니다.
출력 장치: card 2 (bcm2835 Headphones) = 3.5mm 잭

사용법:
    python 02_play_wav.py audio.wav
    python 02_play_wav.py audio.wav --dev 2
"""
import wave
import pyaudio
import argparse
import sys

CHUNK     = 2048   # 버퍼 크기 (Pi 4B 언더런 방지)
ALSA_CARD = 2      # bcm2835 Headphones


def play_wav(filename: str, device_index: int = ALSA_CARD):
    try:
        wf = wave.open(filename, "rb")
    except FileNotFoundError:
        print(f"[오류] 파일 없음: {filename}")
        sys.exit(1)
    except wave.Error as e:
        print(f"[오류] WAV 형식 오류: {e}")
        print("  → MP3 파일은 03_play_pygame.py 또는 04_play_mpg123.py 를 사용하세요.")
        sys.exit(1)

    pa   = pyaudio.PyAudio()
    ch   = wf.getnchannels()
    rate = wf.getframerate()
    sw   = wf.getsampwidth()
    nf   = wf.getnframes()

    print(f"\n[WAV 재생]")
    print(f"  파일     : {filename}")
    print(f"  채널     : {ch}  ({'모노' if ch == 1 else '스테레오'})")
    print(f"  샘플레이트: {rate} Hz")
    print(f"  비트     : {sw * 8}-bit")
    print(f"  길이     : {nf / rate:.2f} 초")
    print(f"  출력 장치 : card {device_index}")

    stream = pa.open(
        format=pa.get_format_from_width(sw),
        channels=ch,
        rate=rate,
        output=True,
        output_device_index=device_index,
        frames_per_buffer=CHUNK,
    )

    print("\n  ▶ 재생 중... (Ctrl+C 로 중단)\n")
    try:
        data = wf.readframes(CHUNK)
        while data:
            stream.write(data)
            data = wf.readframes(CHUNK)
    except KeyboardInterrupt:
        print("\n  [중단됨]")

    stream.stop_stream()
    stream.close()
    pa.terminate()
    wf.close()
    print("  ✓ 재생 완료\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WAV 파일 재생")
    parser.add_argument("file",  type=str,                    help="재생할 WAV 파일")
    parser.add_argument("--dev", type=int, default=ALSA_CARD, help=f"출력 장치 인덱스 (기본: {ALSA_CARD})")
    args = parser.parse_args()
    play_wav(args.file, args.dev)
```

---

### 6.3 MP3 / WAV 재생 (pygame) — `03_play_pygame.py`

```python
#!/usr/bin/env python3
"""
03_play_pygame.py
pygame.mixer 로 WAV / MP3 / OGG 파일을 재생합니다.
~/.asoundrc 에서 기본 장치를 card 2 로 설정해 두어야 합니다.

사용법:
    python 03_play_pygame.py music.mp3
    python 03_play_pygame.py music.mp3 --volume 0.9
"""
import pygame
import time
import os
import sys
import argparse


def play_with_pygame(filename: str, volume: float = 0.8):
    if not os.path.exists(filename):
        print(f"[오류] 파일 없음: {filename}")
        sys.exit(1)

    ext = os.path.splitext(filename)[1].lower()

    # pygame mixer 초기화
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
    freq, bits, ch = pygame.mixer.get_init()

    print(f"\n[pygame 재생]")
    print(f"  파일    : {filename}  ({ext})")
    print(f"  볼륨    : {volume:.1f}")
    print(f"  mixer   : {freq}Hz  {abs(bits)}-bit  {'스테레오' if ch == 2 else '모노'}")

    pygame.mixer.music.load(filename)
    pygame.mixer.music.set_volume(volume)
    pygame.mixer.music.play()

    print("\n  ▶ 재생 중... (Ctrl+C 로 중단)\n")
    try:
        while pygame.mixer.music.get_busy():
            pos_ms = pygame.mixer.music.get_pos()
            print(f"\r  경과: {pos_ms / 1000:6.1f}s", end="", flush=True)
            time.sleep(0.2)
    except KeyboardInterrupt:
        pygame.mixer.music.stop()
        print("\n  [중단됨]")

    print("\n  ✓ 재생 완료")
    pygame.mixer.quit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="pygame으로 MP3/WAV 재생")
    parser.add_argument("file",     type=str,               help="재생할 파일 (mp3/wav/ogg)")
    parser.add_argument("--volume", type=float, default=0.8, help="볼륨 0.0~1.0 (기본 0.8)")
    args = parser.parse_args()
    play_with_pygame(args.file, args.volume)
```

---

### 6.4 MP3 재생 (mpg123 subprocess) — `04_play_mpg123.py`

```python
#!/usr/bin/env python3
"""
04_play_mpg123.py
mpg123 을 subprocess 로 호출하여 MP3 를 재생합니다.
pygame 없이 가장 가볍게 MP3 를 재생할 수 있는 방법입니다.

사전 설치:
    sudo apt install -y mpg123

사용법:
    python 04_play_mpg123.py music.mp3
    python 04_play_mpg123.py music.mp3 --card 2
"""
import subprocess
import argparse
import os
import sys

ALSA_CARD = 2   # bcm2835 Headphones


def play_mp3_mpg123(filename: str, card: int = ALSA_CARD):
    if not os.path.exists(filename):
        print(f"[오류] 파일 없음: {filename}")
        sys.exit(1)

    # mpg123 설치 확인
    if subprocess.run(["which", "mpg123"], capture_output=True).returncode != 0:
        print("[오류] mpg123 가 설치되어 있지 않습니다.")
        print("  → sudo apt install -y mpg123")
        sys.exit(1)

    alsa_dev = f"plughw:{card},0"
    print(f"\n[mpg123 재생]")
    print(f"  파일    : {filename}")
    print(f"  ALSA    : {alsa_dev}  (card {card} = bcm2835 Headphones)")
    print("\n  ▶ 재생 중... (Ctrl+C 로 중단)\n")

    try:
        subprocess.run(["mpg123", "-a", alsa_dev, filename], check=True)
    except KeyboardInterrupt:
        print("\n  [중단됨]")
    except subprocess.CalledProcessError as e:
        print(f"\n[오류] mpg123 실행 실패: {e}")
        sys.exit(1)

    print("  ✓ 재생 완료\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="mpg123으로 MP3 재생")
    parser.add_argument("file",   type=str,                    help="재생할 MP3 파일")
    parser.add_argument("--card", type=int, default=ALSA_CARD, help=f"ALSA 카드 번호 (기본: {ALSA_CARD})")
    args = parser.parse_args()
    play_mp3_mpg123(args.file, args.card)
```

---

### 6.5 파형 시각화 — `05_waveform.py`

```python
#!/usr/bin/env python3
"""
05_waveform.py
WAV 파일의 파형(Waveform)을 matplotlib 으로 시각화합니다.
RMS / Peak 레벨(dBFS)도 함께 계산합니다.

사용법:
    python 05_waveform.py audio.wav
    python 05_waveform.py audio.wav --no-save
"""
import wave
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import argparse
import os
import sys


def load_wav_mono(filename: str):
    """WAV → float32 numpy 배열 (스테레오이면 모노 다운믹스)"""
    try:
        with wave.open(filename, "rb") as wf:
            frames    = wf.getnframes()
            fs        = wf.getframerate()
            sw        = wf.getsampwidth()
            n_ch      = wf.getnchannels()
            raw       = wf.readframes(frames)
    except (FileNotFoundError, wave.Error) as e:
        print(f"[오류] {e}")
        sys.exit(1)

    dtype   = np.int16 if sw == 2 else np.int32
    samples = np.frombuffer(raw, dtype=dtype).astype(np.float32) / np.iinfo(dtype).max
    if n_ch == 2:
        samples = samples.reshape(-1, 2).mean(axis=1)
    return samples, fs, n_ch


def plot_waveform(filename: str, save: bool = True):
    samples, fs, n_ch = load_wav_mono(filename)
    duration = len(samples) / fs
    t        = np.linspace(0, duration, num=len(samples))

    rms    = np.sqrt(np.mean(samples ** 2))
    rms_db = 20 * np.log10(rms + 1e-12)
    pk_db  = 20 * np.log10(np.max(np.abs(samples)) + 1e-12)

    fig, ax = plt.subplots(figsize=(14, 4), facecolor="#0e0e0e")
    ax.set_facecolor("#111111")

    ax.plot(t, samples, color="#00BFFF", linewidth=0.4, alpha=0.85)
    ax.fill_between(t, samples, alpha=0.15, color="#00BFFF")
    ax.axhline( 0.9, color="#FF4444", linewidth=0.6, linestyle="--", alpha=0.6, label="클리핑 경계 ±0.9")
    ax.axhline(-0.9, color="#FF4444", linewidth=0.6, linestyle="--", alpha=0.6)
    ax.axhline( 0.0, color="#888888", linewidth=0.4, alpha=0.5)

    ax.set_xlim(0, duration)
    ax.set_ylim(-1.05, 1.05)
    ax.set_xlabel("시간 (초)", color="#cccccc")
    ax.set_ylabel("진폭 (정규화)", color="#cccccc")
    ax.tick_params(colors="#aaaaaa")
    ax.xaxis.set_minor_locator(ticker.AutoMinorLocator())
    ax.legend(fontsize=8, facecolor="#222222", labelcolor="#aaaaaa")

    ax.set_title(
        f"Waveform  ─  {os.path.basename(filename)}  |  "
        f"{fs}Hz  {n_ch}ch  {duration:.2f}s  |  "
        f"RMS {rms_db:.1f} dBFS   Peak {pk_db:.1f} dBFS",
        color="#eeeeee", fontsize=10
    )
    ax.grid(True, alpha=0.15, color="#555555")
    for sp in ax.spines.values():
        sp.set_edgecolor("#444444")

    plt.tight_layout()

    if save:
        out = filename.replace(".wav", "_waveform.png")
        plt.savefig(out, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
        print(f"  ✓ 저장: {out}")

    plt.show()
    print(f"\n  파일     : {os.path.basename(filename)}")
    print(f"  샘플레이트: {fs} Hz  |  채널: {n_ch}  |  길이: {duration:.2f}s")
    print(f"  RMS      : {rms_db:.2f} dBFS")
    print(f"  Peak     : {pk_db:.2f} dBFS")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WAV 파형 시각화")
    parser.add_argument("file",      type=str,            help="분석할 WAV 파일")
    parser.add_argument("--no-save", action="store_true", help="PNG 저장 건너뜀")
    args = parser.parse_args()
    plot_waveform(args.file, save=not args.no_save)
```

---

### 6.6 FFT 스펙트럼 분석 — `06_fft_spectrum.py`

```python
#!/usr/bin/env python3
"""
06_fft_spectrum.py
WAV 파일의 주파수 스펙트럼(FFT)을 분석합니다.
선형 스펙트럼(log 주파수 축) + dB 스펙트럼 + Top-10 주요 주파수 출력

사용법:
    python 06_fft_spectrum.py audio.wav
    python 06_fft_spectrum.py audio.wav --window blackman
"""
import wave
import numpy as np
import matplotlib.pyplot as plt
import argparse
import os
import sys

WINDOW_FUNCS = {
    "hann":     np.hanning,
    "hamming":  np.hamming,
    "blackman": np.blackman,
    "rect":     np.ones,
}


def compute_fft(samples: np.ndarray, fs: int, window: str = "hann"):
    N      = len(samples)
    win    = WINDOW_FUNCS.get(window, np.hanning)(N)
    fft_c  = np.fft.rfft(samples * win)
    mag    = np.abs(fft_c) / N
    mag_db = 20 * np.log10(mag + 1e-12)
    freq   = np.fft.rfftfreq(N, d=1.0 / fs)
    return freq, mag_db, mag


def plot_fft(filename: str, window: str = "hann", save: bool = True):
    try:
        with wave.open(filename, "rb") as wf:
            frames = wf.getnframes()
            fs     = wf.getframerate()
            sw     = wf.getsampwidth()
            n_ch   = wf.getnchannels()
            raw    = wf.readframes(frames)
    except (FileNotFoundError, wave.Error) as e:
        print(f"[오류] {e}")
        sys.exit(1)

    dtype   = np.int16 if sw == 2 else np.int32
    samples = np.frombuffer(raw, dtype=dtype).astype(np.float32) / np.iinfo(dtype).max
    if n_ch == 2:
        samples = samples.reshape(-1, 2).mean(axis=1)

    freq, mag_db, mag = compute_fft(samples, fs, window)

    top10_idx  = np.argsort(mag)[-10:][::-1]
    top10_freq = freq[top10_idx]
    top10_db   = mag_db[top10_idx]

    fig, axes = plt.subplots(2, 1, figsize=(14, 8), facecolor="#0e0e0e")
    fig.suptitle(
        f"FFT Spectrum  ─  {os.path.basename(filename)}  |  {fs}Hz  window={window}",
        color="#eeeeee", fontsize=11
    )

    for ax in axes:
        ax.set_facecolor("#111111")
        ax.tick_params(colors="#aaaaaa")
        ax.grid(True, alpha=0.15, color="#555555")
        for sp in ax.spines.values():
            sp.set_edgecolor("#444444")

    # 상단: 선형 진폭 (log 주파수 축)
    axes[0].semilogx(freq[1:], mag[1:], color="#FF6B6B", linewidth=0.7)
    axes[0].set_title("선형 진폭 스펙트럼 (log 주파수 축)", color="#cccccc", fontsize=10)
    axes[0].set_xlabel("주파수 (Hz)", color="#cccccc")
    axes[0].set_ylabel("진폭", color="#cccccc")
    axes[0].set_xlim(20, fs / 2)

    # 하단: dB 스펙트럼 + Top-5 마커
    axes[1].plot(freq, mag_db, color="#4ECDC4", linewidth=0.7)
    for f, db in zip(top10_freq[:5], top10_db[:5]):
        axes[1].axvline(f, color="#FFD700", alpha=0.5, linewidth=0.8, linestyle="--")
        axes[1].annotate(
            f"{f:.0f}Hz", xy=(f, db),
            xytext=(5, 5), textcoords="offset points",
            color="#FFD700", fontsize=7, alpha=0.9
        )
    axes[1].set_title("dB 스펙트럼 + Top-5 주요 주파수", color="#cccccc", fontsize=10)
    axes[1].set_xlabel("주파수 (Hz)", color="#cccccc")
    axes[1].set_ylabel("크기 (dBFS)", color="#cccccc")
    axes[1].set_xlim(0, fs / 2)
    axes[1].set_ylim(-90, 5)

    plt.tight_layout()

    if save:
        out = filename.replace(".wav", "_fft.png")
        plt.savefig(out, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
        print(f"  ✓ 저장: {out}")

    plt.show()

    print(f"\n  ┌─ Top-10 주요 주파수 {'─'*38}┐")
    for rank, (f, db) in enumerate(zip(top10_freq, top10_db), 1):
        bar = "█" * int(max(0, (db + 90) / 9))
        print(f"  │  {rank:2d}위: {f:8.1f} Hz  {db:7.2f} dBFS  {bar}")
    print(f"  └{'─'*58}┘\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WAV FFT 스펙트럼 분석")
    parser.add_argument("file",      type=str,              help="분석할 WAV 파일")
    parser.add_argument("--window",  type=str, default="hann",
                        choices=list(WINDOW_FUNCS.keys()),  help="윈도우 함수 (기본: hann)")
    parser.add_argument("--no-save", action="store_true",   help="PNG 저장 건너뜀")
    args = parser.parse_args()
    plot_fft(args.file, args.window, save=not args.no_save)
```

---

### 6.7 Waterfall 스펙트로그램 — `07_waterfall.py`

```python
#!/usr/bin/env python3
"""
07_waterfall.py
WAV 파일의 Waterfall(STFT) 스펙트로그램을 시각화합니다.
시간(X) × 주파수(Y) × 강도(색상) 3차원 정보를 2D 히트맵으로 표현합니다.

사용법:
    python 07_waterfall.py audio.wav
    python 07_waterfall.py audio.wav --fmax 8000 --cmap magma
"""
import wave
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import argparse
import os
import sys

COLORMAPS = ["inferno", "magma", "plasma", "viridis", "hot", "jet"]


def load_wav_mono(filename: str):
    try:
        with wave.open(filename, "rb") as wf:
            frames = wf.getnframes()
            fs     = wf.getframerate()
            sw     = wf.getsampwidth()
            n_ch   = wf.getnchannels()
            raw    = wf.readframes(frames)
    except (FileNotFoundError, wave.Error) as e:
        print(f"[오류] {e}")
        sys.exit(1)

    dtype   = np.int16 if sw == 2 else np.int32
    samples = np.frombuffer(raw, dtype=dtype).astype(np.float32) / np.iinfo(dtype).max
    if n_ch == 2:
        samples = samples.reshape(-1, 2).mean(axis=1)
    return samples, fs


def compute_stft(samples: np.ndarray, fs: int,
                 win_size: int = 2048, hop: int = 512):
    """Short-Time Fourier Transform → (시간, 주파수, dB 행렬)"""
    window   = np.hanning(win_size)
    n_frames = 1 + (len(samples) - win_size) // hop
    stft     = np.zeros((win_size // 2 + 1, n_frames))

    for i in range(n_frames):
        seg = samples[i * hop : i * hop + win_size]
        if len(seg) < win_size:
            seg = np.pad(seg, (0, win_size - len(seg)))
        stft[:, i] = np.abs(np.fft.rfft(seg * window)) / win_size

    stft_db = 20 * np.log10(stft + 1e-12)
    freqs   = np.fft.rfftfreq(win_size, d=1.0 / fs)
    times   = np.arange(n_frames) * hop / fs
    return times, freqs, stft_db


def plot_waterfall(filename: str,
                   fmax: float = None,
                   cmap: str   = "inferno",
                   save: bool  = True):
    samples, fs = load_wav_mono(filename)
    duration    = len(samples) / fs

    print(f"\n[Waterfall 분석]")
    print(f"  파일    : {os.path.basename(filename)}")
    print(f"  길이    : {duration:.2f}s  |  샘플레이트: {fs}Hz")
    print("  STFT 계산 중...")

    times, freqs, stft_db = compute_stft(samples, fs)

    fmax = fmax or min(fs / 2, 20000)
    mask = freqs <= fmax

    fig, ax = plt.subplots(figsize=(14, 6), facecolor="#0e0e0e")
    ax.set_facecolor("#0e0e0e")

    vmin = np.percentile(stft_db[mask, :], 10)
    vmax = np.percentile(stft_db[mask, :], 99)

    img = ax.pcolormesh(
        times, freqs[mask], stft_db[mask, :],
        cmap=cmap,
        norm=mcolors.Normalize(vmin=vmin, vmax=vmax),
        shading="gouraud",
        rasterized=True,
    )

    cbar = plt.colorbar(img, ax=ax, pad=0.01, fraction=0.03)
    cbar.set_label("크기 (dBFS)", color="#cccccc", fontsize=9)
    cbar.ax.yaxis.set_tick_params(color="#aaaaaa")
    plt.setp(cbar.ax.yaxis.get_ticklabels(), color="#aaaaaa")

    ax.set_xlabel("시간 (초)", color="#cccccc")
    ax.set_ylabel("주파수 (Hz)", color="#cccccc")
    ax.tick_params(colors="#aaaaaa")
    ax.set_xlim(0, times[-1])
    ax.set_ylim(0, fmax)
    for sp in ax.spines.values():
        sp.set_edgecolor("#333333")

    ax.set_title(
        f"Waterfall Spectrogram  ─  {os.path.basename(filename)}  |  "
        f"0 ~ {fmax/1000:.1f} kHz  |  cmap={cmap}",
        color="#eeeeee", fontsize=11
    )

    plt.tight_layout()

    if save:
        out = filename.replace(".wav", "_waterfall.png")
        plt.savefig(out, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
        print(f"  ✓ 저장: {out}")

    plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Waterfall 스펙트로그램")
    parser.add_argument("file",      type=str,              help="분석할 WAV 파일")
    parser.add_argument("--fmax",    type=float, default=None,
                        help="표시 최대 주파수 Hz (기본: fs/2)")
    parser.add_argument("--cmap",    type=str,  default="inferno",
                        choices=COLORMAPS,      help="컬러맵 (기본: inferno)")
    parser.add_argument("--no-save", action="store_true",   help="PNG 저장 건너뜀")
    args = parser.parse_args()
    plot_waterfall(args.file, args.fmax, args.cmap, save=not args.no_save)
```

---

### 6.8 통합 플레이어 — `08_player.py`

```python
#!/usr/bin/env python3
"""
08_player.py
재생 + 파형 + FFT + Waterfall 을 한 번에 실행하는 통합 스크립트

사용법:
    python 08_player.py audio.wav                       # 재생 + 전체 시각화
    python 08_player.py music.mp3 --no-play             # 시각화만 (MP3 → WAV 변환)
    python 08_player.py audio.wav --plots waveform fft  # 선택적 시각화
    python 08_player.py audio.wav --fmax 8000 --cmap magma
"""
import argparse
import os
import sys
import subprocess
import tempfile


def convert_to_wav(src: str) -> str:
    """MP3/OGG → 임시 WAV 변환 (ffmpeg)"""
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    r = subprocess.run(
        ["ffmpeg", "-y", "-i", src, "-ar", "44100", "-ac", "1", "-f", "wav", tmp.name],
        capture_output=True, text=True
    )
    if r.returncode != 0:
        print(f"[오류] ffmpeg 변환 실패:\n{r.stderr}")
        sys.exit(1)
    return tmp.name


def main():
    parser = argparse.ArgumentParser(
        description="통합 오디오 플레이어 + 시각화",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python 08_player.py audio.wav
  python 08_player.py music.mp3 --no-play
  python 08_player.py audio.wav --plots waveform fft
  python 08_player.py audio.wav --fmax 8000 --cmap magma
"""
    )
    parser.add_argument("file",                                      help="재생/분석 파일 (wav/mp3)")
    parser.add_argument("--no-play",  action="store_true",           help="재생 건너뜀")
    parser.add_argument("--plots",    nargs="+", default=["all"],
                        choices=["waveform", "fft", "waterfall", "all"],
                        help="시각화 선택 (기본: all)")
    parser.add_argument("--fmax",     type=float, default=None,      help="Waterfall 최대 주파수 Hz")
    parser.add_argument("--cmap",     type=str,   default="inferno", help="Waterfall 컬러맵")
    parser.add_argument("--card",     type=int,   default=2,         help="ALSA 카드 번호 (기본: 2)")
    args = parser.parse_args()

    if not os.path.exists(args.file):
        print(f"[오류] 파일 없음: {args.file}")
        sys.exit(1)

    ext     = os.path.splitext(args.file)[1].lower()
    is_mp3  = ext in (".mp3", ".ogg", ".aac")
    wav_tmp = None

    print(f"\n{'═'*55}")
    print(f"  파일: {args.file}")
    print(f"{'═'*55}")

    # ── 재생 ──────────────────────────────────────────────
    if not args.no_play:
        if is_mp3:
            print("\n[재생] mpg123")
            subprocess.run(["mpg123", "-a", f"plughw:{args.card},0", args.file])
        else:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from play_wav import play_wav
            play_wav(args.file, args.card)

    # ── MP3 → WAV 변환 (시각화용) ─────────────────────────
    wav_file = args.file
    if is_mp3:
        print("\n[변환] MP3 → WAV (시각화용)")
        wav_tmp  = convert_to_wav(args.file)
        wav_file = wav_tmp
        print(f"  임시: {wav_tmp}")

    # ── 시각화 ────────────────────────────────────────────
    do_all = "all" in args.plots
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    if do_all or "waveform" in args.plots:
        print("\n[시각화] Waveform")
        from waveform     import plot_waveform
        plot_waveform(wav_file)

    if do_all or "fft" in args.plots:
        print("\n[시각화] FFT Spectrum")
        from fft_spectrum  import plot_fft
        plot_fft(wav_file)

    if do_all or "waterfall" in args.plots:
        print("\n[시각화] Waterfall")
        from waterfall     import plot_waterfall
        plot_waterfall(wav_file, fmax=args.fmax, cmap=args.cmap)

    if wav_tmp and os.path.exists(wav_tmp):
        os.unlink(wav_tmp)

    print("\n  ✓ 완료\n")


if __name__ == "__main__":
    main()
```

---

## 7. 실행 방법

### 7.1 환경 활성화

```bash
cd ~/pi4-audio
source venv/bin/activate
cd src
```

### 7.2 장치 확인 (첫 번째 단계)

```bash
aplay -l                    # ALSA 장치 목록
python 01_device_list.py    # pyaudio 장치 인덱스 확인
```

### 7.3 CLI 재생 테스트 (Python 전)

```bash
aplay -D plughw:2,0 /usr/share/sounds/alsa/Front_Center.wav
speaker-test -D plughw:2,0 -t sine -f 440 -c 2 -s 1
```

### 7.4 WAV / MP3 재생

```bash
python 02_play_wav.py  /usr/share/sounds/alsa/Front_Center.wav
python 03_play_pygame.py  music.mp3
python 04_play_mpg123.py  music.mp3
```

### 7.5 시각화

```bash
python 05_waveform.py     audio.wav
python 06_fft_spectrum.py audio.wav
python 06_fft_spectrum.py audio.wav --window blackman
python 07_waterfall.py    audio.wav
python 07_waterfall.py    audio.wav --fmax 8000 --cmap magma
```

### 7.6 통합 플레이어

```bash
python 08_player.py audio.wav                      # 재생 + 전체 시각화
python 08_player.py music.mp3 --no-play            # 시각화만
python 08_player.py audio.wav --plots waveform fft # 파형 + FFT 만
```

---

## 8. 트러블슈팅

### 소리가 안 날 때

```bash
amixer -c 2 set PCM 90%
aplay -D plughw:2,0 /usr/share/sounds/alsa/Front_Center.wav
cat ~/.asoundrc    # 설정 확인
```

### `amixer cset numid=3 1` → Operation not permitted

```
Debian Trixie / Kernel 6.12 에서 numid=3 컨트롤은 더 이상 존재하지 않습니다.
~/.asoundrc 로 card 2 를 기본 장치로 고정하세요. (3. ALSA 설정 섹션 참조)
```

### `wave.Error: file does not start with RIFF id`

```
MP3 파일을 02_play_wav.py 에 전달하면 발생합니다.
MP3 는 03_play_pygame.py 또는 04_play_mpg123.py 를 사용하세요.
```

### pyaudio 설치 오류

```bash
sudo apt install --reinstall portaudio19-dev libportaudio2
pip install pyaudio
```

### Waterfall 렌더링이 느릴 때

```bash
python 07_waterfall.py audio.wav --fmax 4000    # 분석 대역 제한
```

---

## 참고

- [Raspberry Pi 오디오 공식 문서](https://www.raspberrypi.com/documentation/accessories/audio.html)
- [ALSA Project](https://www.alsa-project.org/)
- [PyAudio 문서](https://people.csail.mit.edu/hubert/pyaudio/docs/)
- [matplotlib 문서](https://matplotlib.org/stable/index.html)

---

*환경: Raspberry Pi 4B · Debian GNU/Linux 13 (Trixie) · Kernel 6.12 · Python 3.13*  
*최종 수정: 2026-03-21*
