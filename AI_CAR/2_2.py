import mycamera
import cv2

if __name__ == "__main__":
    camera = mycamera.MyPiCamera(640,480)

    while camera.isOpened():
        _, image = camera.read()
        cv2.imshow("mycamera", image)
        
        if cv2.waitKey(1) == ord('q'):
            break

    cv2.destroyAllWindows()