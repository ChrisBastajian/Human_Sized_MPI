import pyvisa
import time

def connect_waveform_generator(gpib_address):
    try:
        rm = pyvisa.ResourceManager()
        inst = rm.open_resource(f'GPIB::{gpib_address}')
        return inst
    except pyvisa.Error as e:
        print(f"Error connecting to the waveform generator: {e}")
        return None

def send_voltage(inst, voltage, frequency, channel):
    try:
        inst.write(f"SOURCE{channel}:VOLTage {voltage}Vpp")
        inst.write(f"SOURCE{channel}:FREQuency {frequency} HZ")
        inst.write(f"OUTPUT{channel} ON")
        inst.write(f"OUTPUT:SYNC{channel} ON")  # Enable synchronization for the channel
        inst.write(f"TRIGger:MODE:SOURCE{channel} IMM")  # Set trigger mode to immediate for the channel
        inst.write(f"TRIGger:SOURCE{channel} BUS")  # Set trigger source to bus for the channel
        print(f"Voltage set to {voltage} V")
        print(f"Output on Channel {channel} enabled with synchronization and triggering.")
    except pyvisa.Error as e:
        print(f"Error: {e}")
    time.sleep(0.01) #to receive better data (allows time for system to adapt)

#Turn off:
def turn_off(inst, channel):
    inst.write(f"OUTPUT{channel} OFF")
    inst.close()
#example
#waveform_generator = connect_waveform_generator(10)
#send_voltage(waveform_generator, 0.1, 1000,1)

#time.sleep(5)

#waveform_generator.write(f"OUTPUT{1} OFF")
#waveform_generator.close()
