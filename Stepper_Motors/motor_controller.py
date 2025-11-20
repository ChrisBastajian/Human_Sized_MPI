import serial
import time

def send_to_c_program(usb_port, message):
    ser = serial.Serial(usb_port, 9600, timeout=1)
    time.sleep(2) #wait for the connection to establish
    ser.write((str(message)+"\n").encode())

def continuous_stepper_rotation(rot_time, angle, stepper_number=1, usb_port='COM1'):
    #stepper # 1 = rotation | stepper#2 = translation
    send_to_c_program(usb_port,f"{stepper_number},{angle},{rot_time},f0\n")

def continuous_double_rotation(rot_time, angle_xy, angle_z, usb_port = 'COM1'):
    send_to_c_program(usb_port,f"{angle_xy},{angle_z},{rot_time},f1\n")

def read_serial(port, baudrate):
     ser = serial.Serial(port, baudrate, timeout=1)
     data_raw = ser.readline()
     if data_raw:
         data_str = data_raw.decode('utf-8').strip()
         print(f"Received: {data_str}")
         return data_str
     else:
         return None


#testing script:
#continuous_servo_rotation(rot_time=10, angle=180, stepper_number=1)