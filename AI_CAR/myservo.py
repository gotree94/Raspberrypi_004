import smbus
import time

CENTER_STEETING_VALUE = 81
LEFT_MAX_STEETING_VALUE = 26
RIGHT_MAX_STEETING_VALUE = 118

CENTER_STEETING_OFFSET = 90 - CENTER_STEETING_VALUE

class PCA9685:
    def __init__(self, address=0x40, bus_num=1):
        self.address = address
        self.bus = smbus.SMBus(bus_num)
        self.MODE1 = 0x00
        self.MODE2 = 0x01
        self.PRESCALE = 0xFE
        self.LED0_ON_L = 0x06
        self.LED0_ON_H = 0x07
        self.LED0_OFF_L = 0x08
        self.LED0_OFF_H = 0x09
        self._init_pca9685()

    def _init_pca9685(self):
        self.bus.write_byte_data(self.address, self.MODE1, 0x00)
        self.set_pwm_freq(60)

    def set_pwm_freq(self, freq):
        prescale_val = int(25000000.0 / (4096 * freq) - 1)
        old_mode = self.bus.read_byte_data(self.address, self.MODE1)
        new_mode = (old_mode & 0x7F) | 0x10  # sleep
        self.bus.write_byte_data(self.address, self.MODE1, new_mode)
        self.bus.write_byte_data(self.address, self.PRESCALE, prescale_val)
        self.bus.write_byte_data(self.address, self.MODE1, old_mode)
        time.sleep(0.005)
        self.bus.write_byte_data(self.address, self.MODE1, old_mode | 0x80)

    def set_pwm(self, channel, on, off):
        self.bus.write_byte_data(self.address, self.LED0_ON_L + 4*channel, on & 0xFF)
        self.bus.write_byte_data(self.address, self.LED0_ON_H + 4*channel, on >> 8)
        self.bus.write_byte_data(self.address, self.LED0_OFF_L + 4*channel, off & 0xFF)
        self.bus.write_byte_data(self.address, self.LED0_OFF_H + 4*channel, off >> 8)

    def set_row_servo_angle(self, channel, angle):
        pulse_length = 1000000.0 / 60 / 4096 
        pulse = int((angle * (2500 / 180) + 500) / pulse_length)
        self.set_pwm(channel, 0, pulse)
        
        return angle

    def set_servo_angle(self, channel, angle):
        mapped_angle = angle - CENTER_STEETING_OFFSET
        
        if mapped_angle > RIGHT_MAX_STEETING_VALUE:
            mapped_angle = RIGHT_MAX_STEETING_VALUE
        elif mapped_angle < LEFT_MAX_STEETING_VALUE:
            mapped_angle = LEFT_MAX_STEETING_VALUE
        
        self.set_row_servo_angle(channel, mapped_angle)
        
        return mapped_angle + CENTER_STEETING_OFFSET

def main():
    pca9685 = PCA9685()
    channel = 0

    try:
        while True:
            in_angle = int(input("row angle:"))
            pca9685.set_row_servo_angle(channel, in_angle)

    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()

