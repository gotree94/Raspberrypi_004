# 5-1 PyTorch란 무엇인가?

딥러닝 프레임워크 PyTorch의 개념과 특징을 이해합니다.
PyTorch가 제공하는 주요 기능과 TensorFlow와의 차이점을 비교하여, 꽤 많은 연구와 산업 분야에서 PyTorch를 사용하는지 살펴봅니다.
또한 PyTorch의 기본 구조를 통해 이후 실습에서 사용할 주요 구성 요소를 미리 익힙니다.

PyTorch(파이토치)는 인공지능과 딥러닝을 쉽게 개발할 수 있도록 도와주는 파이썬 기반 라이브러리입니다.
복잡한 수학 계산(특히 미분)을 자동으로 처리해주기 때문에,
우리는 "모델의 구조"만 정의하고 PyTorch가 알아서 학습(오차 줄이기)을 해줍니다.

## 라이브러리 설치

```Bash
pip install torch torchvision
```

## PyTorch 불러오기 & 버전 확인

PyTorch는 딥러닝을 쉽게 구현하기 위한 파이썬 기반 라이브러리입니다.
이 코드에서는 PyTorch가 정상적으로 설치되어 있는지, 그리고 기본적인 Tensor가 작동하는지 확인합니다.

* 5_1_1.py

```Python
import torch

print("PyTorch version: ", torch.__version__)
print("Tensor test: ", torch.tensor([1, 2, 3]))
```

## 계산기처럼 사용하기

* 5_1_2.py

```Python
import torch

a = torch.tenso(3.0)
b = torch.tenso(2.0)
result=a*b+5
print('Result:",  result
```



## 

* 5_1_3.py

```Python
import torch

x = torch.tensor(2.0,  requires_grad=True)
y1 = x*2
y2 = y1+3
y3 = y2 **2

print("x: ", x)
print("y1: ", y1)
print("y2: ", y2)
print("y3: ", y3)

print("y3 grad-f n : ", y3.grad-fn)
print('y2 grad-f n :", y2. grad-fn)
print("y1 grad-fn:", yl.grad-fn)

```

## 

* 5_1_4.py

```Python

import torch
x = torch.tenso(2.0, requires-grad=True) y=x**2+3*X+1
y.backward0
print("dyldx :', x.grad)
```

## 

* 5_1_5.py

```Python
import torch
x = torch.tensor(1.0,  requires_grad=True) z = torch.tensor(2.0,  requires_grad=True)
y =3*X +4*Z**2
y. backward o
print("dyldx: ", x.grad)
print("dyldz:  ", z. grad)
```

## 

* 5_1_6.py

```Python

import torch
02
03    x = torch.tenso(1 .0, requires-grad=True)
04
05    for step in range(3):
06
07
08
09
10
y = (x -3)**2
y.backward0
print(f'Step {sleprl} | x={x item0. 4fi l y={y rtem0 4f} l grad={x grad.item(): 4f}") x=x-0.1 *x.grad
x = x.detach0.clone0.requires-grad_(True)
```
