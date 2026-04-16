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


def B_racetrack_vectorized(x, y, z, cx, cy, cz, coil_z, L, R, N, I):
    s_total = 2 * np.pi * R + 2 * L
    s_vals = np.linspace(0, s_total, N)
    obs = np.array([x - cx, y - cy, z - cz - coil_z])
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
    grid = data['grid']
    x_min, x_max = float(grid['x_min']) * 1e-2, float(grid['x_max']) * 1e-2
    y_min, y_max = float(grid['y_min']) * 1e-2, float(grid['y_max']) * 1e-2
    z_min, z_max = float(grid['z_min']) * 1e-2, float(grid['z_max']) * 1e-2
    x_res, y_res, z_res = int(grid['x_res']), int(grid['y_res']), int(grid['z_res'])

    X, Y, Z = np.meshgrid(
        np.linspace(x_min, x_max, x_res),
        np.linspace(y_min, y_max, y_res),
        np.linspace(z_min, z_max, z_res),
        indexing='ij'
    )

    points = np.vstack([X.ravel(), Y.ravel(), Z.ravel()]).T
    N_points = 100

    coil_paths = []
    unit_fields = {}  # Store 1A fields per coil

    for coil in data['coils']:
        if not coil['active']:
            continue

        cx, cy, cz = float(coil['cx']) * 1e-2, float(coil['cy']) * 1e-2, float(coil['cz']) * 1e-2
        R_inner = float(coil['R']) * 1e-2
        L_straight = float(coil['L']) * 1e-2
        height = float(coil['height']) * 1e-2
        num_layers = int(coil['num_layers'])
        num_turns = int(coil['num_turns'])
        wire_thick = float(coil['wire_thickness']) * 1e-3

        # WE FORCE CURRENT TO 1A FOR THE BASE CALCULATION
        current = 1.0
        coil_id = coil['id']

        radii = np.linspace(R_inner, R_inner + wire_thick * (num_layers - 1), num_layers)
        z_thickness = height / num_turns
        z_positions = np.arange(0, height, z_thickness)

        U_c, V_c, W_c = np.zeros_like(points[:, 0]), np.zeros_like(points[:, 1]), np.zeros_like(points[:, 2])

        for i, obs in enumerate(points):
            B_total = np.zeros(3)
            for z_pos in z_positions:
                for radius in radii:
                    B_total += B_racetrack_vectorized(obs[0], obs[1], obs[2], cx, cy, cz, z_pos, L_straight, radius,
                                                      N_points, current)
            U_c[i] += B_total[0]
            V_c[i] += B_total[1]
            W_c[i] += B_total[2]

        unit_fields[coil_id] = {
            'u': U_c.tolist(),
            'v': V_c.tolist(),
            'w': W_c.tolist()
        }

        # Generate paths for plotting
        all_x, all_y, all_z = [], [], []
        for i in range(num_layers):
            radius = radii[i]
            s_total = 2 * np.pi * radius + 2 * L_straight
            s_vals = np.linspace(0, s_total, 100)
            for j in range(num_turns):
                z_start = z_positions[j]
                z_vals = cz + z_start + (s_vals / s_total) * z_thickness
                path = np.array([racetrack_path(s, L_straight, radius) for s in s_vals])
                all_x.extend((path[:, 0] + cx).tolist())
                all_y.extend((path[:, 1] + cy).tolist())
                all_z.extend(z_vals.tolist())
            if i < num_layers - 1:
                next_radius = radii[i + 1]
                all_x.extend([(-L_straight / 2) + cx, (-L_straight / 2) + cx])
                all_y.extend([-next_radius + cy, -next_radius + cy])
                all_z.extend([cz + height, cz])

        coil_paths.append({'x': all_x, 'y': all_y, 'z': all_z, 'name': coil['name']})

    return jsonify({
        'grid': {
            'x': points[:, 0].tolist(),
            'y': points[:, 1].tolist(),
            'z': points[:, 2].tolist(),
        },
        'unit_fields': unit_fields,
        'coil_paths': coil_paths,
    })


if __name__ == '__main__':
    app.run(debug=True, port=5000)