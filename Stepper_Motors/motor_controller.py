import serial
import time

def send_to_c_program(message):
    usb_port = 'COM4'
    ser = serial.Serial(usb_port, 9600, timeout=1)
    time.sleep(2) #wait for the connection to establish
    ser.write((str(message)+"\n").encode())

def continuous_servo_rotation(rot_time, angle, stepper_number=1):
    #stepper # 1 = rotation | stepper#2 = translation
    send_to_c_program(f"{stepper_number},{time},{angle}")

#testing script:
continuous_servo_rotation(rot_time=10, angle=180, stepper_number=1)