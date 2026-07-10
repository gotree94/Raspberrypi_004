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
# PyTorch 라이브러리를 불러옴 (딥러닝 및 텐서 연산용)
import torch

# 현재 설치된 PyTorch의 버전을 출력
print("PyTorch version: ", torch.__version__)
# [1,2,3] 값으로 구성된 텐서를 생성하고 "Tensor test:"라는 문구와 함께 출력
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

---

## 라이브러리 설치

```bash
pip install tensorflow
```

```bash
(base) C:\Users\Administrator>pip install tensorflow
Requirement already satisfied: tensorflow in c:\programdata\anaconda3\lib\site-packages (2.18.0)
Requirement already satisfied: absl-py>=1.0.0 in c:\programdata\anaconda3\lib\site-packages (from tensorflow) (2.2.2)
Requirement already satisfied: astunparse>=1.6.0 in c:\programdata\anaconda3\lib\site-packages (from tensorflow) (1.6.3)
Requirement already satisfied: flatbuffers>=24.3.25 in c:\programdata\anaconda3\lib\site-packages (from tensorflow) (25.2.10)
Requirement already satisfied: gast!=0.5.0,!=0.5.1,!=0.5.2,>=0.2.1 in c:\programdata\anaconda3\lib\site-packages (from tensorflow) (0.6.0)
Requirement already satisfied: google-pasta>=0.1.1 in c:\programdata\anaconda3\lib\site-packages (from tensorflow) (0.2.0)
Requirement already satisfied: libclang>=13.0.0 in c:\programdata\anaconda3\lib\site-packages (from tensorflow) (18.1.1)
...
```

<br>

---

<br>


# TensorFlow

* CPU만 사용:
    * pip install tensorflow 한 줄이면 끝

* GPU 가속 사용:
   * CUDA 지원 GPU 필요 (NVIDIA)
   * CUDA Toolkit + cuDNN 설치 필요
   * TensorFlow 버전과 CUDA 버전 호환 확인 (예: TF 2.16+는 CUDA 11.8, TF 2.18+는 CUDA 12.x)
   * pip install tensorflow[and-cuda] 또는 pip install tensorflow 후 알아서 GPU 인식

```
pip install tensorflow
```

```

```

## TensorFlow 불러오기 & 버전 확인

TensorFlow는 Google이 개발한 딥러닝 프레임워크입니다.<br>
이 코드에서는 TensorFlow가 정상적으로 설치되어 있는지, 그리고 기본적인 Tensor가 작동하는지 확인합니다.

* tf_1_1.py

```python
# TensorFlow 라이브러리를 불러옴 (딥러닝 및 텐서 연산용)
import tensorflow as tf

# 현재 설치된 TensorFlow의 버전을 출력
print("TensorFlow version: ", tf.__version__)
# [1,2,3] 값으로 구성된 텐서를 생성하고 "Tensor test:"라는 문구와 함께 출력
print("Tensor test: ", tf.constant([1, 2, 3]))
```

```bash
TensorFlow version:  2.18.0
Tensor test:  tf.Tensor([1 2 3], shape=(3,), dtype=int32)
```

<br>

---

<br>

## 계산기처럼 사용하기

TensorFlow는 단순한 수학 계산도 할 수 있습니다.

* tf_1_2.py

```python
import tensorflow as tf

a = tf.constant(3.0)
b = tf.constant(2.0)
result = a * b + 5
print("Result:", result)
```

```bash
Result: tf.Tensor(11.0, shape=(), dtype=float32)
```

<br>

---

<br>

## Tensor는 계산 과정을 기록한다

TensorFlow 2.x에서는 `tf.GradientTape` 컨텍스트 안에서 연산하면 자동 미분을 위한 계산 과정이 기록됩니다.

* tf_1_3.py

```python
import tensorflow as tf

x = tf.Variable(2.0)

with tf.GradientTape(persistent=True) as tape:
    y1 = x * 2
    y2 = y1 + 3
    y3 = y2 ** 2

print("x: ", x)
print("y1: ", y1)
print("y2: ", y2)
print("y3: ", y3)

# tape는 그라디언트를 계산하는 데 사용됨 (PyTorch의 grad_fn 역할)
print("dy3/dy2:", tape.gradient(y3, y2))
print("dy2/dy1:", tape.gradient(y2, y1))
print("dy1/dx:", tape.gradient(y1, x))

del tape
```

```bash
x:  <tf.Variable 'Variable:0' shape=() dtype=float32, numpy=2.0>
y1:  tf.Tensor(4.0, shape=(), dtype=float32)
y2:  tf.Tensor(7.0, shape=(), dtype=float32)
y3:  tf.Tensor(49.0, shape=(), dtype=float32)
dy3/dy2: tf.Tensor(14.0, shape=(), dtype=float32)
dy2/dy1: tf.Tensor(1.0, shape=(), dtype=float32)
dy1/dx: tf.Tensor(2.0, shape=(), dtype=float32)
```

> **PyTorch와의 차이:** PyTorch는 `requires_grad=True`를 설정하면 자동으로 연산 그래프를 추적하고, `backward()`로 미분합니다.<br>
> TensorFlow는 `tf.GradientTape` 블록 안에서 연산을 감싸야 그래프가 기록되며, `tape.gradient()`로 미분합니다.

<br>

---

<br>

## 자동미분으로 기울기 구하기

TensorFlow는 수학적으로 미분 값을 자동으로 계산할 수 있습니다.
이는 "기울기(gradient)" 계산이며, 학습(오차 수정)의 핵심 개념입니다.

* tf_1_4.py

```python
import tensorflow as tf

x = tf.Variable(2.0)

with tf.GradientTape() as tape:
    y = x ** 2 + 3 * x + 1

dy_dx = tape.gradient(y, x)
print("dy/dx:", dy_dx)
```

```bash
dy/dx: tf.Tensor(7.0, shape=(), dtype=float32)
```

<br>

---

<br>

## 여러 변수의 자동 미분

여러 변수가 동시에 있을 때도 TensorFlow는 각각의 미분 값을 자동으로 계산합니다.

* tf_1_5.py

```python
import tensorflow as tf

x = tf.Variable(1.0)
z = tf.Variable(2.0)

with tf.GradientTape() as tape:
    y = 3 * x + 4 * z ** 2

dy_dx, dy_dz = tape.gradient(y, [x, z])

print("dy/dx:", dy_dx)
print("dy/dz:", dy_dz)
```

```bash
dy/dx: tf.Tensor(3.0, shape=(), dtype=float32)
dy/dz: tf.Tensor(16.0, shape=(), dtype=float32)
```

<br>

---

<br>

## 기울기를 이용해 오차를 줄이는 방향으로 이동

이 예제는 "학습의 원리"를 보여줍니다.
목표는 y = (x - 3)² 가 최소(=0)가 되는 x를 찾는 것입니다.
TensorFlow는 기울기를 이용해 오차를 줄이는 방향으로 x를 조정합니다.

* tf_1_6.py

```python
import tensorflow as tf

x = tf.Variable(1.0)

for step in range(3):
    with tf.GradientTape() as tape:
        y = (x - 3) ** 2

    grad = tape.gradient(y, x)
    print(f"Step{step + 1} | x={x.numpy():.4f} | y={y.numpy():.4f} | grad={grad.numpy():.4f}")
    x.assign_sub(0.1 * grad)  # x = x - 0.1 * grad
```

```bash
Step1 | x=1.0000 | y=4.0000 | grad=-4.0000
Step2 | x=1.4000 | y=2.5600 | grad=-3.2000
Step3 | x=1.7200 | y=1.6384 | grad=-2.5600
```

<br>

---

<br>

## 정리: PyTorch vs TensorFlow 문법 비교

| 기능 | PyTorch | TensorFlow |
|:---|:---|:---|
| 라이브러리 임포트 | `import torch` | `import tensorflow as tf` |
| 텐서 생성 | `torch.tensor([1, 2, 3])` | `tf.constant([1, 2, 3])` |
| 변수 (학습 대상) | `torch.tensor(..., requires_grad=True)` | `tf.Variable(...)` |
| 자동미분 시작 | `y.backward()` | `tape.gradient(y, x)` |
| 그래프 기록 방식 | 자동 (requires_grad) | 명시적 (`tf.GradientTape` 블록) |
| 기울기 접근 | `x.grad` | `tape.gradient(y, x)`의 반환값 |
| 값 읽기 | `x.item()` | `x.numpy()` |
| 값 업데이트 | `x = x - lr * grad` + `detach().clone()` | `x.assign_sub(lr * grad)` |
| 버전 확인 | `torch.__version__` | `tf.__version__` |
