# 5-3 자동미분 이해하기


## 단일 변수의 기울기 계산

* 5_3_1.py

```python
import torch

x = torch.tensor(2.0, requires-grad=True)
y = x**3 +2*x
y.backward0
print("x:", x.item0)
print('y:", y.item0)
print('dy/dx:',  x.grad. itemO)
```

## 단일 변수의 기울기 계산

* 5_3_2.py

```python
import torch
x = torch.tensor(1.0,  requires_grad=True)
z = torch.tensor(2,0,  requires_grad=True)
y = (x +2tz)**2
y. backward()
print("x:", x.itemo, "z:", z.itemo)
print('y:', y.item0)
print("dy/dx: ", x.grad. item0)
print('dyldz:", z.grad. item0)
```



## 단일 변수의 기울기 계산

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



## 단일 변수의 기울기 계산

* 5_3_4.py

```python
import torch
x = torch.tensor(2.0, requires-grad=True)
y =xx2
sl = (y**2)
sl.backwardO
print("grad  with tracking :', x.grad. item0)

with torch.no-grad0:
  y2 = x*2
  s2 = (y2**2)
print('y2 requ  res-grad:", y2. requires_grad)
print('s2 req u i res-grad :', s2. requires-grad)
print('x.grad after no_grad path:', x.grr6.;t".0,

x2 = torch.tensor(2.0, requires-grad=True)
y-detached = (x2 *2).detach0
print("detached requires,grad:", y_detached.requires_grad)
```



