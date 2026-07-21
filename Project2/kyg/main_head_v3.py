import statistics
import tkinter as tk
from tkinter import ttk, filedialog
import multiprocessing as mp
import math
import time
import cv2
import datetime
from PIL import Image, ImageTk

from vision_proc import vision_worker
from uart_proc import uart_worker

class HeadNodeApp:
    def __init__(self, root, uart_tx, uart_rx, vision_rx, vision_cmd_tx):
        self.root = root
        self.root.title("Antigravity Autonomous Rover - Head Node V2")
        self.root.geometry("800x600") # 화면 크기 축소 
        
        self.uart_tx = uart_tx
        self.uart_rx = uart_rx
        self.vision_rx = vision_rx
        self.vision_cmd_tx = vision_cmd_tx
        
        # 차량 초기 위치 (화면 축소로 인해 보이지 않는 문제 해결)
        self.pose = {'x': 200.0, 'y': 200.0, 'theta': 0.0}
        self.last_dist_l = 0.0
        self.last_dist_r = 0.0
        self.yaw = 0.0
        self.sonar = {'f': 999.0, 'l': 999.0, 'r': 999.0}
        
        self.mode = 'MANUAL'
        self.lane_keeping_enabled = True 
        
        # 완전 개편된 Reactive State Machine (V3)
        self.dwa_state = 'NORMAL_DRIVE' 
        self.evade_dir = 'none' 
        self.target_dist = 0.0
        self.clearance_start_pose = None
        self.step_start_pose = None
        self.f_dist_at_impact = 0.0
        
        # 비블로킹 타이머 변수
        self.step_start_time = 0.0
        self.stop_assess_start_time = 0.0
        self.enc_accumulated = 0.0
        self.target_enc_dist = 0.0
        self.step_cmd = 'w'
        self.last_side_dist = 999.0
        self.wall_tracking = False
        self.tracked_wall = 'none'
        self.clear_corner_pending = False
        self.bug_mode = 'SEEK'
        self.bug_hit_dist = 0.0
        self.sonar_history_f = []
        self.sonar_history_l = []
        self.sonar_history_r = []
        self.pursuit_step_time = 0.0
        self.pursuit_state = 'IDLE' # 'IDLE', 'TURN', 'FORWARD'
        self.clear_corner_stage = 0 # 0, 1, 2
        self.last_cmd = 'x'
        
        self.turn_count = 0
        self.last_turn_state = ''
        self.accumulated_angle = 0.0
        self.last_theta = 0.0
        self.best_escape_theta = None
        self.min_err = 999.0
        
        self.trajectory = []
        self.obstacles = []
        self.waypoints = [] 
        
        self.current_angle = 90.0
        
        self.setup_ui()
        self.update_loop()

    def log_print(self, msg):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        full_msg = f"[{timestamp}] {msg}"
        print(full_msg)
        
        self.txt_log.config(state=tk.NORMAL)
        self.txt_log.insert(tk.END, full_msg + "\n")
        self.txt_log.see(tk.END)
        self.txt_log.config(state=tk.DISABLED)

    def setup_ui(self):
        pw = ttk.PanedWindow(self.root, orient=tk.VERTICAL)
        pw.pack(fill=tk.BOTH, expand=True)
        
        # --- TOP: MAP & Control ---
        top_frame = tk.Frame(pw, height=350)
        pw.add(top_frame, weight=3)
        
        left_top = tk.Frame(top_frame)
        left_top.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tk.Label(left_top, text="SLAM Local Map (Left Click: Add Waypoint)", font=("Arial", 12, "bold")).pack()
        
        self.canvas = tk.Canvas(left_top, width=450, height=350, bg="#2C3E50", bd=2, relief=tk.SUNKEN)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.canvas.bind("<Configure>", lambda e: self.draw_map())
        self.canvas.bind("<Button-1>", self.on_map_click)
        
        right_top = tk.Frame(top_frame, width=350)
        right_top.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)
        
        self.lbl_mode = tk.Label(right_top, text="MANUAL", fg="blue", font=("Arial", 16, "bold"))
        self.lbl_mode.pack(pady=2)
        tk.Button(right_top, text="Toggle AUTO/MANUAL (t/u)", command=self.toggle_mode, width=30, height=2).pack(pady=2)
        
        # 장애물 회피 거리 슬라이더
        tk.Label(right_top, text="Evade Distance Threshold (cm)", font=("Arial", 9, "bold")).pack(pady=(5,0))
        self.scale_evade = tk.Scale(right_top, from_=10, to=150, orient=tk.HORIZONTAL, length=200)
        self.scale_evade.set(50)
        self.scale_evade.pack()

        # 기능 버튼들
        self.btn_lane = tk.Button(right_top, text="Lane Keeping: ON (l)", command=self.toggle_lane_keeping, width=30, bg="#A9DFBF")
        self.btn_lane.pack(pady=2)
        
        tk.Button(right_top, text="Return to Origin (Traceback)", command=self.action_traceback, width=30, bg="#F39C12").pack(pady=2)
        
        btn_frame_vid = tk.Frame(right_top)
        btn_frame_vid.pack(pady=5)
        tk.Button(btn_frame_vid, text="Load Video", command=self.load_video, width=15, bg="#D7BDE2").pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame_vid, text="Virtual Stream", command=self.load_virtual_stream, width=15, bg="#AED6F1").pack(side=tk.LEFT, padx=2)
        
        tk.Button(right_top, text="Reset Map & Waypoints", command=self.action_reset, width=30, bg="#F9E79F").pack(pady=2)
        tk.Button(right_top, text="Emergency Stop (x)", command=self.action_stop, width=30, bg="#ffcccc").pack(pady=2)
        
        # KEYPAD
        tk.Label(right_top, text="Manual Control (W/A/S/D)", font=("Arial", 10, "bold")).pack(pady=2)
        btn_frame = tk.Frame(right_top)
        btn_frame.pack()
        tk.Button(btn_frame, text="Q", width=4, command=lambda: self.send_cmd('q')).grid(row=0, column=0, padx=2, pady=2)
        tk.Button(btn_frame, text="W", width=4, command=lambda: self.send_cmd('w')).grid(row=0, column=1, padx=2, pady=2)
        tk.Button(btn_frame, text="E", width=4, command=lambda: self.send_cmd('e')).grid(row=0, column=2, padx=2, pady=2)
        tk.Button(btn_frame, text="A", width=4, command=lambda: self.send_cmd('a')).grid(row=1, column=0, padx=2, pady=2)
        tk.Button(btn_frame, text="S", width=4, command=lambda: self.send_cmd('s')).grid(row=1, column=1, padx=2, pady=2)
        tk.Button(btn_frame, text="D", width=4, command=lambda: self.send_cmd('d')).grid(row=1, column=2, padx=2, pady=2)

        # AI State Indicator
        self.lbl_ai = tk.Label(right_top, text="AI Steering: IDLE", font=("Arial", 10, "bold"), fg="purple")
        self.lbl_ai.pack(pady=(5,0))

        # 가상 CLCD
        tk.Label(right_top, text="Vehicle Log (SPI-LCD Mock)", font=("Arial", 10, "bold")).pack(pady=(5,0))
        self.txt_log = tk.Text(right_top, height=8, width=35, bg="#000000", fg="#00FF00", font=("Consolas", 9))
        self.txt_log.pack(fill=tk.BOTH, expand=True)
        self.txt_log.config(state=tk.DISABLED)

        # --- BOTTOM: CAMERA FEED ---
        bot_frame = tk.Frame(pw, height=250)
        pw.add(bot_frame, weight=1)
        
        tk.Label(bot_frame, text="ESP32-CAM Vision (Live or Video)", font=("Arial", 10, "bold")).pack()
        feed_frame = tk.Frame(bot_frame)
        feed_frame.pack(fill=tk.BOTH, expand=True)
        
        self.lbl_orig = tk.Label(feed_frame, bg="black")
        self.lbl_orig.pack(side=tk.LEFT, expand=True, padx=5, pady=5)
        
        self.lbl_proc = tk.Label(feed_frame, bg="black")
        self.lbl_proc.pack(side=tk.RIGHT, expand=True, padx=5, pady=5)
        
        self.root.bind("<KeyPress>", self.key_press)
        self.log_print("System Initialized. Waiting for Telemetry...")

    def on_map_click(self, event):
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        scale = 1.0
        offset_x = cw/2 - self.pose['x'] * scale
        offset_y = ch/2 - self.pose['y'] * scale
        
        real_x = (event.x - offset_x) / scale
        real_y = (event.y - offset_y) / scale
        
        self.waypoints.append((real_x, real_y))
        self.log_print(f"Waypoint Added: X={real_x:.1f}, Y={real_y:.1f}")
        self.draw_map()

    def load_video(self):
        path = filedialog.askopenfilename(filetypes=[("Video Files", "*.mp4 *.mov *.avi"), ("All Files", "*.*")])
        if path:
            self.vision_cmd_tx.put({'cmd': 'load_video', 'path': path})
            self.log_print(f"Loading Local Video: {path}")

    def load_virtual_stream(self):
        url = "http://127.0.0.1:81/"
        self.vision_cmd_tx.put({'cmd': 'load_video', 'path': url})
        self.log_print("Returned to Virtual Stream")

    def toggle_lane_keeping(self):
        self.lane_keeping_enabled = not self.lane_keeping_enabled
        if self.lane_keeping_enabled:
            self.btn_lane.config(text="Lane Keeping: ON (l)", bg="#A9DFBF")
            self.log_print("Lane Keeping Mode: ON (Vision Priority)")
        else:
            self.btn_lane.config(text="Lane Keeping: OFF (l)", bg="#F5B041")
            self.log_print("Lane Keeping Mode: OFF (Waypoint Pure Pursuit Priority)")

    def action_traceback(self):
        if len(self.trajectory) < 2:
            self.log_print("Not enough trajectory data for Traceback.")
            return
            
        trace = self.trajectory[::-1]
        downsampled = [trace[0]]
        for pt in trace[1:]:
            last_pt = downsampled[-1]
            if math.hypot(pt[0]-last_pt[0], pt[1]-last_pt[1]) > 20.0:
                downsampled.append(pt)
                
        self.waypoints = downsampled
        self.log_print(f"Traceback Initiated: {len(self.waypoints)} points to origin.")
        
        self.lane_keeping_enabled = False
        self.btn_lane.config(text="Lane Keeping: OFF (l)", bg="#F5B041")
        if self.mode != 'AUTO':
            self.toggle_mode()

    def action_reset(self):
        self.trajectory.clear()
        self.obstacles.clear()
        self.waypoints.clear()
        self.dwa_state = 'NORMAL_DRIVE'
        self.evade_dir = 'none'
        self.log_print("Map and Waypoints Reset.")
        self.draw_map()

    def toggle_mode(self):
        if self.mode == 'MANUAL':
            self.mode = 'AUTO'
            self.lbl_mode.config(text="AUTO", fg="red")
            self.send_cmd('t')
            self.log_print("Mode Changed: AUTO")
        else:
            self.mode = 'MANUAL'
            self.lbl_mode.config(text="MANUAL", fg="blue")
            self.send_cmd('u')
            self.send_cmd('x')
            self.log_print("Mode Changed: MANUAL")

    def action_stop(self):
        self.mode = 'MANUAL'
        self.lbl_mode.config(text="MANUAL", fg="blue")
        self.send_cmd('x')
        self.dwa_state = 'NORMAL_DRIVE'
        self.evade_dir = 'none'
        self.log_print("EMERGENCY STOP Triggered (State Reset)")

    def send_cmd(self, cmd):
        try: self.uart_tx.put_nowait(cmd)
        except: pass

    def key_press(self, event):
        char = event.char.lower()
        if char == 't' or char == 'u':
            self.toggle_mode()
        elif char == 'l':
            self.toggle_lane_keeping()
        elif char == 'x':
            self.action_stop()
        elif self.mode == 'MANUAL':
            if char in ['w', 'a', 's', 'd', 'q', 'e', 'z', 'c', '1', '2', '3']:
                self.send_cmd(char)

    def update_loop(self):
        try:
            while not self.uart_rx.empty():
                data = self.uart_rx.get_nowait()
                
                if data['crash'] == 1:
                    self.log_print("CRASH DETECTED from Body IMU!")
                    if self.mode == 'AUTO': self.action_stop()
                
                d_l = data['enc_l'] - self.last_dist_l
                d_r = data['enc_r'] - self.last_dist_r
                self.last_dist_l = data['enc_l']
                self.last_dist_r = data['enc_r']
                
                ddist = (d_l + d_r) / 2.0
                self.enc_accumulated += abs(ddist)
                self.yaw = data['yaw']
                
                rad = math.radians(self.yaw)
                self.pose['x'] += ddist * math.cos(rad)
                self.pose['y'] += ddist * math.sin(rad)
                self.pose['theta'] = self.yaw
                
                if not self.trajectory or math.hypot(self.pose['x'] - self.trajectory[-1][0], self.pose['y'] - self.trajectory[-1][1]) > 2.0:
                    self.trajectory.append((self.pose['x'], self.pose['y']))
                
                self.sonar_history_f.append(data['sonar_f'])
                self.sonar_history_l.append(data['sonar_l'])
                self.sonar_history_r.append(data['sonar_r'])
                
                if len(self.sonar_history_f) > 5:
                    self.sonar_history_f.pop(0)
                    self.sonar_history_l.pop(0)
                    self.sonar_history_r.pop(0)
                    
                self.sonar['f'] = statistics.median(self.sonar_history_f) if self.sonar_history_f else data['sonar_f']
                self.sonar['l'] = statistics.median(self.sonar_history_l) if self.sonar_history_l else data['sonar_l']
                self.sonar['r'] = statistics.median(self.sonar_history_r) if self.sonar_history_r else data['sonar_r']
                
                if int(time.time()*10) % 10 == 0:
                    print(f"[Telemetry] F:{self.sonar['f']:.1f} L:{self.sonar['l']:.1f} R:{self.sonar['r']:.1f} Yaw:{self.yaw:.1f}")

                self.update_local_obstacles()
                self.draw_map()
        except: pass

        try:
            if not self.vision_rx.empty():
                angle, orig, proc = self.vision_rx.get_nowait()
                self.current_angle = angle
                
                # UI에 맞게 이미지 크기 축소 (320x240 -> 240x180)
                orig_rgb = cv2.resize(cv2.cvtColor(orig, cv2.COLOR_BGR2RGB), (240, 180))
                proc_rgb = cv2.resize(cv2.cvtColor(proc, cv2.COLOR_BGR2RGB), (240, 180))
                
                im1 = ImageTk.PhotoImage(image=Image.fromarray(orig_rgb))
                im2 = ImageTk.PhotoImage(image=Image.fromarray(proc_rgb))
                
                self.lbl_orig.config(image=im1)
                self.lbl_orig.image = im1
                self.lbl_proc.config(image=im2)
                self.lbl_proc.image = im2
        except: pass

        if self.mode == 'AUTO':
            try:
                self.execute_dwa()
            except Exception as e:
                self.log_print(f"ERROR in DWA: {e}")
                self.action_stop()
        else:
            self.lbl_ai.config(text="AI Steering: IDLE", fg="purple")

        self.root.after(50, self.update_loop)

    def update_local_obstacles(self):
        rad = math.radians(self.pose['theta'])
        cx, cy = self.pose['x'], self.pose['y']
        
        if self.sonar['f'] < 100.0:
            ox = cx + self.sonar['f'] * math.cos(rad)
            oy = cy + self.sonar['f'] * math.sin(rad)
            self.add_obstacle_to_map(ox, oy)
        if self.sonar['l'] < 100.0:
            ox = cx + self.sonar['l'] * math.cos(rad - math.pi/2)
            oy = cy + self.sonar['l'] * math.sin(rad - math.pi/2)
            self.add_obstacle_to_map(ox, oy)
        if self.sonar['r'] < 100.0:
            ox = cx + self.sonar['r'] * math.cos(rad + math.pi/2)
            oy = cy + self.sonar['r'] * math.sin(rad + math.pi/2)
            self.add_obstacle_to_map(ox, oy)

    def add_obstacle_to_map(self, x, y):
        for ox, oy in self.obstacles[-50:]: 
            if math.hypot(ox - x, oy - y) < 5.0: return
        self.obstacles.append((x, y))
        if len(self.obstacles) > 1000: self.obstacles.pop(0)

    def get_valid_local_obstacles(self, cx, cy, radius=50.0):
        local_obs = [(x, y) for x, y in self.obstacles if math.hypot(x-cx, y-cy) <= radius]
        valid_obs = []
        for x1, y1 in local_obs:
            neighbors = sum(1 for x2, y2 in local_obs if math.hypot(x1-x2, y1-y2) < 15.0)
            if neighbors >= 2: # At least 2 neighbors within 15cm (excluding self)
                valid_obs.append((x1, y1))
        return valid_obs

    def execute_dwa(self):
        f_dist, l_dist, r_dist = self.sonar['f'], self.sonar['l'], self.sonar['r']
        
        # --- 1. 차선 인식 모드 (부드러운 곡선 제어 및 회피) ---
        if self.lane_keeping_enabled:
            if self.dwa_state == 'NORMAL_DRIVE':
                if f_dist < 40.0 or l_dist < 20.0 or r_dist < 20.0:
                    self.dwa_state = 'LANE_EVADE'
                    self.last_evade_cmd = 'q' if r_dist < l_dist else 'e'
                    self.log_print(f"LANE KEEPING: Obstacle detected. Evading ({self.last_evade_cmd})")
                else:
                    err = self.current_angle - 90.0
                    if err > 15.0: cmd = 'a'
                    elif err < -15.0: cmd = 'd'
                    else: cmd = 'w'
                    self.send_cmd(cmd)
                    return
            
            if self.dwa_state == 'LANE_EVADE':
                if f_dist > 50.0 and l_dist > 40.0 and r_dist > 40.0:
                    self.dwa_state = 'LANE_RETURN'
                    self.step_start_time = time.time()
                    self.log_print("LANE KEEPING: Obstacle cleared. Returning to lane.")
                else:
                    self.send_cmd(self.last_evade_cmd)
                return
            
            elif self.dwa_state == 'LANE_RETURN':
                if time.time() - self.step_start_time > 1.5:
                    self.dwa_state = 'NORMAL_DRIVE'
                    self.log_print("LANE KEEPING: Returned to lane.")
                else:
                    cmd = 'e' if self.last_evade_cmd == 'q' else 'q'
                    self.send_cmd(cmd)
                return
            return

        # --- 2. 장애물 회피 모드 (VFH + 이산 스텝/제자리 회전) ---
        
        # 2-1. 스텝 직진 상태
        if self.dwa_state == 'STEP_FORWARD':
            if self.enc_accumulated >= self.target_enc_dist:
                self.send_cmd('x')
                self.dwa_state = 'NORMAL_DRIVE'
                self.lbl_ai.config(text="AI State: NORMAL_DRIVE (Step Done)", fg="blue")
            else:
                self.send_cmd('w')
                self.lbl_ai.config(text=f"AI State: STEP_FORWARD ({self.enc_accumulated:.1f}/{self.target_enc_dist}cm)", fg="orange")
            return
            
        # 2-2. 제자리 회전 상태
        elif self.dwa_state == 'TURN_IN_PLACE':
            turned = abs(self.pose['theta'] - self.align_start_pose['theta'])
            if turned > 180: turned = 360 - turned
            
            if turned >= self.align_target_angle:
                self.send_cmd('x')
                if self.clear_corner_pending:
                    self.clear_corner_pending = False
                    self.dwa_state = 'STEP_FORWARD'
                    self.target_enc_dist = 8.8
                    self.enc_accumulated = 0.0
                    self.send_cmd('w')
                    self.log_print("State: STEP_FORWARD (After Corner Turn)")
                else:
                    self.dwa_state = 'STEP_FORWARD'
                    self.target_enc_dist = 8.8
                    self.enc_accumulated = 0.0
                    self.send_cmd('w')
                    self.log_print("State: STEP_FORWARD (After VFH Turn)")
            else:
                self.send_cmd(self.align_turn_dir)
                self.lbl_ai.config(text=f"AI State: TURN_IN_PLACE ({turned:.1f}/{self.align_target_angle} deg)", fg="red")
            return

        # 2-3. 모서리 탈출 (벽 끝에서 1바퀴 직진)
        elif self.dwa_state == 'CLEAR_CORNER_STEP':
            if self.enc_accumulated >= 17.6: # 1바퀴 (8슬릿)
                self.send_cmd('x')
                self.dwa_state = 'TURN_IN_PLACE'
                self.align_target_angle = 85.0
                self.align_start_pose = self.pose.copy()
                self.align_turn_dir = self.corner_turn_dir
                self.clear_corner_pending = True
                self.send_cmd(self.align_turn_dir)
                self.log_print("State: TURN_IN_PLACE (Cleared corner 1 lap, turning 90deg)")
            else:
                self.send_cmd('w')
                self.lbl_ai.config(text=f"AI State: CLEAR_CORNER_STEP ({self.enc_accumulated:.1f}/17.6cm)", fg="purple")
            return

        # 2-4. 판단 모드 (VFH)
        if not self.waypoints:
            self.send_cmd('x')
            return

        if f_dist < 15.0: # 초근접 비상
            self.send_cmd('s')
            return
            
        cx, cy = self.pose['x'], self.pose['y']
        valid_obs = self.get_valid_local_obstacles(cx, cy, radius=70.0)
        
        tx, ty = self.waypoints[0]
        dist_to_target = math.hypot(tx - cx, ty - cy)
        
        if dist_to_target < 20.0:
            self.waypoints.pop(0)
            self.bug_mode = 'SEEK'
            return
            
        target_rad = math.atan2(ty - cy, tx - cx)
        target_deg = (math.degrees(target_rad) % 360)
        robot_theta = self.pose['theta']
        
        # Bug 모드 상태 전이 로직
        if self.bug_mode == 'SEEK':
            if f_dist < 50.0 and l_dist < 50.0 and r_dist < 50.0:
                self.bug_mode = 'FOLLOW_RIGHT'
                self.bug_hit_dist = dist_to_target
                self.log_print(f"BUG MODE: TRAPPED (3-Sides)! Switched to FOLLOW_RIGHT.")
            elif f_dist < 30.0:
                self.bug_mode = 'FOLLOW_RIGHT' if l_dist < r_dist else 'FOLLOW_LEFT'
                self.bug_hit_dist = dist_to_target
                self.log_print(f"BUG MODE: TRAPPED (Front)! Switched to {self.bug_mode}.")
        else:
            if dist_to_target < self.bug_hit_dist - 15.0:
                clear_to_target = True
                for ox, oy in valid_obs:
                    obs_rad = math.atan2(oy - cy, ox - cx)
                    obs_deg = (math.degrees(obs_rad) % 360)
                    ang_diff = abs(obs_deg - target_deg)
                    if ang_diff > 180: ang_diff = 360 - ang_diff
                    if ang_diff < 20.0 and math.hypot(ox-cx, oy-cy) < 40.0:
                        clear_to_target = False
                        break
                if clear_to_target:
                    self.bug_mode = 'SEEK'
                    self.log_print("BUG MODE: Escaped Local Minima! Returning to SEEK.")

        # 10도 단위 탐색 (-40도 ~ +40도)
        best_angle = None
        min_cost = 999999
        
        for offset in range(-40, 41, 10):
            eval_deg = (robot_theta + offset) % 360
            
            if self.bug_mode == 'SEEK':
                obs_cost = 0
                for ox, oy in valid_obs:
                    obs_rad = math.atan2(oy - cy, ox - cx)
                    obs_deg = (math.degrees(obs_rad) % 360)
                    ang_diff = abs(obs_deg - eval_deg)
                    if ang_diff > 180: ang_diff = 360 - ang_diff
                    dist = math.hypot(ox - cx, oy - cy)
                    if ang_diff < 15.0 and dist < 50.0: 
                        obs_cost += (50.0 - dist) * 10.0
                
                if obs_cost > 100: continue
                
                t_diff = abs(target_deg - eval_deg)
                if t_diff > 180: t_diff = 360 - t_diff
                total_cost = obs_cost + t_diff
                
                if total_cost < min_cost:
                    min_cost = total_cost
                    best_angle = offset
                    
            elif self.bug_mode == 'FOLLOW_RIGHT':
                min_r_dist = 999.0
                best_r_ang_diff = 999.0
                front_obs = False
                for ox, oy in valid_obs:
                    obs_rad = math.atan2(oy - cy, ox - cx)
                    obs_deg = (math.degrees(obs_rad) % 360)
                    dist = math.hypot(ox - cx, oy - cy)
                    
                    ang_diff_f = abs(obs_deg - eval_deg)
                    if ang_diff_f > 180: ang_diff_f = 360 - ang_diff_f
                    if ang_diff_f < 20.0 and dist < 20.0:
                        front_obs = True
                        break
                        
                    target_r = (eval_deg + 90) % 360
                    ang_diff_r = abs(obs_deg - target_r)
                    if ang_diff_r > 180: ang_diff_r = 360 - ang_diff_r
                    
                    if ang_diff_r < 90.0: # 우측 반구 전체
                        if dist < min_r_dist:
                            min_r_dist = dist
                            best_r_ang_diff = ang_diff_r
                
                if front_obs: continue 
                
                if min_r_dist > 100.0:
                    total_cost = 500.0 - offset # 우측으로 강하게 회전 유도
                else:
                    total_cost = abs(min_r_dist - 30.0) * 10.0 + best_r_ang_diff
                    
                if total_cost < min_cost:
                    min_cost = total_cost
                    best_angle = offset
                    
            elif self.bug_mode == 'FOLLOW_LEFT':
                min_l_dist = 999.0
                best_l_ang_diff = 999.0
                front_obs = False
                for ox, oy in valid_obs:
                    obs_rad = math.atan2(oy - cy, ox - cx)
                    obs_deg = (math.degrees(obs_rad) % 360)
                    dist = math.hypot(ox - cx, oy - cy)
                    
                    ang_diff_f = abs(obs_deg - eval_deg)
                    if ang_diff_f > 180: ang_diff_f = 360 - ang_diff_f
                    if ang_diff_f < 20.0 and dist < 20.0:
                        front_obs = True
                        break
                        
                    target_l = (eval_deg - 90) % 360
                    ang_diff_l = abs(obs_deg - target_l)
                    if ang_diff_l > 180: ang_diff_l = 360 - ang_diff_l
                    
                    if ang_diff_l < 90.0: # 좌측 반구 전체
                        if dist < min_l_dist:
                            min_l_dist = dist
                            best_l_ang_diff = ang_diff_l
                
                if front_obs: continue 
                
                if min_l_dist > 100.0:
                    total_cost = 500.0 + offset # 좌측으로 강하게 회전 유도 (- offset)
                else:
                    total_cost = abs(min_l_dist - 30.0) * 10.0 + best_l_ang_diff
                    
                if total_cost < min_cost:
                    min_cost = total_cost
                    best_angle = offset

        # 모서리 돌파 감지 로직 (벽타기 종료)
        # 벽을 타고 있었는데 (이전 거리 < 30), 이제 좌우 양쪽 다 뚫렸을 때 (50cm 이상)
        if self.wall_tracking and self.last_side_dist < 30.0 and l_dist > 50.0 and r_dist > 50.0:
            self.wall_tracking = False
            self.dwa_state = 'CLEAR_CORNER_STEP'
            self.enc_accumulated = 0.0
            # 벽이 있던 방향으로 90도 회전할 준비
            self.corner_turn_dir = 'a' if self.tracked_wall == 'left' else 'd'
            self.send_cmd('w')
            self.log_print(f"Wall Ended! Transition to CLEAR_CORNER_STEP. Will turn {self.corner_turn_dir}")
            return

        # 벽타기 상태 지속 업데이트
        if l_dist < 30.0:
            self.wall_tracking = True
            self.tracked_wall = 'left'
            self.last_side_dist = l_dist
        elif r_dist < 30.0:
            self.wall_tracking = True
            self.tracked_wall = 'right'
            self.last_side_dist = r_dist
            
        if best_angle is None:
            # 모든 방향이 막힘 -> 유턴
            self.dwa_state = 'TURN_IN_PLACE'
            self.align_target_angle = 170.0
            self.align_start_pose = self.pose.copy()
            self.align_turn_dir = 'd'
            self.send_cmd('d')
            self.log_print("VFH: Trapped! U-Turn initiated.")
            return
            
        if abs(best_angle) > 5.0:
            # 회전이 필요한 경우 제자리 회전
            self.dwa_state = 'TURN_IN_PLACE'
            self.align_target_angle = abs(best_angle)
            self.align_start_pose = self.pose.copy()
            self.align_turn_dir = 'd' if best_angle > 0 else 'a'
            self.clear_corner_pending = False
            self.send_cmd(self.align_turn_dir)
            self.lbl_ai.config(text=f"AI State: VFH Turn ({best_angle}deg)", fg="red")
        else:
            # 정렬되어 있으면 직진 스텝
            self.dwa_state = 'STEP_FORWARD'
            self.target_enc_dist = 8.8
            self.enc_accumulated = 0.0
            self.send_cmd('w')
            self.lbl_ai.config(text="AI State: VFH Step (w)", fg="green")

    def draw_map(self):
        self.canvas.delete("all")
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw <= 1 or ch <= 1: return
        
        scale = 1.0
        offset_x = cw/2 - self.pose['x'] * scale
        offset_y = ch/2 - self.pose['y'] * scale
        
        if len(self.trajectory) > 1:
            for i in range(max(0, len(self.trajectory)-200), len(self.trajectory)-1):
                p1, p2 = self.trajectory[i], self.trajectory[i+1]
                x1, y1 = p1[0]*scale + offset_x, p1[1]*scale + offset_y
                x2, y2 = p2[0]*scale + offset_x, p2[1]*scale + offset_y
                self.canvas.create_line(x1, y1, x2, y2, fill="#7F8C8D", width=2)
                
        if self.waypoints:
            wp_pts = [(self.pose['x'], self.pose['y'])] + self.waypoints
            for i in range(len(wp_pts)-1):
                x1, y1 = wp_pts[i][0]*scale + offset_x, wp_pts[i][1]*scale + offset_y
                x2, y2 = wp_pts[i+1][0]*scale + offset_x, wp_pts[i+1][1]*scale + offset_y
                self.canvas.create_line(x1, y1, x2, y2, fill="#8E44AD", width=2, dash=(4,2))
                
            for wp in self.waypoints:
                x = wp[0]*scale + offset_x
                y = wp[1]*scale + offset_y
                self.canvas.create_oval(x-5, y-5, x+5, y+5, fill="#F1C40F", outline="black")
                
        for obs in self.obstacles:
            x = obs[0]*scale + offset_x
            y = obs[1]*scale + offset_y
            self.canvas.create_oval(x-3, y-3, x+3, y+3, fill="#E74C3C", outline="")

        cx = self.pose['x']*scale + offset_x
        cy = self.pose['y']*scale + offset_y
        rad = math.radians(self.pose['theta'])
        
        L = 15
        pts = [
            (cx + L*math.cos(rad), cy + L*math.sin(rad)),
            (cx + (L-5)*math.cos(rad + 2.5), cy + (L-5)*math.sin(rad + 2.5)),
            (cx - (L-10)*math.cos(rad) + 10*math.cos(rad + 1.57), cy - (L-10)*math.sin(rad) + 10*math.sin(rad + 1.57)),
            (cx - (L-10)*math.cos(rad) - 10*math.cos(rad + 1.57), cy - (L-10)*math.sin(rad) - 10*math.sin(rad + 1.57)),
            (cx + (L-5)*math.cos(rad - 2.5), cy + (L-5)*math.sin(rad - 2.5))
        ]
        self.canvas.create_polygon(pts, fill="#3498DB", outline="#ECF0F1", width=2)

if __name__ == '__main__':
    mp.freeze_support()
    try:
        mp.set_start_method('spawn')
    except RuntimeError:
        pass
    
    uart_tx_q = mp.Queue(maxsize=10)
    uart_rx_q = mp.Queue(maxsize=10)
    vision_rx_q = mp.Queue(maxsize=3)
    vision_cmd_tx_q = mp.Queue(maxsize=3)
    
    SIMULATION_MODE = True
    
    if SIMULATION_MODE:
        UART_PORT = 'TCP:127.0.0.1:9999'
        CAM_URL = "http://127.0.0.1:81/"
    else:
        UART_PORT = 'COM3' 
        CAM_URL = "http://192.168.0.100:81/" 
        
    MODEL_PATH = r"C:\Users\user\Desktop\RasberryPi\class_lesson\Chapter07\model_out_author_invert_clahe\lane_navigation_final.torchscript"
    
    p_uart = mp.Process(target=uart_worker, args=(UART_PORT, 115200, uart_rx_q, uart_tx_q), daemon=True)
    p_vision = mp.Process(target=vision_worker, args=(CAM_URL, MODEL_PATH, vision_rx_q, vision_cmd_tx_q), daemon=True)
    
    p_uart.start()
    p_vision.start()
    
    root = tk.Tk()
    app = HeadNodeApp(root, uart_tx_q, uart_rx_q, vision_rx_q, vision_cmd_tx_q)
    root.mainloop()
    
    p_uart.terminate()
    p_vision.terminate()
