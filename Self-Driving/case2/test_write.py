
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['figure.dpi'] = 120
plt.rcParams['font.size'] = 10

OUTDIR = r'C:\Users\Administrator\Desktop\Self-Driving\case2'
FILEPATH = r'C:\Users\Administrator\Desktop\Self-Driving\case2\SLAM_CarA_20260701_203246.xlsx'

df = pd.read_excel(FILEPATH)
print('Shape:', df.shape)
print('Columns:', list(df.columns))
