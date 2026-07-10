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
import zipfile
import os
import shutil

current_dir = os.path.dirname(os.path.abspath(__file__))
zip_path = os.path.join(current_dir, 'video.zip')
extract_folder = os.path.join(current_dir, 'video')

if os.path.exists(extract_folder):
    shutil.rmtree(extract_folder)

with zipfile.ZipFile(zip_path, 'r') as zip_ref:
    zip_ref.extractall(current_dir)

print("done")
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
from sklearn.model_selection import train_test_split
import matplotlib
import matplotlib.pyplot as plt
import PIL
from PIL import Image
import pandas as pd

def safe_ver(module, attr="__version__"):
    return getattr(module, attr, "N/A")

import sys
print("=== Python Environment ===")
print(f"python: {sys.version.split()[0]}")
print()
print("=== Library Versions ===")
print(f"torch: {safe_ver(torch)}")
print(f"numpy: {safe_ver(np)}")
print(f"opencv-python (cv2): {safe_ver(cv2)}")
print(f"matplotlib: {safe_ver(matplotlib)}")
print(f"pandas: {safe_ver(pd)}")
print(f"scikit-learn: {safe_ver(__import__('sklearn'))}")
print(f"Pillow (PIL): {safe_ver(PIL)}")
print()
print("=== PyTorch System Info ===")
cuda_available = torch.cuda.is_available()
print(f"CUDA available: {cuda_available}")
print(f"torch.version.cuda: {getattr(torch.version, 'cuda', None)}")
try:
    cudnn_ver = torch.backends.cudnn.version()
except Exception:
    cudnn_ver = None
print(f"cuDNN version: {cudnn_ver}")
if cuda_available:
    device = torch.device("cuda")
    print(f"GPU count: {torch.cuda.device_count()}")
    print(f"GPU name[0]: {torch.cuda.get_device_name(0)}")
else:
    device = torch.device('cpu')
    print('Using CPU')
print()
try:
    x = torch.randn(2, 3, device=device)
    y = torch.randn(2, 3, device=device)
    z = (x + y).mean().item()
    print("PyTorch test: OK")
except Exception as e:
    print('PyTorch test: FAIL')
    print(e)
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
import numpy as np
import torch
from PIL import Image
import matplotlib.pyplot as plt

data_dir = os.path.join(os.path.dirname(__file__), "video")
image_paths = []
steering_angles = []

for filename in os.listdir(data_dir):
    if fnmatch.fnmatch(filename, "*.png"):
        image_paths.append(os.path.join(data_dir, filename))
        angle = int(filename[-7:-4])
        steering_angles.append(angle)

random_indices = random.sample(range(len(image_paths)), 10)
fig, axes = plt.subplots(2, 5, figsize=(15, 6))

for i, ax in enumerate(axes.flat):
    idx = random_indices[i]
    img = Image.open(image_paths[idx]).convert("RGB")
    ax.imshow(img)
    ax.set_title(f"Angle: {steering_angles[idx]}")
    ax.axis('off')

plt.tight_layout()
plt.show()
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
import matplotlib.pyplot as plt
import torch

data_dir = os.path.join(os.path.dirname(__file__), "video")
image_paths = []
steering_angles = []

for filename in os.listdir(data_dir):
    if fnmatch.fnmatch(filename, "*.png"):
        image_paths.append(os.path.join(data_dir, filename))
        angle = int(filename[-7:-4])
        steering_angles.append(angle)

df = pd.DataFrame({"SteeringAngle": steering_angles})

plt.figure(figsize=(10, 5))
plt.hist(df['SteeringAngle'], bins=30, color="skyblue", edgecolor="black")
plt.title("Distribution of Steering Angles")
plt.xlabel('Steering Angle')
plt.ylabel("Frequency")
plt.grid(True)
plt.show()
```

## 5.학습 데이터와 검증 데이터를 분리

* 이미지 파일 이름에서 조향각 데이터를 추축한 위
* 학습용(train)과 검증용(validation)  epdlxjfh skdnrh,
* 두 데이터의 조향각 분포를 히스토그램으로 비교하는 코드입니다.
* 증, 데이터가 균등하게 분리되었는지 시각적으로 확인하는 역할을 합니다.

* 5_Train_validation_split.py

```python
import os
import fnmatch
import random
import numpy as np
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
import torch

data_dir = os.path.join(os.path.dirname(__file__), "video")
image_paths = []
steering_angles = []

for filename in os.listdir(data_dir):
    if fnmatch.fnmatch(filename, "*.png"):
        image_paths.append(os.path.join(data_dir, filename))
        angle = int(filename[-7:-4])
        steering_angles.append(angle)

X_train, X_valid, y_train, y_valid = train_test_split(
    image_paths, steering_angles, test_size=0.2, random_state=42
)

plt.figure(figsize=(10, 5))
plt.hist(y_train, bins=30, alpha=0.6, label="Training", color="blue", edgecolor="black")
plt.hist(y_valid, bins=30, alpha=0.6, label="Validation", color="red", edgecolor="black")
plt.title('Training vs Validation Steering Angle Distribution')
plt.xlabel("Steering Angle")
plt.ylabel("Frequency")
plt.legend()
plt.grid(True)
plt.show()
```

## 6. 이미지 읽어오기 및 정규화

* 이미지를 정규화하여 학습 효과를 높여보도록 합니다.
* 정규화 과정은 쉽게 말해 데이터의 스케일을 일정하게 맞추는 작업으로, <br>
  픽셀값의 범위를 조정하여 모델이 이미지의특징을 더 안정적으로 학습할 수 있도록 도와줍니다.


* 6_Image_input_and_normalization_functions.py

```python
import os
import random
import fnmatch
import numpy as np
import cv2
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
import torch

data_dir = os.path.join(os.path.dirname(__file__), "video")
image_paths = []
steering_angles = []

for filename in os.listdir(data_dir):
    if fnmatch.fnmatch(filename, "*.png"):
        image_paths.append(os.path.join(data_dir, filename))
        angle = int(filename[-7:-4])
        steering_angles.append(angle)

X_train, X_valid, y_train, y_valid = train_test_split(
    image_paths, steering_angles, test_size=0.2, random_state=42
)

def my_imread(image_path):
    image = cv2.imread(image_path)
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    return image

def img_preprocess(image):
    image = image.astype(np.float32) / 255.0
    return image

image_index = random.randint(0, len(image_paths) - 1)
fig, axes = plt.subplots(1, 2, figsize=(15, 8))

image_orig = my_imread(image_paths[image_index])
image_processed = img_preprocess(image_orig)

axes[0].imshow(image_orig)
axes[0].set_title("Original Image")
axes[0].axis("off")

axes[1].imshow(image_processed)
axes[1].set_title("Normalized Image")
axes[1].axis('off')

plt.tight_layout()
plt.show()


```


## 7.nvidia 모델 구성

* 그래픽카드 제조회사인 NVIDIA에서 차선 인식을 위한 논문에서 제공된 모델을 이용하여 학습모델을 구성합니다.
* NVIDIA 자율주행 구조를 따른 딥러닝 모델을 구성하고 모델의 전체 구조를 출력하는기능을 코드를 작성합니다.

* 7_NVIDIA_model_configuration.py

```python
import os
import fnmatch
from sklearn.modet_selection import train-test-sptit
import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
data-dir = os.path. join(os.path.dirname(--file--), "video")
image_paths = []
steering_angles = []
for fiIename in os.listdir(data_dir)  :
if  fnmatch. fnmatch(fitename,'+.  png") :
image_paths.append(os.path.   join(data-dir, filename)) angte =int(filename[-7  : -4])
steering_angles.  append(angle)
X_train, X_valid, y_train, y_valid = train_test_split(
image_paths, steering_angles, test-size=O,2, random-state=42 )
def my_imread(image_path) :
image = cv2.imread(image_path)
image = cv2.cvtColor(image,  cv2.C0LOR_BGR2RGB)
return image
def img_preprocess (image) :
image = image.astype(np.float32)  /255.0 image = np.transpose(image,  (2, 0, L)) return image
class Nvidial{odet(nn.Hodule) :
def __init__(setf):
superO . __init__o
self .features = nn.Sequential(
nn. Conv2d(3, 24, kernel-size=Sr stride=2), nn. ELU(inplace=True),
nn.Conv2d(24, 36, kernel-size=5, stride=2), nn.ELU(inplace=True),
nn.Conv2d(36, 48, kernel_size=S, stride=2), nn.ELIJ(inplace=True), nn.Conv2d(48, 64, kernel_size=3, stride=l),  nn.ELU(inplace=True), nn. Dropout (P=0 . 2) ,
nn.Conv2d(64, 64, kernel_size=3, stride=l), nn.Elu(inplace=True), )
self .flatten = nn. Flatteno
with torch.no_gradO:
tmp = 1or.6..eros(1,  3, 66, 200)
f =self.features(tmp)
flat_dim = f.numeto
self .mlP = nn.Sequential(
nn . Dropout (P=0. 2) ,
nn.Linear(flat_dim,  1.00), nn.ELU(inplace=True), nn.Linear(100, 50), nn.ELU(inplace=True), nn.Linear(50,  r0), nn.ELU(inplace=True), nn.Linear(10,1),
)
def forward(self, x): x --self.features(x) x =self.flatten(x)
x =self.mlp(x) return x
65    model = NvidiaModel0
66    criterion = nn.MSELoss0
67 optimizer = optim.Adam(model.  parameters0, lr= 1 e-3)
68
bv
70
11
72
/3
print(model)
total-params = sum(p.numel0 for p in model.parameters0)
trainable-params = sum(p.numel0 for p in model.parameters0 if p.requires_grad) print(f" total_params:  itotal_paramsl")
print(f"trainable-params   : {trainable_params}")
```



##8.학습 데이터와 검증 데이터를 분리

* 모든 이미지를 이용하여 삭습하기에는 너무 많은 시간이 소요되므로 학습, <br>
  검증으로 분리된 데이터에서 랜덤하게 추출하여 학습 데이터와 검증데이터를 생겅하는 코드를 작성해봅니다.

* 8_Generating_traing_data.py

```python

import os
import random
import fnmatch
import numpy as np
import cv2
import matptottib.pyplot  as plt
from sklearn.model_selection import train-test-split import torch
data_dir = os.path. join(os.path.dirname(__fiIe__),   "video")
image-paths = []
steering_angles = []
for filename in os.listdir(data_dir):
if  fnmatch.fnmatch(filename,  "r. png") :
image_paths.  append (os. path. j oin (data_dir,  fi lename) ) angte =int(filename[-7  :-4])
steering_angles.  append(angte)
X_train, X_valid, y_train, y_valid = train_test_split(
image_paths, steering_angles,  test_size=o.2, random_state=42
)
def my_imread(image_path) :
image = cv2.imread(image_path)
image = cv2.cvtColor(image, cv2.CoLoR_BGR2RGB)
return image
def img_preprocess (image) :
image = image.astype(np.float32)   /255.0
return image
def image_data_generator(image_paths, steering_angtes, batch_size) : n =len(image_paths)
while True:
batch-images = []
batch-angles = []
for 
_ in range(batch_size):
idx = random.randint(O,  n -1) image = my_imread(image_paths[idx]) angte = steering_angleslidxl image = img_preprocess(image) batch_images. append (image) batch_angles.  append(angIe)
yield np.asarray(batch_images),   np.asarray(batch_angles, dtype=np.float32)
nrow =2
ncol =2
batch_size=nrow*ncol
X_train_batch, y_train_batch =next(image_data_generator(X_train,  y-train, batch_size)) X_valid_batch, y_valid_batch =next(image_data_generator(X_va1id,  y_valid, batch_size)) fig, axes = plt.subptots(nrow, ncol *2, fig5lzs=(16, 8))
for i in range(nrow):
for j in range(ncol):
idx=i*ncot+j
axeslil U *2l.imshow(X-train-batchlidxl)
axes[i]U *2l.set-title(f"Train Angle: {y-train_batchIidx]]") axes[i] U *21. axis("of f ")
axeslilU *2 +ll.imshow(X_valid-batch[idx])
axeslilU *2 +1l.set-titte(f"Valid  Angle: {y_valid_batch[idx]]")
68    plt.tight_layout0
69    plt.showO
```



## 9. 모델 학습(10분가량 소요)

* 데이터를 이용하여 실제 학습하는 과정으로 컴퓨터의 성능에 따라서 5~20분가량 소요됩니다.
* 학습이 끝나면 모델데이터가 생성됩니다.

* 9_make_model.py

```python
import os
import fnmatch
import random
import pickte
from datetime import datetime
import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
SEED =42
random. seed (SEED)
np. random.seed(SEED)
torch. manual_seed(SEED)
base_dir = os.path.dirname(__fite__) data_dir = os.path.join(base_dir,  "video")
batch_size =L00 epochs =10

tr = 1e-3
steps_per_epoch  =300
validation_steps  =200
device = torch.device("cuda"if  torch. cuda. is_availableo else "cpu")
028        def list_image_paths_and_angles(folder)   :
029
030
937
037
033
034
035
036
031
038
039
040
041
042
043
044
045
046
047
048
049
0s0
051
0s2
053
054
055
056
057
058
059
060
06L
062
063
064
06s
066
067
068
069
070
071
072
073
paths, angles = [], []
for fiIename in os.listdir(folder):
if  fnmatch.fnmatch(filename,  "*. png") :
paths.append(os.path. join(folder, filename)) angte =int(filename[-7  : -4])
angles. append(float (angte) )
return paths, angtes
def train-valid-split(paths, angles, valid-ratio=0.2) idxs = tist(ranse(len(paths)))
random. shullle(idxs)
n =len(idxs)
n_valid =int(n * vatid_ratio)
vatid_idx = idxs[:n-vatid]
train_idx = idxs[n_valid:  ]
X_train = [paths[i] for i in train_idxl
y_train = [angtesli] for i in train-idxl
X_vatid = [paths[i] for i in valid-idxl
y_valid = [anglesli] for i in vatid-idxl
return X_train, X_vatid, y-train, y-vatid
def preprocess_for_training(bgr)  :
img = 59...t,ype(np.float32) /255.0
imo = nr.l.rnspose(img, (2, 0, t))
return img
def infinite-batch(image-paths,  steering-angles, batch-size) : n =len(image-paths)
assert n >0
while True:
idxs = np.random.randint(0, n, size=batch-size) xS, !s = [], []
for i in idxs:
img = 612.ir.ead(image-pathslil,  cv2.IHREAD-C0L0R)
if  img is None:
raise FilelrlotFoundError(image_pathsIi]  )
x = preprocess_for_training(img)
xs . append (x)
ys. append ( [steering-anglesIi] I )
x_batch = torch.from_numpy(np.stack(xs)).floato
y_batch = torch.from-numpy(np.array(ys, dtype=np.float32)) yietd x-batch, y-batch
class Nvidial''lodet (nn. Hodute) : def __init__(setf):
superO  . --init--o
self .features = nn.Sequential(
nn.Conv2d(3, 24, kernel-size=s, stride=2), nn.ELU(inplace=True), nn.Conv2d(24, 36, kernel-size=5, stride=2), nn. ELU(inplace=True), nn.Conv2d(36, 48, kernel-size=5, stride=2), nn. ElU(inplace=True), nn.Conv2d(48, 64, kernel-size=3, stride=1), nn.ELU(inplace=True),
nn . Dropout (P=0 . 2) ,
nn.Conv2d(64, 64, kernel-size=3, stride=1), nn.ELU(inplace=True), )
self ,flatten = nn. Flatteno
with torch.no_grado:
tmp = 1sr.6.reros(1,  3, 66, 200)
f =self.features(tmp)
flat_dim = f.numelo
setf .mlp = nn.Sequentiat(
nn. Dropout(P=0. 2),
nn.Linear(flat_dim,  100), nn.ELU(inplace=True), nn.Linear(100, 50), nn.ELU(inplace=True), nn.Linear(50,  10), nn.ELU(inptace=True), nn.Linear(10,1),
)
def forward(self, x): x =self.features(x) x =self.flatten(x) x =self.mlp(x) return x
702        def train_one_epoch(model, optimizer, criterion, train_gen, steps_per_epoch)
103
704
t05
706
707
108
109
n0
111
tt2
113
11.4
115
116
It7
118
Ltg
720
17L
L22
r23
724
model. traino
run_loss =0,0
seen =0
for _ in range(steps_per_epoch):
xr y =next(train-gen) x, Y = x.to(device), y.to(device)
optimizer. zero_grad  (set_to_none=True) pred = model(x)
toss = criterion(pred, y) loss. backwardo
optimizer. stepo
bs = x.size(0)
run_toss += loss.itemo * bs seen += bs
return run_loss / max(seen, 1)
@torch . no_grad o
def evaluate(model, criterion, valid_gen, validation_steps): modet. eval o
total_loss, total_mae =0.0, 0.0
Seen =0
for _ in range(validation_steps):
x, y =next(vatid-gen) x, y = x.to(device), y.to(device) pred = model(x)
loss = criterion(pred, y) mae = torch.mean(torch.abs(pred   - y)) bs = x.size(0)
total_loss += loss.itemo * bs
total-mae += nng.itsmo * [5
Seen += bS
if  seen ==0:
return float('inf "), float("inf ") return total_loss / seen, total_mae / seen
def maino:
paths, angles = list_image_paths-and-angtes(data-dir) if  len(Paths) ==0:
raise RuntimeError(f'No PNG images found in: {data-dir}")
patience=2)
149
150
151
152
153 L54 155 156 157 158 159 160 161 162 163 764 165 166 767 168 169 170 17L
va t-l'lAE(deg)  ={val-mae : . 3f } ")
772  if val_toss < best_val:
X_train, X_valid, y_train, y_valid = train_valid,sptit(paths,  angles, vatid-ratio=0.2)
model = NvidialttodelO. to(device)
criterion = nn.lilsELosso
optimizer = optim.Adam(model.parametersO, tr=lr)
scheduler  = optim,lr-scheduler.ReduceLROnPlateau(optimizer,     mode="min",  factor=0.5,
timestamp  = datetime.nowo.strftime("xY%m%d_%H%H%S")
save-dir = os.path. join(base-dir, f"model-{timestamp}")
os.makedirs(save_dir, exist-ok=True)
best-vat = float("inf")
history = {"train_loss": [], "va1_loss": [], "val-mae": []]
train_gen = infinite_batch(X_train, y_train, batch_size)
valid_gen = infinite_batch(X_valid,   y_vatid, batch_size)
for ep in range(1, epochs +1):
tr_loss = train_one_epoch(model, optimizer, criterion, train-gen, steps-per-epoch) vat_loss, vat-mae = evatuate(model,  criterion, vatid-gen, validation-steps)
old_lr = optimizer.param-groups[0]["1r"]
scheduter. step(va1-toss)
new_lr = optimizer.param-groups[0]["1r"]
if  new_lr != otd_lr:
print(f"Ischeduler]  LR reduced: {old-Ir:.6S} -> {new-lr:.69}")
history ['t rain_ loss " ] . append (tr-loss)
history["va  I_1oss" ] . append(val-loss)
history[ " va t_mae " ] . append (vat-mae)
print(f"Epoch {ep:02dU{epochs} ! train-tss5={fr-loss:.5f} | val-tos5={v3t-loss:.5f}
L73 
best_val = val_loss
best-pt = os.path. join(save-dir,  "lane_navigation-best.pt")
torch.save({"model-state": model.state-dictO,  "va1-loss": val-Ioss}, best-pt) print(f"Saved BEST checkpoint -> {best_pt}")
final_pt = os.path. join(save_dir, "lane_navigation_finat.pt")
torch. save({"modet_state" : model. state_dict O }, final-pt)
print(f"Saved final weights -> {final_pt}")
model.evalo
example = torch.zeros(1, 3, 66, 200, device=device)
traced = torch.jit.trace(modet, example)
ts_path = os. path. j oin(save_dir,  " Iane_navigation_fina1. torchsc ript " ) traced. save(ts_path)
print(f"Saved TorchScript -> {ts_path}")
hist_path = os.path. join(save_dir, "history.pickte") with open(hist_path,  "wb") as f:
pickle.dump(history, f, pickle.HIGHEST_PROTOCOL) print(f"Saved history -> {hist_path}")
print(f"Training  complete.  Modet saved to: {save_dir}")
if  _-narne-- =="__main__"  r main0

```


## 10.결과확인

* history.pickle 파일을 이용하여 모델 학습 과정 중 저장된 손실값(loss, val_loss)을 불러와서 에폭별로 학습 손실과 검증 손실이 어떻게 변했는지 그래프로 시각화하는 기능을 수행하는 코드를 작성해 봅니다.
* 모델의 생성 시점에 따랄 모델이 저장된 폴더의 이름이 변경되므로 6줄의 폴더는 생성된 시간의 폴터 이름으로 변경합니다.

* 10_Result_analysis.py

```python
import os
import pickle
import matplotlib.pyplot  as plt
model_folder.
history-path = os.path. join(model-folder,  "hi.story.pickle") with open(history_path,  "rb") as f:
history = pickte.load(f)
print('History keys: ", history. keysO)
train_loss = history.get("train_loss",  history.get("Ioss")) val_loss = history. get("vaI_toss")
vat_mae = history. get("val_mae")
plt.figure(figsize=(10, 5) )
if train_Ioss is not None:
plt.ptot(train_toss, tabet="Training  Loss") if  val_Ioss is not None:
ptt.plot(va1-Ioss,  label="Validation Loss") plt.title("Model Training History - Loss")
ptt. xlabet(" Epoch" )
pIt. ylabel(" Loss" )
ptt. tegendo
plt. grid(True)
plt. showo
if  val_mae is not None:
plt.figure(figsize=(10, 5) )
ptt. plot (val-mae, label="Va lidat ion l'lAE " ) plt.titte("Hodel Training History - l4AE") plt. xlabel(" Epoch")
plt.ytabel("MAE  (deg) ") ptt. legendo
plt.grid(True) pIt.showo

```





