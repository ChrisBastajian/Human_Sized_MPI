import serial
import time

arduino = serial.Serial(port="COM4", baudrate=9600, timeout=0.1)

def send_to_c_program(message):
    usb_port = 'COM4'
    ser = serial.Serial(usb_port, 9600, timeout=1)
    time.sleep(2) #wait for the connection to establish
    ser.write((str(message)+"\n").encode())

def continuous_servo_rotation(time, angle, servo_number=1):
    #servo # 1 = rotation | servo#2 = translation
    send_to_c_program(f"{servo_number},{time},{angle}")

#testing script:
continuous_servo_rotation(time=10, angle=180, servo_number=1)