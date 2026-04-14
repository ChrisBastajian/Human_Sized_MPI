import numpy as np

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

def biot_savart_vectorized(path_func, dpath_func, s_vals, obs):
    mu0 = 4 * np.pi * 1e-7

    # Calculate midpoints for the integration steps to match the original logic
    s_mid = s_vals[:-1]
    ds = s_vals[1:] - s_vals[:-1]

    # Generate all path and dpath vectors at once
    l_vecs = np.array([path_func(s) for s in s_mid])
    dl_vecs = np.array([dpath_func(s) for s in s_mid])

    # Calculate all r vectors at once
    r_vecs = obs - l_vecs

    # Calculate norms for all r vectors (axis=1 means across the x,y,z components)
    r_norms = np.linalg.norm(r_vecs, axis=1)[:, np.newaxis]

    # Create a mask to ignore points where r is dangerously close to 0
    valid = r_norms.flatten() > 1e-9

    # Perform the cross product for ALL segments simultaneously
    dB = np.zeros_like(r_vecs)
    dB[valid] = np.cross(dl_vecs[valid], r_vecs[valid]) / (r_norms[valid] ** 3)

    # Multiply by ds and sum everything up in one go
    B = np.sum(dB * ds[:, np.newaxis], axis=0)

    return (mu0 / (4 * np.pi)) * B


def B_racetrack_vectorized(x, y, z, L, R, N, I):
    s_total = 2 * np.pi * R + 2 * L
    s_vals = np.linspace(0, s_total, N)
    obs = np.array([x, y, z])
    B = biot_savart_vectorized(lambda s: racetrack_path(s, L, R),
                               lambda s: racetrack_dpath(s, L, R),
                               s_vals, obs)
    return I * B

value =0
#we loop through every layer (z_pos) and every turn in that layer (radius)
for z_pos in z_positions:
    for radius in radii:
        value += B_racetrack_vectorized(0, 0, (outer_dimensions[2]/2)-z_pos, length, radius, N=2000, I=30)
        #-z_pos and not plus because this is from frame of reference of the obs point (coil goes up in z referred to center of coil)
print(value)