import sys
import random
import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import socket
import json

class PlateReaderSimTk:
    def __init__(self, root):
        self.root = root
        self.root.title("🔬 Microplate Reader Simulator")
        self.root.geometry("800x550")
        
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.initUI()
        
        # 소켓 서버 스레드 가동 (Port: 50053)
        threading.Thread(target=self.start_server, daemon=True).start()
        
    def initUI(self):
        title_frame = ttk.Frame(self.root, padding=10)
        title_frame.pack(fill=tk.X)
        ttk.Label(title_frame, text="🔬 Microplate Reader Simulator", font=("Arial", 14, "bold")).pack(side=tk.LEFT)
        self.status_val = ttk.Label(title_frame, text="Status: IDLE", font=("Arial", 11, "bold"))
        self.status_val.pack(side=tk.RIGHT, padx=20)
        
        paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        left_frame = ttk.LabelFrame(paned, text=" [Reader Info & Stream] ", padding=10)
        paned.add(left_frame, weight=2)
        
        self.data_box = scrolledtext.ScrolledText(left_frame, height=15, width=35, font=("Consolas", 9))
        self.data_box.pack(fill=tk.BOTH, expand=True, pady=5)
        self.data_box.insert(tk.END, "[System] Server listening on Port 50053...\n")
        
        right_frame = ttk.LabelFrame(paned, text=" [Measurement Heatmap] ", padding=10)
        paned.add(right_frame, weight=3)
        
        grid_frame = ttk.Frame(right_frame)
        grid_frame.pack(anchor=tk.CENTER, pady=20)
        
        self.wells = {}
        for col in range(1, 13):
            ttk.Label(grid_frame, text=str(col), width=4, anchor="center").grid(row=0, column=col)
            
        rows = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
        for r_idx, row in enumerate(rows):
            ttk.Label(grid_frame, text=row, width=3, anchor="center").grid(row=r_idx + 1, column=0)
            for col in range(1, 13):
                well = tk.Label(grid_frame, width=4, height=1, bg="#F5F5F5", relief="groove")
                well.grid(row=r_idx + 1, column=col, padx=1, pady=1)
                self.wells[(row, col)] = well

    def remote_scan(self, current_rpm, conn):
        self.status_val.configure(text="Status: SCANNING...", foreground="orange")
        self.data_box.insert(tk.END, f"[Network] Received Scan Request (Target RPM Source: {current_rpm})\n")
        
        # 물리 모델 기반 흡광도 계산
        base_efficiency = current_rpm / 4000.0
        max_val = 0.0
        generated_data = []
        
        rows_list = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
        for row_char in rows_list:
            row_values = []
            for col in range(1, 13):
                val = round(base_efficiency * 1.1 + random.uniform(-0.04, 0.04), 3)
                if val < 0: val = 0.0
                row_values.append(val)
                if val > max_val: max_val = val
                
                intensity = int((val / 1.2) * 10)
                shades = ["#F7FBFF", "#DEEBF7", "#C6DBEF", "#9ECAE1", "#6BAED6", "#4292C6", "#2171B5", "#08519C", "#08306B", "#051A3B", "#020B1C"]
                self.wells[(row_char, col)].configure(bg=shades[min(max(intensity, 0), 10)])
            generated_data.append(row_values)
            self.data_box.insert(tk.END, f"Row {row_char}: {row_values}\n")
            self.root.update()
            
        self.status_val.configure(text="Status: COMPLETE", foreground="green")
        self.data_box.insert(tk.END, f"Scan Done. Max Absorbance: {max_val}\n\n")
        
        # 오케스트레이터에게 실제 측정된 최대 흡광도 값을 전송
        conn.sendall(str(max_val).encode('utf-8'))
        conn.close()

    def start_server(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(('127.0.0.1', 50053))
        server.listen(5)
        while True:
            conn, addr = server.accept()
            data = conn.recv(1024).decode('utf-8')
            if data.startswith("SCAN:"):
                rpm = int(data.split(":")[1])
                # GUI 관련 스레드 안전 조치
                self.root.after(0, self.remote_scan, rpm, conn)

if __name__ == "__main__":
    root = tk.Tk()
    app = PlateReaderSimTk(root)
    root.mainloop()