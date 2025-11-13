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
VQ = 2.5 #Vq ranges from 2.375 to 2.5 (use 2.375 for currents less than 5A and 2.5 for anything more
sensitivity = 40 *1e-3 #bidirectional 50 A detector


#Input parameters:
vi = 1 #100mVpp
f = 60 #60Hz
channel=1

i_rms = []

inst = wave_gen.find_and_connect_waveform_generator()
wave_gen.send_voltage(inst, vi, f, channel)
def receive_raw_voltage(daq_location, sample_rate, num_samples):
    with nidaqmx.Task() as task:
        task.ai_channels.add_ai_voltage_chan(daq_location)
        task.timing.cfg_samp_clk_timing(sample_rate, samps_per_chan=num_samples)
        voltage_raw = task.read(number_of_samples_per_channel= num_samples)
        return(voltage_raw)


def get_rms_current(daq_location, fs, num_samples):
    voltage = receive_raw_voltage(daq_location, fs, num_samples)
    squares_added = 0
    voltages_raw = np.zeros(num_samples)
    currents = np.zeros(num_samples)
    squares = np.zeros(num_samples)
    squares_added = 0
    for j in range(num_samples):
        voltages_raw[j] = voltage[j]
        voltage_corrected = voltages_raw[j] - VQ
        currents[j] = voltage_corrected / sensitivity

        squares[j] = currents[j] ** 2
        squares_added += squares[j]
    mean_square = squares_added / num_samples
    rms_current = np.sqrt(mean_square)

    print(f"I(rms): {rms_current:.2f}")

    return rms_current

# Main loop
daq_location = "Dev1/ai1"

v = receive_raw_voltage(daq_location, fs, num_samples)
print(f"Raw voltage: min={np.min(v):.3f} V, mean={np.mean(v):.3f} V, max={np.max(v):.3f} V")

for i in range(20):
    i_rms.append(get_rms_current(daq_location, fs, num_samples))
    time.sleep(0.01)
wave_gen.turn_off(inst, channel=1)
inst.close()

plt.figure()
plt.plot(i_rms)
plt.grid()
plt.xlabel("Samples")
plt.ylabel("RMS current")
plt.show()
