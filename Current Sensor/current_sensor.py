import numpy as np
import nidaqmx
import time
import matplotlib.pyplot as plt

import wave_gen
import matplotlib
matplotlib.use('TkAgg')
fs=10000
num_samples = 10000

#current sensing variables:
Vcc = 5
VQ = 0.5 * Vcc
sensitivity = 0.1
voltages_raw = np.zeros(num_samples)
currents = np.zeros(num_samples)
squares = np.zeros(num_samples)
squares_added = 0
mean_square = 0
rms_current = 0
i = 0

#Input parameters:
vi = 0 #100mVpp
f = 1000 #1kHz
channel=1
inst = wave_gen.find_and_connect_waveform_generator()
wave_gen.send_voltage(inst, vi, f, channel)
def receive_raw_voltage(daq_location, sample_rate, num_samples):
    with nidaqmx.Task() as task:
        task.ai_channels.add_ai_voltage_chan(daq_location)
        task.timing.cfg_samp_clk_timing(sample_rate, samps_per_chan=num_samples)
        voltage_raw = task.read(number_of_samples_per_channel= num_samples)
        return(voltage_raw)


def get_rms_current(daq_location, fs, num_samples):
    global i, squares_added, rms_current
    voltage = receive_raw_voltage(daq_location, fs, num_samples)
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

# Main loop
daq_location = "Dev1/ai1"
for i in range(100):
    rms_current = get_rms_current(daq_location, fs, num_samples)
    time.sleep(0.01)
wave_gen.turn_off(inst, channel=1)
inst.close()

plt.figure()
plt.plot(rms_current)
plt.grid()
plt.xlabel("Samples")
plt.ylabel("RMS current")
plt.show()
