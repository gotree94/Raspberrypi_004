# 5-1 PyTorch란 무엇인가?

딥러닝 프레임워크 PyTorch의 개념과 특징을 이해합니다.<br>
PyTorch가 제공하는 주요 기능과 TensorFlow와의 차이점을 비교하여, <br>
꽤 많은 연구와 산업 분야에서 PyTorch를 사용하는지 살펴봅니다.<br>
또한 PyTorch의 기본 구조를 통해 이후 실습에서 사용할 주요 구성 요소를 미리 익힙니다.<br>

PyTorch(파이토치)는 인공지능과 딥러닝을 쉽게 개발할 수 있도록 도와주는 파이썬 기반 라이브러리입니다.<br>
복잡한 수학 계산(특히 미분)을 자동으로 처리해주기 때문에,<br>
우리는 "모델의 구조"만 정의하고 PyTorch가 알아서 학습(오차 줄이기)을 해줍니다.<br>

OyTorch(파이토치)는 인공지능과 딥러닝을 쉽게 개발할 수 있도록 도와주는 파이썬 기반 라이브러리 입니다.<br>
복합한 수삭 계산(특히 미ㅜㄴ)을 자동으로 처리해 주기 때문에, <br>
우리는 "모델의 구조"만 정의하고  PyTorch가 알아서 학습(오차 줄이기)을 해줍니다.

<br>
---
<br>

## 라이브러리 설치

```Bash
pip install torch torchvision
```

```Bash
(base) C:\Users\Administrator>pip install torch torchvision
Requirement already satisfied: torch in c:\programdata\anaconda3\lib\site-packages (2.6.0+cu124)
Requirement already satisfied: torchvision in c:\programdata\anaconda3\lib\site-packages (0.21.0+cu124)
Requirement already satisfied: filelock in c:\programdata\anaconda3\lib\site-packages (from torch) (3.29.0)
Requirement already satisfied: typing-extensions>=4.10.0 in c:\programdata\anaconda3\lib\site-packages (from torch) (4.15.0)
Requirement already satisfied: networkx in c:\programdata\anaconda3\lib\site-packages (from torch) (3.6.1)
Requirement already satisfied: jinja2 in c:\programdata\anaconda3\lib\site-packages (from torch) (3.1.6)
Requirement already satisfied: fsspec in c:\programdata\anaconda3\lib\site-packages (from torch) (2026.4.0)
Requirement already satisfied: setuptools in c:\programdata\anaconda3\lib\site-packages (from torch) (70.2.0)
Requirement already satisfied: sympy==1.13.1 in c:\programdata\anaconda3\lib\site-packages (from torch) (1.13.1)
Requirement already satisfied: mpmath<1.4,>=1.1.0 in c:\programdata\anaconda3\lib\site-packages (from sympy==1.13.1->torch) (1.3.0)
Requirement already satisfied: numpy in c:\programdata\anaconda3\lib\site-packages (from torchvision) (1.26.4)
Requirement already satisfied: pillow!=8.3.*,>=5.3.0 in c:\programdata\anaconda3\lib\site-packages (from torchvision) (12.2.0)
Requirement already satisfied: MarkupSafe>=2.0 in c:\programdata\anaconda3\lib\site-packages (from jinja2->torch) (3.0.3)
```

<br>
---
<br>

## PyTorch 불러오기 & 버전 확인
  
PyTorch는 딥러닝을 쉽게 구현하기 위한 파이썬 기반 라이브러리입니다.<br>
이 코드에서는 PyTorch가 정상적으로 설치되어 있는지, 그리고 기본적인 Tensor가 작동하는지 확인합니다.

* 5_1_1.py

```Python
import torch

print("PyTorch version: ", torch.__version__)
print("Tensor test: ", torch.tensor([1, 2, 3]))
```

```Bash
PyTorch version:  2.6.0+cu124
Tensor test:  tensor([1, 2, 3])
```

<br>
---
<br>

## 계산기처럼 사용하기

* PyTorch는 단순한 수학 계산도 할 수 있습니다.

* 5_1_2.py

```Python
import torch

a = torch.tensor(3.0)
b = torch.tensor(2.0)
result=a*b+5
print("Result:",  result)
```

```Bash
Result: tensor(11.)
```

<br>
---
<br>

## Tensor는 계산 과정을 기억한다.

* PyTorch의 핵심은 계산 과정을 자동으로 추적한다는 것입니다.
* requies_grad = True로 설정하면 연산 과정이 모두 저장되너, 나중에 자동미분에 활용됩니다.

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

print("y3 grad_fn:", y3.grad_fn)
print("y2 grad_fn:", y2.grad_fn)
print("y1 grad_fn:", y1.grad_fn)
```

```Bash
(base) C:\Users\Administrator>python 5_1_3.py
x:  tensor(2., requires_grad=True)
y1:  tensor(4., grad_fn=<MulBackward0>)
y2:  tensor(7., grad_fn=<AddBackward0>)
y3:  tensor(49., grad_fn=<PowBackward0>)
y3 grad_fn: <PowBackward0 object at 0x0000020782A01000>
y2 grad_fn: <AddBackward0 object at 0x0000020782A01000>
y1 grad_fn: <MulBackward0 object at 0x0000020782A01000>
```

<br>
---
<br>

## 자동미분으로 기울기 구하기

* PyTorch는 수학적으로 미분 값을 자동으로 계산할 수 있습니다.
* 이는 "기울기(gradient)" 계산이며, 학습(오차 수정)의 핵심 개념 입니다.

* 5_1_4.py

```Python
import torch

x = torch.tensor(2.0, requires_grad=True)
y=x**2+3*x+1
y.backward()
print("dy/dx:", x.grad)
```

```Bash
(base) C:\Users\Administrator>python 5_1_4.py
dy/dx: tensor(7.)
```

<br>
---
<br>

## 여러 변수의 자동 미분

* 여러 변수가 동시에 있을 때도 PyTorch는 각각의 미분 값을 자동으로 계산합니다.

* 5_1_5.py

```Python
import torch
x = torch.tensor(1.0, requires_grad=True)
z = torch.tensor(2.0, requires_grad=True)

y =3*x+4*z**2
y.backward()

print("dyldx:", x.grad)
print("dyldz:", z.grad)
```

```Bash
dyldx: tensor(3.)
dyldz: tensor(16.)
```

<br>
---
<br>

## 기울기를 이용해 오차를 줄이는 방향으로 이동

* 이 예제는 "학습의 원리"를 보여줍니다.
* 목표는 y = (x - 3)^2 가 최소(=0)가 되는 x를 찾는 것입니다.
* PyTorch는 기울기를 이용해 오차를 줄이는 방향으로 x를 조정합니다.

* 5_1_6.py

```Python
import torch

x = torch.tensor(1.0, requires_grad=True)

for step in range(3):
    y = (x -3)**2
    y.backward()
    print(f"Step{step+1} | x={x.item():.4f} | y={y.item():.4f} | grad={x.grad.item():.4f}")
    x = x - 0.1*x.grad
    x = x.detach().clone().requires_grad_(True)
```

```Bash
(base) C:\Users\Administrator>python 5_1_6.py
Step1 | x=1.0000 | y=4.0000 | grad=-4.0000
Step2 | x=1.4000 | y=2.5600 | grad=-3.2000
Step3 | x=1.7200 | y=1.6384 | grad=-2.5600
```
