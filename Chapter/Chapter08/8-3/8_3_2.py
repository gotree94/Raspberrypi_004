#import mycamera
import torch
import cv2
import numpy as np

MODEL_PATH = "model-20260714_231443\\lane_navigation_final.torchscript"

clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

def img_preprocess(image):
    h, w, c = image.shape
    image = image[:h//2, :, :]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray_eq = clahe.apply(gray)
    inv = 255 - gray_eq
    inv_eq = clahe.apply(inv)
    blurred = cv2.GaussianBlur(inv_eq, (3, 3), 0)
    resized = cv2.resize(blurred, (200, 66))
    img = resized.astype(np.float32) / 255.0
    img = np.stack([img, img, img], axis=2)
    return img

def main():
    #camera = mycamera.MyPiCamera(640, 480)
    camera = cv2.VideoCapture(0)
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
    model = torch.jit.load(MODEL_PATH, map_location="cpu")
    model.eval()
    torch.set_num_threads(1)

    try:
        while camera.isOpened():
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break

            ok, image = camera.read()
            if not ok:
                continue

            image = cv2.flip(image, -1)

            pre = img_preprocess(image)
            x = pre.transpose(2, 0, 1)
            x = np.expand_dims(x, axis=0)
            x_tensor = torch.from_numpy(x).float()

            with torch.no_grad():
                y = model(x_tensor)

            angle = int(float(y.item()))
            print('predict angle:', angle)

            cv2.imshow("camera", image)
            cv2.imshow('preprocess', (pre * 255).astype(np.uint8))

    finally:
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()