import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import serial.tools.list_ports
import random
import os
import json

CONFIG_FILE = "config.txt"

class RobotSimulatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ROBOT SYSTEM SIMULATOR (위치 조정 모드: 클릭 후 방향키 이동 / Enter로 저장)")
        self.root.geometry("1200x675")
        self.root.resizable(False, False)

        # 배경 이미지 로드
        try:
            self.bg_img = Image.open("sim.png")
            self.bg_img = self.bg_img.resize((1200, 675), Image.Resampling.LANCZOS)
            self.bg_photo = ImageTk.PhotoImage(self.bg_img)
            self.bg_label = tk.Label(root, image=self.bg_photo)
            self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)
        except Exception as e:
            messagebox.showerror("Error", f"배경 이미지(sim.png)를 로드할 수 없습니다.\n{e}")
            self.root.destroy()
            return

        # 기본 좌표 설정 (config.txt 파일이 없을 때 사용할 초기값)
        self.positions = {
            "port_combo": {"x": 90, "y": 65},
            "btn_refresh": {"x": 230, "y": 62},
            "baud_combo": {"x": 400, "y": 65},
            "btn_connect": {"x": 520, "y": 60},
            "lbl_status": {"x": 630, "y": 65},
            "lbl_speed_fl": {"x": 50, "y": 200},
            "lbl_speed_fr": {"x": 320, "y": 200},
            "lbl_speed_rl": {"x": 50, "y": 400},
            "lbl_speed_rr": {"x": 320, "y": 400},
            "lbl_servo_pan_in": {"x": 50, "y": 550},
            "lbl_servo_pan_deg": {"x": 50, "y": 570},
            "lbl_servo_tilt_in": {"x": 250, "y": 550},
            "lbl_servo_tilt_deg": {"x": 250, "y": 570},
            "lcd_line1": {"x": 500, "y": 160},
            "lcd_line2": {"x": 500, "y": 185},
            "led_2color": {"x": 500, "y": 260},
            "led_3color_1": {"x": 570, "y": 260},
            "led_3color_2": {"x": 640, "y": 260},
            "btn_laser": {"x": 500, "y": 340},
            "btn_buzzer": {"x": 500, "y": 375},
            "btn_relay": {"x": 500, "y": 410},
            "lbl_ultrasonic": {"x": 850, "y": 160},
            "lbl_lt_left": {"x": 800, "y": 280},
            "lbl_lt_center": {"x": 860, "y": 280},
            "lbl_lt_right": {"x": 920, "y": 280},
            "lbl_remote": {"x": 800, "y": 350},
            "remote_frame": {"x": 800, "y": 380},
            "lbl_env": {"x": 800, "y": 500},
            "lbl_fire": {"x": 500, "y": 470}
        }
        
        self.load_positions() # 파일에서 좌표 불러오기
        
        # 상태 변수 선언
        self.is_connected = False
        self.motor_speeds = {"FL": 680, "FR": 412, "RL": 915, "RR": 220}
        self.servo_inputs = {"Pan": 555, "Tilt": 777}
        self.ultrasonic_val = 112.4
        self.line_tracker = {"Left": True, "Center": True, "Right": False}
        self.remote_input = 4
        self.temperature = 24.5
        self.humidity = 58.2
        self.fire_detected = False
        self.laser_status = False
        self.buzzer_status = True
        self.relay_status = True

        self.widgets = {} # 생성된 위젯 추적용 디렉토리
        self.selected_widget_name = None

        # UI 생성 및 배치
        self.create_communication_widgets()
        self.create_simulation_widgets()
        
        # 키보드 이벤트 바인딩 (위치 조정용)
        self.root.bind("<KeyPress>", self.handle_key_press)
        self.root.bind("<Return>", self.save_positions)

        self.update_simulation_data()

    def load_positions(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    saved = json.load(f)
                    # 기존 딕셔너리에 덮어쓰기
                    for k, v in saved.items():
                        if k in self.positions:
                            self.positions[k] = v
            except Exception as e:
                print(f"설정 파일을 읽는 중 오류 발생: {e}")

    def save_positions(self, event=None):
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.positions, f, indent=4)
            self.root.title("ROBOT SYSTEM SIMULATOR (위치 저장 완료!)")
            # 1초 뒤 원래 타이틀로 복귀
            self.root.after(1000, lambda: self.root.title("ROBOT SYSTEM SIMULATOR (위치 조정 모드)"))
        except Exception as e:
            messagebox.showerror("Error", f"위치 저장 실패: {e}")

    # 위젯 등록 및 클릭 이벤트 바인딩 함수
    def register_widget(self, name, widget):
        self.widgets[name] = widget
        pos = self.positions[name]
        widget.place(x=pos["x"], y=pos["y"])
        
        # 마우스 클릭 시 선택되도록 설정
        widget.bind("<Button-1>", lambda event, n=name: self.select_widget(n))

    def select_widget(self, name):
        self.selected_widget_name = name
        # 선택된 위젯 강조를 위해 타이틀 표시
        self.root.title(f"선택됨: [{name}] - 방향키로 이동 / Enter로 저장")

    def handle_key_press(self, event):
        if not self.selected_widget_name:
            return

        name = self.selected_widget_name
        pos = self.positions[name]
        
        # Shift 누르면 10픽셀씩, 그냥 누르면 1픽셀씩 이동
        move_step = 10 if (event.state & 0x0001) else 1

        if event.keysym == "Up":
            pos["y"] -= move_step
        elif event.keysym == "Down":
            pos["y"] += move_step
        elif event.keysym == "Left":
            pos["x"] -= move_step
        elif event.keysym == "Right":
            pos["x"] += move_step
        else:
            return

        # 화면 보정 반영
        self.widgets[name].place(x=pos["x"], y=pos["y"])

    def create_communication_widgets(self):
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(self.root, textvariable=self.port_var, width=15)
        self.register_widget("port_combo", self.port_combo)
        self.refresh_ports()

        self.btn_refresh = tk.Button(self.root, text="Refresh Ports", bg="#1e90ff", fg="white", 
                                     command=self.refresh_ports, relief="flat", font=("Arial", 9, "bold"))
        self.register_widget("btn_refresh", self.btn_refresh)

        self.baud_var = tk.StringVar(value="115200")
        self.baud_combo = ttk.Combobox(self.root, textvariable=self.baud_var, width=10, values=["9600", "57600", "115200"])
        self.register_widget("baud_combo", self.baud_combo)

        self.btn_connect = tk.Button(self.root, text="CONNECT", bg="#4CAF50", fg="white", 
                                     command=self.toggle_connection, relief="flat", font=("Arial", 10, "bold"))
        self.register_widget("btn_connect", self.btn_connect)
        self.widgets["btn_connect"].place_configure(width=90, height=30)
        
        self.lbl_status = tk.Label(self.root, text="STATUS: DISCONNECTED", fg="red", bg="#2c3e50", font=("Arial", 10, "bold"))
        self.register_widget("lbl_status", self.lbl_status)

    def refresh_ports(self):
        ports = [port.device for port in serial.tools.list_ports.comports()]
        if not ports:
            ports = ["No Ports Found"]
        self.port_combo['values'] = ports
        self.port_combo.current(0)

    def toggle_connection(self):
        if not self.is_connected:
            selected_port = self.port_var.get()
            if selected_port == "No Ports Found":
                messagebox.showwarning("Warning", "연결할 시리얼 포트가 없습니다.")
                return
            self.is_connected = True
            self.btn_connect.config(text="DISCONNECT", bg="#d9534f")
            self.lbl_status.config(text=f"CONNECTED ({selected_port})", fg="#4CAF50")
        else:
            self.is_connected = False
            self.btn_connect.config(text="CONNECT", bg="#4CAF50")
            self.lbl_status.config(text="STATUS: DISCONNECTED", fg="red")

    def create_simulation_widgets(self):
        self.lbl_speed_fl = tk.Label(self.root, text="680", font=("Arial", 14, "bold"), fg="white", bg="#222")
        self.register_widget("lbl_speed_fl", self.lbl_speed_fl)
        
        self.lbl_speed_fr = tk.Label(self.root, text="412", font=("Arial", 14, "bold"), fg="white", bg="#222")
        self.register_widget("lbl_speed_fr", self.lbl_speed_fr)
        
        self.lbl_speed_rl = tk.Label(self.root, text="915", font=("Arial", 14, "bold"), fg="white", bg="#222")
        self.register_widget("lbl_speed_rl", self.lbl_speed_rl)
        
        self.lbl_speed_rr = tk.Label(self.root, text="220", font=("Arial", 14, "bold"), fg="white", bg="#222")
        self.register_widget("lbl_speed_rr", self.lbl_speed_rr)

        self.lbl_servo_pan_in = tk.Label(self.root, text="Input: 555", fg="white", bg="#222")
        self.register_widget("lbl_servo_pan_in", self.lbl_servo_pan_in)
        
        self.lbl_servo_pan_deg = tk.Label(self.root, text="Angle: 100°", fg="cyan", bg="#222", font=("Arial", 10, "bold"))
        self.register_widget("lbl_servo_pan_deg", self.lbl_servo_pan_deg)

        self.lbl_servo_tilt_in = tk.Label(self.root, text="Input: 777", fg="white", bg="#222")
        self.register_widget("lbl_servo_tilt_in", self.lbl_servo_tilt_in)
        
        self.lbl_servo_tilt_deg = tk.Label(self.root, text="Angle: 140°", fg="cyan", bg="#222", font=("Arial", 10, "bold"))
        self.register_widget("lbl_servo_tilt_deg", self.lbl_servo_tilt_deg)

        self.lcd_line1 = tk.Label(self.root, text="Temp:24.5C RH:58%", font=("Courier", 12, "bold"), fg="#00ff00", bg="#003300")
        self.register_widget("lcd_line1", self.lcd_line1)
        
        self.lcd_line2 = tk.Label(self.root, text="Dis:112cm FIRE:NO", font=("Courier", 12, "bold"), fg="#00ff00", bg="#003300")
        self.register_widget("lcd_line2", self.lcd_line2)

        self.led_2color = tk.Label(self.root, text="●", font=("Arial", 16), fg="green", bg="#222")
        self.register_widget("led_2color", self.led_2color)
        
        self.led_3color_1 = tk.Label(self.root, text="●", font=("Arial", 16), fg="blue", bg="#222")
        self.register_widget("led_3color_1", self.led_3color_1)
        
        self.led_3color_2 = tk.Label(self.root, text="●", font=("Arial", 16), fg="red", bg="#222")
        self.register_widget("led_3color_2", self.led_3color_2)

        self.btn_laser = tk.Button(self.root, text="Laser OFF", command=self.toggle_laser, bg="#555", fg="white")
        self.register_widget("btn_laser", self.btn_laser)
        self.widgets["btn_laser"].place_configure(width=80)
        
        self.btn_buzzer = tk.Button(self.root, text="Buzzer ON", command=self.toggle_buzzer, bg="#dfa000", fg="black")
        self.register_widget("btn_buzzer", self.btn_buzzer)
        self.widgets["btn_buzzer"].place_configure(width=80)
        
        self.btn_relay = tk.Button(self.root, text="Relay ON", command=self.toggle_relay, bg="green", fg="white")
        self.register_widget("btn_relay", self.btn_relay)
        self.widgets["btn_relay"].place_configure(width=80)

        self.lbl_ultrasonic = tk.Label(self.root, text="112.4 cm", font=("Arial", 18, "bold"), fg="white", bg="#222")
        self.register_widget("lbl_ultrasonic", self.lbl_ultrasonic)

        self.lbl_lt_left = tk.Label(self.root, text="L:[ON]", fg="green", bg="#222")
        self.register_widget("lbl_lt_left", self.lbl_lt_left)
        
        self.lbl_lt_center = tk.Label(self.root, text="C:[ON]", fg="green", bg="#222")
        self.register_widget("lbl_lt_center", self.lbl_lt_center)
        
        self.lbl_lt_right = tk.Label(self.root, text="R:[OFF]", fg="red", bg="#222")
        self.register_widget("lbl_lt_right", self.lbl_lt_right)

        self.lbl_remote = tk.Label(self.root, text="INPUT: 4", font=("Arial", 12, "bold"), fg="yellow", bg="#222")
        self.register_widget("lbl_remote", self.lbl_remote)
        
        self.remote_frame = tk.Frame(self.root, bg="#222")
        self.register_widget("remote_frame", self.remote_frame)
        for i in range(1, 10):
            btn = tk.Button(self.remote_frame, text=str(i), width=2, command=lambda num=i: self.press_remote(num))
            btn.grid(row=(i-1)//3, column=(i-1)%3, padx=2, pady=2)

        self.lbl_env = tk.Label(self.root, text="Temp: 24.5°C\nHumi: 58.2%", font=("Arial", 11), fg="white", bg="#222", justify="left")
        self.register_widget("lbl_env", self.lbl_env)

        self.lbl_fire = tk.Label(self.root, text="NO", font=("Arial", 12, "bold"), fg="green", bg="#222")
        self.register_widget("lbl_fire", self.lbl_fire)

    def toggle_laser(self):
        self.laser_status = not self.laser_status
        self.btn_laser.config(text="Laser ON" if self.laser_status else "Laser OFF", bg="red" if self.laser_status else "#555")

    def toggle_buzzer(self):
        self.buzzer_status = not self.buzzer_status
        self.btn_buzzer.config(text="Buzzer ON" if self.buzzer_status else "Buzzer OFF", bg="#dfa000" if self.buzzer_status else "#555")

    def toggle_relay(self):
        self.relay_status = not self.relay_status
        self.btn_relay.config(text="Relay ON" if self.relay_status else "Relay OFF", bg="green" if self.relay_status else "#555")

    def press_remote(self, num):
        self.remote_input = num
        self.lbl_remote.config(text=f"INPUT: {num}")

    def update_simulation_data(self):
        if self.is_connected:
            for key in self.motor_speeds:
                self.motor_speeds[key] = random.randint(0, 999)
            
            self.lbl_speed_fl.config(text=str(self.motor_speeds["FL"]))
            self.lbl_speed_fr.config(text=str(self.motor_speeds["FR"]))
            self.lbl_speed_rl.config(text=str(self.motor_speeds["RL"]))
            self.lbl_speed_rr.config(text=str(self.motor_speeds["RR"]))

            self.servo_inputs["Pan"] = random.randint(0, 999)
            self.servo_inputs["Tilt"] = random.randint(0, 999)
            pan_deg = int(self.servo_inputs["Pan"] * 180 / 999)
            tilt_deg = int(self.servo_inputs["Tilt"] * 180 / 999)
            
            self.lbl_servo_pan_in.config(text=f"Input: {self.servo_inputs['Pan']}")
            self.lbl_servo_pan_deg.config(text=f"Angle: {pan_deg}°")
            self.lbl_servo_tilt_in.config(text=f"Input: {self.servo_inputs['Tilt']}")
            self.lbl_servo_tilt_deg.config(text=f"Angle: {tilt_deg}°")

            self.ultrasonic_val = round(random.uniform(10.0, 400.0), 1)
            self.lbl_ultrasonic.config(text=f"{self.ultrasonic_val} cm")

            for key in self.line_tracker:
                self.line_tracker[key] = random.choice([True, False])
            
            left_txt = "ON" if self.line_tracker["Left"] else "OFF"
            center_txt = "ON" if self.line_tracker["Center"] else "OFF"
            right_txt = "ON" if self.line_tracker["Right"] else "OFF"

            self.lbl_lt_left.config(text=f"L:[{left_txt}]", fg="green" if self.line_tracker['Left'] else "red")
            self.lbl_lt_center.config(text=f"C:[{center_txt}]", fg="green" if self.line_tracker['Center'] else "red")
            self.lbl_lt_right.config(text=f"R:[{right_txt}]", fg="green" if self.line_tracker['Right'] else "red")

            self.temperature = round(random.uniform(20.0, 30.0), 1)
            self.humidity = round(random.uniform(40.0, 70.0), 1)
            self.lbl_env.config(text=f"Temp: {self.temperature}°C\nHumi: {self.humidity}%")

            self.fire_detected = random.choice([True, False])
            self.lbl_fire.config(text="!!FIRE!!" if self.fire_detected else "NO", fg="red" if self.fire_detected else "green")

            self.lcd_line1.config(text=f"Temp:{self.temperature}C RH:{self.humidity}%")
            self.lcd_line2.config(text=f"Dis:{int(self.ultrasonic_val)}cm FIRE:{'YES' if self.fire_detected else 'NO'}")

            self.led_2color.config(fg=random.choice(["green", "red"]))
            self.led_3color_1.config(fg=random.choice(["red", "green", "blue"]))

        self.root.after(1000, self.update_simulation_data)

if __name__ == "__main__":
    root = tk.Tk()
    app = RobotSimulatorApp(root)
    root.mainloop()