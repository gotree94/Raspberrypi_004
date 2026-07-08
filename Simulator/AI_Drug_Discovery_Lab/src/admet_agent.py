import tkinter as tk
from tkinter import scrolledtext
import threading
import socket
import json
import random
import time
import sys
import argparse
import re
import math

MOTOR_NAMES = ["Absorption", "Distribution", "Metabolism", "Excretion", "Toxicity"]
MOTOR_COLORS = {"IDLE": "gray", "RUNNING": "green", "COMPLETED": "blue", "FAILED": "red"}
SENSOR_NAMES = ["QED", "LogP", "Solubility", "BBB Score", "hERG Risk", "LD50"]
SENSOR_RANGES = {"QED": "0-1", "LogP": "-2-10", "Solubility": "-10-2", "BBB Score": "0-1", "hERG Risk": "0-100%", "LD50": "1-5000"}
SENSOR_UNITS = {"QED": "", "LogP": "", "Solubility": "", "BBB Score": "", "hERG Risk": "%", "LD50": "mg/kg"}


class ADMETAgent:
    def __init__(self):
        self.reset()

    def reset(self):
        self.motors = {n: "IDLE" for n in MOTOR_NAMES}
        self.sensors = {n: 0.0 for n in SENSOR_NAMES}
        self.last_smiles = ""
        self.status = "ready"

    def count_hbd(self, smiles):
        return len(re.findall(r'[NnOo]', smiles))

    def count_hba(self, smiles):
        return len(re.findall(r'[NnOoFf]', smiles))

    def predict_admet(self, smiles):
        length = len(smiles)
        qed = round(random.uniform(0.3, 0.9), 3)
        logp = round(random.uniform(0.5, 5.0), 2)
        if length > 50:
            qed = round(random.uniform(0.2, 0.5), 3)
            logp = round(random.uniform(3.0, 5.0), 2)
        elif length < 10:
            qed = round(random.uniform(0.5, 0.9), 3)
            logp = round(random.uniform(0.5, 3.0), 2)
        solubility = round(random.uniform(-6.0, 0.0), 2)
        bbb = round(random.uniform(0, 1.0), 3)
        herg = round(random.uniform(0, 100), 1)
        ld50 = round(random.uniform(100, 3000), 1)
        hbd = self.count_hbd(smiles)
        hba = self.count_hba(smiles)
        lipinski_score = (1 if length <= 50 else 0) + (1 if logp <= 5 else 0) + (1 if hbd <= 5 else 0) + (1 if hba <= 10 else 0)
        self.sensors["QED"] = qed
        self.sensors["LogP"] = logp
        self.sensors["Solubility"] = solubility
        self.sensors["BBB Score"] = bbb
        self.sensors["hERG Risk"] = herg
        self.sensors["LD50"] = ld50
        self.last_smiles = smiles
        self.status = "completed"
        return {"QED": qed, "LogP": logp, "Solubility": solubility, "BBB": bbb, "hERG": herg, "LD50": ld50, "Lipinski": lipinski_score >= 3, "Lipinski_Score": lipinski_score}

    def filter_drug(self, smiles):
        length = len(smiles)
        logp = round(random.uniform(0.5, 5.0), 2)
        hbd = self.count_hbd(smiles)
        hba = self.count_hba(smiles)
        rules = {"MW <= 500": length <= 50, "LogP <= 5": logp <= 5, "HBD <= 5": hbd <= 5, "HBA <= 10": hba <= 10}
        passed = sum(rules.values())
        return {"PASS": passed >= 3, "Rules": rules, "Score": passed}


class Application:
    def __init__(self, root, port):
        self.root = root
        self.port = port
        self.agent = ADMETAgent()
        self.busy = False
        root.title(f"ADMET Prediction Agent (Port {port})")
        root.protocol("WM_DELETE_WINDOW", self.on_close)
        root.geometry("800x600+100+100")
        self.build_gui()

    def build_gui(self):
        main = tk.Frame(self.root)
        main.pack(fill=tk.BOTH, expand=True)
        top = tk.Frame(main)
        top.pack(fill=tk.BOTH, expand=True)

        left = tk.LabelFrame(top, text="Computational Motors", padx=5, pady=5)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=3, pady=3)
        self.motor_inds = {}
        for name in MOTOR_NAMES:
            f = tk.Frame(left)
            f.pack(fill=tk.X, pady=2)
            c = tk.Canvas(f, width=20, height=20, highlightthickness=0)
            c.pack(side=tk.LEFT, padx=3)
            ind = c.create_oval(2, 2, 18, 18, fill="gray", outline="black")
            self.motor_inds[name] = (c, ind)
            tk.Label(f, text=name, width=14, anchor="w").pack(side=tk.LEFT)

        self.radar = tk.Canvas(top, width=280, height=280, bg="white", highlightthickness=1, highlightbackground="#ccc")
        self.radar.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=3, pady=3)
        self.radar.bind("<Configure>", lambda e: self.draw_radar())

        right = tk.LabelFrame(top, text="AI Sensors", padx=5, pady=5)
        right.pack(side=tk.RIGHT, fill=tk.Y, padx=3, pady=3)
        self.sensor_vals = {}
        for name in SENSOR_NAMES:
            f = tk.Frame(right)
            f.pack(fill=tk.X, pady=2)
            tk.Label(f, text=f"{name} [{SENSOR_RANGES[name]}]", width=14, anchor="w").pack(side=tk.LEFT)
            v = tk.Label(f, text="---", width=10, anchor="e", relief=tk.SUNKEN, bd=1)
            v.pack(side=tk.RIGHT, padx=3)
            self.sensor_vals[name] = v

        bot = tk.Frame(main)
        bot.pack(fill=tk.BOTH, padx=3, pady=3)
        tk.Label(bot, text="Command Log", anchor="w").pack(fill=tk.X)
        self.log = scrolledtext.ScrolledText(bot, height=8, state=tk.DISABLED)
        self.log.pack(fill=tk.BOTH, expand=True)

        self.logmsg("ADMET Prediction Agent started on port {}".format(self.port))

    def logmsg(self, msg):
        self.log.config(state=tk.NORMAL)
        self.log.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        self.log.see(tk.END)
        self.log.config(state=tk.DISABLED)

    def set_motor(self, name, state):
        c, ind = self.motor_inds[name]
        c.itemconfig(ind, fill=MOTOR_COLORS[state])
        self.agent.motors[name] = state

    def set_sensor(self, name, value):
        if isinstance(value, float):
            if name == "hERG Risk":
                d = f"{value:.1f}"
            elif name == "LD50":
                d = f"{value:.1f}"
            else:
                d = f"{value:.2f}"
        else:
            d = str(value)
        self.sensor_vals[name].config(text=d)
        self.agent.sensors[name] = value

    def draw_radar(self):
        self.radar.delete("all")
        w = self.radar.winfo_width()
        h = self.radar.winfo_height()
        if w < 10 or h < 10:
            return
        cx, cy = w // 2, h // 2
        r = min(w, h) * 0.35
        angles = [-math.pi / 2 + 2 * math.pi * i / 5 for i in range(5)]
        for i, name in enumerate(MOTOR_NAMES):
            ax = cx + r * math.cos(angles[i])
            ay = cy + r * math.sin(angles[i])
            self.radar.create_line(cx, cy, ax, ay, fill="#ddd")
            tx = cx + (r + 22) * math.cos(angles[i])
            ty = cy + (r + 22) * math.sin(angles[i])
            self.radar.create_text(tx, ty, text=name[:4], font=("TkDefaultFont", 8))
        for ratio in [0.25, 0.5, 0.75, 1.0]:
            pts = []
            for a in angles:
                pts.append(cx + r * ratio * math.cos(a))
                pts.append(cy + r * ratio * math.sin(a))
            self.radar.create_polygon(pts, outline="#ddd", fill="", tags="g")
        motor_val = {"IDLE": 0.0, "RUNNING": 0.5, "COMPLETED": 1.0, "FAILED": 0.2}
        pts = []
        for i, name in enumerate(MOTOR_NAMES):
            v = motor_val.get(self.agent.motors[name], 0.0)
            pts.append(cx + r * v * math.cos(angles[i]))
            pts.append(cy + r * v * math.sin(angles[i]))
        if len(pts) >= 10:
            self.radar.create_polygon(pts, outline="#44f", fill="#44f", stipple="gray25", width=2)

    def run_prediction(self, smiles):
        self.busy = True
        self.logmsg(f"Starting prediction: {smiles}")
        for name in MOTOR_NAMES:
            if not self.busy:
                break
            self.root.after(0, lambda n=name: self.set_motor(n, "RUNNING"))
            self.root.after(0, self.draw_radar)
            duration = random.uniform(1, 3)
            time.sleep(duration)
            if not self.busy:
                break
            state = "COMPLETED" if random.random() > 0.1 else "FAILED"
            self.root.after(0, lambda n=name, s=state: self.set_motor(n, s))
            self.root.after(0, self.draw_radar)
            self.logmsg(f"  {name}: {state} ({duration:.1f}s)")
        if self.busy:
            result = self.agent.predict_admet(smiles)
            self.root.after(0, lambda r=result: self.apply_results(r))
            lip = "PASS" if result["Lipinski"] else "FAIL"
            self.logmsg(f"Prediction done. Lipinski: {lip} ({result['Lipinski_Score']}/4)")
        self.busy = False

    def apply_results(self, r):
        self.set_sensor("QED", r["QED"])
        self.set_sensor("LogP", r["LogP"])
        self.set_sensor("Solubility", r["Solubility"])
        self.set_sensor("BBB Score", r["BBB"])
        self.set_sensor("hERG Risk", r["hERG"])
        self.set_sensor("LD50", r["LD50"])
        self.draw_radar()

    def handle_predict(self, smiles):
        if self.busy:
            return json.dumps({"error": "busy"})
        threading.Thread(target=self.run_prediction, args=(smiles,), daemon=True).start()
        return json.dumps({"status": "started", "smiles": smiles})

    def handle_filter(self, smiles):
        result = self.agent.filter_drug(smiles)
        return json.dumps({"smiles": smiles, "result": "PASS" if result["PASS"] else "FAIL", "details": result})

    def handle_status(self):
        return json.dumps({"status": self.agent.status, "motors": self.agent.motors, "sensors": self.agent.sensors, "last_smiles": self.agent.last_smiles})

    def handle_reset(self):
        self.busy = False
        self.agent.reset()
        for name in MOTOR_NAMES:
            self.root.after(0, lambda n=name: self.set_motor(n, "IDLE"))
        for name in SENSOR_NAMES:
            self.root.after(0, lambda n=name: self.set_sensor(n, 0.0))
        self.root.after(0, self.draw_radar)
        self.logmsg("Agent reset")
        return json.dumps({"status": "reset"})

    def on_close(self):
        self.busy = False
        self.running = False
        self.root.destroy()

    def server_loop(self):
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(("0.0.0.0", self.port))
        srv.listen(5)
        srv.settimeout(1.0)
        self.logmsg(f"TCP server listening on port {self.port}")
        while self.running:
            try:
                conn, addr = srv.accept()
                self.logmsg(f"Connection from {addr}")
                threading.Thread(target=self.serve_client, args=(conn, addr), daemon=True).start()
            except socket.timeout:
                continue
            except OSError:
                break
        srv.close()

    def serve_client(self, conn, addr):
        try:
            data = conn.recv(8192).decode().strip()
            if not data:
                return
            self.logmsg(f"RX: {data}")
            if data.startswith("PREDICT:"):
                resp = self.handle_predict(data[8:].strip())
            elif data.startswith("FILTER:"):
                resp = self.handle_filter(data[7:].strip())
            elif data == "STATUS":
                resp = self.handle_status()
            elif data == "RESET":
                resp = self.handle_reset()
            else:
                resp = json.dumps({"error": "unknown command"})
            conn.send(resp.encode())
        except Exception as e:
            try:
                conn.send(json.dumps({"error": str(e)}).encode())
            except:
                pass
        finally:
            conn.close()

    def start(self):
        self.running = True
        threading.Thread(target=self.server_loop, daemon=True).start()
        self.root.mainloop()


def main():
    parser = argparse.ArgumentParser(description="ADMET Prediction Agent")
    parser.add_argument("--port", type=int, default=50063, help="TCP port (default: 50063)")
    args = parser.parse_args()
    root = tk.Tk()
    app = Application(root, args.port)
    app.start()


if __name__ == "__main__":
    main()
