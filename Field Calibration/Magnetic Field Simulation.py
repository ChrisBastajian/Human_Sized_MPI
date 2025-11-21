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

def B_center(x):     # center of coil
    return 0.4198 * x * 1e-3

def Bfield(x, zg):  #x is current in amps and zg is gantry height in meters
    z = L / 2
    theta2 = np.arcsin(z / np.sqrt(z ** 2 + r ** 2))
    theta1 = np.arcsin((-z) / np.sqrt(z ** 2 + r ** 2))

    B = B_center(x)
    I = (2 * B) / (mu0 * n * (np.sin(theta2) - np.sin(theta1)))

    zvals = np.arange(-0.09, 0.205, 0.005)
    Bvar = []

    for z2 in zvals:
        theta2 = np.arctan(z2 / r)
        z1 = L - z2
        theta1 = np.arctan(-z1 / r)
        Bval = (mu0 * I * n * (np.sin(theta2) - np.sin(theta1))) / 2
        Bvar.append(Bval)

    zvals_shifted = np.linspace(-0.085 + zg, 0.205 + zg, 59)
    #df = pd.DataFrame({'zvals': zvals_cm, 'Bvar': Bvar})
    #df.to_excel('Bvar.xlsx', index=False)
    return zvals_shifted * 100, np.array(Bvar) * 1000 # z values in cm and B values in mT

fig, ax = plt.subplots(figsize=(8,5))
line, = ax.plot([], [])
ax.set_title('Magnetic Field Strength Through Center of Solenoid (B)')
ax.set_xlabel('Distance from Base Position of Gantry (cm)')
ax.set_ylabel('Magnetic Field (mT)')
ax.grid(True)

x_val = 30
zg_val = 0

def update(frame):
    global x_val
    global zg_val

    x_val = 30
    zg_val += 0.5
    zgvals, Bvals = Bfield(x_val, zg_val)
    line.set_data(zgvals, Bvals)
    ax.set_xlim(min(zgvals), max(zgvals))
    ax.set_ylim(min(Bvals), max(Bvals))
    print("Frame", frame)
    return line,

ani = FuncAnimation(fig, update, interval=200)
plt.show()