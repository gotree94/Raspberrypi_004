# Thonny IDE — 초보자를 위한 Python 통합 개발 환경

> Thonny는 Python 학습자를 위해 설계된 무료 오픈소스 IDE입니다.
> Raspberry Pi OS에 기본 탑재되어 있으며, 디버깅과 변수 추적이 직관적입니다.

---

## 1. 설치 및 실행

```bash
# Raspberry Pi OS (기본 설치됨)
thonny

# 설치가 안 된 경우
sudo apt update
sudo apt install thonny
```

---

## 2. 주요 기능

| 기능 | 설명 |
|------|------|
| **내장 Python** | 별도 설치 없이 Python 인터프리터 내장 |
| **변수 보기** | 실행 중 변수 값을 실시간으로 확인 |
| **단계별 디버깅** | F5(실행), F6(큰 단계), F7(작은 단계) |
| **표현식 평가** | 코드가 한 줄씩 평가되는 과정을 시각화 |
| **Pip GUI** | `Tools → Manage packages` 로 패키지 설치 |

---

## 3. 예제로 기능 살펴보기

### 3.1. 기본 코드 작성 및 실행

Thonny를 열고 아래 코드를 입력한 후 **F5**를 눌러 실행합니다.

```python
# 1-4_example1.py
name = input("이름을 입력하세요: ")
age = int(input("나이를 입력하세요: "))
year = 2026 - age
print(f"{name}님은 {year}년생이시군요!")
```

**실행 과정 (F5):**
```
이름을 입력하세요: 홍길동
나이를 입력하세요: 30
홍길동님은 1996년생이시군요!
```

---

### 3.2. 변수 보기 기능 (`View → Variables`)

변수 창을 열고 위 코드를 실행하면 각 변수의 값이 실시간으로 표시됩니다.

| 변수명 | 값 | 타입 |
|--------|----|------|
| `name` | `'홍길동'` | `str` |
| `age` | `30` | `int` |
| `year` | `1996` | `int` |

> 초보자가 변수의 변화를 눈으로 확인할 수 있어 이해가 쉽습니다.

---

### 3.3. 단계별 디버깅 (F6 / F7)

```python
# 1-4_example2.py
def add(a, b):
    result = a + b    # ★ F7로 이 줄에서 멈춤
    return result

x = 10
y = 20
z = add(x, y)
print(f"{x} + {y} = {z}")
```

**조작법:**
- **F5** — 일반 실행
- **F6** — 큰 단계 (함수를 한 덩어리로 실행)
- **F7** — 작은 단계 (함수 내부로 들어가서 한 줄씩 실행)

**F7로 실행 시 흐름:**
```
 1: def add(a, b):          ← 함수 정의 (건너뜀)
 5: x = 10                  ← x에 10 할당
 6: y = 20                  ← y에 20 할당
 7: z = add(x, y)           ← add(10, 20) 호출
     1: def add(a, b):      ← a=10, b=20
     2:     result = a + b  ← result = 30
     3:     return result   ← 30 반환
 8: print("10 + 20 = 30")   ← 출력
```

---

### 3.4. 표현식 평가 (Small Step)

```python
# 1-4_example3.py
a = 5
b = 3
c = (a + b) * (a - b)   # ★ F7 연속 클릭으로 표현식 단위 평가
print(c)
```

**F7을 계속 누르면 Thonny가 표현식을 하나씩 평가하는 과정을 보여줍니다:**

```
  (a + b) * (a - b)
→ (5 + 3) * (5 - 3)       ← 변수를 값으로 치환
→    8     *    2          ← 괄호 안 계산
→          16              ← 최종 결과
```

> Thonny는 각 하위 표현식 위에 연한 파란색 박스를 표시하여
> 값이 어떻게 계산되는지 시각적으로 보여줍니다.

---

### 3.5. 패키지 설치 (Tools → Manage packages)

```python
# 1-4_example4.py — requests 패키지 사용 예제
import requests

response = requests.get("https://api.github.com")
print(f"상태 코드: {response.status_code}")
print(f"메시지: {response.json()['message']}")
```

**설치 방법:**
1. `Tools → Manage packages` 클릭
2. 검색창에 `requests` 입력 후 `Install`
3. 설치 완료 후 위 코드를 F5로 실행

**출력 예시:**
```
상태 코드: 200
메시지: Hello, world!
```

---

### 3.6. GPIO 제어 (Raspberry Pi)

```python
# 1-4_example5.py — LED 깜빡임
from gpiozero import LED
from time import sleep

led = LED(17)   # GPIO 17번 핀에 LED 연결

print("LED를 5번 깜빡입니다. Ctrl+C로 중단 가능")
for _ in range(5):
    led.on()
    sleep(0.5)
    led.off()
    sleep(0.5)

print("완료!")
```

> Thonny는 Raspberry Pi OS에서 GPIO 제어를 테스트하기에 가장 간편한 IDE입니다.

---

## 4. 유용한 단축키

| 단축키 | 기능 |
|--------|------|
| **F5** | 실행 |
| **Ctrl+F5** | 디버그 모드 실행 (중단점 없이 단계별) |
| **F6** | 큰 단계 (함수 넘기기) |
| **F7** | 작은 단계 (함수 내부로) |
| **F8** | 계속 실행 (다음 중단점까지) |
| **Ctrl+Shift+F5** | 중단/재시작 |
| **Ctrl+N** | 새 파일 |
| **Ctrl+S** | 저장 |
| **Ctrl+Shift+F** | 코드 정리 |
| **Ctrl+Space** | 자동 완성 |

---

## 5. 팁 — 가상환경(venv)과 연동

Thonny 기본 인터프리터를 venv로 변경하려면:

```
Run → Select interpreter → Alternative Python 3 interpreter
→ /home/gotree94/AI_CAR/venv/bin/python
```

또는 터미널에서 직접:
```bash
/home/gotree94/AI_CAR/venv/bin/python -m thonny
```

---

> **참고:** Thonny 공식 문서는 [thonny.org](https://thonny.org/) 에서 확인할 수 있습니다.
>
> *마지막 업데이트: 2026년 7월*
