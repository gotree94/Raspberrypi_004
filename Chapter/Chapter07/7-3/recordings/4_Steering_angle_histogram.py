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