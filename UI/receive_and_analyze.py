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
def get_rms_current(daq_location, fs, num_samples, trigger_location):
    # current sensing variables:
    Vcc = 5.0
    VQ = 0.5 * Vcc
    sensitivity = 0.1
    voltages_raw = np.zeros(num_samples)
    currents = np.zeros(num_samples)
    squares = np.zeros(num_samples)
    squares_added = 0
    i = 0
    voltage = receive_raw_voltage(daq_location, fs, num_samples, trigger_location)
    squares_added = 0

    for i in range(num_samples):
        voltages_raw[i] = voltage[i]
        voltage_corrected = voltages_raw[i] - VQ
        currents[i] = voltage_corrected / sensitivity

        squares[i] = currents[i] ** 2
        squares_added += squares[i]

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

