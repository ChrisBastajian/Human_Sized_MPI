import numpy as np
import json
from collections import defaultdict
from scipy.interpolate import RegularGridInterpolator
import matplotlib.pyplot as plt
from scipy.optimize import minimize
# =========================================================
# CONFIGURATION
# =========================================================

MAX_CURRENT = 1.0


# =========================================================
# READ JSON DATA
# =========================================================

def read_json_data(fname='magnetic_field_data.json'):
    with open(fname, 'r') as f:
        data = json.load(f)

    P = defaultdict(list)
    grid = defaultdict(list)

    for coil in data["unit_fields"]:
        for dim in data["unit_fields"][coil]:
            for dim_data in data["unit_fields"][coil][dim]:
                P[coil, dim].append(dim_data)

    for dim in data["grid"]:
        for grid_data in data["grid"][dim]:
            grid[dim].append(grid_data)

    return grid, P


# =========================================================
# MAGNETIC FIELD FUNCTIONS
# =========================================================

def get_B_field(Px, Py, Pz, i):
    return {"Bx": i * Px, "By": i * Py, "Bz": i * Pz}


def get_total_B_field(P1x, P1y, P1z, P2x, P2y, P2z, P3x, P3y, P3z, i1, i2, i3):
    B1 = get_B_field(P1x, P1y, P1z, i1)
    B2 = get_B_field(P2x, P2y, P2z, i2)
    B3 = get_B_field(P3x, P3y, P3z, i3)

    return {
        "Bx": B1["Bx"] + B2["Bx"] + B3["Bx"],
        "By": B1["By"] + B2["By"] + B3["By"],
        "Bz": B1["Bz"] + B2["Bz"] + B3["Bz"]
    }


def get_B_from_P(P_dict, i1, i2, i3):
    P1x, P2x, P3x = np.array(P_dict["c1", "u"]), np.array(P_dict["c2", "u"]), np.array(P_dict["c3", "u"])
    P1y, P2y, P3y = np.array(P_dict["c1", "v"]), np.array(P_dict["c2", "v"]), np.array(P_dict["c3", "v"])
    P1z, P2z, P3z = np.array(P_dict["c1", "w"]), np.array(P_dict["c2", "w"]), np.array(P_dict["c3", "w"])

    return get_total_B_field(P1x, P1y, P1z, P2x, P2y, P2z, P3x, P3y, P3z, i1, i2, i3)


def get_P(P_dict):
    P1x, P2x, P3x = np.array(P_dict["c1", "u"]), np.array(P_dict["c2", "u"]), np.array(P_dict["c3", "u"])
    P1y, P2y, P3y = np.array(P_dict["c1", "v"]), np.array(P_dict["c2", "v"]), np.array(P_dict["c3", "v"])
    P1z, P2z, P3z = np.array(P_dict["c1", "w"]), np.array(P_dict["c2", "w"]), np.array(P_dict["c3", "w"])

    return P1x, P2x, P3x, P1y, P2y, P3y, P1z, P2z, P3z


# =========================================================
# GRID / INTERPOLATION
# =========================================================

def build_grid(x, y, z):
    x_coords = np.unique(x)
    y_coords = np.unique(y)
    z_coords = np.unique(z)

    ix = np.searchsorted(x_coords, x)
    iy = np.searchsorted(y_coords, y)
    iz = np.searchsorted(z_coords, z)

    return ix, iy, iz


def build_interpolator(flat_array, nx, ny, nz, ix, iy, iz):
    grid_3d = np.zeros((nx, ny, nz))
    grid_3d[ix, iy, iz] = flat_array

    return RegularGridInterpolator(
        (np.unique(x_array), np.unique(y_array), np.unique(z_array)),
        grid_3d,
        method='linear',
        bounds_error=False,
        fill_value=None
    )


# =========================================================
# CURRENT RATIO SOLUTION
# =========================================================

def get_current_ratios(Px1, Pz1, Px2, Pz2, Px3, Pz3):
    A = np.array([[Px2, Px3], [Pz2, Pz3]])
    B = np.array([-Px1, -Pz1])
    return np.linalg.solve(A, B)


# =========================================================
# CURRENT NORMALIZATION
# =========================================================

def normalize_currents(alpha, beta, max_current=MAX_CURRENT):
    raw_currents = np.array([1.0, alpha, beta], dtype=float)
    max_magnitude = np.max(np.abs(raw_currents))

    if not np.isfinite(max_magnitude):
        raise ValueError("Current ratio solution contains NaN or infinity.")

    if max_magnitude < 1e-15:
        raise ValueError("Current ratio solution has zero magnitude.")

    return tuple(raw_currents * (max_current / max_magnitude))


# =========================================================
# GRADIENT CALCULATION
# =========================================================

def get_gradients_at_point(position, I1, I2, I3, unit_interps, d=1e-5):
    x, y, z = position
    P1x_int, P2x_int, P3x_int, P1y_int, P2y_int, P3y_int, P1z_int, P2z_int, P3z_int = unit_interps

    def get_mag_at(px, py, pz):
        pts = [[px, py, pz]]

        bx = I1 * P1x_int(pts)[0] + I2 * P2x_int(pts)[0] + I3 * P3x_int(pts)[0]
        by = I1 * P1y_int(pts)[0] + I2 * P2y_int(pts)[0] + I3 * P3y_int(pts)[0]
        bz = I1 * P1z_int(pts)[0] + I2 * P2z_int(pts)[0] + I3 * P3z_int(pts)[0]

        return np.sqrt(bx**2 + by**2 + bz**2)

    B_x_plus = get_mag_at(x + d, y, z)
    B_x_minus = get_mag_at(x - d, y, z)
    B_z_plus = get_mag_at(x, y, z + d)
    B_z_minus = get_mag_at(x, y, z - d)

    avg_grad_x = (B_x_plus + B_x_minus) / (2.0 * d)
    avg_grad_z = (B_z_plus + B_z_minus) / (2.0 * d)

    return avg_grad_x, avg_grad_z


# =========================================================
# VISUALIZATION
# =========================================================

def plot_xz_heatmap(I1, I2, I3, unit_interps, y_val=0.0, x_range=(-0.07, 0.07), z_range=(-0.07, 0.07), resolution=100,
                    ffl_point=None):
    print(f"\nGenerating heatmap for I1={I1}A, I2={I2}A, I3={I3}A at y={y_val}m...")

    P1x_int, P2x_int, P3x_int, P1y_int, P2y_int, P3y_int, P1z_int, P2z_int, P3z_int = unit_interps

    x_vals = np.linspace(x_range[0], x_range[1], resolution)
    z_vals = np.linspace(z_range[0], z_range[1], resolution)
    X, Z = np.meshgrid(x_vals, z_vals)
    Y = np.full_like(X, y_val)

    pts = np.vstack([X.ravel(), Y.ravel(), Z.ravel()]).T

    bx = I1 * P1x_int(pts) + I2 * P2x_int(pts) + I3 * P3x_int(pts)
    by = I1 * P1y_int(pts) + I2 * P2y_int(pts) + I3 * P3y_int(pts)
    bz = I1 * P1z_int(pts) + I2 * P2z_int(pts) + I3 * P3z_int(pts)

    b_mag = np.sqrt(bx ** 2 + by ** 2 + bz ** 2)
    b_mag_2d = b_mag.reshape(resolution, resolution)

    plt.figure(figsize=(8, 6))
    extent = [x_range[0] * 100, x_range[1] * 100, z_range[0] * 100, z_range[1] * 100]

    im = plt.imshow(b_mag_2d * 1000, extent=extent, origin='lower', cmap='viridis', aspect='auto')

    cbar = plt.colorbar(im)
    cbar.set_label('Magnetic Field Magnitude |B| (mT)', fontsize=12)

    # Plot the FFL marker if provided
    if ffl_point is not None:
        ffl_x, ffl_z, min_b = ffl_point
        plt.plot(ffl_x * 100, ffl_z * 100, 'r*', markersize=12,
                 label=f'FFL ({ffl_x * 100:.2f} cm, {ffl_z * 100:.2f} cm)\nMin |B|: {min_b * 1000:.3f} mT')
        plt.legend(loc='upper right')

    plt.xlabel('X position (cm)', fontsize=12)
    plt.ylabel('Z position (cm)', fontsize=12)
    plt.title(f'Magnetic Field in XZ Plane (y = {y_val * 100} cm)\n$I_1={I1}$ A,  $I_2={I2}$ A,  $I_3={I3}$ A',
              fontsize=14)

    plt.tight_layout()
    plt.show()

def plot_xz_contourmap(
    I1, I2, I3, unit_interps,
    y_val=0.0,
    x_range=(-0.07, 0.07),
    z_range=(-0.07, 0.07),
    resolution=100,
    ffl_point=None,
    levels=50
):
    print(
        f"\nGenerating Contourmap for "
        f"I1={I1}A, I2={I2}A, I3={I3}A at y={y_val}m..."
    )

    P1x_int, P2x_int, P3x_int, \
    P1y_int, P2y_int, P3y_int, \
    P1z_int, P2z_int, P3z_int = unit_interps

    x_vals = np.linspace(x_range[0], x_range[1], resolution)
    z_vals = np.linspace(z_range[0], z_range[1], resolution)

    X, Z = np.meshgrid(x_vals, z_vals)
    Y = np.full_like(X, y_val)

    pts = np.vstack([
        X.ravel(),
        Y.ravel(),
        Z.ravel()
    ]).T

    bx = I1 * P1x_int(pts) + I2 * P2x_int(pts) + I3 * P3x_int(pts)
    by = I1 * P1y_int(pts) + I2 * P2y_int(pts) + I3 * P3y_int(pts)
    bz = I1 * P1z_int(pts) + I2 * P2z_int(pts) + I3 * P3z_int(pts)

    b_mag = np.sqrt(bx**2 + by**2 + bz**2)
    b_mag_2d = b_mag.reshape(resolution, resolution) * 1000  # mT

    X_cm = X * 100
    Z_cm = Z * 100

    plt.figure(figsize=(8, 6))

    # Filled contour map
    contour = plt.contourf(
        X_cm,
        Z_cm,
        b_mag_2d,
        levels=levels,
        cmap='viridis'
    )

    # Contour lines
    lines = plt.contour(
        X_cm,
        Z_cm,
        b_mag_2d,
        levels=levels,
        colors='k',
        linewidths=0.8,
        alpha=0.35
    )

    cbar = plt.colorbar(contour)
    cbar.set_label(
        'Magnetic Field Magnitude |B| (mT)',
        fontsize=12
    )

    # Plot the FFL marker if provided
    if ffl_point is not None:
        ffl_x, ffl_z, min_b = ffl_point

        plt.plot(
            ffl_x * 100,
            ffl_z * 100,
            'r*',
            markersize=12,
            label=(
                f'FFL ({ffl_x * 100:.2f} cm, '
                f'{ffl_z * 100:.2f} cm)\n'
                f'Min |B|: {min_b * 1000:.3f} mT'
            )
        )

        plt.legend(loc='upper right')

    plt.xlabel('X position (cm)', fontsize=12)
    plt.ylabel('Z position (cm)', fontsize=12)

    plt.title(
        f'Magnetic Field in XZ Plane (y = {y_val * 100:.2f} cm)\n'
        f'$I_1={I1}$ A,  $I_2={I2}$ A,  $I_3={I3}$ A',
        fontsize=14
    )

    plt.tight_layout()
    plt.show()

# =========================================================
# FFL (FIELD-FREE LINE) SOLVER
# =========================================================

def find_ffl_position(
    I1, I2, I3,
    unit_interps,
    y_val=0.0,
    x_bounds=(-0.07, 0.07),
    z_bounds=(-0.07, 0.07),
    coarse_resolution=200,
    method='Nelder-Mead'
):
    P1x_int, P2x_int, P3x_int, \
    P1y_int, P2y_int, P3y_int, \
    P1z_int, P2z_int, P3z_int = unit_interps

    def get_b_squared(xz):
        x, z = xz

        pts = np.array([[x, y_val, z]])

        bx = (
            I1 * P1x_int(pts)[0] +
            I2 * P2x_int(pts)[0] +
            I3 * P3x_int(pts)[0]
        )

        by = (
            I1 * P1y_int(pts)[0] +
            I2 * P2y_int(pts)[0] +
            I3 * P3y_int(pts)[0]
        )

        bz = (
            I1 * P1z_int(pts)[0] +
            I2 * P2z_int(pts)[0] +
            I3 * P3z_int(pts)[0]
        )

        return bx**2 + by**2 + bz**2

    # ---------------------------------------------------------
    # Step 1: Dense coarse search
    # ---------------------------------------------------------

    xs = np.linspace(
        x_bounds[0],
        x_bounds[1],
        coarse_resolution
    )

    zs = np.linspace(
        z_bounds[0],
        z_bounds[1],
        coarse_resolution
    )

    X, Z = np.meshgrid(xs, zs)

    pts = np.column_stack([
        X.ravel(),
        np.full(X.size, y_val),
        Z.ravel()
    ])

    bx = (
        I1 * P1x_int(pts) +
        I2 * P2x_int(pts) +
        I3 * P3x_int(pts)
    )

    by = (
        I1 * P1y_int(pts) +
        I2 * P2y_int(pts) +
        I3 * P3y_int(pts)
    )

    bz = (
        I1 * P1z_int(pts) +
        I2 * P2z_int(pts) +
        I3 * P3z_int(pts)
    )

    mags_sq = bx**2 + by**2 + bz**2

    min_idx = np.argmin(mags_sq)

    guess_x = pts[min_idx, 0]
    guess_z = pts[min_idx, 2]

    print(
        f"Coarse FFL estimate: "
        f"x={guess_x*100:.5f} cm, "
        f"z={guess_z*100:.5f} cm"
    )

    # ---------------------------------------------------------
    # Step 2: Local optimization
    # ---------------------------------------------------------

    res = minimize(
        get_b_squared,
        x0=[guess_x, guess_z],
        method=method,
        bounds=[
            x_bounds,
            z_bounds
        ],
        options={
            'xatol': 1e-12,
            'fatol': 1e-18,
            'maxiter': 5000
        }
    )

    ffl_x, ffl_z = res.x
    min_b_mag = np.sqrt(res.fun)

    print(
        f"Optimized FFL: "
        f"x={ffl_x*100:.6f} cm, "
        f"z={ffl_z*100:.6f} cm"
    )

    print(
        f"Minimum |B| = {min_b_mag*1000:.9f} mT"
    )

    print(f"Optimization success: {res.success}")
    print(f"Message: {res.message}")

    return ffl_x, ffl_z, min_b_mag

# =========================================================
# INITIALIZATION
# =========================================================

grid_vals, P_vals = read_json_data('magnetic_field_data(3).json')
P1x, P2x, P3x, P1y, P2y, P3y, P1z, P2z, P3z = get_P(P_vals)

x_array = np.array(grid_vals["x"])
y_array = np.array(grid_vals["y"])
z_array = np.array(grid_vals["z"])


# =========================================================
# BUILD GRID
# =========================================================

ix, iy, iz = build_grid(x_array, y_array, z_array)
nx, ny, nz = len(np.unique(ix)), len(np.unique(iy)), len(np.unique(iz))

print("Grid:")
print(f"  X points: {nx}")
print(f"  Y points: {ny}")
print(f"  Z points: {nz}")
print(f"  Total points: {len(x_array)}")

print("\nCoordinate ranges:")
print(f"  X: {x_array.min():.6g} to {x_array.max():.6g} m")
print(f"  Y: {y_array.min():.6g} to {y_array.max():.6g} m")
print(f"  Z: {z_array.min():.6g} to {z_array.max():.6g} m")

print("\nBuilding unit interpolators...")


# =========================================================
# BUILD UNIT FIELD INTERPOLATORS
# =========================================================

inter_P1x = build_interpolator(P1x, nx, ny, nz, ix, iy, iz)
inter_P2x = build_interpolator(P2x, nx, ny, nz, ix, iy, iz)
inter_P3x = build_interpolator(P3x, nx, ny, nz, ix, iy, iz)

inter_P1y = build_interpolator(P1y, nx, ny, nz, ix, iy, iz)
inter_P2y = build_interpolator(P2y, nx, ny, nz, ix, iy, iz)
inter_P3y = build_interpolator(P3y, nx, ny, nz, ix, iy, iz)

inter_P1z = build_interpolator(P1z, nx, ny, nz, ix, iy, iz)
inter_P2z = build_interpolator(P2z, nx, ny, nz, ix, iy, iz)
inter_P3z = build_interpolator(P3z, nx, ny, nz, ix, iy, iz)

unit_interps = (
    inter_P1x, inter_P2x, inter_P3x,
    inter_P1y, inter_P2y, inter_P3y,
    inter_P1z, inter_P2z, inter_P3z
)


# =========================================================
# POINT CURRENT SOLVER
# =========================================================

def get_point_currents(x, y, z, max_current=MAX_CURRENT):
    target_pos = [x, y, z]

    P1x_pt = inter_P1x([target_pos])[0]
    P2x_pt = inter_P2x([target_pos])[0]
    P3x_pt = inter_P3x([target_pos])[0]

    P1z_pt = inter_P1z([target_pos])[0]
    P2z_pt = inter_P2z([target_pos])[0]
    P3z_pt = inter_P3z([target_pos])[0]

    alpha_val, beta_val = get_current_ratios(P1x_pt, P1z_pt, P2x_pt, P2z_pt, P3x_pt, P3z_pt)

    return normalize_currents(alpha_val, beta_val, max_current)


# =========================================================
# PUBLIC GRADIENT FUNCTIONS
# =========================================================

def dbdx(x, y, z):
    I1, I2, I3 = get_point_currents(x, y, z)
    grad_x, _ = get_gradients_at_point((x, y, z), I1, I2, I3, unit_interps)
    return grad_x


def dbdz(x, y, z):
    #I1, I2, I3 = get_point_currents(x, y, z)
    _, grad_z = get_gradients_at_point((x, y, z), I1, I2, I3, unit_interps)
    return grad_z


# =========================================================
# EXAMPLE / TEST
# =========================================================

if __name__ == '__main__':
    #finding the FFL first at the equal currents position:
    manual_I1 = 1.0
    manual_I2 = 1.0
    manual_I3 = 0

    # Define the bounds for your plot (in meters) based on your grid size
    x_bounds = (x_array.min(), x_array.max())
    z_bounds = (z_array.min(), z_array.max())

    ffl_x, ffl_z, min_mag = find_ffl_position(
        manual_I1, manual_I2, manual_I3,
        unit_interps,
        y_val=0.0,
        x_bounds=x_bounds,
        z_bounds=z_bounds,
        coarse_resolution=300
    )
    print(f"FFL is located at: {ffl_x, ffl_z}")

    # Generate the plot
    plot_xz_contourmap(
        I1=manual_I1,
        I2=manual_I2,
        I3=manual_I3,
        unit_interps=unit_interps,
        y_val=0.0,  # Y plane to slice through
        x_range=x_bounds,
        z_range=z_bounds,
        resolution=1500# Increase for a smoother image, decrease for faster rendering
        #ffl_point=(ffl_x,ffl_z, min_mag)
    )
    # x_vals = np.linspace(-7e-2, 7e-2, 15)
    x_vals = [ffl_x]
    y_test = 0
    z_test = ffl_z

    print(f"\nMaximum current magnitude = {MAX_CURRENT:.3f} A\n")
    print(
        f"{'X (cm)':<10} | {'I1 (A)':<12} | {'I2 (A)':<12} | {'I3 (A)':<12} | {'dB/dx (mT/m)':<17} | {'dB/dz (mT/m)':<17}")
    print("-" * 95)

    for x in x_vals:
        I1, I2, I3 = get_point_currents(x, y_test, z_test)
        grad_x, grad_z = get_gradients_at_point((x, y_test, z_test), I1, I2, I3, unit_interps)

        print(
            f"{x * 100:<10.1f} | {I1:<12.6f} | {I2:<12.6f} | {I3:<12.6f} | {grad_x * 1e3:<17.6f} | {grad_z * 1e3:<17.6f}")

