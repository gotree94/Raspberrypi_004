import sys
import time
import json
import socket
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

class OrchestratorGui:
    def __init__(self, root):
        self.root = root
        self.root.title("🎛️ Lab Orchestrator (Closed-Loop)")
        self.root.geometry("700x550")
        
        self.style = ttk.Style()
        self.style.theme_use("clam")
        
        # 알고리즘 내부 제어 변수들
        self.target_absorbance = 0.8
        self.tolerance = 0.05
        self.current_rpm = 2000
        self.iteration = 1
        self.max_iterations = 5
        self.is_running = False
        
        self.initUI()
        self.load_plan_file()

    def initUI(self):
        # 상단 타이틀 및 상태 제어 바
        top_frame = ttk.Frame(self.root, padding=10)
        top_frame.pack(fill=tk.X)
        
        ttk.Label(top_frame, text="🎛️ Central Orchestrator", font=("Arial", 14, "bold")).pack(side=tk.LEFT)
        
        self.status_lbl = ttk.Label(top_frame, text="Status: READY", font=("Arial", 11, "bold"), foreground="blue")
        self.status_lbl.pack(side=tk.RIGHT, padx=10)
        
        # 메인 콘텐츠 영역 (실험 계획 정보 + 실시간 모니터링 로그)
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 1. 왼쪽: 불러온 계획 파일 정보 요약
        info_frame = ttk.LabelFrame(main_frame, text=" [ Loaded Experiment Plan ] ", padding=10, width=220)
        info_frame.pack_propagate(False)
        info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False)
        
        self.exp_name_lbl = ttk.Label(info_frame, text="Name: None", font=("Arial", 9, "bold"))
        self.exp_name_lbl.pack(anchor=tk.W, pady=5)
        
        self.target_lbl = ttk.Label(info_frame, text="Target: None")
        self.target_lbl.pack(anchor=tk.W, pady=2)
        
        ttk.Label(info_frame, text="\n[Sequence Order]").pack(anchor=tk.W)
        self.seq_listbox = tk.Listbox(info_frame, height=12, width=25, font=("Consolas", 9), bg="#F9F9F9")
        self.seq_listbox.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 2. 오른쪽: 실시간 중앙 모니터링 로그 출력창
        log_frame = ttk.LabelFrame(main_frame, text=" [ Closed-Loop Live Report ] ", padding=10)
        log_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)
        
        self.log_box = scrolledtext.ScrolledText(log_frame, font=("Consolas", 10))
        self.log_box.pack(fill=tk.BOTH, expand=True)
        self.log_box.insert(tk.END, "[System] Initialized. Click '실험 가동' to start.\n")
        
        # 하단 제어 버튼
        btn_frame = ttk.Frame(self.root, padding=10)
        btn_frame.pack(fill=tk.X)
        
        self.reload_btn = ttk.Button(btn_frame, text="⚙️ JSON 계획서 다시 불러오기", command=self.load_plan_file)
        self.reload_btn.pack(side=tk.LEFT, padx=5)
        
        self.start_btn = ttk.Button(btn_frame, text="▶️ 실험 시퀀스 가동 시작", command=self.start_orchestration_thread)
        self.start_btn.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=5)

    def log(self, text):
        self.log_box.insert(tk.END, text + "\n")
        self.log_box.see(tk.END)

    def load_plan_file(self):
        try:
            with open("experiment_plan.json", "r", encoding="utf-8") as f:
                self.plan = json.load(f)
                
            self.target_absorbance = self.plan['target']['value']
            self.tolerance = self.plan['target']['tolerance']
            
            self.exp_name_lbl.configure(text=f"Name: {self.plan['experiment_name']}")
            self.target_lbl.configure(text=f"Target Abs: {self.target_absorbance}\nTolerance: ±{self.tolerance}")
            
            self.seq_listbox.delete(0, tk.END)
            for step in self.plan['sequence']:
                self.seq_listbox.insert(tk.END, f"Step {step['step']}: {step['device']}")
                
            self.log("[System] experiment_plan.json 스크립트 파일을 성공적으로 로드했습니다.")
        except FileNotFoundError:
            messagebox.showerror("Error", "experiment_plan.json 파일을 찾을 수 없습니다!")
        except Exception as e:
            messagebox.showerror("Error", f"파일 파싱 에러: {str(e)}")

    def send_command(self, port, message):
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect(('127.0.0.1', port))
            client.sendall(message.encode('utf-8'))
            response = client.recv(1024).decode('utf-8')
            client.close()
            return response
        except ConnectionRefusedError:
            self.log(f"❌ 장비 연결 실패 (Port: {port}). 장비가 켜져 있는지 확인하세요.")
            return None

    def start_orchestration_thread(self):
        if self.is_running:
            return
        self.is_running = True
        self.start_btn.configure(state='disabled')
        self.reload_btn.configure(state='disabled')
        self.status_lbl.configure(text="Status: RUNNING", foreground="orange")
        
        threading.Thread(target=self.run_closed_loop, daemon=True).start()

    def run_closed_loop(self):
        self.iteration = 1
        self.current_rpm = 2000
        
        self.log("\n==================================================")
        self.log(f"🚀 자동 제어 오케스트레이션 가동 시작")
        self.log("==================================================")

        while self.iteration <= self.max_iterations:
            self.log(f"\n🔄 [CYCLE {self.iteration}] Closed-Loop 연동 루프 가동 (제어 인자: {self.current_rpm} RPM)")
            self.log("--------------------------------------------------")
            
            # Step 1: 호텔 연동
            self.log(" -> [Step 2] 플레이트 호텔 샘플 인출 명령 송신...")
            self.send_command(self.plan['sequence'][0]['port'], self.plan['sequence'][0]['cmd'])
            time.sleep(1.5)
            
            # Step 2: 리퀴드 핸들러 연동
            self.log(" -> [Step 2] 리퀴드 핸들러 시약 분주 명령 송신...")
            self.send_command(self.plan['sequence'][1]['port'], self.plan['sequence'][1]['cmd'])
            time.sleep(1.5)
            
            # Step 3: 원심분리기 연동
            self.log(f" -> [Step 3] 원심분리기 연동 시작 ({self.current_rpm} RPM)...")
            spin_cmd = f"SPIN:{self.current_rpm}"
            self.send_command(self.plan['sequence'][2]['port'], spin_cmd)
            
            # Step 4: 플레이트 리더기 연동
            self.log(" -> [Step 4] 마이크로플레이트 리더기 원격 스캔 구동...")
            scan_cmd = f"SCAN:{self.current_rpm}"
            resp = self.send_command(self.plan['sequence'][3]['port'], scan_cmd)
            
            if resp is None:
                self.log("🚨 장비 네트워크 응답 누락으로 강제 중단합니다.")
                break
                
            result_val = float(resp)
            
            error = result_val - self.target_absorbance
            self.log(f"\n📝 [Cycle {self.iteration} 분석 실시간 보고서]")
            self.log(f"  - 리더기 계측 피드백 수치: {result_val} (목표: {self.target_absorbance})")
            self.log(f"  - 오차 계산: {round(error, 3)}")

            if abs(error) <= self.tolerance:
                self.log("\n✅ [품질 만족] 최적 수렴 목표 오차 도달 완료!")
                self.log(f"🎉 최적화 산출 매개변수 결과: 원심분리기 = {self.current_rpm} RPM")
                break
            else:
                self.log("❌ [오차 과다] 다음 루프를 위해 통제 인자를 재계산합니다.")
                if error < 0:
                    adjustment = 500
                    self.log(f"  💡 피드백: 흡광도가 낮으므로 고형 축적을 위해 RPM을 +{adjustment} 조절합니다.")
                    self.current_rpm = min(self.current_rpm + adjustment, 4000)
                else:
                    adjustment = 400
                    self.log(f"  💡 피드백: 흡광도가 너무 높아 과포화 상태이므로 RPM을 -{adjustment} 조절합니다.")
                    self.current_rpm = max(self.current_rpm - adjustment, 1000)
            
            self.iteration += 1
            self.log("\n다음 최적화 사이클 준비 중 (4초 대기)...")
            time.sleep(4)
        else:
            self.log(f"\n🚨 [실패] 최대 시도 횟수({self.max_iterations}회) 초과로 루프를 중단합니다.")

        self.is_running = False
        self.start_btn.configure(state='normal')
        self.reload_btn.configure(state='normal')
        self.status_lbl.configure(text="Status: READY", foreground="blue")

if __name__ == "__main__":
    root = tk.Tk()
    app = OrchestratorGui(root)
    root.mainloop()