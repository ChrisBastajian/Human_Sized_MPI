import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

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

    zvals = np.arange(-0.09 + zg, 0.205 + zg, 0.005)
    Bvar = np.array(Bvar) * 1000      # Tesla → mT
    zvals_cm = zvals * 100            # m -> cm

    df = pd.DataFrame({'zvals': zvals_cm, 'Bvar': Bvar})
    df.to_excel('Bvar.xlsx', index=False)

    plt.figure(figsize=(8,5))
    plt.plot(zvals_cm, Bvar)
    plt.title('Magnetic Field Strength Through Center of Solenoid')
    plt.xlabel('Distance from Top of Coil (cm)')
    plt.ylabel('Magnetic Field (mT)')
    plt.grid(True)
    plt.show()

    return df

df = Bfield(x = 30, zg = 0.05)