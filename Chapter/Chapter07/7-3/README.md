# 7-3 자율주행 자동차 학습모델 생성하기

* 수집된 주행 데이터를 이용해 자율주행 자동차의 인공지능 모델을 학습하는 과정을 실습합니다.
* PyTorch를 사용하여 신경망을 구성하고, 입력 영상과 조향각도 데이터를 바탕으로 모델을 학습시킵니다.
* 훈련이 완료된 모델은 자동차의 판단 알고리즘으로 활용되며, 이후 라즈베리파이에 배포 하여 실제 주행제어에 적용할 수 있습니다.
* 이를 통해 학습자는 인공디능 모델 학습의 전 과정을 이애하고, 자율주행의 핵심 기술을 직접 구현 할 수 있습니다.


## 1. video.zip 파일 압축 풀기

* 1_unzip_video.py

* 6장에서 라즈베리파이에서 학습한 데이터인 [video.zip]파일을 준비합니다.
* Document 폴더로 복사하였기 때문에 문서 폴더에서 확인 할 수 있습니다.

```python
import zipfite
j.mport os
import shutil
current_dir = os.path.dirname(os.path.abspath(--fite--))
zip_path = os.path.join(current_dir,'video.zip') extract_fotder = os.path. join(current-dir,'video')
10     if os. path.exists(extract-folded
1'l
12
sh uti l. rmtree(extract_f older)
13     with zipfile.ZipFile(zip_path, r') as zip_ref:
14
'1 5
zip-ref  . extracta ll(current-d ir)
16     print("done")
```



## 2. 라이브터리 설치 확인

* 모델을 만들기 위해 다양한 라이브러리가 필요로 합니다.
* 라이브러리가 잘 설치되었는지 확인하는 코드를 작성해 봅니다.
* 코드 작성 후 [2_library_check.py] 이름으로 저장합니다.

* 2_library_check.py

```python
import os
import random
import pickle
import fnmatch
from datetime import datetime
import numpy as np
import cv2
import torch
import torch.nn as nn
import torch.optim as optim
f rom sklearn.model_selection import train_test_split import matptotlib
import matplotlib.pyplot  as plt
import PIL
from PIL import Image
import pandas as pd
def safe_ver(module,  attr="__version__")
return getattr(module, attr, "N/A')
import sys
print("=== Python Environmgnt  ===")
print(f'python: {sys.version.splitO[0]]")
printo
print("=== Library Vgr5ien5 ===")
print(f"torch:  {safe_ver(torch)}')
print(f "numpy: {safe_ver(np)}")
print(f'opencv-python (cv2): {safe_ver(cv2)}') print(f"matptotlib: {safe_ver(matptottib)}')
print(f 'pandas : {safe_ver(pd)}")
print(f'scikit-learn: {safe_ver(__import__('sktearn'))}") print(f"Pitlow (PIL) : {safe_ver(PIL)}")
printo
print("=== PyTorch lsyi6s tnfs ===")
cuda_available  = torch.cuda.is_avaitableo print(f"CUDA  available: {cuda-avaitable}") print(f"torch.version.cuda: {getattr(torch.version,
t ry:
cudnn_ver = torch.backends.cudnn.versiono except Exception:
cudnn_ver  =None
'cuda', None)]")
print(f"cuDNN version: {cudnn-ver}")
if  cuda_availabte:
device = torch.device("cuda")
print(f"GPU count: {torch.cuda.device-countO}") print(f"GPU  name[0] : {torch.cuda.get-device_name(0)}")
else:
device = torch.device('cpu')
print('Using  CPU")
print0
try:
x = torch.randn(2,  3, device=device) y = torch.randn(2,  3, device=device) 2=(x+y).meanQ.item0
print("PyTorch test: OK") except Exception as e:
print('PyTorch test: FAI L") print(e)
```


## 3. 데이터 불러오기

* 데이터를 불러와 이미지로 확인해보도록 합니다.
* 너무 터무니 없는 데이터가 들어가 있는지 확인하는 과정으로 이때 이상한 데이터가 있다면 다시 학습 하도록 합니다.
* 코드 작성 후 [3_data_shck.py] 이름으로 저장합니다.

* 3_data_shck.py

```python
import os
import random
import fnmatch
import numpy as np import torch
from PIL import Image
import matplotlib.pyplot  as plt
data-dir = os.path. join(os.path.dirname(--fite--),   "video")
image-paths = []
steering_angles = []
for filename in os.Iistdir(data_dir):
if  fnmatch,fnmatch(fitename,  "*. png") :
image_paths.  append(os.  path. j oin (data_dir,  fi lename) ) angle =int(fitename[-7  : -4])
steering_angles.  append(ang1e)
random_indices = random.sampte(ran9e(len(image_paths)),  10) fig, axes = plt.subplots(2, 5, figsize=(fS, 0))
for i, ax in enumerate(axes.flat):
idx = random_indices[i]
img = 16.r..open(image-paths[idx]).convert("RGB") ax.imshow(img)
ax.set-title(f" Angle : {steering,ang  les Iidx]]") ax.axis('off")
plt.tight-layout0 plt.showO
```


## 4. 조향각의 분포를 확인

* 저장된 이미지 파일 이름으로 조향각 데이터를 추출한고,
* 조향각이 어떤 분포를 가젺는지 히스토그램으로 시작화하는 코드를 작성합니다.
* 코드 작성 후[4_Street_angle_histogram.py] 이름으로 저장합니다.

* 4_Steering_angle_histogram.py

```python
import os
import fnmatch
import random
import numpy as np
import pandas as pd
import matptotlib. pyplot as plt
import torch

data_dir = os.path. join(os.path.dirname(__file__),   "video") image-paths = []
steering-angles  = []
14     for f ilename in os.listdi(data_dir):
15
16
if fnmatch.fnmatch(filename,'" png'):
image_paths.append(os.path.ioin(data_dir,    f ilename))
17
'18
19
angle =int(f rlename[-7 :-4]) steering_a  ng les.append(a  ngle)
20 6f = pd. DataFrame(i"SteenngAngle"  : steering_angles))
21
22    plt.f igure(f igsize=(1 0, 5))
1Q
24
26
28
plt.hist(df['SteerrngAngle'],   bins=30,  color="skybiue", edgecolor="black') plt.title("Distribution  of Steerrng Angles')
plt.xlabel('Steer-i ng Angie') plt.ylabel(" Freq u e n cy" ) plt.grid(True)
plt.showQ
```

## 5.학습 데이터와 검증 데이터를 분리

* 이미지 파일 이름에서 조향각 데이터를 추축한 위
* 학습용(train)과 검증용(validation)  epdlxjfh skdnrh,
* 두 데이터의 조향각 분포를 히스토그램으로 비교하는 코드입니다.
* 증, 데이터가 균등하게 분리되었는지 시각적으로 확인하는 역할을 합니다.

* 5_Train_validation_split.py

```python

```







## 6. 이미지 읽어오기 및 정규화

* 이미지를 정규화하여 학습 효과를 높여보도록 합니다.
* 정규화 과정은 쉽게 말해 데이터의 스케일을 일정하게 맞추는 작업으로, <br>
  픽셀값의 범위를 조정하여 모델이 이미지의특징을 더 안정적으로 학습할 수 있도록 도와줍니다.


* 6_Image_input_and_normalization_functions.py

```python


```


## 7.nvidia 모델 구성

* 그래픽카드 제조회사인 NVIDIA에서 차선 인식을 위한 논문에서 제공된 모델을 이용하여 학습모델을 구성합니다.
* NVIDIA 자율주행 구조를 따른 딥러닝 모델을 구성하고 모델의 전체 구조를 출력하는기능을 코드를 작성합니다.

* 7_NVIDIA_model_configuration.py

```python

```



##8.학습 데이터와 검증 데이터를 분리

* 모든 이미지를 이용하여 삭습하기에는 너무 많은 시간이 소요되므로 학습, <br>
  검증으로 분리된 데이터에서 랜덤하게 추출하여 학습 데이터와 검증데이터를 생겅하는 코드를 작성해봅니다.

* 8_Generating_traing_data.py

```python


```



## 9. 모델 학습(10분가량 소요)

* 데이터를 이용하여 실제 학습하는 과정으로 컴퓨터의 성능에 따라서 5~20분가량 소요됩니다.
* 학습이 끝나면 모델데이터가 생성됩니다.

* 9_make_model.py

```python


```


## 10.결과확인

* history.pickle 파일을 이용하여 모델 학습 과정 중 저장된 손실값(loss, val_loss)을 불러와서 에폭별로 학습 손실과 검증 손실이 어떻게 변했는지 그래프로 시각화하는 기능을 수행하는 코드를 작성해 봅니다.
* 모델의 생성 시점에 따랄 모델이 저장된 폴더의 이름이 변경되므로 6줄의 폴더는 생성된 시간의 폴터 이름으로 변경합니다.

* 10_Result_analysis.py

```python


```





