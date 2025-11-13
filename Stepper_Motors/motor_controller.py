import serial
import time

def send_to_c_program(message):
    usb_port = 'COM4'
    ser = serial.Serial(usb_port, 9600, timeout=1)
    time.sleep(2) #wait for the connection to establish
    ser.write((str(message)+"\n").encode())

def continuous_stepper_rotation(rot_time, angle, stepper_number=1):
    #stepper # 1 = rotation | stepper#2 = translation
    send_to_c_program(f"{stepper_number},{angle},{rot_time}")

def continuous_double_rotation(rot_time, angle_xy, angle_z):
    send_to_c_program(f"{angle_xy},{angle_z},{rot_time}")

def read_serial(port,baudrate):
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