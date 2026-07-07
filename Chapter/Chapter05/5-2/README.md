# 5-2 Tensor 실습

PyTorch의 핵심 데이터 구조인 Rensor를 다루는 방법을 학습합니다.
Tensor 의 생성, 형태 변환, 수학 연산 등을 실습하며 데이터 처리의 기본 대념을 익힙니다.
이를 통해 싱견망 연산의 기초가 되는 Tensor의 개념을 명확히 이해할 수 있습니다.

## Tensor 만들기와 기본 성질 확인

* 5_2_1.py

```python
import torch
torch. manua 1_seed (0)
a = torch.tensor([[1.0, 2.0], [3.0, 4.0]l)
b = torch.zeros((2,  2))
c = torch.rand((2,  2))

print("a:", a)
print("b:", b)
print("c:", c)
print("a shape :", a.shape,  "dtype :', a.dtype)
print("b shape:", b.shape, "dtype:-, b.dtype)
print('c shape :", c.shape, "dtype:", c.dtype)
```


## 연산과 축(reduction) 다루기

* 5_2_2.py

```python
import torch

a = torch.tenso(t[1.0, 2.01, t3.0, 4.011)
b = torch.ones((2, 2))

print('a+b:',a+b)
print("a * b:", a'b)
print("mean(a):", a.meanO)
print("sum(a, dim=0):', a.sum(dim=0))
print("max(a) :", a.max0)
```


## 모양 바꾸기(reshape/view), 차원 추가/제거

* 5_2_3.py

```python
import torch

x = torch.arange(6)
y = x.view(2, 3)
z = y.unsqueeze(0)
z2 = z.squeeze0
r = y.reshape(3,  2)

print("x:', x)
print("v:", y)
print("2 shape:",  z.shape)
print("22 shape:",  z2.shape)
print('r:', r)
```


## Numpy <-> Tensor 변환과 메모리 공유

* 5_2_1.py

```python
import torch
import numpy as np

n = np.array([[10, 20], [30, 40]])
t = torch.from_numpy(n)
t[0, o] =99
print("n after t edit:", n)

back = t.numpy()
back[l, t] =77
print("t after back edit;", t)
```


## Tensor 만들기와 기본 성질 확인

* 5_2_1.py

```python

```


