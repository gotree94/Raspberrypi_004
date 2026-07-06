# 작품 24. 기상청 날씨 표시기 (Weather Display)

Raspberry Pi + Python tkinter 으로 만드는 실시간 온도 · 습도 디스플레이.  
기존 기상청 RSS(`kma.go.kr/wid/queryDFSRSS.jsp`) 서비스가 종료됨에 따라  
**Open-Meteo API** (무료, API 키 불필요) 와 **기상청 공공데이터포털 API** 두 가지 버전으로 재구현.

---

## 📁 파일 구성

```
project24/
├── weather_display_openmeteo.py   ← ✅ 권장 (API 키 불필요, 즉시 실행)
├── weather_display_kma.py         ← 기상청 공공API 버전 (API 키 필요)
└── README.md
```

---

## ✅ Version A — Open-Meteo (권장)

### 특징

| 항목 | 내용 |
|------|------|
| API 키 | 불필요 |
| 비용 | 완전 무료 |
| 데이터 갱신 | 15분 간격 |
| 제공 정보 | 기온 · 습도 · 체감온도 |
| 데이터 출처 | 유럽 기상모델 (ECMWF 기반) |
| 실시간 여부 | ✅ 실시간 |

### 실행 화면

```
┌─────────────────────────────────────────────────────┐
│  Open-Meteo Live Weather                            │
│  1.2°C   Humi 69%   Feels -1.6°C                   │
└─────────────────────────────────────────────────────┘
```

### 설치 및 실행

```bash
# 패키지 설치
pip install requests
또는
sudo apt install python3-requests

# 실행
python weather_display_openmeteo.py
```

### 위치 변경

`weather_display_openmeteo.py` 상단의 `LAT`, `LON` 값을 수정합니다.

```python
LAT = 35.1595   # Gwangju
LON = 126.8526

# Sejong: LAT=36.4800, LON=127.2890
# Seoul:  LAT=37.5665, LON=126.9780
```

> 위경도 좌표 확인: [Google Maps](https://maps.google.com) 에서 원하는 위치 우클릭 → 좌표 복사
> https://findmycoordinates.com/find-coordinates 를 사용할 수도 있음.

### API 응답 확인 (브라우저)

아래 URL을 브라우저 주소창에 붙여넣으면 JSON 원본 데이터를 직접 확인할 수 있습니다.

```
https://api.open-meteo.com/v1/forecast?latitude=35.1595&longitude=126.8526&current=temperature_2m,relative_humidity_2m,apparent_temperature&timezone=Asia/Seoul
```

응답 예시:

```json
{
  "current": {
    "time": "2026-03-20T14:00",
    "temperature_2m": 1.2,
    "relative_humidity_2m": 69,
    "apparent_temperature": -1.6
  }
}
```

> Chrome 확장 **JSONVue** 또는 **JSON Formatter** 설치 시 보기 좋게 표시됩니다.

### 소스 코드

```python
import requests
import tkinter
import tkinter.font

LAT = 35.1595   # Gwangju
LON = 126.8526

def fetch_weather():
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={LAT}&longitude={LON}"
        "&current=temperature_2m,relative_humidity_2m,apparent_temperature"
        "&timezone=Asia%2FSeoul"
    )
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    current = data["current"]
    temp  = current["temperature_2m"]
    humi  = current["relative_humidity_2m"]
    feel  = current["apparent_temperature"]
    return temp, humi, feel

def tick1Min():
    try:
        temp, humi, feel = fetch_weather()
        display = f"{temp:.1f}°C   Humi {humi}%   Feels {feel:.1f}°C"
        label.config(text=display, fg="#00BFFF")
    except Exception as e:
        label.config(text=f"Error: {e}", fg="red")
    window.after(60000, tick1Min)   # refresh every 1 min

window = tkinter.Tk()
window.title("TEMP HUMI DISPLAY")
window.geometry("660x110")
window.resizable(False, False)
window.configure(bg="#1a1a2e")

font_main  = tkinter.font.Font(family="Consolas", size=24, weight="bold")
font_title = tkinter.font.Font(family="Consolas", size=10)

title_label = tkinter.Label(
    window, text="Open-Meteo Live Weather",
    font=font_title, bg="#1a1a2e", fg="#888888"
)
title_label.pack(pady=(6, 0))

label = tkinter.Label(
    window, text="Loading...",
    font=font_main, bg="#1a1a2e", fg="#CCCCCC",
    wraplength=640, anchor="center"
)
label.pack(pady=4)

tick1Min()
window.mainloop()
```

---

## 🔑 Version B — 기상청 공공데이터포털 API

> ⚠️ **주의:** 이 버전은 초단기실황 데이터로 **1시간 단위 발표** 자료입니다.  
> 실시간 연속 갱신이 필요한 경우 Version A (Open-Meteo) 를 사용하세요.

### 특징

| 항목 | 내용 |
|------|------|
| API 키 | 필요 (공공데이터포털 발급) |
| 비용 | 무료 (일 1,000회 제한) |
| 데이터 갱신 | 1시간 간격 (02, 05, 08, 11, 14, 17, 20, 23시 발표) |
| 제공 정보 | 기온 · 습도 · 1시간 강수량 |
| 데이터 출처 | 기상청 공식 관측 자료 |
| 실시간 여부 | ⚠️ 1시간 단위 (초단기실황) |

### API 키 발급 방법

1. [https://www.data.go.kr](https://www.data.go.kr) 접속 → 회원가입 / 로그인
2. 검색창에 `초단기실황조회` 입력
3. **기상청_단기예보 조회서비스(공공)** 선택 → **활용신청** 클릭
4. 마이페이지 → **일반 인증키(Decoding)** 복사
5. 승인: 즉시 또는 최대 1~2시간 소요

### 격자 좌표 (NX, NY) 확인

기상청 동네예보는 위경도 대신 **격자 좌표**를 사용합니다.

| 지역 | NX | NY |
|------|----|----|
| 광주광역시 광산구 | 57 | 74 |
| 세종시 | 66 | 100 |
| 서울 중구 | 60 | 127 |
| 부산 해운대구 | 99 | 75 |

> 전체 좌표표 다운로드: [기상청 격자 위경도 엑셀](https://www.kma.go.kr/kma/info/neighborhoodInfo.jsp)

### 설치 및 실행

```bash
# 패키지 설치
pip install requests

# SERVICE_KEY 입력 후 실행
python weather_display_kma.py
```

### SERVICE_KEY 설정

```python
# weather_display_kma.py 상단
SERVICE_KEY = "발급받은_인증키_여기에_붙여넣기"   # <- 필수
NX = 57    # 격자 X (광주 예시)
NY = 74    # 격자 Y
```

### 사용 API 엔드포인트

```
GET http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst
```

| 파라미터 | 설명 |
|----------|------|
| `serviceKey` | 발급받은 인증키 |
| `base_date` | 조회 날짜 (YYYYMMDD) |
| `base_time` | 발표 시각 (HHmm, 예: 1400) |
| `nx` / `ny` | 격자 좌표 |
| `dataType` | JSON |

### 응답 카테고리

| 카테고리 | 설명 | 단위 |
|----------|------|------|
| `T1H` | 기온 | °C |
| `REH` | 습도 | % |
| `RN1` | 1시간 강수량 | mm |
| `WSD` | 풍속 | m/s |
| `PTY` | 강수형태 | 코드 |

---

## ⚖️ 두 버전 비교

| 항목 | Open-Meteo (A) | 기상청 공공API (B) |
|------|:--------------:|:-----------------:|
| API 키 필요 | ❌ | ✅ |
| 즉시 실행 | ✅ | ❌ |
| 데이터 출처 | 유럽 기상모델 | 기상청 공식 |
| 갱신 주기 | 15분 | 1시간 |
| 체감온도 | ✅ | ❌ |
| 강수량 | ❌ | ✅ |
| 라즈베리파이 권장 | ✅ | - |

---

## 🛠️ 트러블슈팅

### 한글 깨짐
Consolas 폰트는 영문 전용입니다. 코드 내 모든 표시 문자열을 영문으로 유지하세요.  
라즈베리파이(Linux)에서 한글이 필요한 경우:
```bash
sudo apt install fonts-nanum -y
```

### 창이 잘려서 일부만 보임
`window.geometry("660x110")` 값에서 너비를 더 늘리세요.
```python
window.geometry("800x110")
```

### Version B — `Error: ...serviceKey=Enter_your_service_key_here...`
`SERVICE_KEY` 를 실제 발급받은 키로 교체하지 않은 경우입니다.  
Version A (Open-Meteo) 사용을 권장합니다.

### requests 모듈 없음
```bash
pip install requests
# 라즈베리파이
pip3 install requests
```

---

## 📦 환경

- Python 3.7+
- Raspberry Pi 3B+ / 4B (Raspberry Pi OS Bookworm / Trixie)
- Windows 10/11 에서도 동일하게 동작

---

## 📝 변경 이력

| 버전 | 내용 |
|------|------|
| v1.0 | 기상청 RSS (`queryDFSRSS.jsp`) 사용 — **서비스 종료로 동작 불가** |
| v2.0 | Open-Meteo API 로 대체 (API 키 불필요) |
| v2.1 | 기상청 공공데이터포털 API 버전 추가 |
| v2.2 | 한글 → 영문 전환, 창 너비 660px 로 확장, wraplength 적용 |
