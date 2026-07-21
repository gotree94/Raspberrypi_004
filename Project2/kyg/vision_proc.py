import cv2
import time
import torch
import torchvision.transforms as transforms
import os

def vision_worker(cam_url, model_path, output_queue, cmd_rx_q=None):
    print("[Vision] Process Started.")
    
    # Load Model
    device = torch.device('cpu')
    model = None
    try:
        model = torch.jit.load(model_path, map_location=device)
        model.eval()
        print(f"[Vision] AI Model Loaded: {os.path.basename(model_path)}")
    except Exception as e:
        print(f"[Vision] Failed to load model. Fallback to CV. {e}")
        
    # transform is no longer used, preprocessing is done via NumPy like ch8_1_test_model.py
    
    current_source = cam_url
    cap = cv2.VideoCapture(current_source)
    is_video_file = not current_source.startswith("http")
    
    while True:
        try:
            # 1. Check for commands
            if cmd_rx_q is not None and not cmd_rx_q.empty():
                cmd = cmd_rx_q.get_nowait()
                if cmd.get('cmd') == 'load_video':
                    new_path = cmd.get('path')
                    print(f"[Vision] Changing Video Source to: {new_path}")
                    cap.release()
                    current_source = new_path
                    cap = cv2.VideoCapture(current_source)
                    is_video_file = not current_source.startswith("http")

            ret, frame = cap.read()
            if not ret:
                if is_video_file:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                else:
                    print("[Vision] Connection Lost. Retrying...")
                    time.sleep(1)
                    cap = cv2.VideoCapture(current_source)
                    continue

            frame = cv2.resize(frame, (320, 240))
            angle = 90.0 # Default Straight
            
            if model is not None:
                try:
                    import numpy as np
                    
                    # 1. Model Inference Preprocessing (Matched exactly with training)
                    h, w, c = frame.shape
                    cropped = frame[h//2:, :, :] if h > 100 else frame
                    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                    
                    gray = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)
                    gray_eq = clahe.apply(gray)
                    inv = 255 - gray_eq
                    inv_eq = clahe.apply(inv)
                    blurred = cv2.GaussianBlur(inv_eq, (3, 3), 0)
                    resized = cv2.resize(blurred, (200, 66))
                    img = resized.astype(np.float32) / 255.0
                    
                    input_tensor = torch.tensor(np.stack([img, img, img], axis=0)).unsqueeze(0).to(device)
                    
                    with torch.no_grad():
                        output = model(input_tensor)
                        angle = output.item()
                        
                    # 2. GUI Visualization Preprocessing (Full Frame)
                    full_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    full_gray_eq = clahe.apply(full_gray)
                    full_inv = 255 - full_gray_eq
                    full_inv_eq = clahe.apply(full_inv)
                    full_blurred = cv2.GaussianBlur(full_inv_eq, (3, 3), 0)
                    proc_img = cv2.cvtColor(full_blurred, cv2.COLOR_GRAY2BGR)
                    
                except Exception as e:
                    print(f"[Vision] AI Inference Error: {e}")
                    proc_img = frame.copy()
            else:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                blur = cv2.GaussianBlur(gray, (5, 5), 0)
                edges = cv2.Canny(blur, 50, 150)
                
                M = cv2.moments(edges)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    angle = (cx - 160) * 0.3
                proc_img = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
                angle = 90.0 + angle 
                
            # 조향선 렌더링 (Red Line) - 화면 내에서 AI가 지시하는 조향 방향을 직관적으로 확인
            err = angle - 90.0
            target_x = 160 - int(err * 3) # 각도가 90 이상이면 좌회전(X감소), 90 미만이면 우회전(X증가)
            
            # 원본 이미지(좌측)에 빨간 선 표시
            cv2.line(frame, (160, 240), (target_x, 120), (0, 0, 255), 4)
            # 처리 이미지(우측)에도 동일하게 표시 및 각도 텍스트 오버레이
            cv2.line(proc_img, (160, 240), (target_x, 120), (0, 0, 255), 4)
            cv2.putText(proc_img, f"AI Angle: {angle:.1f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 2)
            cv2.putText(proc_img, f"Steer Cmd: {'LEFT(a)' if err>15 else 'RIGHT(d)' if err<-15 else 'STRAIGHT(w)'}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)

            if output_queue.full():
                output_queue.get() 
            output_queue.put((angle, frame, proc_img))
            
            if is_video_file:
                time.sleep(0.03)

        except Exception as e:
            print(f"[Vision] Exception: {e}")
            time.sleep(1)
