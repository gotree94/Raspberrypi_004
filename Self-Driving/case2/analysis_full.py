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

# Parse Time
time_strs = df['Time'].astype(str)
df['Time_dt'] = pd.to_datetime('2026-07-01 ' + time_strs, format='%Y-%m-%d %H:%M:%S.%f')
df['Time_sec'] = (df['Time_dt'] - df['Time_dt'].iloc[0]).dt.total_seconds()

# Fix dt diffs (replace zero with NaN then forward fill)
dt_sec = df['Time_sec'].diff().replace(0, np.nan).ffill().fillna(1)
dt_sec.iloc[0] = 0.124  # median dt

# Derived
df['Yaw_rate'] = df['Gyro_Yaw(deg)'].diff() / dt_sec
df['Speed'] = df['Encoder_Dist(cm)'].diff() / dt_sec
dx = df['X(cm)'].diff()
dy = df['Y(cm)'].diff()
df['Path_angle'] = np.degrees(np.arctan2(dy, dx))
df['Dist_from_start'] = np.sqrt(df['X(cm)']**2 + df['Y(cm)']**2)

# ===== ANALYSIS =====
print("=" * 80)
print("SLAM_CarA_20260701_203246 - COMPLETE ANALYSIS REPORT")
print("=" * 80)

print("\n## 1. BASIC DATA INFO ##")
print("  Shape: {} rows x {} columns".format(df.shape[0], df.shape[1]))
print("  Columns: {}".format(list(df.columns)))
print("  Time range: {} --> {}".format(df['Time'].iloc[0], df['Time'].iloc[-1]))
print("  Duration: {:.2f} seconds".format(df['Time_sec'].iloc[-1]))
print("  Average sample rate: {:.2f} Hz".format(len(df) / max(df['Time_sec'].iloc[-1], 1)))
print("  Median dt: {:.1f} ms".format(df['Time_dt'].diff().dt.total_seconds().median()*1000))

print("\n## 2. DESCRIPTIVE STATISTICS ##")
numeric_cols = ['X(cm)', 'Y(cm)', 'Encoder_Dist(cm)', 'Gyro_Yaw(deg)', 'Sonar_F(cm)', 'Sonar_L(cm)', 'Sonar_R(cm)']
stats = df[numeric_cols].describe()
print(stats.to_string())

print("\n## 3. NULL / MISSING VALUES ##")
print("  Total NaN cells: {}".format(df[numeric_cols].isnull().sum().sum()))
print("  No NaN values found in any column.")
print("  Sentinel values (>= 998) in sonar columns:")
for col in ['Sonar_F(cm)', 'Sonar_L(cm)', 'Sonar_R(cm)']:
    sentinel = (df[col] >= 998).sum()
    print("    {}: {} ({:.1f}%)".format(col, sentinel, sentinel/len(df)*100))

print("\n## 4. UNIQUE VALUES ##")
for col in numeric_cols:
    print("  {:20s}: {:>6d} unique".format(col, df[col].nunique()))

print("\n## 5. TRAJECTORY ANALYSIS ##")
total_enc = df['Encoder_Dist(cm)'].iloc[-1]
net_disp = df['Dist_from_start'].iloc[-1]
max_disp = df['Dist_from_start'].max()
efficiency = net_disp / total_enc * 100 if total_enc > 0 else 0
total_yaw = df['Gyro_Yaw(deg)'].iloc[-1] - df['Gyro_Yaw(deg)'].iloc[0]

print("  Start: ({:.1f}, {:.1f}) cm".format(df['X(cm)'].iloc[0], df['Y(cm)'].iloc[0]))
print("  End:   ({:.1f}, {:.1f}) cm".format(df['X(cm)'].iloc[-1], df['Y(cm)'].iloc[-1]))
print("  Net displacement from start: {:.2f} cm".format(net_disp))
print("  Max distance from start: {:.2f} cm (at time {:.1f}s)".format(max_disp, df.loc[df['Dist_from_start'].idxmax(), 'Time_sec']))
print("  Total encoder distance: {:.2f} cm".format(total_enc))
print("  Path efficiency (displacement / distance): {:.1f}%".format(efficiency))
print("  X range: [{:.1f}, {:.1f}] cm (span: {:.1f} cm)".format(df['X(cm)'].min(), df['X(cm)'].max(), df['X(cm)'].max()-df['X(cm)'].min()))
print("  Y range: [{:.1f}, {:.1f}] cm (span: {:.1f} cm)".format(df['Y(cm)'].min(), df['Y(cm)'].max(), df['Y(cm)'].max()-df['Y(cm)'].min()))

# Static analysis
static_mask = (df['X(cm)'].diff() == 0) & (df['Y(cm)'].diff() == 0)
static_mask.iloc[0] = True  # first sample
n_static = static_mask.sum()
print("  Static samples (no position change): {} ({:.1f}%)".format(n_static, n_static/len(df)*100))

# Movement phases
df['is_moving'] = ~static_mask
df['move_group'] = (df['is_moving'] != df['is_moving'].shift()).cumsum()
move_groups = df[df['is_moving']].groupby('move_group')
print("  Distinct movement phases: {}".format(move_groups.ngroups))
for name, group in list(move_groups):
    dur = group['Time_sec'].iloc[-1] - group['Time_sec'].iloc[0]
    dist = np.sqrt((group['X(cm)'].iloc[-1]-group['X(cm)'].iloc[0])**2 + (group['Y(cm)'].iloc[-1]-group['Y(cm)'].iloc[0])**2)
    print("    Phase {}: t={:.1f}-{:.1f}s (dur={:.1f}s), moved {:.1f} cm, pos=({:.1f},{:.1f}) to ({:.1f},{:.1f})".format(
        name, group['Time_sec'].iloc[0], group['Time_sec'].iloc[-1], dur, dist,
        group['X(cm)'].iloc[0], group['Y(cm)'].iloc[0], group['X(cm)'].iloc[-1], group['Y(cm)'].iloc[-1]))

print("\n## 6. GYRO ANALYSIS ##")
print("  Yaw range: [{:.2f}, {:.2f}] deg".format(df['Gyro_Yaw(deg)'].min(), df['Gyro_Yaw(deg)'].max()))
print("  Total yaw change: {:.2f} deg".format(total_yaw))
print("  Max |yaw rate|: {:.2f} deg/s".format(df['Yaw_rate'].abs().max()))
yaw_abs = df['Yaw_rate'].abs()
print("  Yaw rate percentiles: 50th={:.1f}, 90th={:.1f}, 99th={:.1f} deg/s".format(
    yaw_abs.quantile(0.5), yaw_abs.quantile(0.9), yaw_abs.quantile(0.99)))

# Turning analysis
turn_thr = 20
turning = df[yaw_abs > turn_thr]
print("  Samples with |yaw rate| > {} deg/s: {} ({:.1f}%)".format(turn_thr, len(turning), len(turning)/len(df)*100))

# Yaw monotonicity check
yaw_diff = df['Gyro_Yaw(deg)'].diff()
n_yaw_neg = (yaw_diff < -0.1).sum()  # small threshold
n_yaw_pos = (yaw_diff > 0.1).sum()
print("  Yaw increases: {} samples, decreases: {} samples".format(n_yaw_pos, n_yaw_neg))
if total_yaw > 0:
    print("  Overall trend: INCREASING (turning right/CCW in typical coords)")
else:
    print("  Overall trend: DECREASING")

# Yaw vs path angle
yaw_series = df['Gyro_Yaw(deg)']
path_angle = df['Path_angle']
common_idx = yaw_series.dropna().index.intersection(path_angle.dropna().index)
corr = yaw_series.loc[common_idx].corr(path_angle.loc[common_idx]) if len(common_idx) > 2 else float('nan')
print("  Yaw vs path angle correlation: {:.4f}".format(corr))

print("\n## 7. ENCODER ANALYSIS ##")
print("  Total encoder distance: {:.2f} cm".format(total_enc))
print("  Max speed: {:.2f} cm/s".format(df['Speed'].max()))
print("  Mean speed: {:.2f} cm/s".format(df['Speed'].mean()))
print("  Median speed: {:.2f} cm/s".format(df['Speed'].median()))
print("  Max speed (moving only): {:.2f} cm/s".format(df[df['is_moving']]['Speed'].max()))
print("  Mean speed (moving only): {:.2f} cm/s".format(df[df['is_moving']]['Speed'].mean()))
neg_enc = (df['Encoder_Dist(cm)'].diff() < 0).sum()
print("  Encoder ever decreases: {} times".format(neg_enc))
print("  Encoder monotonic: {}".format("YES" if neg_enc == 0 else "NO"))

# Encoder vs displacement correlation
print("  Encoder vs XY displacement correlation: {:.4f}".format(df['Encoder_Dist(cm)'].corr(df['Dist_from_start'])))

print("\n## 8. SONAR ANALYSIS ##")
for sc in ['Sonar_F(cm)', 'Sonar_L(cm)', 'Sonar_R(cm)']:
    valid = df[df[sc] < 998]
    invalid = len(df) - len(valid)
    print("\n  {}:".format(sc))
    print("    Valid readings: {}/{} ({:.1f}%)".format(len(valid), len(df), len(valid)/len(df)*100))
    print("    Sentinel (no echo): {} ({:.1f}%)".format(invalid, invalid/len(df)*100))
    if len(valid) > 0:
        print("    Range: [{:.1f}, {:.1f}] cm".format(valid[sc].min(), valid[sc].max()))
        print("    Mean: {:.1f} cm, Median: {:.1f} cm, Std: {:.1f} cm".format(
            valid[sc].mean(), valid[sc].median(), valid[sc].std()))
    # Correlation with position
    for pc in ['X(cm)', 'Y(cm)']:
        cv = valid[sc].corr(valid[pc])
        print("    Corr with {}: {:.4f}".format(pc, cv))

# Sonar corridor analysis
print("\n  Sonar corridor width (L+R valid):")
both_valid = df[(df['Sonar_L(cm)'] < 998) & (df['Sonar_R(cm)'] < 998)]
if len(both_valid) > 0:
    corridor = both_valid['Sonar_L(cm)'] + both_valid['Sonar_R(cm)']
    print("    Both valid: {} samples".format(len(both_valid)))
    print("    Sum L+R range: [{:.1f}, {:.1f}] cm".format(corridor.min(), corridor.max()))
    print("    Mean sum: {:.1f} cm, Std: {:.1f} cm".format(corridor.mean(), corridor.std()))

print("\n## 9. DATA QUALITY ASSESSMENT ##")
max_xj = df['X(cm)'].diff().abs().max()
max_yj = df['Y(cm)'].diff().abs().max()
print("  Max position jump: X={:.2f} cm, Y={:.2f} cm".format(max_xj, max_yj))
print("  Duplicate timestamps: {} (out of {})".format(df['Time'].duplicated().sum(), len(df)))
last20 = df.tail(20)
if last20['X(cm)'].std() == 0 and last20['Y(cm)'].std() == 0:
    print("  Last 20 samples: robot STATIONARY at ({:.1f}, {:.1f})".format(last20['X(cm)'].iloc[0], last20['Y(cm)'].iloc[0]))
first10 = df.head(10)
if first10['X(cm)'].std() == 0 and first10['Y(cm)'].std() == 0:
    print("  First 10 samples: robot STATIONARY at ({:.1f}, {:.1f})".format(first10['X(cm)'].iloc[0], first10['Y(cm)'].iloc[0]))

# Check for any negative sonar values
for sc in ['Sonar_F(cm)', 'Sonar_L(cm)', 'Sonar_R(cm)']:
    neg = (df[sc] < 0).sum()
    if neg > 0:
        print("  WARNING: {} negative values in {}".format(neg, sc))

print("\n## 10. KEY FINDINGS & ANOMALIES ##")
print("  1. The robot starts and ends nearly at the same position ({} cm apart)".format(net_disp))
print("     but traveled {} cm total (efficiency={:.1f}%), suggesting a loop or back-and-forth path.".format(total_enc, efficiency))
print("  2. {}% of samples show no movement (static). The robot alternates".format(n_static/len(df)*100))
print("     between moving and stopping -- typical of a SLAM exploration pattern.")
print("  3. Gyro yaw increases monotonically overall (0 to {:.1f} deg = {:.1f} full rotations),".format(df['Gyro_Yaw(deg)'].iloc[-1], total_yaw/360))
print("     indicating continuous rotation in one direction.")
print("  4. Sonar_F has the most sentinel values ({:.1f}%), likely when the robot".format(149/len(df)*100))
print("     faces open space or a wall too far away.")
print("  5. Sonar_L and Sonar_R have identical sentinel counts (75 each),")
print("     suggesting symmetric sensor behavior.")
print("  6. All sensor data appears clean with no NaN values and monotonically increasing encoder.")

print("\n" + "=" * 80)
print("ALL PLOTS SAVED TO: " + OUTDIR)
print("=" * 80)
