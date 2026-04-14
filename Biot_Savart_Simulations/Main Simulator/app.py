from flask import Flask, render_template, request, jsonify
import numpy as np

app = Flask(__name__)


# --- Vectorized Biot-Savart Core Math ---
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


def biot_savart_vectorized(path_func, dpath_func, s_vals, obs):
    mu0 = 4 * np.pi * 1e-7
    s_mid = s_vals[:-1]
    ds = s_vals[1:] - s_vals[:-1]

    l_vecs = np.array([path_func(s) for s in s_mid])
    dl_vecs = np.array([dpath_func(s) for s in s_mid])

    r_vecs = obs - l_vecs
    r_norms = np.linalg.norm(r_vecs, axis=1)[:, np.newaxis]

    valid = r_norms.flatten() > 1e-9
    dB = np.zeros_like(r_vecs)
    dB[valid] = np.cross(dl_vecs[valid], r_vecs[valid]) / (r_norms[valid] ** 3)

    B = np.sum(dB * ds[:, np.newaxis], axis=0)
    return (mu0 / (4 * np.pi)) * B


def B_racetrack_vectorized(x, y, z, coil_z, L, R, N, I):
    s_total = 2 * np.pi * R + 2 * L
    s_vals = np.linspace(0, s_total, N)

    obs = np.array([x, y, z - coil_z])
    B = biot_savart_vectorized(lambda s: racetrack_path(s, L, R),
                               lambda s: racetrack_dpath(s, L, R),
                               s_vals, obs)
    return B * I


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/calculate', methods=['POST'])
def calculate():
    data = request.json

    # Coil Parameters (Directly using R and L)
    R_inner = float(data['R']) * 1e-2
    L_straight = float(data['L']) * 1e-2
    height = float(data['height']) * 1e-2
    num_layers = int(data['num_layers'])
    num_turns = int(data['num_turns'])
    wire_thick = float(data['wire_thickness']) * 1e-3
    current = float(data['current'])

    # Grid Parameters
    x_min, x_max = float(data['x_min']) * 1e-2, float(data['x_max']) * 1e-2
    y_min, y_max = float(data['y_min']) * 1e-2, float(data['y_max']) * 1e-2
    z_min, z_max = float(data['z_min']) * 1e-2, float(data['z_max']) * 1e-2
    grid_res = int(data['grid_res'])

    # Derived Arrays
    radii = np.linspace(R_inner, R_inner + wire_thick * (num_layers - 1), num_layers)
    z_thickness = height / num_turns
    z_positions = np.arange(0, height, z_thickness)

    # 1. Generate 3D Grid Space
    X, Y, Z = np.meshgrid(
        np.linspace(x_min, x_max, grid_res),
        np.linspace(y_min, y_max, grid_res),
        np.linspace(z_min, z_max, grid_res),
        indexing='ij'
    )

    points = np.vstack([X.ravel(), Y.ravel(), Z.ravel()]).T
    U, V, W = np.zeros_like(points[:, 0]), np.zeros_like(points[:, 1]), np.zeros_like(points[:, 2])

    N_points = 100  # Integration segments per loop

    # 2. Calculate B-field
    for i, obs in enumerate(points):
        B_total = np.zeros(3)
        for z_pos in z_positions:
            for radius in radii:
                B_total += B_racetrack_vectorized(obs[0], obs[1], obs[2], z_pos, L_straight, radius, N_points, current)
        U[i], V[i], W[i] = B_total[0], B_total[1], B_total[2]

    # 3. Generate Single Continuous Coil Path
    all_x, all_y, all_z = [], [], []
    num_pts_per_loop = 100

    for i in range(num_layers):
        radius = radii[i]
        s_total = 2 * np.pi * radius + 2 * L_straight
        s_vals = np.linspace(0, s_total, num_pts_per_loop)

        for j in range(num_turns):
            z_start = z_positions[j]
            z_vals = z_start + (s_vals / s_total) * z_thickness
            path = np.array([racetrack_path(s, L_straight, radius) for s in s_vals])

            all_x.extend(path[:, 0].tolist())
            all_y.extend(path[:, 1].tolist())
            all_z.extend(z_vals.tolist())

        if i < num_layers - 1:
            next_radius = radii[i + 1]
            # Flyback wire shifting outwards and dropping to z=0
            all_x.extend([-L_straight / 2, -L_straight / 2])
            all_y.extend([-next_radius, -next_radius])
            all_z.extend([height, 0])

    coil_paths = [{'x': all_x, 'y': all_y, 'z': all_z}]

    return jsonify({
        'grid': {
            'x': points[:, 0].tolist(),
            'y': points[:, 1].tolist(),
            'z': points[:, 2].tolist(),
            'u': U.tolist(),
            'v': V.tolist(),
            'w': W.tolist()
        },
        'coil_paths': coil_paths
    })


if __name__ == '__main__':
    app.run(debug=True, port=5000)