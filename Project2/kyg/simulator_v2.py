import tkinter as tk
from tkinter import ttk
import serial
import threading
import time
import math
import cv2
import numpy as np
import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

# 전역 밝기 제어를 위한 변수 (GUI에서 조절)
global_brightness = 100 

# ==========================================
# 1. MJPEG 스트리밍 서버 (ESP32-CAM 모사)
# ==========================================
class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    pass

class MJPEGHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global global_brightness
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'multipart/x-mixed-replace; boundary=frame')
            self.end_headers()
            
            frame_w, frame_h = 320, 240
            offset = 0
            
            while True:
                try:
                    img = np.zeros((frame_h, frame_w, 3), dtype=np.uint8)
                    img[:] = (100, 100, 100)
                    
                    offset = (offset + 5) % 40
                    for y in range(0, frame_h, 40):
                        cv2.line(img, (frame_w//2, y + offset), (frame_w//2, y + 20 + offset), (0, 255, 255), 4)
                        
                    cv2.line(img, (50, 0), (10, frame_h), (255, 255, 255), 3)
                    cv2.line(img, (frame_w-50, 0), (frame_w-10, frame_h), (255, 255, 255), 3)
                    
                    # 조도 (Brightness) 적용 (어두워지는 효과)
                    factor = max(global_brightness / 100.0, 0.1) # 완전히 까맣게 되는 것을 방지
                    img = cv2.convertScaleAbs(img, alpha=factor, beta=0)
                    
                    cv2.putText(img, f"ESP32-CAM Simulator | B:{global_brightness}%", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255), 1)

                    ret, jpeg = cv2.imencode('.jpg', img)
                    frame_bytes = jpeg.tobytes()
                    
                    self.wfile.write(b'--frame\r\n')
                    self.send_header('Content-type', 'image/jpeg')
                    self.send_header('Content-length', len(frame_bytes))
                    self.end_headers()
                    self.wfile.write(frame_bytes)
                    self.wfile.write(b'\r\n')
                    
                    time.sleep(0.05) 
                except Exception as e:
                    break

def start_mjpeg_server():
    try:
        server = ThreadedHTTPServer(('0.0.0.0', 81), MJPEGHandler)
        print("[Simulator] MJPEG Server started on port 81")
        server.serve_forever()
    except OSError as e:
        print(f"[Simulator] MJPEG Port 81 in use: {e}")

# ==========================================
# 2. 메인 시뮬레이터 클래스 
# ==========================================
class SimulatorV2App:
    def __init__(self, root):
        self.root = root
        self.root.title("Antigravity Autonomous Rover - Environment Simulator V2 (Day/Night)")
        self.root.geometry("800x600") # 절반 정도로 축소 (사용자 요청)
        
        self.pose = {'x': 200.0, 'y': 200.0, 'theta': 0.0}
        self.enc_l = 0.0
        self.enc_r = 0.0
        self.v = 0.0
        self.w = 0.0
        self.target_v = 0.0
        self.target_w = 0.0
        self.crash = 0
        
        self.sonar = {'f': 999.0, 'l': 999.0, 'r': 999.0}
        self.line_obstacles = [] 
        
        self.drag_start = None
        self.ser = None
        self.is_connected = False
        
        self.setup_ui()
        
        self.sim_thread = threading.Thread(target=self.physics_loop, daemon=True)
        self.sim_thread.start()
        
        self.serial_thread = threading.Thread(target=self.serial_loop, daemon=True)
        self.serial_thread.start()

    def log_lcd(self, msg):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.txt_lcd.config(state=tk.NORMAL)
        self.txt_lcd.insert(tk.END, f"[{timestamp}] {msg}\n")
        self.txt_lcd.see(tk.END)
        self.txt_lcd.config(state=tk.DISABLED)

    def setup_ui(self):
        left_frame = tk.Frame(self.root)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        toolbar = tk.Frame(left_frame)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(toolbar, text="Map Zoom:").pack(side=tk.LEFT)
        self.scale_zoom = tk.Scale(toolbar, from_=0.5, to=3.0, resolution=0.1, orient=tk.HORIZONTAL, command=self.on_zoom)
        self.scale_zoom.set(1.5)
        self.scale_zoom.pack(side=tk.LEFT, padx=5)
        
        tk.Label(toolbar, text="[Right-Click & Drag] to draw Walls", fg="blue").pack(side=tk.LEFT, padx=20)
        
        # 조도 제어 바
        tk.Label(toolbar, text="Env Brightness (%):", fg="orange", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=(30, 5))
        self.scale_bright = tk.Scale(toolbar, from_=0, to=100, orient=tk.HORIZONTAL, command=self.on_bright)
        self.scale_bright.set(100)
        self.scale_bright.pack(side=tk.LEFT)
        
        self.canvas = tk.Canvas(left_frame, bg="#EAECEE", bd=2, relief=tk.SUNKEN)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.canvas.bind("<ButtonPress-3>", self.on_rclick_press)
        self.canvas.bind("<B3-Motion>", self.on_rclick_drag)
        self.canvas.bind("<ButtonRelease-3>", self.on_rclick_release)
        
        right_frame = tk.Frame(self.root, width=320)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)
        right_frame.pack_propagate(False)
        
        self.lbl_conn = tk.Label(right_frame, text="COM4 Waiting...", fg="orange", font=("Arial", 12, "bold"))
        self.lbl_conn.pack(pady=10)
        
        tk.Label(right_frame, text="Current Telemetry", font=("Arial", 10, "bold")).pack(pady=5)
        self.lbl_sf = tk.Label(right_frame, text="Front: 999.0")
        self.lbl_sf.pack()
        self.lbl_sl = tk.Label(right_frame, text="Left: 999.0")
        self.lbl_sl.pack()
        self.lbl_sr = tk.Label(right_frame, text="Right: 999.0")
        self.lbl_sr.pack()
        self.lbl_pose = tk.Label(right_frame, text="X: 0.0, Y: 0.0, Yaw: 0.0")
        self.lbl_pose.pack()
        self.lbl_enc = tk.Label(right_frame, text="Enc L: 0.0 | R: 0.0")
        self.lbl_enc.pack()
        
        tk.Label(right_frame, text="Last Command", font=("Arial", 9)).pack(pady=(10,0))
        self.lbl_cmd = tk.Label(right_frame, text="Idle (x)", font=("Arial", 16, "bold"), fg="blue")
        self.lbl_cmd.pack()
        
        tk.Label(right_frame, text="Vehicle State (Mock)", font=("Arial", 10, "bold")).pack(pady=(10,5))
        self.car_ui = tk.Canvas(right_frame, width=150, height=120, bg="#FFFFFF", highlightthickness=1, highlightbackground="gray")
        self.car_ui.pack()
        self.draw_car_ui('x')
        
        tk.Button(right_frame, text="Reset Map & Pose", command=self.reset_sim, bg="#ffcccc", height=2).pack(fill=tk.X, pady=10)
        
        # SPI-LCD / CLCD 로그 시뮬레이션 창
        tk.Label(right_frame, text="SPI-LCD / CLCD Output", font=("Arial", 10, "bold"), bg="#1ABC9C", fg="white").pack(fill=tk.X, pady=(10,0))
        self.txt_lcd = tk.Text(right_frame, height=10, width=35, bg="#2C3E50", fg="#F1C40F", font=("Consolas", 9))
        self.txt_lcd.pack(fill=tk.BOTH, expand=True)
        self.txt_lcd.config(state=tk.DISABLED)

    def on_zoom(self, event=None):
        self.update_gui_map()
        
    def on_bright(self, event=None):
        global global_brightness
        global_brightness = self.scale_bright.get()
        self.draw_car_ui(self.lbl_cmd.cget("text")[-2]) # 현재 명령어 추출 후 다시 그리기

    def get_real_coords(self, event):
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        zoom = self.scale_zoom.get()
        cx, cy = cw/2, ch/2
        rx = (event.x - cx) / zoom + self.pose['x']
        ry = (event.y - cy) / zoom + self.pose['y']
        return rx, ry

    def on_rclick_press(self, event):
        rx, ry = self.get_real_coords(event)
        self.drag_start = (rx, ry)
        
    def on_rclick_drag(self, event):
        if not self.drag_start: return
        self.canvas.delete("temp_line")
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        zoom = self.scale_zoom.get()
        cx, cy = cw/2, ch/2
        x1 = (self.drag_start[0] - self.pose['x']) * zoom + cx
        y1 = (self.drag_start[1] - self.pose['y']) * zoom + cy
        self.canvas.create_line(x1, y1, event.x, event.y, fill="red", width=3, dash=(4,4), tags="temp_line")
        
    def on_rclick_release(self, event):
        if not self.drag_start: return
        self.canvas.delete("temp_line")
        rx, ry = self.get_real_coords(event)
        if math.hypot(rx - self.drag_start[0], ry - self.drag_start[1]) > 10.0:
            self.line_obstacles.append((self.drag_start[0], self.drag_start[1], rx, ry))
            self.log_lcd("Obstacle Wall Added")
        self.drag_start = None
        self.update_gui_map()

    def reset_sim(self):
        self.pose = {'x': 100.0, 'y': 400.0, 'theta': 0.0}
        self.enc_l = 0.0
        self.enc_r = 0.0
        self.target_v = 0.0
        self.target_w = 0.0
        self.line_obstacles.clear()
        self.log_lcd("Simulation Reset")
        self.update_gui_map()

    def draw_car_ui(self, cmd):
        if cmd not in ['w','a','s','d','q','e','z','c','x']: cmd = 'x'
        c = self.car_ui
        c.delete("all")
        
        c.create_rectangle(50, 20, 100, 100, fill="#2C3E50", outline="black", width=2)
        c.create_rectangle(55, 30, 95, 55, fill="#85C1E9") 
        
        c.create_rectangle(40, 25, 48, 45, fill="black")
        c.create_rectangle(102, 25, 110, 45, fill="black")
        c.create_rectangle(40, 75, 48, 95, fill="black") 
        c.create_rectangle(102, 75, 110, 95, fill="black") 
        
        # 헤드라이트 (LED 효과) - 조도가 30 이하일 때 켜짐
        if global_brightness <= 30:
            c.create_oval(55, 15, 65, 25, fill="yellow", outline="orange")
            c.create_oval(85, 15, 95, 25, fill="yellow", outline="orange")
            c.create_text(75, 10, text="LED ON", fill="orange", font=("Arial", 7))
        else:
            c.create_oval(55, 15, 65, 25, fill="gray", outline="black")
            c.create_oval(85, 15, 95, 25, fill="gray", outline="black")
        
        if cmd == 'w': c.create_polygon(75, 5, 60, 20, 90, 20, fill="#27AE60")
        elif cmd == 'a': c.create_polygon(35, 60, 50, 45, 50, 75, fill="#27AE60")
        elif cmd == 'd': c.create_polygon(115, 60, 100, 45, 100, 75, fill="#27AE60")
        elif cmd == 's': c.create_polygon(75, 115, 60, 100, 90, 100, fill="#E74C3C")
        elif cmd == 'q': c.create_polygon(40, 5, 30, 20, 55, 20, fill="#27AE60")
        elif cmd == 'e': c.create_polygon(110, 5, 95, 20, 120, 20, fill="#27AE60")
        elif cmd == 'x': c.create_oval(70, 55, 80, 65, fill="red")
            
        self.lbl_cmd.config(text=f"Command: '{cmd}'")

    def serial_loop(self):
        import socket
        host = '127.0.0.1'
        port = 9999
        
        while True:
            try:
                server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                server.bind((host, port))
                server.listen(1)
                
                self.root.after(0, lambda: self.lbl_conn.config(text="TCP Server: Waiting for Head Node...", fg="orange"))
                
                conn, addr = server.accept()
                conn.settimeout(0.1)
                self.is_connected = True
                self.root.after(0, lambda: self.lbl_conn.config(text=f"TCP Connected: {addr[0]}:{addr[1]}", fg="green"))
                self.log_lcd("TCP Connected.")
                
                while True:
                    packet = f"S:{self.sonar['f']:.1f},{self.sonar['l']:.1f},{self.sonar['r']:.1f}|Y:{self.pose['theta']:.1f}|E:{self.enc_l:.1f},{self.enc_r:.1f}|C:{self.crash}\n"
                    conn.sendall(packet.encode('utf-8'))
                    
                    try:
                        data = conn.recv(1024)
                        if not data:
                            break
                        char_str = data.decode('utf-8', errors='ignore')
                        for char in char_str:
                            if char in ['w', 'a', 's', 'd', 'q', 'e', 'z', 'c', 'x']:
                                self.process_command(char)
                    except socket.timeout:
                        pass
                        
                    time.sleep(0.1)
                    
            except Exception as e:
                self.is_connected = False
                self.root.after(0, lambda: self.lbl_conn.config(text="TCP Disconnected. Re-listening...", fg="red"))
                time.sleep(1)
            finally:
                try: server.close()
                except: pass

    def process_command(self, cmd):
        speed = 30.0 
        w_speed = 45.0 
        
        if cmd == 'w': self.target_v = speed; self.target_w = 0.0
        elif cmd == 's': self.target_v = -speed; self.target_w = 0.0
        elif cmd == 'a': self.target_v = 0.0; self.target_w = -w_speed
        elif cmd == 'd': self.target_v = 0.0; self.target_w = w_speed
        elif cmd == 'q': self.target_v = speed; self.target_w = -w_speed/2
        elif cmd == 'e': self.target_v = speed; self.target_w = w_speed/2
        elif cmd == 'x': self.target_v = 0.0; self.target_w = 0.0
            
        self.root.after(0, lambda: self.draw_car_ui(cmd))

    def physics_loop(self):
        dt = 0.05 
        last_log_time = time.time()
        
        while True:
            self.v += (self.target_v - self.v) * 0.2
            self.w += (self.target_w - self.w) * 0.2
            
            rad = math.radians(self.pose['theta'])
            dx = self.v * math.cos(rad) * dt
            dy = self.v * math.sin(rad) * dt
            dtheta = self.w * dt
            
            self.pose['x'] += dx
            self.pose['y'] += dy
            self.pose['theta'] = (self.pose['theta'] + dtheta) % 360
            
            self.enc_l += self.v * dt - (self.w * 0.1) * dt
            self.enc_r += self.v * dt + (self.w * 0.1) * dt
            
            self.sonar['f'] = self.raycast_cone(self.pose['x'], self.pose['y'], self.pose['theta'])
            self.sonar['l'] = self.raycast_cone(self.pose['x'], self.pose['y'], self.pose['theta'] - 90)
            self.sonar['r'] = self.raycast_cone(self.pose['x'], self.pose['y'], self.pose['theta'] + 90)
            
            if self.check_physical_collision():
                if self.v > 0:
                    self.v = 0.0
                    self.target_v = 0.0
                
            if time.time() - last_log_time > 1.0:
                self.root.after(0, lambda: self.log_lcd(f"DistF:{self.sonar['f']:.1f} Yaw:{self.pose['theta']:.1f} MV:{(self.enc_l+self.enc_r)/2:.1f}"))
                last_log_time = time.time()
            
            self.root.after(0, self.update_gui_vars)
            time.sleep(dt)

    def raycast(self, ox, oy, angle_deg, max_dist=200.0):
        rad = math.radians(angle_deg)
        dx = math.cos(rad)
        dy = math.sin(rad)
        min_dist = max_dist
        
        for (x3, y3, x4, y4) in self.line_obstacles:
            x1, y1 = ox, oy
            x2, y2 = ox + dx * max_dist, oy + dy * max_dist
            
            den = (x1-x2)*(y3-y4) - (y1-y2)*(x3-x4)
            if den == 0: continue
            
            t = ((x1-x3)*(y3-y4) - (y1-y3)*(x3-x4)) / den
            u = -((x1-x2)*(y1-y3) - (y1-y2)*(x1-x3)) / den
            
            if 0 <= t <= 1 and 0 <= u <= 1:
                ix = x1 + t * (x2 - x1)
                iy = y1 + t * (y2 - y1)
                dist = math.hypot(ix - ox, iy - oy)
                if dist < min_dist:
                    min_dist = dist
        return min_dist

    def raycast_cone(self, ox, oy, angle_deg, max_dist=200.0, cone_width=5):
        min_dist = max_dist
        for a in [angle_deg - cone_width/2, angle_deg, angle_deg + cone_width/2]:
            d = self.raycast(ox, oy, a, max_dist)
            if d < min_dist:
                min_dist = d
        return min_dist

    def check_physical_collision(self):
        cx, cy = self.pose['x'], self.pose['y']
        for (x3, y3, x4, y4) in self.line_obstacles:
            px, py = x4 - x3, y4 - y3
            norm = px*px + py*py
            u = ((cx - x3) * px + (cy - y3) * py) / float(norm) if norm > 0 else -1
            if u > 1: u = 1
            elif u < 0: u = 0
            ix, iy = x3 + u * px, y3 + u * py
            if math.hypot(ix - cx, iy - cy) < 12.0:
                return True
        return False

    def update_gui_vars(self):
        self.lbl_pose.config(text=f"X: {self.pose['x']:.1f}, Y: {self.pose['y']:.1f}, Yaw: {self.pose['theta']:.1f}")
        self.lbl_enc.config(text=f"Enc L: {self.enc_l:.1f} | R: {self.enc_r:.1f}")
        
        def color(val): return "red" if val < 25.0 else "black"
        self.lbl_sf.config(text=f"Front: {self.sonar['f']:.1f}", fg=color(self.sonar['f']))
        self.lbl_sl.config(text=f"Left: {self.sonar['l']:.1f}", fg=color(self.sonar['l']))
        self.lbl_sr.config(text=f"Right: {self.sonar['r']:.1f}", fg=color(self.sonar['r']))
        
        self.update_gui_map()

    def update_gui_map(self):
        self.canvas.delete("all")
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw <= 1 or ch <= 1: return
        
        zoom = self.scale_zoom.get()
        cx, cy = cw/2, ch/2
        offset_x = cx - self.pose['x'] * zoom
        offset_y = cy - self.pose['y'] * zoom
        
        grid_step = 50 * zoom
        start_x = offset_x % grid_step
        start_y = offset_y % grid_step
        
        for x in np.arange(start_x, cw, grid_step):
            self.canvas.create_line(x, 0, x, ch, fill="#D5D8DC", dash=(2,2))
        for y in np.arange(start_y, ch, grid_step):
            self.canvas.create_line(0, y, cw, y, fill="#D5D8DC", dash=(2,2))
            
        for (x1, y1, x2, y2) in self.line_obstacles:
            px1, py1 = x1*zoom + offset_x, y1*zoom + offset_y
            px2, py2 = x2*zoom + offset_x, y2*zoom + offset_y
            self.canvas.create_line(px1, py1, px2, py2, fill="#E74C3C", width=4, capstyle=tk.ROUND)
            
        rad_f = math.radians(self.pose['theta'])
        rad_l = math.radians(self.pose['theta'] - 90)
        rad_r = math.radians(self.pose['theta'] + 90)
        rx, ry = self.pose['x']*zoom + offset_x, self.pose['y']*zoom + offset_y
        
        for rad, dist in [(rad_f, self.sonar['f']), (rad_l, self.sonar['l']), (rad_r, self.sonar['r'])]:
            if dist < 200.0:
                tx = rx + dist * math.cos(rad) * zoom
                ty = ry + dist * math.sin(rad) * zoom
                self.canvas.create_line(rx, ry, tx, ty, fill="#F39C12", dash=(4,2))
                
        L = 20 * zoom 
        rad = math.radians(self.pose['theta'])
        pts = [
            (rx + L*math.cos(rad), ry + L*math.sin(rad)),
            (rx + (L-5*zoom)*math.cos(rad + 2.5), ry + (L-5*zoom)*math.sin(rad + 2.5)),
            (rx - (L-10*zoom)*math.cos(rad) + 10*zoom*math.cos(rad + 1.57), ry - (L-10*zoom)*math.sin(rad) + 10*zoom*math.sin(rad + 1.57)),
            (rx - (L-10*zoom)*math.cos(rad) - 10*zoom*math.cos(rad + 1.57), ry - (L-10*zoom)*math.sin(rad) - 10*zoom*math.sin(rad + 1.57)),
            (rx + (L-5*zoom)*math.cos(rad - 2.5), ry + (L-5*zoom)*math.sin(rad - 2.5))
        ]
        self.canvas.create_polygon(pts, fill="#3498DB", outline="#2C3E50", width=2)

if __name__ == "__main__":
    mjpeg_thread = threading.Thread(target=start_mjpeg_server, daemon=True)
    mjpeg_thread.start()
    
    root = tk.Tk()
    app = SimulatorV2App(root)
    root.mainloop()
