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