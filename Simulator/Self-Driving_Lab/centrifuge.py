import sys
import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import socket

class CentrifugeSimTk:
    def __init__(self, root):
        self.root = root
        self.root.title("🌀 Centrifuge Simulator")
        self.root.geometry("600x480")
        
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.initUI()
        
        # 소켓 서버 스레드 가동 (Port: 50054)
        threading.Thread(target=self.start_server, daemon=True).start()
        
    def initUI(self):
        title_frame = ttk.Frame(self.root, padding=10)
        title_frame.pack(fill=tk.X)
        ttk.Label(title_frame, text="🌀 Centrifuge Simulator", font=("Arial", 14, "bold")).pack(side=tk.LEFT)
        
        middle_frame = ttk.Frame(self.root, padding=10)
        middle_frame.pack(fill=tk.BOTH, expand=True)
        
        left_frame = ttk.LabelFrame(middle_frame, text=" [Rotor Telemetry] ", padding=10)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        self.rpm_label = ttk.Label(left_frame, text="Current: 0 RPM\nTarget: 0 RPM", font=("Consolas", 12, "bold"))
        self.rpm_label.pack(pady=20)
        
        self.rpm_progress = ttk.Progressbar(left_frame, orient="vertical", mode="determinate", length=150)
        self.rpm_progress.pack(pady=10)
        
        right_frame = ttk.LabelFrame(middle_frame, text=" [Chamber Status] ", padding=10)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)
        
        self.door_status = ttk.Label(right_frame, text="Door Interlock: UNLOCKED 🔓", font=("Arial", 10))
        self.door_status.pack(anchor=tk.W, pady=2)
        self.temp_status = ttk.Label(right_frame, text="Chamber Temp: 22.1 °C")
        self.temp_status.pack(anchor=tk.W, pady=2)
        
        self.log_box = scrolledtext.ScrolledText(right_frame, height=10, width=30, font=("Consolas", 9))
        self.log_box.pack(fill=tk.BOTH, expand=True, pady=10)
        self.log_box.insert(tk.END, "[System] Server listening on Port 50054...\n")
        
        self.current_rpm = 0
        self.target_rpm = 0
        self.state = "STOPPED"

    def log(self, text):
        self.log_box.insert(tk.END, text + "\n")
        self.log_box.see(tk.END)

    def start_spin(self, target_rpm, conn):
        self.state = "ACCELERATING"
        self.target_rpm = target_rpm
        self.door_status.configure(text="Door Interlock: LOCKED 🔒", foreground="red")
        self.log(f"[Network] Rx Spin Request: {target_rpm} RPM")
        self.physics_loop(conn)
            
    def physics_loop(self, conn):
        if self.state == "ACCELERATING":
            if self.current_rpm < self.target_rpm:
                self.current_rpm += 500
                self.temp_status.configure(text="Chamber Temp: 12.4 °C")
                self.update_telemetry()
                self.root.after(50, lambda: self.physics_loop(conn))
            else:
                self.current_rpm = self.target_rpm
                self.state = "RUNNING"
                self.log("[System] Target reached. Spinning...")
                self.root.after(1000, lambda: self.trigger_deceleration(conn))
                
        elif self.state == "DECELERATING":
            if self.current_rpm > 0:
                self.current_rpm -= 500
                self.update_telemetry()
                self.root.after(50, lambda: self.physics_loop(conn))
            else:
                self.current_rpm = 0
                self.state = "STOPPED"
                self.door_status.configure(text="Door Interlock: UNLOCKED 🔓", foreground="black")
                self.temp_status.configure(text="Chamber Temp: 21.8 °C")
                self.log("[System] Spin done. Door unlocked.")
                self.update_telemetry()
                
                # 가동 완료 신호를 오케스트레이터로 반환
                conn.sendall(b"SPIN_SUCCESS")
                conn.close()

    def trigger_deceleration(self, conn):
        self.state = "DECELERATING"
        self.target_rpm = 0
        self.physics_loop(conn)

    def update_telemetry(self):
        self.rpm_label.configure(text=f"Current: {self.current_rpm} RPM\nTarget: {self.target_rpm} RPM")
        self.rpm_progress['value'] = int((self.current_rpm / 4000) * 100)
        self.root.update()

    def start_server(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(('127.0.0.1', 50054))
        server.listen(5)
        while True:
            conn, addr = server.accept()
            data = conn.recv(1024).decode('utf-8')
            if data.startswith("SPIN:"):
                rpm = int(data.split(":")[1])
                self.root.after(0, self.start_spin, rpm, conn)

if __name__ == "__main__":
    root = tk.Tk()
    app = CentrifugeSimTk(root)
    root.mainloop()