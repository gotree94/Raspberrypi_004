(반드시 PC에서 작업할것)

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

```Bash
pip install tensorflow
```

```Bash
(base) C:\Users\user>pip install tensorflow
Defaulting to user installation because normal site-packages is not writeable
Collecting tensorflow
  Downloading tensorflow-2.21.0-cp313-cp313-win_amd64.whl.metadata (4.5 kB)
Collecting absl-py>=1.0.0 (from tensorflow)
  Downloading absl_py-2.5.0-py3-none-any.whl.metadata (3.3 kB)
Collecting astunparse>=1.6.0 (from tensorflow)
  Downloading astunparse-1.6.3-py2.py3-none-any.whl.metadata (4.4 kB)
Requirement already satisfied: flatbuffers>=25.9.23 in c:\users\user\appdata\roaming\python\python313\site-packages (from tensorflow) (25.12.19)
Collecting gast!=0.5.0,!=0.5.1,!=0.5.2,>=0.2.1 (from tensorflow)
  Downloading gast-0.7.0-py3-none-any.whl.metadata (1.5 kB)
Collecting google_pasta>=0.1.1 (from tensorflow)
  Downloading google_pasta-0.2.0-py3-none-any.whl.metadata (814 bytes)
Collecting libclang>=13.0.0 (from tensorflow)
  Downloading libclang-18.1.1-py2.py3-none-win_amd64.whl.metadata (5.3 kB)
Collecting opt_einsum>=2.3.2 (from tensorflow)
  Downloading opt_einsum-3.4.0-py3-none-any.whl.metadata (6.3 kB)
Requirement already satisfied: packaging in c:\programdata\anaconda3\lib\site-packages (from tensorflow) (25.0)
Collecting protobuf<8.0.0,>=6.31.1 (from tensorflow)
  Downloading protobuf-7.35.1-cp310-abi3-win_amd64.whl.metadata (595 bytes)
Requirement already satisfied: requests<3,>=2.21.0 in c:\programdata\anaconda3\lib\site-packages (from tensorflow) (2.32.5)
Requirement already satisfied: setuptools in c:\programdata\anaconda3\lib\site-packages (from tensorflow) (80.9.0)
Requirement already satisfied: six>=1.12.0 in c:\programdata\anaconda3\lib\site-packages (from tensorflow) (1.17.0)
Collecting termcolor>=1.1.0 (from tensorflow)
  Downloading termcolor-3.3.0-py3-none-any.whl.metadata (6.5 kB)
Requirement already satisfied: typing_extensions>=3.6.6 in c:\programdata\anaconda3\lib\site-packages (from tensorflow) (4.15.0)
Requirement already satisfied: wrapt>=1.11.0 in c:\programdata\anaconda3\lib\site-packages (from tensorflow) (1.17.0)
Collecting grpcio<2.0,>=1.24.3 (from tensorflow)
  Downloading grpcio-1.82.1-cp313-cp313-win_amd64.whl.metadata (3.8 kB)
Collecting keras>=3.12.0 (from tensorflow)
  Downloading keras-3.15.0-py3-none-any.whl.metadata (6.3 kB)
Requirement already satisfied: numpy>=1.26.0 in c:\users\user\appdata\roaming\python\python313\site-packages (from tensorflow) (2.3.5)
Collecting h5py<3.15.0,>=3.11.0 (from tensorflow)
  Downloading h5py-3.14.0-cp313-cp313-win_amd64.whl.metadata (2.7 kB)
Collecting ml_dtypes<1.0.0,>=0.5.1 (from tensorflow)
  Downloading ml_dtypes-0.5.4-cp313-cp313-win_amd64.whl.metadata (9.2 kB)
Requirement already satisfied: charset_normalizer<4,>=2 in c:\programdata\anaconda3\lib\site-packages (from requests<3,>=2.21.0->tensorflow) (3.4.4)
Requirement already satisfied: idna<4,>=2.5 in c:\programdata\anaconda3\lib\site-packages (from requests<3,>=2.21.0->tensorflow) (3.11)
Requirement already satisfied: urllib3<3,>=1.21.1 in c:\programdata\anaconda3\lib\site-packages (from requests<3,>=2.21.0->tensorflow) (2.5.0)
Requirement already satisfied: certifi>=2017.4.17 in c:\programdata\anaconda3\lib\site-packages (from requests<3,>=2.21.0->tensorflow) (2025.11.12)
Requirement already satisfied: wheel<1.0,>=0.23.0 in c:\programdata\anaconda3\lib\site-packages (from astunparse>=1.6.0->tensorflow) (0.45.1)
Requirement already satisfied: rich in c:\programdata\anaconda3\lib\site-packages (from keras>=3.12.0->tensorflow) (14.2.0)
Collecting namex (from keras>=3.12.0->tensorflow)
  Downloading namex-0.1.0-py3-none-any.whl.metadata (322 bytes)
Collecting optree (from keras>=3.12.0->tensorflow)
  Downloading optree-0.19.1-cp313-cp313-win_amd64.whl.metadata (32 kB)
Requirement already satisfied: markdown-it-py>=2.2.0 in c:\programdata\anaconda3\lib\site-packages (from rich->keras>=3.12.0->tensorflow) (2.2.0)
Requirement already satisfied: pygments<3.0.0,>=2.13.0 in c:\programdata\anaconda3\lib\site-packages (from rich->keras>=3.12.0->tensorflow) (2.19.2)
Requirement already satisfied: mdurl~=0.1 in c:\programdata\anaconda3\lib\site-packages (from markdown-it-py>=2.2.0->rich->keras>=3.12.0->tensorflow) (0.1.2)
Downloading tensorflow-2.21.0-cp313-cp313-win_amd64.whl (351.2 MB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 351.2/351.2 MB 11.4 MB/s  0:00:31
Downloading grpcio-1.82.1-cp313-cp313-win_amd64.whl (5.0 MB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 5.0/5.0 MB 11.2 MB/s  0:00:00
Downloading h5py-3.14.0-cp313-cp313-win_amd64.whl (2.9 MB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 2.9/2.9 MB 8.9 MB/s  0:00:00
Downloading ml_dtypes-0.5.4-cp313-cp313-win_amd64.whl (212 kB)
Downloading protobuf-7.35.1-cp310-abi3-win_amd64.whl (439 kB)
Downloading absl_py-2.5.0-py3-none-any.whl (137 kB)
Downloading astunparse-1.6.3-py2.py3-none-any.whl (12 kB)
Downloading gast-0.7.0-py3-none-any.whl (22 kB)
Downloading google_pasta-0.2.0-py3-none-any.whl (57 kB)
Downloading keras-3.15.0-py3-none-any.whl (1.7 MB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.7/1.7 MB 11.1 MB/s  0:00:00
Downloading libclang-18.1.1-py2.py3-none-win_amd64.whl (26.4 MB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 26.4/26.4 MB 11.1 MB/s  0:00:02
Downloading opt_einsum-3.4.0-py3-none-any.whl (71 kB)
Downloading termcolor-3.3.0-py3-none-any.whl (7.7 kB)
Downloading namex-0.1.0-py3-none-any.whl (5.9 kB)
Downloading optree-0.19.1-cp313-cp313-win_amd64.whl (343 kB)
Installing collected packages: namex, libclang, termcolor, protobuf, optree, opt_einsum, ml_dtypes, h5py, grpcio, google_pasta, gast, astunparse, absl-py, keras, tensorflow
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╺━━ 14/15 [tensorflow]  WARNING: The scripts saved_model_cli.exe, tf_upgrade_v2.exe, tflite_convert.exe and toco.exe are installed in 'C:\Users\user\AppData\Roaming\Python\Python313\Scripts' which is not on PATH.
  Consider adding this directory to PATH or, if you prefer to suppress this warning, use --no-warn-script-location.
ERROR: pip's dependency resolver does not currently take into account all the packages that are installed. This behaviour is the source of the following dependency conflicts.
streamlit 1.51.0 requires protobuf<7,>=3.20, but you have protobuf 7.35.1 which is incompatible.
Successfully installed absl-py-2.5.0 astunparse-1.6.3 gast-0.7.0 google_pasta-0.2.0 grpcio-1.82.1 h5py-3.14.0 keras-3.15.0 libclang-18.1.1 ml_dtypes-0.5.4 namex-0.1.0 opt_einsum-3.4.0 optree-0.19.1 protobuf-7.35.1 tensorflow-2.21.0 termcolor-3.3.0

(base) C:\Users\user>
```

* 스크립트 PATH 누락: C:\Users\user\AppData\Roaming\Python\Python313\Scripts를 환경변수 PATH에 추가해야 saved_model_cli 등을 사용할 수 있습니다.
* protobuf 충돌: Streamlit이 protobuf<7을 요구하는데 TF가 protobuf 7.35.1을 설치했지만, Streamlit을 안 쓴다면 무시해도 됩니다.
* GPU 사용하려면: NVIDIA GPU + CUDA Toolkit + cuDNN이 필요합니다. TF 2.21은 CUDA 12.x 대응입니다.

* 간단히 확인:

```python
import tensorflow as tf
print(tf.__version__)
print("GPU:", tf.config.list_physical_devices('GPU'))
```

```Bash
WARNING: All log messages before absl::InitializeLog() is called are written to STDERR
I0000 00:00:1783644875.252990    9340 port.cc:153] oneDNN custom operations are on. You may see slightly different numerical results due to floating-point round-off errors from different computation orders. To turn them off, set the environment variable `TF_ENABLE_ONEDNN_OPTS=0`.
WARNING: All log messages before absl::InitializeLog() is called are written to STDERR
I0000 00:00:1783644879.913355    9340 port.cc:153] oneDNN custom operations are on. You may see slightly different numerical results due to floating-point round-off errors from different computation orders. To turn them off, set the environment variable `TF_ENABLE_ONEDNN_OPTS=0`.
2.21.0
WARNING:tensorflow:TensorFlow GPU support is not available on native Windows for TensorFlow >= 2.11. Even if CUDA/cuDNN are installed, GPU will not be used. Please use WSL2 or the TensorFlow-DirectML plugin.
GPU: []
```

* TensorFlow 2.21.0 정상 설치 확인 (2.21.0), CPU 모드로 동작 중입니다.
* 중요: TensorFlow 2.11 이후로 네이티브 Windows에서 GPU 지원이 중단되었습니다. GPU를 사용하려면 두 가지 방법이 있습니다:
  * WSL2 + CUDA (권장) — WSL2에 Ubuntu 설치 후 그 안에서 TF+GPU 사용
  * TensorFlow-DirectML plugin — pip install tensorflow-directml-plugin (DirectML 기반, 성능은 WSL2보다 낮음)


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

```
WARNING: All log messages before absl::InitializeLog() is called are written to STDERR
I0000 00:00:1783645136.231235    8436 port.cc:153] oneDNN custom operations are on. You may see slightly different numerical results due to floating-point round-off errors from different computation orders. To turn them off, set the environment variable `TF_ENABLE_ONEDNN_OPTS=0`.
WARNING: All log messages before absl::InitializeLog() is called are written to STDERR
I0000 00:00:1783645137.866315    8436 port.cc:153] oneDNN custom operations are on. You may see slightly different numerical results due to floating-point round-off errors from different computation orders. To turn them off, set the environment variable `TF_ENABLE_ONEDNN_OPTS=0`.
TensorFlow version:  2.21.0
I0000 00:00:1783645139.582911    8436 cpu_feature_guard.cc:227] This TensorFlow binary is optimized to use available CPU instructions in performance-critical operations.
To enable the following instructions: SSE3 SSE4.1 SSE4.2 AVX AVX2 AVX_VNNI FMA, in other operations, rebuild TensorFlow with the appropriate compiler flags.
Tensor test:  tf.Tensor([1 2 3], shape=(3,), dtype=int32)
```

* 경고를 끄려면 코드 상단에 아래를 추가하세요:
```
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # 0=ALL, 1=INFO, 2=WARNING, 3=ERROR
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'  # oneDNN 메시지 제거

import tensorflow as tf
print("TensorFlow version: ", tf.__version__)
print("Tensor test: ", tf.constant([1, 2, 3]))
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
