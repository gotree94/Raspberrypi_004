(반드시 PC에서 작업할것)

# 5-2 Tensor 실습 (PyTorch)

PyTorch의 핵심 데이터 구조인 Tensor를 다루는 방법을 학습합니다. <br>
Tensor의 생성, 형태 변환, 수학 연산 등을 실습하며 데이터 처리의 기본 대념을 익힙니다. <br>
이를 통해 신경망 연상의 기초가 되는 Tensor의 개념을 명확히 이해할 수 있습니다. <br>

<br>

---

<br>

## Tensor 만들기와 기본 성질 확인

* Tensor를 생성하고, 값/shape/dtype을 확인합니다.  <br>
* 랜덤 텐서는 결과가 고정되도록 시드를 설정합니다.

* 5_2_1.py

```python
import torch

torch. manual_seed (0)
a = torch.tensor([[1.0, 2.0], [3.0, 4.0]])
b = torch.zeros((2,  2))
c = torch.rand((2,  2))

print("a:", a)
print("b:", b)
print("c:", c)
print("a shape:", a.shape, "dtype:", a.dtype)
print("b shape:", b.shape, "dtype:", b.dtype)
print("c shape:", c.shape, "dtype:", c.dtype)
```

```Bash
a: tensor([[1., 2.],
        [3., 4.]])
b: tensor([[0., 0.],
        [0., 0.]])
c: tensor([[0.4963, 0.7682],
        [0.0885, 0.1320]])
a shape: torch.Size([2, 2]) dtype: torch.float32
b shape: torch.Size([2, 2]) dtype: torch.float32
c shape: torch.Size([2, 2]) dtype: torch.float32
```

<br>

---

<br>

## 연산과 축(reduction) 다루기

* 덧셈,곱셈 같은 원소별 연산과 평균,합,최대값 등 축(reduction)연산을 실습합니다.

* 5_2_2.py

```python
import torch

a = torch.tensor([[1.0, 2.0], [3.0, 4.0]])
b = torch.ones((2, 2))

print("a+b:",a+b)
print("a * b:", a*b)
print("mean(a):", a.mean())
print("sum(a, dim=0):", a.sum(dim=0))
print("max(a):", a.max())
```

```Bash
a+b: tensor([[2., 3.],
        [4., 5.]])
a * b: tensor([[1., 2.],
        [3., 4.]])
mean(a): tensor(2.5000)
sum(a, dim=0): tensor([4., 6.])
max(a): tensor(4.)
```

<br>

---

<br>

## 모양 바꾸기(reshape/view), 차원추가/제거

* Tensor의 형태를 바꾸거나, 차원을 추가하거나 제거하는 방법을 실습합니다.

* 5_2_3.py

```python
import torch 

x = torch.arange(6)
y = x.view(2, 3)
z = y.unsqueeze(0)
z2 = z.squeeze()

r = y.reshape(3,  2)
print("x:", x)
print("v:", y)
print("2 shape:",  z.shape)
print("22 shape:",  z2.shape)
print("r:", r)
```

```
x: tensor([0, 1, 2, 3, 4, 5])
v: tensor([[0, 1, 2],
        [3, 4, 5]])
2 shape: torch.Size([1, 2, 3])
22 shape: torch.Size([2, 3])
r: tensor([[0, 1],
        [2, 3],
        [4, 5]])
```

<br>

---

<br>


## Numpy <-> Tensor 변환과 메모리 공유

* Numpy 배열과 PyTorch Tensor는 서로 변환이 가능합니다.
* 이때 메모리를 공유하기 때문에 한쪽을 수정하면 다른 쪽도 함께 바뀝니다.

* 5_2_4.py

```python
import torch
import numpy as np

n = np.array([[10, 20], [30, 40]])
t = torch.from_numpy(n)
t[0, 0] = 99
print("n after t edit:", n)

back = t.numpy()
back[1, 1] =77
print("t after back edit;", t)
```

```
n after t edit: [[99 20]
 [30 40]]
t after back edit; tensor([[99, 20],
        [30, 77]], dtype=torch.int32)
```


---

# 5-2 Tensor 실습 (TensorFlow)

TensorFlow의 핵심 데이터 구조인 Tensor를 다루는 방법을 학습합니다. <br>
Tensor의 생성, 형태 변환, 수학 연산 등을 실습하며 데이터 처리의 기본 개념을 익힙니다. <br>
이를 통해 신경망 연산의 기초가 되는 Tensor의 개념을 명확히 이해할 수 있습니다. <br>

<br>

---

<br>

## Tensor 만들기와 기본 성질 확인

* Tensor를 생성하고, 값/shape/dtype을 확인합니다. <br>
* 랜덤 텐서는 결과가 고정되도록 시드를 설정합니다.

* tf_2_1.py

```python
import tensorflow as tf

tf.random.set_seed(0)
a = tf.constant([[1.0, 2.0], [3.0, 4.0]])
b = tf.zeros((2, 2))
c = tf.random.uniform((2, 2))

print("a:", a)
print("b:", b)
print("c:", c)
print("a shape:", a.shape, "dtype:", a.dtype)
print("b shape:", b.shape, "dtype:", b.dtype)
print("c shape:", c.shape, "dtype:", c.dtype)
```

```bash
a: tf.Tensor(
[[1. 2.]
 [3. 4.]], shape=(2, 2), dtype=float32)
b: tf.Tensor(
[[0. 0.]
 [0. 0.]], shape=(2, 2), dtype=float32)
c: tf.Tensor(
[[0.8108953  0.6205596 ]
 [0.12704396 0.77111244]], shape=(2, 2), dtype=float32)
a shape: (2, 2) dtype: <dtype: 'float32'>
b shape: (2, 2) dtype: <dtype: 'float32'>
c shape: (2, 2) dtype: <dtype: 'float32'>
```

<br>

---

<br>

## 연산과 축(reduction) 다루기

* 덧셈, 곱셈 같은 원소별 연산과 평균, 합, 최대값 등 축(reduction) 연산을 실습합니다.

* tf_2_2.py

```python
import tensorflow as tf

a = tf.constant([[1.0, 2.0], [3.0, 4.0]])
b = tf.ones((2, 2))

print("a + b:", a + b)
print("a * b:", a * b)
print("mean(a):", tf.reduce_mean(a))
print("sum(a, axis=0):", tf.reduce_sum(a, axis=0))
print("max(a):", tf.reduce_max(a))
```

```bash
a + b: tf.Tensor(
[[2. 3.]
 [4. 5.]], shape=(2, 2), dtype=float32)
a * b: tf.Tensor(
[[1. 2.]
 [3. 4.]], shape=(2, 2), dtype=float32)
mean(a): tf.Tensor(2.5, shape=(), dtype=float32)
sum(a, axis=0): tf.Tensor([4. 6.], shape=(2,), dtype=float32)
max(a): tf.Tensor(4.0, shape=(), dtype=float32)
```

> **참고:** PyTorch는 `a.mean()`, `a.sum(dim=0)`처럼 메서드 형태이지만, TensorFlow는 `tf.reduce_mean(a)`, `tf.reduce_sum(a, axis=0)`처럼 함수 형태입니다. `dim` 대신 `axis` 키워드를 사용합니다.

<br>

---

<br>

## 모양 바꾸기(reshape), 차원 추가/제거

* Tensor의 형태를 바꾸거나, 차원을 추가하거나 제거하는 방법을 실습합니다.

* tf_2_3.py

```python
import tensorflow as tf

x = tf.range(6)
y = tf.reshape(x, (2, 3))
z = tf.expand_dims(y, axis=0)   # unsqueeze
z2 = tf.squeeze(z)               # squeeze

r = tf.reshape(y, (3, 2))
print("x:", x)
print("y:", y)
print("z shape:", z.shape)
print("z2 shape:", z2.shape)
print("r:", r)
```

```bash
x: tf.Tensor([0 1 2 3 4 5], shape=(6,), dtype=int32)
y: tf.Tensor(
[[0 1 2]
 [3 4 5]], shape=(2, 3), dtype=int32)
z shape: (1, 2, 3)
z2 shape: (2, 3)
r: tf.Tensor(
[[0 1]
 [2 3]
 [4 5]], shape=(3, 2), dtype=int32)
```

> **PyTorch vs TensorFlow 대응:**
> - `view(2,3)` → `tf.reshape(x, (2,3))`
> - `unsqueeze(0)` → `tf.expand_dims(y, axis=0)`
> - `squeeze()` → `tf.squeeze(z)`

<br>

---

<br>

## Numpy <-> Tensor 변환과 메모리 공유

* Numpy 배열과 TensorFlow Tensor는 서로 변환이 가능합니다.
* TensorFlow는 메모리를 복사하며, PyTorch처럼 공유하지 않습니다.

* tf_2_4.py

```python
import tensorflow as tf
import numpy as np

n = np.array([[10, 20], [30, 40]])
t = tf.constant(n)                    # numpy → Tensor (복사)
# tf.constant는 복사본을 만듦 → n은 영향 없음
# 메모리를 공유하려면 tf.Variable(n) 사용

print("t:", t)

back = t.numpy()                      # Tensor → numpy (복사)
print("back:", back)

# TensorFlow는 기본적으로 복사본을 만들므로
# numpy 배열을 수정해도 Tensor에 영향 없음
n[0, 0] = 99
print("n after edit:", n)
print("t after n edit:", t)
```

```bash
t: tf.Tensor(
[[10 20]
 [30 40]], shape=(2, 2), dtype=int64)
back: [[10 20]
 [30 40]]
n after edit: [[99 20]
 [30 40]]
t after n edit: tf.Tensor(
[[10 20]
 [30 40]], shape=(2, 2), dtype=int64)
```

> **PyTorch와의 중요한 차이:**<br>
> PyTorch의 `torch.from_numpy()`는 Numpy와 **메모리를 공유**하여 한쪽 수정이 다른 쪽에 즉시 반영됩니다.<br>
> 반면 TensorFlow의 `tf.constant()`와 `.numpy()`는 기본적으로 **데이터를 복사**합니다. 메모리를 공유하려면 `tf.Variable(n)`을 사용해야 합니다.

<br>

---

<br>

## 정리: PyTorch vs TensorFlow Tensor 연산 비교

| 기능 | PyTorch | TensorFlow |
|:---|:---|:---|
| 텐서 생성 | `torch.tensor(...)` | `tf.constant(...)` |
| 0 텐서 | `torch.zeros((2,2))` | `tf.zeros((2,2))` |
| 1 텐서 | `torch.ones((2,2))` | `tf.ones((2,2))` |
| 랜덤 텐서 | `torch.rand((2,2))` | `tf.random.uniform((2,2))` |
| 시드 설정 | `torch.manual_seed(0)` | `tf.random.set_seed(0)` |
| 평균 | `a.mean()` | `tf.reduce_mean(a)` |
| 합계 | `a.sum(dim=0)` | `tf.reduce_sum(a, axis=0)` |
| 최대값 | `a.max()` | `tf.reduce_max(a)` |
| 모양 변경 | `x.view(2,3)` / `x.reshape(2,3)` | `tf.reshape(x, (2,3))` |
| 차원 추가 | `x.unsqueeze(0)` | `tf.expand_dims(x, axis=0)` |
| 차원 제거 | `x.squeeze()` | `tf.squeeze(x)` |
| 연속 범위 | `torch.arange(6)` | `tf.range(6)` |
| Numpy → Tensor | `torch.from_numpy(n)` (공유) | `tf.constant(n)` (복사) |
| Tensor → Numpy | `t.numpy()` | `t.numpy()` |
