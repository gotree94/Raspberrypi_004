import myservo

def main():
    pca9685 = myservo.PCA9685()
    channel = 0

    try:
        while True:
            in_angle = int(input("angle:"))
            set_angle = pca9685.set_servo_angle(channel, in_angle)
            print("set angle:",set_angle)

    except KeyboardInterrupt:
        pca9685.set_servo_angle(90)

if __name__ == "__main__":
    main()
