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

def racetrack_path(s, L, R):
    if s < L:
        return np.array([(-L/2)+s, -R, 0]) #lower side where s is in [0,L]
    elif s < L+np.pi*R:
        theta = (s-L)/R #arc length / radius but arc length is from the center of the whole coil...
        return np.array([(L/2)+R*np.cos(theta - np.pi/2), R*np.sin(theta - np.pi/2), 0]) #for s between L and L+R*pi
    elif s < 2*L +np.pi*R:
        return np.array([(-L/2) - (s-(L+np.pi*R)), R, 0]) #where s is between L+R*pi and 2*L+R*pi
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

def B_racetrack_coil(x, y, z, L, R, N=2000, I=1.0, turns=10, spacing=3e-3): #the thickness of the coil is approx 3mm
    B_total = np.zeros(3)
    for i in range (turns):
        B_total += B_racetrack(x, y, z-i*spacing, L, R, N, I) #-i*spacing and not plus because this is from frame of reference of the obs point.

    return B_total

L=0.25
R=0.1
value = 0
for i in range(4): #The radius will increase for each layer of coils (increasing outwards) by the thickness of the wire
    value += B_racetrack_coil(0, 0, 150e-3, L, R+3e-3, turns=100, I=30) #z is also centered...
print(value)
