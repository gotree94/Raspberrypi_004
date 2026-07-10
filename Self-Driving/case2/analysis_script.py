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
print("=" * 80)
print("1. BASIC INFO")
print("=" * 80)
print("Shape: {} rows x {} columns".format(df.shape[0], df.shape[1]))
print("Columns: {}".format(list(df.columns)))
print("\nDtypes:")
print(df.dtypes)

# Parse Time
time_strs = df['Time'].astype(str)
df['Time_dt'] = pd.to_datetime('2026-07-01 ' + time_strs, format='%Y-%m-%d %H:%M:%S.%f')
df['Time_sec'] = (df['Time_dt'] - df['Time_dt'].iloc[0]).dt.total_seconds()

print("\nTime range: {} --> {}".format(df['Time'].iloc[0], df['Time'].iloc[-1]))
print("Duration: {:.2f} seconds".format(df['Time_sec'].iloc[-1]))
print("Average sample rate: {:.2f} Hz".format(len(df) / df['Time_sec'].iloc[-1]))
print("Median dt: {:.1f} ms".format(df['Time_dt'].diff().dt.total_seconds().median()*1000))

# 2. STATS
print("\n" + "=" * 80)
print("2. DESCRIPTIVE STATISTICS")
print("=" * 80)
numeric_cols = [c for c in df.select_dtypes(include=[np.number]).columns if c != 'Time_sec']
print(df[numeric_cols].describe().to_string())

# 3. NULLS
print("\n" + "=" * 80)
print("3. MISSING VALUES")
print("=" * 80)
print(df.isnull().sum().to_string())
print("Total missing: {}".format(df.isnull().sum().sum()))
for col in ['Sonar_F(cm)', 'Sonar_L(cm)', 'Sonar_R(cm)']:
    sentinel = (df[col] >= 998).sum()
    print("  {}: {} sentinel values >= 998 ({:.1f}%)".format(col, sentinel, sentinel/len(df)*100))

# 4. UNIQUE
print("\n" + "=" * 80)
print("4. UNIQUE VALUES")
print("=" * 80)
for col in df.columns:
    print("  {:20s}: {:>6d} unique".format(col, df[col].nunique()))

# 5. DERIVED
df['Yaw_rate'] = df['Gyro_Yaw(deg)'].diff() / df['Time_sec'].diff()
df['Speed'] = df['Encoder_Dist(cm)'].diff() / df['Time_sec'].diff()
dx = df['X(cm)'].diff()
dy = df['Y(cm)'].diff()
df['Path_angle'] = np.degrees(np.arctan2(dy, dx))
df['Dist_from_start'] = np.sqrt(df['X(cm)']**2 + df['Y(cm)']**2)

# 6. PLOT: Trajectory
fig, ax = plt.subplots(figsize=(10, 10))
sc = ax.scatter(df['X(cm)'], df['Y(cm)'], c=df['Time_sec'], cmap='viridis', s=2, alpha=0.7)
ax.plot(df['X(cm)'], df['Y(cm)'], 'b-', alpha=0.15, linewidth=0.5)
ax.plot(df['X(cm)'].iloc[0], df['Y(cm)'].iloc[0], 'go', markersize=12, label='Start', zorder=5)
ax.plot(df['X(cm)'].iloc[-1], df['Y(cm)'].iloc[-1], 'r^', markersize=12, label='End', zorder=5)
plt.colorbar(sc, ax=ax, label='Time (seconds)')
ax.set_xlabel('X (cm)')
ax.set_ylabel('Y (cm)')
ax.set_title('Robot Trajectory: X vs Y (color = time)', fontsize=14)
ax.set_aspect('equal')
ax.legend(fontsize=11)
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(OUTDIR + '/01_trajectory_XY.png', dpi=150)
plt.close()
print("\nSaved: 01_trajectory_XY.png")

# 7. PLOT: Gyro Yaw
fig, ax = plt.subplots(figsize=(14, 5))
ax.plot(df['Time_sec'], df['Gyro_Yaw(deg)'], 'b-', linewidth=0.8)
ax.set_xlabel('Time (s)')
ax.set_ylabel('Gyro_Yaw (deg)')
ax.set_title('Gyro_Yaw over Time')
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(OUTDIR + '/02_gyro_yaw_time.png', dpi=150)
plt.close()
print("Saved: 02_gyro_yaw_time.png")

# 8. PLOT: Encoder
fig, ax = plt.subplots(figsize=(14, 5))
ax.plot(df['Time_sec'], df['Encoder_Dist(cm)'], 'r-', linewidth=0.8)
ax.set_xlabel('Time (s)')
ax.set_ylabel('Encoder_Dist (cm)')
ax.set_title('Encoder Distance over Time')
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(OUTDIR + '/03_encoder_dist_time.png', dpi=150)
plt.close()
print("Saved: 03_encoder_dist_time.png")

# 9. PLOT: Sonars
fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)
colors = {'Sonar_F(cm)': '#2196F3', 'Sonar_L(cm)': '#FF9800', 'Sonar_R(cm)': '#4CAF50'}
for ax, col in zip(axes, colors):
    ax.plot(df['Time_sec'], df[col], color=colors[col], linewidth=0.7, alpha=0.8)
    ax.set_ylabel(col)
    ax.set_title(col)
    ax.set_ylim(0, 1050)
    ax.axhline(y=998, color='gray', linestyle='--', alpha=0.5, label='Sentinel')
    ax.legend(fontsize=8, loc='upper right')
    ax.grid(True, alpha=0.3)
axes[-1].set_xlabel('Time (s)')
plt.suptitle('Sonar Values over Time', fontsize=14, y=1.01)
plt.tight_layout()
plt.savefig(OUTDIR + '/04_sonars_time.png', dpi=150, bbox_inches='tight')
plt.close()
print("Saved: 04_sonars_time.png")

# 10. PLOT: Yaw rate
fig, axes = plt.subplots(2, 1, figsize=(14, 7), sharex=True)
axes[0].plot(df['Time_sec'], df['Gyro_Yaw(deg)'], 'b-', linewidth=0.8)
axes[0].set_ylabel('Gyro_Yaw (deg)')
axes[0].set_title('Gyro_Yaw')
axes[0].grid(True, alpha=0.3)
axes[1].plot(df['Time_sec'], df['Yaw_rate'], 'r-', linewidth=0.5, alpha=0.7)
axes[1].set_ylabel('Yaw Rate (deg/s)')
axes[1].set_title('Yaw Rate (derivative)')
axes[1].set_xlabel('Time (s)')
axes[1].grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(OUTDIR + '/05_yaw_rate_time.png', dpi=150)
plt.close()
print("Saved: 05_yaw_rate_time.png")

# 11. PLOT: Speed
fig, axes = plt.subplots(2, 1, figsize=(14, 7), sharex=True)
axes[0].plot(df['Time_sec'], df['Encoder_Dist(cm)'], 'r-', linewidth=0.8)
axes[0].set_ylabel('Encoder_Dist (cm)')
axes[0].set_title('Encoder Distance (cumulative)')
axes[0].grid(True, alpha=0.3)
axes[1].plot(df['Time_sec'], df['Speed'], 'g-', linewidth=0.5, alpha=0.7)
axes[1].set_ylabel('Speed (cm/s)')
axes[1].set_title('Speed (from encoder)')
axes[1].set_xlabel('Time (s)')
axes[1].grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(OUTDIR + '/06_speed_time.png', dpi=150)
plt.close()
print("Saved: 06_speed_time.png")

# 12. PLOT: XY vs time + distance
fig, axes = plt.subplots(2, 1, figsize=(14, 7), sharex=True)
axes[0].plot(df['Time_sec'], df['X(cm)'], 'm-', linewidth=0.8, label='X')
axes[0].plot(df['Time_sec'], df['Y(cm)'], 'c-', linewidth=0.8, label='Y')
axes[0].set_ylabel('Position (cm)')
axes[0].legend()
axes[0].set_title('X and Y over Time')
axes[0].grid(True, alpha=0.3)
axes[1].plot(df['Time_sec'], df['Dist_from_start'], 'k-', linewidth=0.8)
axes[1].set_ylabel('Dist from start (cm)')
axes[1].set_xlabel('Time (s)')
axes[1].set_title('Euclidean Distance from Start')
axes[1].grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(OUTDIR + '/07_xy_dist_time.png', dpi=150)
plt.close()
print("Saved: 07_xy_dist_time.png")

# 13. PLOT: Yaw vs path angle
path_angle = df['Path_angle']
yaw0 = df['Gyro_Yaw(deg)'].iloc[0]
path0 = path_angle.dropna().iloc[0]
yaw_series = df['Gyro_Yaw(deg)']
common_idx = yaw_series.dropna().index.intersection(path_angle.dropna().index)
corr = yaw_series.loc[common_idx].corr(path_angle.loc[common_idx]) if len(common_idx) > 2 else float('nan')

fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)
axes[0].plot(df['Time_sec'], df['Gyro_Yaw(deg)'], 'b-', linewidth=0.8)
axes[0].set_ylabel('Gyro Yaw (deg)')
axes[0].set_title('Gyro Yaw')
axes[0].grid(True, alpha=0.3)
axes[1].plot(df['Time_sec'], path_angle, 'purple', linewidth=0.8)
axes[1].set_ylabel('Path Angle (deg)')
axes[1].set_title('Path Tangent Angle')
axes[1].grid(True, alpha=0.3)
axes[2].plot(df['Time_sec'], df['Gyro_Yaw(deg)'] - yaw0, 'b-', linewidth=0.8, label='Gyro Yaw (shifted)')
axes[2].plot(df['Time_sec'], path_angle - path0, 'r-', linewidth=0.8, alpha=0.7, label='Path Angle (shifted)')
axes[2].set_ylabel('Angle (deg)')
axes[2].set_xlabel('Time (s)')
axes[2].set_title('Yaw vs Path Angle (correlation = {:.4f})'.format(corr))
axes[2].legend()
axes[2].grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(OUTDIR + '/08_yaw_vs_path_angle.png', dpi=150)
plt.close()
print("Saved: 08_yaw_vs_path_angle.png")

# 14. Sonar on trajectory + correlation
sonar_cols = ['Sonar_F(cm)', 'Sonar_L(cm)', 'Sonar_R(cm)']
print("\n" + "=" * 80)
print("SONAR vs POSITION CORRELATION")
print("=" * 80)
for sc in sonar_cols:
    valid = df[df[sc] < 998]
    print("\n  {} (valid: {}/{})".format(sc, len(valid), len(df)))
    for pc in ['X(cm)', 'Y(cm)']:
        cv = valid[sc].corr(valid[pc])
        print("    Corr with {}: {:.4f}".format(pc, cv))

fig, axes = plt.subplots(1, 3, figsize=(18, 5))
for ax, sc in zip(axes, sonar_cols):
    valid = df[df[sc] < 998]
    m = ax.scatter(valid['X(cm)'], valid['Y(cm)'], c=valid[sc], cmap='coolwarm', s=5, alpha=0.7)
    plt.colorbar(m, ax=ax, label=sc)
    ax.set_xlabel('X (cm)')
    ax.set_ylabel('Y (cm)')
    ax.set_title('{}\n(valid: {}/{})'.format(sc, len(valid), len(df)))
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3)
plt.suptitle('Sonar Readings on Trajectory', fontsize=14)
plt.tight_layout()
plt.savefig(OUTDIR + '/09_sonar_on_trajectory.png', dpi=150, bbox_inches='tight')
plt.close()
print("\nSaved: 09_sonar_on_trajectory.png")

# 15. SUMMARY
print("\n" + "=" * 80)
print("COMPREHENSIVE ANALYSIS SUMMARY")
print("=" * 80)
total_enc = df['Encoder_Dist(cm)'].iloc[-1]
net_disp = df['Dist_from_start'].iloc[-1]
efficiency = net_disp / total_enc * 100 if total_enc > 0 else 0
total_yaw = df['Gyro_Yaw(deg)'].iloc[-1] - df['Gyro_Yaw(deg)'].iloc[0]

print("""
TRAJECTORY:
  Start: ({:.1f}, {:.1f}) cm
  End:   ({:.1f}, {:.1f}) cm
  Net displacement: {:.2f} cm
  Encoder total:    {:.2f} cm
  Path efficiency:  {:.1f}%
  X range: [{:.1f}, {:.1f}]
  Y range: [{:.1f}, {:.1f}]

GYRO:
  Yaw range: [{:.2f}, {:.2f}]
  Total yaw change: {:.2f} deg
  Max yaw rate: {:.2f} deg/s
  Yaw vs path angle correlation: {:.4f}

ENCODER:
  Max speed:   {:.2f} cm/s
  Mean speed:  {:.2f} cm/s
  Median speed: {:.2f} cm/s
""".format(
    df['X(cm)'].iloc[0], df['Y(cm)'].iloc[0],
    df['X(cm)'].iloc[-1], df['Y(cm)'].iloc[-1],
    net_disp, total_enc, efficiency,
    df['X(cm)'].min(), df['X(cm)'].max(),
    df['Y(cm)'].min(), df['Y(cm)'].max(),
    df['Gyro_Yaw(deg)'].min(), df['Gyro_Yaw(deg)'].max(),
    total_yaw, df['Yaw_rate'].abs().max(), corr,
    df['Speed'].max(), df['Speed'].mean(), df['Speed'].median()
))

print("SONAR:")
for sc in sonar_cols:
    valid = df[df[sc] < 998]
    print("  {}: valid={}/{} ({:.1f}%)".format(sc, len(valid), len(df), len(valid)/len(df)*100))
    if len(valid) > 0:
        print("    Range: [{:.1f}, {:.1f}], mean={:.1f}".format(valid[sc].min(), valid[sc].max(), valid[sc].mean()))

turn_thr = 20
turning = df[df['Yaw_rate'].abs() > turn_thr]
print("\nTURNING (|rate| > {} deg/s): {} samples ({:.1f}%)".format(turn_thr, len(turning), len(turning)/len(df)*100))

static = ((df['X(cm)'].diff() == 0) & (df['Y(cm)'].diff() == 0)).sum()
print("STATIC samples: {} ({:.1f}%)".format(static, static/len(df)*100))

neg_enc = (df['Encoder_Dist(cm)'].diff() < 0).sum()
print("Encoder decreases: {} times".format(neg_enc))

last20 = df.tail(20)
if last20['X(cm)'].std() == 0 and last20['Y(cm)'].std() == 0:
    print("Last 20 samples: stationary at ({:.1f}, {:.1f})".format(last20['X(cm)'].iloc[0], last20['Y(cm)'].iloc[0]))

max_xj = df['X(cm)'].diff().abs().max()
max_yj = df['Y(cm)'].diff().abs().max()
print("Max jump X: {:.2f} cm, Max jump Y: {:.2f} cm".format(max_xj, max_yj))

print("\n" + "=" * 80)
print("ALL FILES SAVED TO: " + OUTDIR)
print("=" * 80)
