import csv

path = r"C:\Users\Administrator\Desktop\Self-Driving\case1\slam_data_20260629_124940.csv"

with open(path, encoding='utf-8') as f:
    rows = list(csv.DictReader(f))

print("=== STEP messages (IMU: MPU6050) ===")
for r in rows:
    if r['msg_type'].strip() == 'STEP':
        print(f"  scan={r['scan_index']}, ax={r['pulse_L_or_ax']}, ay={r['pulse_R_or_ay']}, az={r['az']}, gz={r['gz']}")

print()
print("=== S messages first 5 rows (LiDAR + pulses) ===")
cnt = 0
for r in rows:
    if r['msg_type'].strip() == 'S' and cnt < 5:
        print(f"  angle={r['dist_or_yaw']}, L_pulse={r['pulse_L_or_ax']}, R_pulse={r['pulse_R_or_ay']}")
        cnt += 1

print()
print("=== ROT messages ===")
for r in rows:
    if r['msg_type'].strip() == 'ROT':
        print(f"  scan={r['scan_index']}, yaw={r['dist_or_yaw']}, ax={r['pulse_L_or_ax']}, ay={r['pulse_R_or_ay']}")
