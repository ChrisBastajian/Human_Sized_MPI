import matplotlib
matplotlib.use('TkAgg')
import time
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.animation import FuncAnimation

r = 0.08          # meters
L = 0.11          # meters
N = 130.67           # turns
n = N / L         # turns per meter
mu0 = 4 * np.pi * 1e-7
mur = 1

def B_bottom(x):     # bottom of coil
    return 0.293773 * x * 1e-3

def B_center(x):     # center of coil
    return 0.4198 * x * 1e-3

def Bfield(x, zg):  #x is current in amps and zg is gantry height in meters
    """Note: Performs a recalculation of the required current given experimental calibration data of the
        center of the magnetic field. Then, performs an integration of the magnetic field through the center of
        the coil. """
    z = [0, L / 2]
    theta1_arr = []
    theta2_arr = []
    for val in z:
        theta2_arr.append(np.arctan(val / r))
        z1 = L - val
        theta1_arr.append(np.arctan(-z1 / r))

    B0 = B_bottom(x)  # actual center magnetic field
    I0 = (4 * B0) / (mu0 * n * (np.sin(theta2_arr[0]) - np.sin(theta1_arr[0])))  # theoretical current if geometry was perfect

    B1 = B_center(x) #actual center magnetic field
    I1 = (4 * B1) / (mu0 * n * (np.sin(theta2_arr[1]) - np.sin(theta1_arr[1]))) #theoretical current if geometry was perfect

    Iavg = (I0 + I1)/2
    print(f" Field: {B0, B1} | Currents: {I0, I1} | Avg: {Iavg}")
    zvals = np.linspace(-0.095, 0.205, 59)
    Bvar = []

    for z2 in zvals:
        theta2 = np.arctan(z2 / r)
        z1 = L - z2
        theta1 = np.arctan(-z1 / r)
        Bval = np.sqrt(2) * (mu0 * Iavg * n * (np.sin(theta2) - np.sin(theta1))) / 4
        Bvar.append(Bval)


    zvals_shifted = np.linspace(-0.095 + zg, 0.205 + zg, 59)
    #df = pd.DataFrame({'zvals': zvals_cm, 'Bvar': Bvar})
    #df.to_excel('Bvar.xlsx', index=False)
    return zvals_shifted * 100, np.array(Bvar) * 1000 # z values in cm and B values in mT

x_val = 30
zg_val = 0

fig, ax = plt.subplots(figsize=(8,5))
line, = ax.plot([], [])
ax.set_title('Magnetic Field Strength Through Center of Solenoid (B)')
ax.set_ylabel('Distance from Base Position of Gantry (cm)')
ax.set_xlabel('Magnetic Field (mT)')
ax.grid(True)
z_center_cm = (L / 2) * 100
center_line = ax.axhline(z_center_cm, linestyle='--', color='gray', label='Center of Coil')
bottom_line = ax.axhline(0, linestyle=':', color='blue', label='Edge of Coil')
top_line = ax.axhline(L * 100, linestyle=':', color='blue')
ax.legend()

def update(frame):
    global x_val
    global zg_val

    x_val = 30 #Irms
    zg_val += 0.0001 #height #in meters
    zgvals, Bvals = Bfield(x_val, zg_val)
    line.set_data(Bvals, zgvals)
    ax.set_ylim(0, 40)
    ax.set_xlim(min(Bvals), max(Bvals))

    new_center_line = z_center_cm + zg_val * 100
    center_line.set_ydata([new_center_line, new_center_line])
    new_bottom_line = zg_val * 100
    bottom_line.set_ydata([new_bottom_line, new_bottom_line])
    new_top_line = L * 100 + zg_val * 100
    top_line.set_ydata([new_top_line, new_top_line])

    return line,
#call time and length
ani = FuncAnimation(fig, update, interval=10)
plt.show()