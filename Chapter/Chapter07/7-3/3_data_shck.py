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