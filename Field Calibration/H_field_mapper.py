"""
This script is solely based on the tx coil design for the senior design portion of the platform (solenoid coil
for testing platform). The calibration test needs to be reran for future coil geometries and designs.
"""
import numpy as np
def B_bottom(x):     # bottom of coil
    return 0.293773 * x * 1e-3

def B_center(x):     # center of coil
    return 0.4198 * x * 1e-3

def Bfield(x, zg):  #x is current in amps and zg is gantry height in meters
    """Note: Performs a recalculation of the required current given experimental calibration data of the
        center of the magnetic field. Then, performs an integration of the magnetic field through the center of
        the coil. """

    #Initializing parameters based on coil dimensions:
    r = 0.08  # meters
    L = 0.11  # meters
    N = 130.67  # turns
    n = N / L  # turns per meter
    mu0 = 4 * np.pi * 1e-7
    mur = 1

    #Calibrating first to get a "theoretical current". Refer to README.md file for additional info.
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

