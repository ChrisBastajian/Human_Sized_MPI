import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import sympy as sp
import scipy.integrate as quad

def biot_savart_numeric(path_func, dpath_func, s_vals, obs):
    mu0 = 4*np.pi*1e-7
    B = np.zeros(3)

    for i in range(len(s_vals)-1):
        s = s_vals[i]
        ds = s_vals[i+1] - s_vals[i]

        l = path_func(s)
        dl = dpath_func(s)

        r_vec = obs - l
        r_norm = np.linalg.norm(r_vec)

        if r_norm < 1e-9:
            continue

        dB = np.cross(dl, r_vec) / (r_norm**3)
        B += dB * ds

    return (mu0 / (4*np.pi)) * B

def circular_path(s, R):
    theta = s/R
    if s<=2*np.pi*R:
        return np.array([R*np.cos(theta), R*np.sin(theta), 0])
def circular_dpath(s, R): #This is the derivative of what is above
    theta = s/R
    if s <= 2*np.pi*R:
        return np.array([-np.sin(theta), np.cos(theta), 0])

def B_circular(x, y, z, R, N=2000, I=1.0):
    s_total = 2*np.pi*R
    s_vals = np.linspace(0, s_total, N)

    #The reference point is at the center of the coil (x=0, y=0, z=0):
    obs = np.array([x, y, z])
    path = lambda s: circular_path(s, R)
    dpath = lambda s: circular_dpath(s, R)
    B = biot_savart_numeric(path, dpath, s_vals, obs)
    return I*B

def B_solenoid_coil(x, y, z, R, N=2000, I=1.0, turns=10, spacing=3e-3): #the thickness of the coil is approx 3mm
    B_total = np.zeros(3)
    for i in range (turns):
        B_total += B_circular(x, y, z-i*spacing, R, N, I) #-i*spacing and not plus because this is from frame of reference of the obs point.

    return B_total

print(f"Magnetic field at the center: {B_solenoid_coil(0, 0, 15e-3, 100e-3)}")
print(f"Calculated field at the center: {(4*np.pi*1e-7)*10/(np.sqrt(4*pow(100e-3, 2)+pow(30e-3,2)))}")
