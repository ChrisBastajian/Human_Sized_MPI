from flask import Flask, render_template, request, jsonify
import numpy as np
import itertools
import copy
import os
import json

app = Flask(__name__)


# --- Vectorized Biot-Savart Core Math ---
def racetrack_path(s, L, R):
    # Flipped logic: Coils now align along Y instead of X
    if s < L:
        # Segment 1: Right straight (going up along +Y)
        return np.array([R, (-L / 2) + s, 0])
    elif s < L + np.pi * R:
        # Segment 2: Top semicircle
        theta = (s - L) / R
        return np.array([R * np.cos(theta), (L / 2) + R * np.sin(theta), 0])
    elif s < 2 * L + np.pi * R:
        # Segment 3: Left straight (going down along -Y)
        return np.array([-R, (L / 2) - (s - (L + np.pi * R)), 0])
    else:
        # Segment 4: Bottom semicircle
        theta = (s - (2 * L + np.pi * R)) / R
        return np.array([R * np.cos(theta + np.pi), (-L / 2) + R * np.sin(theta + np.pi), 0])


def racetrack_dpath(s, L, R):
    # Flipped logic derivatives for Y-aligned coils
    if s < L:
        return np.array([0, 1, 0])
    elif s < L + np.pi * R:
        theta = (s - L) / R
        return np.array([-np.sin(theta), np.cos(theta), 0])
    elif s < 2 * L + np.pi * R:
        return np.array([0, -1, 0])
    else:
        theta = (s - (2 * L + np.pi * R)) / R
        return np.array([-np.sin(theta + np.pi), np.cos(theta + np.pi), 0])


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


def compute_fields(coils_data, grid_data):
    """
    Centralized function to compute B-fields based on grid and coil payload.
    """
    x_min, x_max = float(grid_data['x_min']) * 1e-2, float(grid_data['x_max']) * 1e-2
    y_min, y_max = float(grid_data['y_min']) * 1e-2, float(grid_data['y_max']) * 1e-2
    z_min, z_max = float(grid_data['z_min']) * 1e-2, float(grid_data['z_max']) * 1e-2
    x_res, y_res, z_res = int(grid_data['x_res']), int(grid_data['y_res']), int(grid_data['z_res'])

    X, Y, Z = np.meshgrid(
        np.linspace(x_min, x_max, x_res),
        np.linspace(y_min, y_max, y_res),
        np.linspace(z_min, z_max, z_res),
        indexing='ij'
    )

    points = np.vstack([X.ravel(), Y.ravel(), Z.ravel()]).T
    N_points = 100

    coil_paths = []
    unit_fields = {}

    for coil in coils_data:
        if not coil['active']:
            continue

        cx, cy, cz = float(coil['cx']) * 1e-2, float(coil['cy']) * 1e-2, float(coil['cz']) * 1e-2
        R_inner = float(coil['R']) * 1e-2
        L_straight = float(coil['L']) * 1e-2
        height = float(coil['height']) * 1e-2
        num_layers = int(coil['num_layers'])
        num_turns = int(coil['num_turns'])
        wire_thick = float(coil['wire_thickness']) * 1e-3

        current = 1.0
        coil_id = coil['id']

        # Swapped Logic: num_turns determines outward radial extensions.
        if num_turns > 1:
            radii = np.linspace(R_inner, R_inner + wire_thick * (num_turns - 1), num_turns)
        else:
            radii = np.array([R_inner])

        # Swapped Logic: num_layers determines the vertical pancake stacks.
        if num_layers > 1:
            z_positions = np.linspace(0, height, num_layers)
        else:
            z_positions = np.array([0.0])

        U_c, V_c, W_c = np.zeros_like(points[:, 0]), np.zeros_like(points[:, 1]), np.zeros_like(points[:, 2])

        # B-field calculation (Core math undisturbed)
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

        # Generate paths for plotting (Updated to reflect pancake layer logic)
        all_x, all_y, all_z = [], [], []
        for i in range(num_layers):  # Iterate through each pancake slice (Z-stack)
            z_start = z_positions[i]
            for j in range(num_turns):  # Iterate through turns (Radial extension)
                radius = radii[j]
                s_total = 2 * np.pi * radius + 2 * L_straight
                s_vals = np.linspace(0, s_total, 100)

                # Flat loops for standard pancake stacking
                z_vals = cz + z_start + np.zeros_like(s_vals)
                path = np.array([racetrack_path(s, L_straight, radius) for s in s_vals])

                all_x.extend((path[:, 0] + cx).tolist())
                all_y.extend((path[:, 1] + cy).tolist())
                all_z.extend(z_vals.tolist())

                # Connect to next outward turn in the same pancake layer
                if j < num_turns - 1:
                    next_radius = radii[j + 1]
                    all_x.extend([radius + cx, next_radius + cx])
                    all_y.extend([(-L_straight / 2) + cy, (-L_straight / 2) + cy])
                    all_z.extend([cz + z_start, cz + z_start])

            # Connect to next vertical pancake layer
            if i < num_layers - 1:
                next_z = z_positions[i + 1]
                all_x.extend([radii[-1] + cx, radii[0] + cx])
                all_y.extend([(-L_straight / 2) + cy, (-L_straight / 2) + cy])
                all_z.extend([cz + z_start, cz + next_z])

        coil_paths.append({'x': all_x, 'y': all_y, 'z': all_z, 'name': coil['name']})

    grid_output = {
        'x': points[:, 0].tolist(),
        'y': points[:, 1].tolist(),
        'z': points[:, 2].tolist(),
    }

    return grid_output, unit_fields, coil_paths


# --- HELPER: Apply Link Sync ---
def sync_coils_if_linked(coils_data, is_linked):
    """
    Forces Coil 2 to have identical structural dimensions to Coil 1,
    while leaving spatial coordinates (cx, cy, cz) independent.
    """
    if not is_linked:
        return coils_data

    c1 = next((c for c in coils_data if c['id'] == 'c1'), None)
    c2 = next((c for c in coils_data if c['id'] == 'c2'), None)

    if c1 and c2:
        sync_attrs = ['R', 'L', 'height', 'num_layers', 'num_turns', 'wire_thickness']
        for attr in sync_attrs:
            c2[attr] = c1[attr]

    return coils_data


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/calculate', methods=['POST'])
def calculate():
    data = request.json
    coils = sync_coils_if_linked(data['coils'], data.get('link_c1_c2', False))
    grid_res, unit_fields, coil_paths = compute_fields(coils, data['grid'])

    return jsonify({
        'grid': grid_res,
        'unit_fields': unit_fields,
        'coil_paths': coil_paths,
    })


@app.route('/api/batch_calculate', methods=['POST'])
def batch_calculate():
    data = request.json
    base_coils = data['coils']
    grid = data['grid']
    sweeps = data['sweeps']
    output_dir = data.get('output_dir', './sweep_results')
    is_linked = data.get('link_c1_c2', False)

    try:
        os.makedirs(output_dir, exist_ok=True)
    except Exception as e:
        return jsonify({'error': f'Failed to create output directory: {str(e)}'}), 400

    # 1. Dynamically build the parameter ranges
    param_ranges = []
    param_keys = []
    for sw in sweeps:
        vals = np.linspace(float(sw['min']), float(sw['max']), int(sw['steps']))

        # Enforce integers for turn and layer counts
        if sw['param'] in ['num_layers', 'num_turns']:
            vals = np.unique(np.round(vals).astype(int))

        param_ranges.append(vals)
        param_keys.append((sw['coil_id'], sw['param']))

    combinations = list(itertools.product(*param_ranges))

    # Static grid processing for base file
    base_grid_res, _, _ = compute_fields(base_coils, grid)

    files_created = 0

    # 2. Iterate through every combination
    for combo_idx, combo in enumerate(combinations):
        current_coils = copy.deepcopy(base_coils)
        combo_params_record = {}

        for idx, val in enumerate(combo):
            c_id, p_name = param_keys[idx]
            val = float(val) if isinstance(val, (np.floating, float)) else int(val)
            combo_params_record[f"{c_id}_{p_name}"] = val

            for c in current_coils:
                if c['id'] == c_id:
                    c[p_name] = val

        # 3. CRITICAL: If linked, force C2 to match C1's post-sweep dimensions
        current_coils = sync_coils_if_linked(current_coils, is_linked)

        # Update the JSON record to reflect the forced sync, so files are accurate
        if is_linked:
            c1 = next((c for c in current_coils if c['id'] == 'c1'), None)
            if c1:
                sync_attrs = ['R', 'L', 'height', 'num_layers', 'num_turns', 'wire_thickness']
                for attr in sync_attrs:
                    combo_params_record[f"c2_{attr}"] = c1[attr]

        # Log active states for accurate contextual JSON analysis
        for c in current_coils:
            combo_params_record[f"{c['id']}_active"] = c['active']

        # 4. Compute the field for this combination
        _, unit_fields, _ = compute_fields(current_coils, grid)

        # 5. Construct the complete payload for this individual file
        file_payload = {
            'run_id': combo_idx + 1,
            'swept_parameters': combo_params_record,
            'all_coil_configs': current_coils,
            'grid': base_grid_res,
            'unit_fields': unit_fields
        }

        # 6. Save the individual file to disk
        filename = f"run_{combo_idx + 1:05d}.json"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, 'w') as f:
            json.dump(file_payload, f, indent=4)

        files_created += 1

    return jsonify({
        'status': 'success',
        'files_created': files_created,
        'output_dir': os.path.abspath(output_dir)
    })


if __name__ == '__main__':
    app.run(debug=True, port=5000)