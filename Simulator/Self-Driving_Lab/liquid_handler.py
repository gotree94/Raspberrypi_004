import sys
import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import socket

class LiquidHandlerSimTk:
    def __init__(self, root):
        self.root = root
        self.root.title("💧 Liquid Handler Simulator")
        self.root.geometry("550x450")
        
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.initUI()
        
        # 소켓 서버 스레드 가동 (Port: 50051)
        threading.Thread(target=self.start_server, daemon=True).start()
        
    def initUI(self):
        title_frame = ttk.Frame(self.root, padding=10)
        title_frame.pack(fill=tk.X)
        ttk.Label(title_frame, text="💧 Liquid Handler Simulator", font=("Arial", 14, "bold")).pack(side=tk.LEFT)
        
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 피펫 팁/헤드 상태 시각화
        pipette_frame = ttk.LabelFrame(main_frame, text=" [Pipette Head Status] ", padding=10)
        pipette_frame.pack(fill=tk.X, pady=5)
        
        self.pipette_status = ttk.Label(pipette_frame, text="Position: HOME | Volume: 0 uL", font=("Consolas", 11, "bold"))
        self.pipette_status.pack(pady=10)
        
        # 분주 진행 바
        self.progress = ttk.Progressbar(pipette_frame, orient="horizontal", mode="determinate", length=300)
        self.progress.pack(pady=5)
        
        # 로그창
        self.log_box = scrolledtext.ScrolledText(main_frame, height=12, font=("Consolas", 9))
        self.log_box.pack(fill=tk.BOTH, expand=True, pady=10)
        self.log_box.insert(tk.END, "[System] Server listening on Port 50051...\n")

    def log(self, text):
        self.log_box.insert(tk.END, text + "\n")
        self.log_box.see(tk.END)

    def remote_dispense(self, volume, conn):
        self.log(f"[Network] Rx Dispense Request: {volume} uL")
        self.pipette_status.configure(text=f"Position: DISPENSING... | Volume: {volume} uL", foreground="blue")
        
        # 간단한 분주 애니메이션 (1초 동안 진행 바 채우기)
        for i in range(1, 101, 10):
            self.progress['value'] = i
            self.root.update()
            self.root.after(50)
            
        self.progress['value'] = 0
        self.pipette_status.configure(text="Position: HOME | Volume: 0 uL", foreground="black")
        self.log(f"[System] Successfully dispensed {volume} uL to plate.")
        self.root.update()
        
        # 오케스트레이터에 완료 신호 전송
        conn.sendall(b"DISPENSE_SUCCESS")
        conn.close()

    def start_server(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(('127.0.0.1', 50051))
        server.listen(5)
        while True:
            conn, addr = server.accept()
            data = conn.recv(1024).decode('utf-8')
            if data.startswith("DISPENSE:"):
                vol = int(data.split(":")[1])
                # GUI 스레드 안전하게 호출
                self.root.after(0, self.remote_dispense, vol, conn)

if __name__ == "__main__":
    root = tk.Tk()
    app = LiquidHandlerSimTk(root)
    root.mainloop()