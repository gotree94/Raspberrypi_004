⚠️ 🚨 (반드시 PC에서 작업할것)❗⛔

# 5-3 자동미분 이해하기 (PyTorch)

* PyTorch의 강력한 기능 중 하나인 자동미분(Autograd) 시스템을 학습합니다.
* 자동미분이란 모델 삭습 시 필요한 기울기 계산을 자동으로 수행하는 기능으로, 신경망 학습의 핵심 원리 입니다.
* 간단한 예제를 통해 자동미분의 동작 과저을 실습하고, 이를 활용하여 모델이 학습되는 과정을 이애 합니다.

<br>

---

<br>

## 단일 변수의 기울기 계산

  * 하나의 변수에 대해 자동미분을 수행하여 기울기(gradient)를 계산합니다.
  * PyTorch는 수식을 따로 작성하지 않아도 미분 값을 자동으로 계산합니다.

* 5_3_1.py

```python
import torch

x = torch.tensor(2.0, requires_grad=True)
y = x**3 +2*x
y.backward()
print("x:", x.item())
print("y:", y.item())
print("dy/dx:",  x.grad.item())
```

```
x: 2.0
y: 12.0
dy/dx: 14.0
```
<br>

---

<br>

## 여러 변수의 기술기 계산

  * 두 변수 x,z를 가진 함수의 기울기를 동시에 계산합니다.
  * .backward()는 모든 입력 변수의 기울기를 자동으로 구해줍니다.  

* 5_3_2.py

```python
import torch

x = torch.tensor(1.0,  requires_grad=True)
z = torch.tensor(2.0,  requires_grad=True)
y = (x +2*z)**2
y. backward()
print("x:", x.item(), "z:", z.item())
print("y:", y.item())
print("dy/dx:", x.grad.item())
print("dy/dz:", z.grad.item())
```

```
x: 1.0 z: 2.0
y: 25.0
dy/dx: 10.0
dy/dz: 20.0
```
<br>

---

<br>

## 기울기 누적과 초기화(zero_() 사용)

  * Pytorch의 기울기는 기본적을 누적됩니다.
  * 이름을 확인하고, .zero_()로 초기화하는 방법을 실습합니다.

* 5_3_3.py

```python
import torch

x = torch.tensor(2.0, requires_grad=True)

Y=x*3
y.backward()
print("after first back,.riard, grad:", x.grad.item())

Y=x*3
y.backward()
print("after secorrd backrvard (accumulated).grad:", x.grad.item())

x.grad.zero_()
Y=x*3
y.backward()
print("after zero_0 then backward.grad :", x.grad.item())
```

```
x: 1.0 z: 2.0
y: 25.0
dy/dx: 10.0
dy/dz: 20.0
```

<br>

---

<br>

## 연산 추적 중단(detech()와 torch.no_grad())

  * 미분 계산이 필요 없는 구간에서는 연산 추적을 중단할 수 있습니다.
  * torch.no_grad()나 detech()를 사용하면 PyTorch는 그 구간을 추적하지 않습니다.

* 5_3_4.py

```python
import torch

x = torch.tensor(2.0, requires_grad=True)
y =x*2
sl = (y**2)
sl.backward()
print("grad with tracking :", x.grad.item())

with torch.no_grad():
  y2 = x*2
  s2 = (y2**2)
print("y2 requires-grad:", y2.requires_grad)
print("s2 requires-grad:", s2.requires_grad)
print("x.grad after no_grad path:", x.grad.item())

x2 = torch.tensor(2.0, requires_grad=True)
y_detached = (x2 *2).detach()
print("detached requires grad:", y_detached.requires_grad)
```

```
grad with tracking : 16.0
y2 requires-grad: False
s2 requires-grad: False
x.grad after no_grad path: 16.0
detached requires grad: False
```

---

# 5-3 자동미분 이해하기 (TensorFlow)

* TensorFlow의 강력한 기능 중 하나인 자동미분(Autograd) 시스템을 학습합니다.
* 자동미분이란 모델 학습 시 필요한 기울기 계산을 자동으로 수행하는 기능으로, 신경망 학습의 핵심 원리입니다.
* 간단한 예제를 통해 자동미분의 동작 과정을 실습하고, 이를 활용하여 모델이 학습되는 과정을 이해합니다.

<br>

---

<br>

## 단일 변수의 기울기 계산

* 하나의 변수에 대해 자동미분을 수행하여 기울기(gradient)를 계산합니다.
* TensorFlow는 `tf.GradientTape` 컨텍스트 안에서 연산을 기록하고 `tape.gradient()`로 미분합니다.

* tf_3_1.py

```python
import tensorflow as tf

x = tf.Variable(2.0)

with tf.GradientTape() as tape:
    y = x ** 3 + 2 * x

dy_dx = tape.gradient(y, x)
print("x:", x.numpy())
print("y:", y.numpy())
print("dy/dx:", dy_dx.numpy())
```

```bash
x: 2.0
y: 12.0
dy/dx: 14.0
```

> **PyTorch와의 차이:** PyTorch는 `requires_grad=True`를 설정하면 자동으로 추적하고 `backward()`로 미분합니다.<br>
> TensorFlow는 `tf.GradientTape`로 명시적으로 감싸고 `tape.gradient()`로 미분합니다.

<br>

---

<br>

## 여러 변수의 기울기 계산

* 두 변수 x, z를 가진 함수의 기울기를 동시에 계산합니다.
* `tape.gradient(y, [x, z])`로 여러 변수의 기울기를 한 번에 구합니다.

* tf_3_2.py

```python
import tensorflow as tf

x = tf.Variable(1.0)
z = tf.Variable(2.0)

with tf.GradientTape() as tape:
    y = (x + 2 * z) ** 2

dy_dx, dy_dz = tape.gradient(y, [x, z])
print("x:", x.numpy(), "z:", z.numpy())
print("y:", y.numpy())
print("dy/dx:", dy_dx.numpy())
print("dy/dz:", dy_dz.numpy())
```

```bash
x: 1.0 z: 2.0
y: 25.0
dy/dx: 10.0
dy/dz: 20.0
```

<br>

---

<br>

## 기울기 누적과 초기화

* TensorFlow의 `GradientTape`는 기본적으로 각 `tape.gradient()` 호출 후 **테이프가 즉시 폐기**됩니다.
* 따라서 PyTorch처럼 누적이 기본으로 발생하지 않으며, 누적이 필요하면 직접 구현해야 합니다.
* `persistent=True` 옵션으로 테이프를 재사용할 수 있습니다.

* tf_3_3.py

```python
import tensorflow as tf

x = tf.Variable(2.0)

# 첫 번째 backward
with tf.GradientTape() as tape:
    y = x * 3
grad1 = tape.gradient(y, x)
print("after first backward, grad:", grad1.numpy())

# 테이프는 이미 폐기됨 → 새 테이프 필요
with tf.GradientTape() as tape:
    y = x * 3
grad2 = tape.gradient(y, x)
print("after second backward, grad:", grad2.numpy())

# --- 기울기 누적을 직접 구현하려면 ---
accum = tf.Variable(0.0)
for i in range(2):
    with tf.GradientTape() as tape:
        y = x * 3
    g = tape.gradient(y, x)
    accum.assign_add(g)
    print(f"step {i+1}: grad={g.numpy()}, accumulated={accum.numpy()}")

# accum 초기화
accum.assign(0.0)
print("after zero_accum:", accum.numpy())
```

```bash
after first backward, grad: 3.0
after second backward, grad: 3.0
step 1: grad=3.0, accumulated=3.0
step 2: grad=3.0, accumulated=6.0
after zero_accum: 0.0
```

> **PyTorch와의 차이:**<br>
> PyTorch는 `x.grad`에 기울기가 **자동 누적**되며 `x.grad.zero_()`로 초기화합니다.<br>
> TensorFlow는 `GradientTape`가 일회용이므로 기본 누적이 없습니다. 필요하면 `tf.Variable`에 직접 누적해야 합니다.

<br>

---

<br>

## 연산 추적 중단 (tf.stop_gradient와 tf.GradientTape 비활성화)

* 미분 계산이 필요 없는 구간에서는 연산 추적을 중단할 수 있습니다.
* `tf.GradientTape` 바깥에서 연산하거나 `tf.stop_gradient()`를 사용하면 추적되지 않습니다.

* tf_3_4.py

```python
import tensorflow as tf

x = tf.Variable(2.0)

# 추적 O
with tf.GradientTape() as tape:
    y = x * 2
    s1 = y ** 2
grad1 = tape.gradient(s1, x)
print("grad with tracking:", grad1.numpy())

# 추적 X - GradientTape 바깥
y2 = x * 2
s2 = y2 ** 2
print("y2 (no tape):", y2.numpy())
print("s2 (no tape):", s2.numpy())

# 추적 X - tf.stop_gradient() 사용
with tf.GradientTape() as tape:
    y3 = x * 2
    y3_stopped = tf.stop_gradient(y3)
    s3 = y3_stopped ** 2
grad3 = tape.gradient(s3, x)
print("grad after stop_gradient:", grad3.numpy())  # None (추적 안 됨)

# detach 대신 tf.stop_gradient
x2 = tf.Variable(2.0)
y_detached = tf.stop_gradient(x2 * 2)
print("y_detached:", y_detached.numpy())
```

```bash
grad with tracking: 16.0
y2 (no tape): 4.0
s2 (no tape): 16.0
grad after stop_gradient: None
y_detached: 4.0
```

> **PyTorch vs TensorFlow 대응:**
> - `torch.no_grad()` → `GradientTape` 블록 **바깥**에서 연산
> - `.detach()` → `tf.stop_gradient()`

<br>

---

<br>

## 정리: PyTorch vs TensorFlow 자동미분 비교

| 기능 | PyTorch | TensorFlow |
|:---|:---|:---|
| 미분 대상 선언 | `requires_grad=True` | `tf.Variable(...)` |
| 미분 실행 | `y.backward()` | `tape.gradient(y, x)` |
| 기울기 접근 | `x.grad` | `tape.gradient()`의 반환값 |
| 기울기 누적 | 자동 누적 (`x.grad`) | 누적 없음 (일회용 tape) |
| 기울기 초기화 | `x.grad.zero_()` | 직접 `tf.Variable` 초기화 |
| 추적 중단 (블록) | `torch.no_grad()` | `GradientTape` 바깥 |
| 추적 중단 (값) | `.detach()` | `tf.stop_gradient()` |
| 여러 변수 미분 | `.backward()` (모두 자동) | `tape.gradient(y, [x, z])` |
| 테이프 재사용 | 해당 없음 | `persistent=True` 옵션 |


