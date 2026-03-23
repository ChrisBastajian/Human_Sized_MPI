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
R = 100e-3 #radius of coil
obs = np.array([0,0,15e-3]) #center of the coil
N=2000
mu0 = 4*np.pi*1e-7
print(f"Magnetic field at the center: {B_solenoid_coil(0, 0, 15e-3, 100e-3)}")
print(f"Calculated field at the center: {(4*np.pi*1e-7)*10/(np.sqrt(4*pow(100e-3, 2)+pow(30e-3,2)))}")

#Inductance formula validation:
from scipy.special import ellipk, ellipe

mu0 = 4*np.pi*1e-7

# -----------------------------------
# Mutual inductance between 2 loops
# -----------------------------------
def mutual_inductance_loops(R1, R2, z):
    k2 = (4 * R1 * R2) / ((R1 + R2)**2 + z**2)
    k = np.sqrt(k2)

    K = ellipk(k2)
    E = ellipe(k2)

    M = mu0 * np.sqrt(R1 * R2) * (
        ((2 - k2) * K - 2 * E) / k
    )

    return M


# -----------------------------------
# Self inductance of a single loop
# -----------------------------------
def self_inductance_loop(R, wire_radius):
    return mu0 * R * (np.log(8*R / wire_radius) - 2)


# -----------------------------------
# Full solenoid inductance
# -----------------------------------
def inductance_solenoid_loops(R, turns, length, wire_radius):
    spacing = length / turns

    # center the coil
    z_positions = np.array([
        (k - (turns-1)/2) * spacing for k in range(turns)
    ])

    L = 0.0

    for i in range(turns):
        # self term
        L += self_inductance_loop(R, wire_radius)

        for j in range(i+1, turns):
            z = abs(z_positions[i] - z_positions[j])
            M = mutual_inductance_loops(R, R, z)

            L += 2 * M  # symmetry

    return L


# -----------------------------------
# Example usage
# -----------------------------------
R = 0.1
turns = 1000
length = 2.0
wire_radius = 1e-3

L_num = inductance_solenoid_loops(R, turns, length, wire_radius)

L_analytical = mu0 * (turns**2) * np.pi * R**2 / length

print(f"Loop-based inductance: {L_num:.6e} H")
print(f"Analytical inductance: {L_analytical:.6e} H")