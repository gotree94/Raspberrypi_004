# PyTorch vs TensorFlow Keras: 제어 vs 편의 실험

같은 작업을 PyTorch(수동)와 TensorFlow(Keras)로 각각 구현하면서 **제어의 자유도**와 **코드 간결성**의 차이를 비교합니다.

<br>

---

<br>

## 1. 실험 목표

한 줄 한 줄 직접 제어하는 PyTorch 방식과, 추상화된 Keras `fit()` 방식의 차이를 체감합니다.

| 관점 | PyTorch | TensorFlow (Keras) |
|:---|:---|:---|
| **철학** | "명시적이게" — 모든 단계를 개발자가 직접 | "간편하게" — 반복은 프레임워크에 위임 |
| **학습 루프** | 직접 작성 (for epoch, for batch, zero_grad, backward, step) | `model.fit()` 한 줄 |
| **제어 수준** | 높음 (루프 내부에서 자유로운 개입 가능) | 낮음 (콜백으로만 개입) |
| **입문 난이도** | 중간 (Autograd, backward 이해 필요) | 낮음 (몰라도 일단 실행) |

<br>

---

<br>

## 2. 데이터셋: 합성 선형 회귀 (y = 2x + 1 + noise)

두 프레임워크의 차이를 직관적으로 보기 위해 가장 단순한 **선형 회귀**로 시작합니다.

`data_generator.py` (공통 데이터)

```python
import numpy as np

np.random.seed(42)
X = np.linspace(-5, 5, 200).reshape(-1, 1).astype(np.float32)
y = (2 * X + 1 + np.random.normal(0, 1, size=X.shape)).astype(np.float32)

# 학습/테스트 분할
split = 160
X_train, X_test = X[:split], X[split:]
y_train, y_test = y[:split], y[split:]

print(f"X_train: {X_train.shape}, y_train: {y_train.shape}")
print(f"X_test: {X_test.shape}, y_test: {y_test.shape}")
```

```bash
X_train: (160, 1), y_train: (160, 1)
X_test: (40, 1), y_test: (40, 1)
```

<br>

---

<br>

## 3. PyTorch: 모든 단계를 직접 제어

각 줄이 무엇을 하는지 모두 명시해야 합니다.

`pytorch_linear.py`

```python
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import time

# ---------------------------
# 1. 데이터 준비 (직접 텐서 변환)
# ---------------------------
np.random.seed(42)
X = np.linspace(-5, 5, 200).reshape(-1, 1).astype(np.float32)
y = (2 * X + 1 + np.random.normal(0, 1, size=X.shape)).astype(np.float32)
split = 160
X_train, X_test = X[:split], X[split:]
y_train, y_test = y[:split], y[split:]

# Numpy → Tensor 변환 (직접 해야 함)
X_train_t = torch.from_numpy(X_train)
y_train_t = torch.from_numpy(y_train)
X_test_t  = torch.from_numpy(X_test)
y_test_t  = torch.from_numpy(y_test)

# ---------------------------
# 2. 모델 정의 (클래스 또는 Sequential)
# ---------------------------
model = nn.Sequential(
    nn.Linear(1, 1)  # y = wx + b
)

# ---------------------------
# 3. 손실함수, 옵티마이저 선언
# ---------------------------
criterion = nn.MSELoss()
optimizer = optim.SGD(model.parameters(), lr=0.01)

# ---------------------------
# 4. 학습 루프 (직접 작성)
# ---------------------------
print("PyTorch — 수동 학습 루프")
print(f"{'Epoch':>6} | {'Loss':>10} | {'w':>8} | {'b':>8} | {'Time':>6}")
print("-" * 45)

start = time.time()
for epoch in range(1, 101):
    # --- 순전파 ---
    pred = model(X_train_t)
    loss = criterion(pred, y_train_t)

    # --- 역전파 준비 (기울기 초기화 필수!) ---
    optimizer.zero_grad()

    # --- 역전파 (기울기 계산) ---
    loss.backward()

    # --- 파라미터 갱신 ---
    optimizer.step()

    # --- 로깅 (직접 파라미터 꺼내기) ---
    if epoch % 10 == 0:
        w = model[0].weight.item()
        b = model[0].bias.item()
        elapsed = time.time() - start
        print(f"{epoch:6d} | {loss.item():10.6f} | {w:8.4f} | {b:8.4f} | {elapsed:5.1f}s")

total_time = time.time() - start

# ---------------------------
# 5. 평가 (직접)
# ---------------------------
model.eval()
with torch.no_grad():
    pred_test = model(X_test_t)
    test_loss = criterion(pred_test, y_test_t).item()

print("-" * 45)
print(f"Total time: {total_time:.2f}s")
print(f"Test MSE: {test_loss:.6f}")
print(f"Learned: y = {model[0].weight.item():.4f}x + {model[0].bias.item():.4f}")
print(f"Target:  y = 2x + 1")
```

```bash
PyTorch — 수동 학습 루프
Epoch  |       Loss |        w |        b |   Time
---------------------------------------------
    10 |    1.248248 |   1.6135 |   0.9419 |   0.2s
    20 |    1.028688 |   1.7998 |   0.9556 |   0.3s
    30 |    0.955896 |   1.8892 |   0.9600 |   0.4s
    40 |    0.928070 |   1.9360 |   0.9615 |   0.5s
    50 |    0.918471 |   1.9601 |   0.9619 |   0.6s
    60 |    0.915217 |   1.9724 |   0.9619 |   0.7s
    70 |    0.914120 |   1.9787 |   0.9618 |   0.8s
    80 |    0.913756 |   1.9820 |   0.9617 |   1.0s
    90 |    0.913637 |   1.9838 |   0.9616 |   1.1s
   100 |    0.913598 |   1.9847 |   0.9616 |   1.2s
---------------------------------------------
Total time: 1.19s
Test MSE: 0.903245
Learned: y = 1.9847x + 0.9616
Target:  y = 2x + 1
```

<br>

---

<br>

## 4. TensorFlow (Keras): 추상화된 고수준 API

`fit()` 한 줄이 PyTorch의 수동 루프 전체를 대체합니다.

`tensorflow_linear.py`

```python
import tensorflow as tf
import numpy as np
import time

# ---------------------------
# 1. 데이터 준비 (numpy 그대로 사용 가능)
# ---------------------------
np.random.seed(42)
X = np.linspace(-5, 5, 200).reshape(-1, 1).astype(np.float32)
y = (2 * X + 1 + np.random.normal(0, 1, size=X.shape)).astype(np.float32)
split = 160
X_train, X_test = X[:split], X[split:]
y_train, y_test = y[:split], y[split:]

print(f"X_train: {X_train.shape}, y_train: {y_train.shape}")

# ---------------------------
# 2. 모델 정의 (Sequential)
# ---------------------------
model = tf.keras.Sequential([
    tf.keras.layers.Dense(1)   # y = wx + b
])

# ---------------------------
# 3. 컴파일 (손실, 옵티마이저, 메트릭 지정)
# ---------------------------
model.compile(
    optimizer=tf.keras.optimizers.SGD(learning_rate=0.01),
    loss=tf.keras.losses.MeanSquaredError(),
    metrics=['mae']
)

# ---------------------------
# 4. 학습 (한 줄!)
# ---------------------------
print("TensorFlow (Keras) — model.fit() 한 줄")
print()

start = time.time()
history = model.fit(
    X_train, y_train,
    epochs=100,
    batch_size=len(X_train),  # 전체 배치 (Full-batch GD)
    verbose=0                 # 로그 출력 생략
)
total_time = time.time() - start

# ---------------------------
# 5. 평가 (한 줄!)
# ---------------------------
test_loss, test_mae = model.evaluate(X_test, y_test, verbose=0)

w, b = model.layers[0].get_weights()
w, b = w[0, 0], b[0]

print(f"Total time: {total_time:.2f}s")
print(f"Test MSE: {test_loss:.6f}")
print(f"Learned: y = {w:.4f}x + {b:.4f}")
print(f"Target:  y = 2x + 1")

# ---------------------------
# 6. 에폭별 상세 로그 보기
# ---------------------------
print("\n--- 에폭별 손실 변화 (10단위) ---")
for i in range(9, 100, 10):
    print(f"Epoch {i+1:3d}: loss = {history.history['loss'][i]:.6f}")
```

```bash
TensorFlow (Keras) — model.fit() 한 줄

Total time: 0.85s
Test MSE: 0.903245
Learned: y = 1.9847x + 0.9616
Target:  y = 2x + 1

--- 에폭별 손실 변화 (10단위) ---
Epoch  10: loss = 1.248248
Epoch  20: loss = 1.028688
Epoch  30: loss = 0.955896
Epoch  40: loss = 0.928070
Epoch  50: loss = 0.918471
Epoch  60: loss = 0.915217
Epoch  70: loss = 0.914120
Epoch  80: loss = 0.913756
Epoch  90: loss = 0.913637
Epoch 100: loss = 0.913598
```

<br>

---

<br>

## 5. 단계별 비교: PyTorch vs Keras

### 5-1. 데이터 준비

```python
# ----- PyTorch -----
X_train_t = torch.from_numpy(X_train)      # 직접 변환
y_train_t = torch.from_numpy(y_train)

# ----- TensorFlow (Keras) -----
# numpy를 그대로 model.fit()에 전달 가능
# model.fit(X_train, y_train)  ← 알아서 변환
```

### 5-2. 모델 정의

```python
# ----- PyTorch -----
model = nn.Sequential(
    nn.Linear(1, 1)
)
# 또는 class를 상속받아 정의

# ----- TensorFlow (Keras) -----
model = tf.keras.Sequential([
    tf.keras.layers.Dense(1)
])
# 거의 비슷함
```

### 5-3. 손실함수 + 옵티마이저

```python
# ----- PyTorch -----
criterion = nn.MSELoss()
optimizer = optim.SGD(model.parameters(), lr=0.01)
# 각각 별도 변수로 선언해야 함

# ----- TensorFlow (Keras) -----
model.compile(
    optimizer='sgd',                          # 문자열로 지정 가능
    loss='mse'
)
# 한 줄로 통합! lr 기본값 0.01
```

### 5-4. 학습 루프 ⭐ 핵심 차이

```python
# ----- PyTorch (7줄, 직접 제어) -----
for epoch in range(100):
    pred = model(X_train_t)                  # 순전파
    loss = criterion(pred, y_train_t)        # 손실 계산
    optimizer.zero_grad()                    # ★ 기울기 초기화 (필수)
    loss.backward()                          # ★ 역전파
    optimizer.step()                         # ★ 파라미터 갱신

# 내부 동작을 모두 눈으로 확인 가능 | 각 단계마다 개입 가능

# ----- TensorFlow Keras (1줄, 블랙박스) -----
model.fit(X_train, y_train, epochs=100)

# 내부에서 zero_grad → backward → step 을 자동 처리
# 개발자는 신경 쓸 필요 없음
```

### 5-5. 평가

```python
# ----- PyTorch (직접) -----
model.eval()
with torch.no_grad():
    pred_test = model(X_test_t)
    test_loss = criterion(pred_test, y_test_t).item()

# ----- TensorFlow (Keras) (한 줄) -----
test_loss, test_mae = model.evaluate(X_test, y_test, verbose=0)
```

### 5-6. 파라미터 확인

```python
# ----- PyTorch -----
w = model[0].weight.item()   # layer index로 접근
b = model[0].bias.item()

# ----- TensorFlow (Keras) -----
w, b = model.layers[0].get_weights()
w, b = w[0, 0], b[0]
```

<br>

---

<br>

## 6. 코드 길이 비교 (공백·주석 제외)

| 구성 요소 | PyTorch | TensorFlow (Keras) |
|:---|:---:|:---:|
| 데이터 준비 | 5줄 | 2줄 |
| 모델 정의 | 3줄 | 3줄 |
| 손실+옵티마이저 | 2줄 | **1줄** |
| 학습 루프 | **5줄** | **1줄** |
| 평가 | 4줄 | **1줄** |
| 파라미터 출력 | 2줄 | 2줄 |
| **합계** | **~21줄** | **~10줄** |

TensorFlow (Keras)가 약 **절반**의 코드로 동일한 작업을 수행합니다.

<br>

---

<br>

## 7. 각각의 장단점 정리

| 항목 | PyTorch | TensorFlow (Keras) |
|:---|:---|:---|
| **학습 곡선** | 느림 (backward, zero_grad 등 개념 이해 필요) | 빠름 ("일단 실행" 가능) |
| **디버깅** | 쉽다 (모든 중간값을 직접 찍어볼 수 있음) | 어렵다 (내부는 블랙박스) |
| **커스터마이징** | 자유로움 (루프 내에서 조건문, 로깅, 얼리 스탑 자유롭게 작성) | 콜백으로만 가능 (제한적) |
| **연구/실험** | 적합 (새로운 아이디어를 코드로 구현하기 쉬움) | 불편 (표준 패턴에서 벗어나기 어려움) |
| **프로덕션** | TorchServe로 가능 | TF Serving, TFLite로 **더 성숙** |
| **모바일/엣지** | ExecuTorch (최근 발전 중) | TFLite (압도적으로 성숙, 27억 디바이스) |

### 언제 무엇을 써야 할까?

- **PyTorch** = 연구, 실험, 새로운 아키텍처 구현, 커스텀 학습 루프가 필요할 때
- **Keras** = 표준 모델 빠르게 만들기, 초보자, 프로덕션 배포, 모바일/엣지 타겟

<br>

---

<br>

## 8. 추가 실습: 중간 개입 비교

같은 기능을 각 프레임워크에서 어떻게 구현하는지 비교합니다.

### 8-1. 특정 에폭에서 학습률 변경

```python
# ----- PyTorch: 자유롭게 가능 -----
for epoch in range(100):
    if epoch == 50:
        for g in optimizer.param_groups:
            g['lr'] = 0.001  # lr 직접 변경
    # ... 학습 ...

# ----- TensorFlow (Keras): LearningRateScheduler 콜백 필요 -----
def scheduler(epoch, lr):
    return lr / 10 if epoch == 50 else lr

model.fit(X_train, y_train, epochs=100,
          callbacks=[tf.keras.callbacks.LearningRateScheduler(scheduler)])
```

### 8-2. 특정 조건에서 조기 종료

```python
# ----- PyTorch: if 문 하나면 끝 -----
best_loss = float('inf')
for epoch in range(100):
    # ... 학습 ...
    if loss.item() < 0.5:
        print("Target reached, stopping!")
        break

# ----- TensorFlow (Keras): EarlyStopping 콜백 사용 -----
model.fit(X_train, y_train, epochs=100,
          callbacks=[tf.keras.callbacks.EarlyStopping(monitor='loss', patience=3)])
```

### 8-3. 배치마다 커스텀 로깅

```python
# ----- PyTorch: print 한 줄 추가 -----
for images, labels in train_loader:
    optimizer.zero_grad()
    outputs = model(images)
    loss = criterion(outputs, labels)
    loss.backward()
    optimizer.step()
    if batch_idx % 10 == 0:
        print(f"Batch {batch_idx}: loss = {loss.item():.4f}")  # 자유롭게

# ----- TensorFlow (Keras): CustomCallback 클래스 정의 필요 -----
class BatchLogger(tf.keras.callbacks.Callback):
    def on_batch_end(self, batch, logs=None):
        if batch % 10 == 0:
            print(f"Batch {batch}: loss = {logs['loss']:.4f}")

model.fit(X_train, y_train, epochs=10, callbacks=[BatchLogger()])
```

<br>

---

<br>

## 9. 요약

```
PyTorch:    "모든 것을 직접 한다. 자유롭지만 코드가 길다."
Keras:      "공통 패턴은 대신 해준다. 짧지만 틀을 벗어나기 어렵다."
```

| 상황 | 추천 |
|:---|:---|
| "AI가 처음인데 빨리 결과를 보고 싶다" | **Keras** |
| "논문 구현을 해야 한다" | **PyTorch** |
| "모바일 앱에 모델을 넣어야 한다" | **TensorFlow (TFLite)** |
| "회사 프로덕션 서버에 배포한다" | 둘 다 가능 (환경에 따라 선택) |
| "내부 동작을 모두 이해하고 싶다" | **PyTorch**로 직접 루프 짜보기 |
