import sys
import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import socket

class PlateHotelSimTk:
    def __init__(self, root):
        self.root = root
        self.root.title("🏨 Plate Hotel Simulator")
        self.root.geometry("500x450")
        
        self.style = ttk.Style()
        self.style.theme_use("clam")
        
        self.initUI()
        
        # 소켓 서버 스레드 가동 (Port: 50052)
        threading.Thread(target=self.start_server, daemon=True).start()
        
    def initUI(self):
        title_frame = ttk.Frame(self.root, padding=10)
        title_frame.pack(fill=tk.X)
        ttk.Label(title_frame, text="🏨 Plate Hotel Simulator", font=("Arial", 14, "bold")).pack(side=tk.LEFT)
        
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 4개 슬롯 시각화
        self.slots = []
        slot_frame = ttk.Frame(main_frame)
        slot_frame.pack(fill=tk.X, pady=10)
        for i in range(4):
            lbl = tk.Label(slot_frame, text=f"Slot {i+1}\n[PLATE]", width=10, height=4, bg="#A8DADC", relief="ridge")
            lbl.pack(side=tk.LEFT, padx=10)
            self.slots.append(lbl)
            
        self.log_box = scrolledtext.ScrolledText(main_frame, height=10, font=("Consolas", 9))
        self.log_box.pack(fill=tk.BOTH, expand=True, pady=10)
        self.log_box.insert(tk.END, "[System] Server listening on Port 50052...\n")

    def log(self, text):
        self.log_box.insert(tk.END, text + "\n")
        self.log_box.see(tk.END)

    def eject_plate(self, slot_num):
        if 1 <= slot_num <= 4:
            self.log(f"[Network] Executing EjectPlate for Slot {slot_num}")
            self.slots[slot_num-1].configure(bg="#E63946", text=f"Slot {slot_num}\n[EMPTY]")
            self.root.update()

    def start_server(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(('127.0.0.1', 50052))
        server.listen(5)
        while True:
            conn, addr = server.accept()
            data = conn.recv(1024).decode('utf-8')
            if data:
                # 데이터 포맷: "EJECT:3"
                if data.startswith("EJECT:"):
                    slot = int(data.split(":")[1])
                    self.root.after(0, self.eject_plate, slot)
                    conn.sendall(b"SUCCESS")
            conn.close()

if __name__ == "__main__":
    root = tk.Tk()
    app = PlateHotelSimTk(root)
    root.mainloop()