import numpy as np
import time

# --- Constants & Geometry Setup ---
num_turns_per_layer = 26
num_layers = 8
wire_thickness = 0.82e-3
outer_dimensions = np.array([5.5, 30, 1.6]) * 1e-2

R_inner = (outer_dimensions[0] - wire_thickness * 2 * num_layers) / 2
radii = np.linspace(R_inner, R_inner + wire_thickness * num_layers, num_layers)
length = outer_dimensions[1] - outer_dimensions[0]

z_thickness = outer_dimensions[2] / num_turns_per_layer
z_positions = np.arange(0, outer_dimensions[2], z_thickness)


# --- 1. Path Definitions (Shared) ---
def racetrack_path(s, L, R):
    if s < L:
        return np.array([(-L / 2) + s, -R, 0])
    elif s < L + np.pi * R:
        theta = (s - L) / R
        return np.array([(L / 2) + R * np.cos(theta - np.pi / 2), R * np.sin(theta - np.pi / 2), 0])
    elif s < 2 * L + np.pi * R:
        return np.array([(L / 2) - (s - (L + np.pi * R)), R, 0])
    else:
        theta = (s - (2 * L + np.pi * R)) / R
        return np.array([(-L / 2) + R * np.cos(theta + np.pi / 2), R * np.sin(theta + np.pi / 2), 0])


def racetrack_dpath(s, L, R):
    if s < L:
        return np.array([1, 0, 0])
    elif s < L + np.pi * R:
        theta = (s - L) / R
        return np.array([-np.sin(theta - np.pi / 2), np.cos(theta - np.pi / 2), 0])
    elif s < 2 * L + np.pi * R:
        return np.array([-1, 0, 0])
    else:
        theta = (s - (2 * L + np.pi * R)) / R
        return np.array([-np.sin(theta + np.pi / 2), np.cos(theta + np.pi / 2), 0])

    # --- 2. Unvectorized (Your Original Approach) ---


def biot_savart_numeric(path_func, dpath_func, s_vals, obs):
    mu0 = 4 * np.pi * 1e-7
    B = np.zeros(3)
    for i in range(len(s_vals) - 1):
        s = s_vals[i]
        ds = s_vals[i + 1] - s_vals[i]

        l = path_func(s)
        dl = dpath_func(s)

        r_vec = obs - l
        r_norm = np.linalg.norm(r_vec)

        if r_norm < 1e-9:
            continue

        dB = np.cross(dl, r_vec) / (r_norm ** 3)
        B += dB * ds
    return (mu0 / (4 * np.pi)) * B


def B_racetrack_unvectorized(x, y, z, L, R, N, I):
    s_total = 2 * np.pi * R + 2 * L
    s_vals = np.linspace(0, s_total, N)
    obs = np.array([x, y, z])
    B = biot_savart_numeric(lambda s: racetrack_path(s, L, R),
                            lambda s: racetrack_dpath(s, L, R),
                            s_vals, obs)
    return I * B


# --- 3. Vectorized Approach ---
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


# --- 4. Validation and Benchmarking ---
if __name__ == "__main__":
    N_points = 1000
    current = 30

    print(f"Running simulation with {num_layers * num_turns_per_layer} total turns...")
    print(f"Integration points per turn: {N_points}\n")

    # --- Run Unvectorized ---
    print("Starting Unvectorized Calculation (This may take 10-20 seconds)...")
    start_time = time.time()
    value_unvectorized = np.zeros(3)

    for z_pos in z_positions:
        for radius in radii:
            value_unvectorized += B_racetrack_unvectorized(0, 0, outer_dimensions[2] - z_pos, length, radius,
                                                           N=N_points, I=current)

    unvectorized_time = time.time() - start_time
    print(f"Unvectorized Result: {value_unvectorized}")
    print(f"Unvectorized Time:   {unvectorized_time:.4f} seconds\n")

    # --- Run Vectorized ---
    print("Starting Vectorized Calculation...")
    start_time = time.time()
    value_vectorized = np.zeros(3)

    for z_pos in z_positions:
        for radius in radii:
            value_vectorized += B_racetrack_vectorized(0, 0, outer_dimensions[2] - z_pos, length, radius, N=N_points,
                                                       I=current)

    vectorized_time = time.time() - start_time
    print(f"Vectorized Result:   {value_vectorized}")
    print(f"Vectorized Time:     {vectorized_time:.4f} seconds\n")

    # --- Comparison ---
    print("--- SUMMARY ---")
    difference = np.linalg.norm(value_unvectorized - value_vectorized)
    print(f"Absolute difference between methods: {difference:.2e} T")
    print(f"Speedup multiplier: {unvectorized_time / vectorized_time:.2f}x faster")