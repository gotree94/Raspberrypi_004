# 7-3 자율주행 자동차 학습모델 생성하기


## 1_unzip_video.py

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



## 2_

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


## 3_

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


## 4_Steeri n g_a n g le_h istog ra m. py

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


