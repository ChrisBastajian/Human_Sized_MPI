import serial
import time
import nidaqmx
from nidaqmx.constants import Edge
import numpy as np

#function for reading raw voltage from the daq card:
def receive_raw_voltage(daq_location, sample_rate, n_samps, trigger_location=None,):
    with nidaqmx.Task() as task:
        task.ai_channels.add_ai_voltage_chan(daq_location)
        # Add a trigger source and set it to rising edge
        if trigger_location is not None:
            task.triggers.start_trigger.cfg_dig_edge_start_trig(trigger_location, Edge.RISING)

        task.timing.cfg_samp_clk_timing(sample_rate, samps_per_chan=int(n_samps))
        voltage_raw = task.read(number_of_samples_per_channel= int(n_samps))
        return voltage_raw

#To receive the current (rms):
def get_rms_current(daq_location, fs, num_samples, sensitivity=0.04):
    voltage = receive_raw_voltage(daq_location, fs, num_samples)
    voltages_raw = np.zeros(num_samples)
    for j in range(num_samples):
        voltages_raw[j] = voltage[j]

    voltage_corrected = voltages_raw - np.mean(voltages_raw) #the mean is the quiescent voltage (since the signal is ac)
    currents = voltage_corrected / sensitivity

    squares = currents ** 2
    squares_added = np.sum(squares)
    mean_square = squares_added / num_samples
    rms_current = np.sqrt(mean_square)

    print(f"I(rms): {rms_current:.2f}")

    return rms_current

def send_serial_message(message, usb_port='COM4'):
    ser = serial.Serial(usb_port, 9600, timeout=1)
    time.sleep(2) #wait for the connection to establish
    ser.write((str(message)+"\n").encode())

def rotate_stepper_motor(rot_time, angle, stepper_number=1):
    #stepper # 1 = rotation | stepper#2 = translation
    send_serial_message(f"single,{stepper_number},{time},{angle}")

def rotate_steppers_simultaneously(rot_time, angles=None):
    if angles is None:
        angles = [360, 720]
    send_serial_message(f"double,{rot_time},{angles[0]},{angles[1]}")

