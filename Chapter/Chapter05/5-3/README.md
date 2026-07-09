# 5-3 자동미분 이해하기

* PyTorch의 강력한 기능 중 하나인 자동미분(Autograd) 시스템을 학습합니다.
* 자동미분이란 모델 삭습 시 필요한 기울기 계산을 자동으로 수행하는 기능으로, 신경망 학습의 핵심 원리 입니다.
* 간단한 예제를 통해 자동미분의 동작 과저을 실습하고, 이를 활용하여 모델이 학습되는 과정을 이애 합니다.


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

## 기울기 누적과 초기화(zero_() 사용)

  * Pytorch의 기울기는 기본적을 누적됩니다.
  * 이름을 확인하고, .zero_()로 초기화하는 방법을 실습합니다.

* 5_3_3.py

```python
import torch

x = torch.tenso(2. 0, requires_grad=True)

Y=x*3
y.backward()
print("after first back,.riard, grad:", x.grad.item())

Y=x*3
y.backward()
print('after secorrd backrvard (accumulated).  grad:", x.grad.item())

x.grad.zero_()
Y=x*3
y.backward()
print("after zero_0 then backward. grad :", x.grad.item())
```



## 연산 추적 중단(detech()와 torch.no_grad())

  * 미분 계산이 필요 없는 구간에서는 연산 추적을 중단할 수 있습니다.
  * torch.no_grad()나 detech()를 사용하면 PyTorch는 그 구간을 추적하지 않습니다.

* 5_3_4.py

```python
import torch

x = torch.tensor(2.0, requires-grad=True)
y =xx2
sl = (y**2)
sl.backwardO
print("grad  with tracking :', x.grad.item())

with torch.no-grad0:
  y2 = x*2
  s2 = (y2**2)
print('y2 requires-grad:", y2.requires_grad)
print('s2 requires-grad:", s2.requires-grad)
print('x.grad after no_grad path:', x.grad.item())

x2 = torch.tensor(2.0, requires-grad=True)
y-detached = (x2 *2).detach0
print("detached requires grad:", y_detached.requires_grad)
```




