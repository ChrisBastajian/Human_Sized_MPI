import numpy as np
import json
from collections import defaultdict
import plotly.graph_objects as go
import plotly.io as pio
from scipy.interpolate import RegularGridInterpolator
import itertools

pio.renderers.default = 'browser'

#currents:
i1, i2, i3, =1, 1, 0
alpha = i2/i1
beta = i3/i1

def read_json_data(fname='magnetic_field_data.json'):
    with open(fname, 'r') as f:
        data = json.load(f)

    P = defaultdict(list)  # will hold the unit fields
    grid = defaultdict(list) #will hold all positions of the grid

    for coil in data["unit_fields"]:
        for dim in data["unit_fields"][coil]:
            for dim_data in data["unit_fields"][coil][dim]:
                P[coil, dim].append(dim_data)

    #Getting the positional values (x,y,z):
    for dim in data["grid"]:
        for grid_data in data["grid"][dim]:
            grid[dim].append(grid_data)

    return grid, P

#Let's say that we want the FFL to be located at (any_pos, 0, 10cm) along x:
def get_B_field(Px, Py, Pz, i):
    Bx = i * Px
    By = i * Py
    Bz = i * Pz
    B_field = {
        "Bx": Bx,
        "By": By,
        "Bz": Bz,
    }
    return B_field

def get_total_B_field(P1x, P1y, P1z, P2x, P2y, P2z, P3x, P3y, P3z, i1, i2, i3):
    B1 = get_B_field(P1x, P1y, P1z, i1)
    B2 = get_B_field(P2x, P2y, P2z, i2)
    B3 = get_B_field(P3x, P3y, P3z, i3)

    Bx_total = B1["Bx"]+B2["Bx"]+B3["Bx"]
    By_total = B1["By"]+B2["By"]+B3["By"]
    Bz_total = B1["Bz"]+B2["Bz"]+B3["Bz"]

    B_total = {
        "Bx": Bx_total,
        "By": By_total,
        "Bz": Bz_total
    }
    return B_total

def get_B_from_P(P_dict, i1, i2, i3):
    P1x = np.array(P_dict["c1", "u"])
    P2x = np.array(P_dict["c2", "u"])
    P3x = np.array(P_dict["c3", "u"])

    P1y = np.array(P_dict["c1", "v"])
    P2y = np.array(P_dict["c2", "v"])
    P3y = np.array(P_dict["c3", "v"])

    P1z = np.array(P_dict["c1", "w"])
    P2z = np.array(P_dict["c2", "w"])
    P3z = np.array(P_dict["c3", "w"])
    return get_total_B_field(P1x, P1y, P1z, P2x, P2y, P2z, P3x, P3y, P3z, i1, i2, i3)

def get_B_mag(Bx, By, Bz):
    B_mag = []
    for n in range(len(Bx)):
        B_mag.append(np.sqrt(Bx[n]**2 + By[n]**2 + Bz[n]**2))
    return np.array(B_mag)

def get_P(P_dict):
    P1x, P2x, P3x = np.array(P_dict["c1", "u"]), np.array(P_dict["c2", "u"]), np.array(P_dict["c3", "u"])
    P1y, P2y, P3y = np.array(P_dict["c1", "v"]), np.array(P_dict["c2", "v"]), np.array(P_dict["c3", "v"])
    P1z, P2z, P3z = np.array(P_dict["c1", "w"]), np.array(P_dict["c2", "w"]), np.array(P_dict["c3", "w"])
    return P1x, P2x, P3x, P1y, P2y, P3y, P1z, P2z, P3z

def build_grid(x, y, z):
    """
        x, y, and z are numpy arrays. This function will reorder them in ascending order.
    """
    # The coordinates for each dimension (without repetition):
    x_coords = np.unique(x_array)
    y_coords = np.unique(y_array)
    z_coords = np.unique(z_array)

    ix = np.searchsorted(x_coords, x_array)
    iy = np.searchsorted(y_coords, y_array)
    iz = np.searchsorted(z_coords, z_array)
    return ix, iy, iz

def build_interpolator(flat_array, nx, ny, nz, ix, iy, iz):
    grid_3d = np.zeros((nx, ny, nz))
    grid_3d[ix, iy, iz] = flat_array
    return RegularGridInterpolator((np.unique(x_array), np.unique(y_array), np.unique(z_array)),
                                   grid_3d, method='linear', bounds_error=False, fill_value=None)

def get_current_ratios(Py1, Pz1, Py2, Pz2, Py3, Pz3):
    A = np.array([[Py2, Py3], [Pz2, Pz3]])
    B = np.array([-Py1, -Pz1])
    return np.linalg.solve(A, B)

def set_ffl_position(position):
    #Creating interpolators to get exact position:
    inter_P1y = build_interpolator(P1y, nx, ny, nz, ix, iy, iz)
    inter_P1z = build_interpolator(P1z, nx, ny, nz, ix, iy, iz)
    inter_P2y = build_interpolator(P2y, nx, ny, nz, ix, iy, iz)
    inter_P2z = build_interpolator(P2z, nx, ny, nz, ix, iy, iz)
    inter_P3y = build_interpolator(P3y, nx, ny, nz, ix, iy, iz)
    inter_P3z = build_interpolator(P3z, nx, ny, nz, ix, iy, iz)

    #Get the exact field vectors at that point by interpolating every direction:
    P1y_point = inter_P1y([position])[0]
    P2y_point = inter_P2y([position])[0]
    P3y_point = inter_P3y([position])[0]
    P1z_point = inter_P1z([position])[0]
    P2z_point = inter_P2z([position])[0]
    P3z_point = inter_P3z([position])[0]

    #Get the current ratios that would set that point to be a zero field:
    alpha, beta = get_current_ratios(P1y_point, P1z_point, P2y_point, P2z_point, P3y_point, P3z_point)

    #The current for each coil:
    i_c1 = 1
    i_c2 = alpha * i_c1
    i_c3 = beta * i_c1

    return i_c1, i_c2, i_c3

def get_interpolated_field(slice_points, Bx_inter, By_inter, Bz_inter, ny, nz):
    Bx = Bx_inter(slice_points)
    By = By_inter(slice_points)
    Bz = Bz_inter(slice_points)

    return get_B_mag(Bx, By, Bz).reshape((ny),(nz))


def maximize_currents(i1, i2, i3, max_amp=50.0):
    """
    Scales the currents so the maximum absolute current is exactly max_amp,
    preserving the ratios required to maintain the FFL position.
    """
    currents = np.array([i1, i2, i3])
    max_val = np.max(np.abs(currents))

    # Avoid division by zero if all currents are somehow 0
    if max_val == 0:
        return 0, 0, 0

    scale_factor = max_amp / max_val
    return tuple(currents * scale_factor)


def get_gradient_at_point(position, I1, I2, I3, unit_interps, d=1e-5):
    """
    Calculates the spatial gradient of the magnetic field magnitude at a specific point
    using a continuous central difference approach.
    'd' is the step size in meters (1e-5 = 10 microns).
    """
    x, y, z = position

    # Unpack the pre-built unit field interpolators
    P1x_int, P2x_int, P3x_int, P1y_int, P2y_int, P3y_int, P1z_int, P2z_int, P3z_int = unit_interps

    def get_mag_at(px, py, pz):
        pts = [[px, py, pz]]
        # Calculate Bx, By, Bz by multiplying the interpolated unit fields by the currents
        bx = I1 * P1x_int(pts)[0] + I2 * P2x_int(pts)[0] + I3 * P3x_int(pts)[0]
        by = I1 * P1y_int(pts)[0] + I2 * P2y_int(pts)[0] + I3 * P3y_int(pts)[0]
        bz = I1 * P1z_int(pts)[0] + I2 * P2z_int(pts)[0] + I3 * P3z_int(pts)[0]
        return np.sqrt(bx ** 2 + by ** 2 + bz ** 2)

    # Since the center point (FFL) is ideally 0, evaluating at +d and -d gives the absolute slopes
    # directly, matching your logic without needing to calculate a massive 2D slice first!
    B_y_plus = get_mag_at(x, y + d, z)
    B_y_minus = get_mag_at(x, y - d, z)

    B_z_plus = get_mag_at(x, y, z + d)
    B_z_minus = get_mag_at(x, y, z - d)

    # Absolute slope average in Y and Z
    avg_grad_y = (B_y_plus + B_y_minus) / (2.0 * d)
    avg_grad_z = (B_z_plus + B_z_minus) / (2.0 * d)

    # Final combined average gradient
    return (avg_grad_y + avg_grad_z) / 2.0

grid_vals, P_vals = read_json_data('magnetic_field_data.json')
P1x, P2x, P3x, P1y, P2y, P3y, P1z, P2z, P3z = get_P(P_vals)
B_total_vals = get_B_from_P(P_vals, i1, i2, i3)

x_array = np.array(grid_vals["x"])
y_array = np.array(grid_vals["y"])
z_array = np.array(grid_vals["z"])

#Reordering the arrays:
ix, iy, iz = build_grid(x_array, y_array, z_array)
nx, ny, nz = len(np.unique(ix)), len(np.unique(iy)), len(np.unique(iz))
print(nx, ny, nz)

#Building interpolators for field magnitude:
field_matrix = get_B_from_P(P_vals, i1, i2, i3) #don't care about ffl position here - just getting unit field

interp_Bx = build_interpolator(field_matrix["Bx"], nx, ny, nz, ix, iy, iz)
interp_By = build_interpolator(field_matrix["By"], nx, ny, nz, ix, iy, iz)
interp_Bz = build_interpolator(field_matrix["Bz"], nx, ny, nz, ix, iy, iz)

#Making a fine grid:
fine_y = np.linspace(y_array.min(), y_array.max(), 1000)
fine_z = np.linspace(0.8e-2, z_array.max(), 1000)

y_mesh, z_mesh = np.meshgrid(fine_y, fine_z)
x_mesh = np.zeros_like(y_mesh) #we are only looking at x = 0

slice_points = np.vstack([x_mesh.ravel(), y_mesh.ravel(), z_mesh.ravel()]).T

B_mag = get_interpolated_field(slice_points, interp_Bx, interp_By, interp_Bz, len(fine_y), len(fine_z))

#Figure:
fig = go.Figure(
    data=go.Heatmap(
        x=fine_y,
        y=fine_z,
        z=B_mag * 1e3,
        colorscale="viridis",
        zsmooth="best",
        colorbar=dict(
            title="B [mT]",
            tickmode="auto",
            outlinewidth=0
        )
    )
)

fig.show()

"""
Doing a Gradient map for setting FFL at a position with max gradient possible
"""
print("Building unit interpolators...")
inter_P1x = build_interpolator(P1x, nx, ny, nz, ix, iy, iz)
inter_P2x = build_interpolator(P2x, nx, ny, nz, ix, iy, iz)
inter_P3x = build_interpolator(P3x, nx, ny, nz, ix, iy, iz)

inter_P1y = build_interpolator(P1y, nx, ny, nz, ix, iy, iz)
inter_P2y = build_interpolator(P2y, nx, ny, nz, ix, iy, iz)
inter_P3y = build_interpolator(P3y, nx, ny, nz, ix, iy, iz)

inter_P1z = build_interpolator(P1z, nx, ny, nz, ix, iy, iz)
inter_P2z = build_interpolator(P2z, nx, ny, nz, ix, iy, iz)
inter_P3z = build_interpolator(P3z, nx, ny, nz, ix, iy, iz)

# Group them up so they are easy to pass to our gradient function
unit_interps = (
    inter_P1x, inter_P2x, inter_P3x,
    inter_P1y, inter_P2y, inter_P3y,
    inter_P1z, inter_P2z, inter_P3z
)

# ---------------------------------------------------------
# 2. RUN THE GRADIENT MAP
# ---------------------------------------------------------
#fine_y = np.linspace(-0.04, 0.04, 100)
#fine_z = np.linspace(0.8e-2, 0.018, 100)

gradient_map = np.zeros((len(fine_y), len(fine_z)))
gradient_results = []

for idx_j, j in enumerate(fine_y):
    for idx_k, k in enumerate(fine_z):
        target_position = (0, j, k)

        # 1. Get raw currents needed to place FFL here (using unit interpolators)
        P1y_pt = inter_P1y([target_position])[0]
        P2y_pt = inter_P2y([target_position])[0]
        P3y_pt = inter_P3y([target_position])[0]
        P1z_pt = inter_P1z([target_position])[0]
        P2z_pt = inter_P2z([target_position])[0]
        P3z_pt = inter_P3z([target_position])[0]

        alpha, beta = get_current_ratios(P1y_pt, P1z_pt, P2y_pt, P2z_pt, P3y_pt, P3z_pt)
        raw_I1, raw_I2, raw_I3 = 1.0, alpha, beta

        # 2. Maximize the currents to 50A
        I1, I2, I3 = maximize_currents(raw_I1, raw_I2, raw_I3, max_amp=50.0)

        # 3. Calculate the gradient dynamically at this point without building a massive grid
        grad = get_gradient_at_point(target_position, I1, I2, I3, unit_interps, d=1e-5)

        gradient_map[idx_j, idx_k] = grad

        gradient_results.append({
            "y": float(j),
            "z": float(k),
            "max_gradient": float(grad),
            "ratios":{
                "alpha":float(alpha),
                "beta":float(beta),
            },
            "currents":{
                "I1":float(I1),
                "I2":float(I2),
                "I3":float(I3)
            }
        })

with open("gradient_map.json", "w") as f:
    json.dump(gradient_results, f, indent=4)

#Figure for max gradient:
fig = go.Figure(
    data=go.Contour(
        x=fine_y,
        y=fine_z,
        z=gradient_map.T,
        colorscale="viridis",
        ncontours=50,
        colorbar=dict(
            title="G [T/m]",
            tickmode="auto",
            outlinewidth=0
        )
    )
)

fig.show()

fig = go.Figure(
    data=go.Surface(
        x=fine_y,
        y=fine_z,
        z=gradient_map.T, # Height is the gradient strength
        colorscale="inferno",
        colorbar=dict(title="Gradient [T/m]")
    )
)

fig.update_layout(
    title="3D Topography of FFL Gradient Capability",
    scene=dict(
        xaxis_title="Y Position (m)",
        yaxis_title="Z Position (m)",
        zaxis_title="Gradient Strength (T/m)"
    )
)
fig.show()

# Create a mask where gradient is strong enough to be "usable"
target_gradient = 1
usable_fov = np.where(gradient_map >= target_gradient, gradient_map, np.nan)

fig = go.Figure(
    data=go.Heatmap(
        x=fine_y,
        y=fine_z,
        z=usable_fov.T,
        colorscale="greens", # Use a distinct color for the usable zone
        zsmooth=False,       # Turn off smoothing for hard boundaries
        colorbar=dict(title="Usable Gradient [T/m]")
    )
)

fig.update_layout(
    title=f"Usable Field of View (Threshold: >{target_gradient} T/m)",
    plot_bgcolor='lightgray' # Areas below threshold will appear gray
)
fig.show()