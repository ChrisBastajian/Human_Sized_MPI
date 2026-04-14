import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import sympy as sp
import scipy.integrate as quad

#Constants:
num_turns_per_layer = 26 #going up in z
num_layers = 8
wire_thickness = 0.82e-3 #square copper wire with each side = 0.82mm
resistance = 154e-3 #upper limit for DC resistance
inductance = 365e-6 #upper limit for inductance measured at 25kHz
outer_dimensions = np.array([5.5, 30, 1.6]) * 1e-2

#Figuring out the dimensions from the constants:
R_inner = (outer_dimensions[0] - wire_thickness * 2 * num_layers) / 2
print(R_inner +wire_thickness *num_layers) # this should give 2.75cm (validated)
radii = np.linspace(R_inner, R_inner + wire_thickness * num_layers, num_layers)
length = outer_dimensions[1]-outer_dimensions[0] #this stays constant all throughout

"""
Note: For the third dimension, the wire_thickness and the z length do not agree.
I will be using a rectangular cross-section for the wires instead where the z dimension
is a little smaller than the value above.
"""

z_thickness = outer_dimensions[2]/num_turns_per_layer
z_positions = np.arange(0, outer_dimensions[2], z_thickness) #when stacking the wires on top of each other


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

def racetrack_path(s, L, R):
    if s < L:
        return np.array([(-L/2)+s, -R, 0]) #lower side where s is in [0,L]
    elif s < L+np.pi*R:
        theta = (s-L)/R #arc length / radius but arc length is from the center of the whole coil...
        return np.array([(L/2)+R*np.cos(theta - np.pi/2), R*np.sin(theta - np.pi/2), 0]) #for s between L and L+R*pi
    elif s < 2*L +np.pi*R:
        return np.array([(L/2) - (s-(L+np.pi*R)), R, 0]) #where s is between L+R*pi and 2*L+R*pi
    else:
        theta = (s-(2*L+np.pi*R))/R
        return np.array([(-L/2)+R*np.cos(theta + np.pi/2), R*np.sin(theta + np.pi/2), 0]) #where s is between 2*L+R*pi and 2*L+2R*pi

def racetrack_dpath(s, L, R): #This is the derivative of what is above
    if s<L:
        return np.array([1, 0, 0])
    elif s < L+np.pi*R:
        theta = (s-L)/R #arc length / radius but arc length is from the center of the whole coil...
        return np.array([-np.sin(theta - np.pi/2), np.cos(theta - np.pi/2), 0]) #for s between L and L+R*pi
    elif s < 2*L +np.pi*R:
        return np.array([-1,0, 0]) #where s is between L+R*pi and 2*L+R*pi
    else:
        theta = (s-(2*L+np.pi*R))/R
        return np.array([-np.sin(theta + np.pi/2), np.cos(theta + np.pi/2), 0]) #where s is between 2*L+R*pi and 2*L+2R*pi

def B_racetrack(x, y, z, L, R, N=2000, I=1.0):
    s_total = 2*np.pi*R + 2*L
    s_vals = np.linspace(0, s_total, N)

    #The reference point is at the center of the coil (x=0, y=0, z=0):
    obs = np.array([x, y, z])
    path = lambda s: racetrack_path(s, L, R)
    dpath = lambda s: racetrack_dpath(s, L, R)
    B = biot_savart_numeric(path, dpath, s_vals, obs)
    return I*B

value =0
#we loop through every layer (z_pos) and every turn in that layer (radius)
for z_pos in z_positions:
    for radius in radii:
        value += B_racetrack(0, 0, (outer_dimensions[2]/2)-z_pos, length, radius, I=30)
        #-z_pos and not plus because this is from frame of reference of the obs point (coil goes up in z referred to center of coil)
print(value)
