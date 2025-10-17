"""
This script will compare many configurations and decrease current if voltage limit is exceeded
"""
import numpy as np
import plotly.express as px
import sympy as sp
import pandas as pd
from scipy.integrate import quad
import plotly.graph_objects as go
import plotly.io as pio
import scipy.optimize as optimize

pio.renderers.default = 'browser'
#Constants:
R = 8 * 1e-2 # the radius of the coil, assuming 90th percentile to be no bigger than 20 (overestimation)
mu0 = 4 * np.pi * 1e-7
wire_thickness = 3 * 1e-3

"""
I = 10 #current intensity in A
h = 20 * 1e-2 #~20cm, assuming 90th percentile to be no bigger than 18 (overestimation)

#finding thickness of litz wire:
num_layers = 4 #4 layers of coils
wire_thickness = 3 * 1e-3

#getting number of turns:
num_turns_per_layer = h/wire_thickness
num_turns = num_turns_per_layer * num_layers
print(f"Number of turns: {num_turns}")
"""
#Function that returns the integrand based on dimensions:
def get_integrand(radius, n_turns, height, I=1):
    phi, x, y, z = sp.symbols('phi,x,y,z')

    #recreate function of current path but in sympy to integrate:
    l = radius * sp.Matrix([sp.cos(phi), sp.sin(phi), (height/(radius * n_turns * 2 * np.pi))*phi])

    #distance away from path:
    r = sp.Matrix([x, y, z])

    #B(r) = ((mu0 * I)/(4piR)) * integral_along_curve\loop([(dl/dt x (r-l))/norm(r-l)^3)]dt
    #so we can simplify by defining r-l (vector of separation):
    difference = r-l
    #print(difference)

    #function to integrate (commented above):
    integrand = (mu0 * I / (4 * np.pi)) * sp.diff(l, phi).cross(difference)/ difference.norm()**3 #this will hold dB/dt for all 3 dimensions

    # need to lambdify all 3 functions into actual array representations of them:
    dBx = sp.lambdify([phi, x, y, z], integrand[0])
    dBy = sp.lambdify([phi, x, y, z], integrand[1])
    dBz = sp.lambdify([phi, x, y, z], integrand[2])

    return integrand, dBx, dBy, dBz

#function to get B from the integrand (integrate):
def B(xo, yo, zo, dBx, dBy, dBz, n_turns):
    return(np.array([
        quad(dBx, 0, n_turns * 2 * np.pi, args=(xo, yo, zo), limit=10000)[0],
        quad(dBy, 0, n_turns * 2 * np.pi, args=(xo, yo, zo), limit=10000)[0],
        quad(dBz, 0, n_turns * 2 * np.pi, args=(xo, yo, zo), limit=10000)[0],
    ]))

def get_inductance(radius, n_turns, height):
    mu_o = 4 * np.pi * 1e-7
    L = (np.pi * pow(n_turns,2) * pow(radius,2) * mu_o)/height
    return L
def get_eq_inductance(parallel, Li, Lj):
    if parallel:
        Leq = pow((1/Li)+(1/Lj), -1)
    else:
        Leq = Li + Lj
    return Leq

def get_impedance(frequency, Leq):
    z_mag = 2 *np.pi * frequency * Leq
    return z_mag

def get_voltage(impedance, current):
    V = impedance * current
    return V
"""
#Example usage of functions

integrands, dBx, dBy, dBz = get_integrand(R, num_turns, h, I=I)
print(dBz(2*np.pi, 1, 1,1 )) #prints the z component at the given location
#calculate B at the center (0, 0, 0)
B_center = B(0, 0, h/2, dBx, dBy, dBz, num_turns)
print(B_center)


print(get_inductance(0.0175, 196, 0.07)) #validation of formula
"""
#Start of Iterative Process:
nl_range = [0,4] #range for layers
irms = 30
freq_range = [20000, 40000]
height_range = [5, 11]
dps = 30

nl_values = range(nl_range[0]+1, nl_range[1]+1) #To get discrete values
height_values = np.linspace(height_range[0], height_range[1], 7)
freq_values = np.linspace(freq_range[0], freq_range[1], dps)

results = {
    "height": [],
    "n_turns" : [],
    "frequency" : [],
    "B" : [],
    "voltage": [],
    "L": [],
    "config": [],
    "I_total": []
}

I_set = 30 #Arms max
V_limit = 1500 #Vrms max --> if this is exceeded, I_set is decreased

for h in height_values:
    num_turns_per_layer = (h * 1e-2) / wire_thickness
    height = h * 1e-2  # convert to meters

    for nl in nl_values:
        L_single = get_inductance(R, num_turns_per_layer, height)  # inductance of one layer

        connection_cases = []
        hybrid_connection_cases = []

        # --- All series ---
        L_series = L_single * nl
        connection_cases.append(("series", L_series, nl, num_turns_per_layer))

        # --- All parallel ---
        if nl >= 2:
            L_parallel = L_single / nl
            connection_cases.append(("parallel", L_parallel, nl, num_turns_per_layer))

        # --- Combined (only if nl == 4) ---
        if nl == 4:
            # Two series pairs, then in parallel
            Leq = L_single  # (2*L) // (2*L) = L
            turns_per_branch = num_turns_per_layer * 2
            connection_cases.append(("combined (2 series || 2 series)", Leq, 2, turns_per_branch))

        #Looping through all configurations:

        for config_name, L_eq, num_groups, turns_used in connection_cases:
            for f in freq_values:

                # Impedance
                Xeq = get_impedance(f, L_eq)

                # Allowed current based on voltage limit
                i_total = min(I_set, V_limit / Xeq) #whichever gives a lower value...

                # Current per layer depending on config
                if config_name == "series":
                    i_layer = i_total
                elif config_name == "parallel":
                    i_layer = i_total / nl
                elif "combined" in config_name:
                    i_layer = i_total / 2  # 2 parallel branches

                # B-field for one "active winding"
                _, dBx, dBy, dBz = get_integrand(R, turns_used, height, I=i_layer)
                B_vec_layer = B(0, 0, height / 2, dBx, dBy, dBz, turns_used)
                B_vec_total = B_vec_layer * num_groups
                B_mag = np.linalg.norm(B_vec_total)

                # Actual voltage across the whole coil
                voltage = get_voltage(Xeq, i_total)

                # Save results
                results["n_turns"].append(turns_used * num_groups)
                results["B"].append(B_mag * 1e3)  # to mT
                results["L"].append(L_eq * 1e3)  # to mH
                results["frequency"].append(f)
                results["height"].append(h)  # in cm
                results["voltage"].append(voltage)
                results["config"].append(config_name)
                results["I_total"].append(i_total)

#hybrid configuration (3-series || 1)
for h in height_values:
    num_turns_per_layer = (h * 1e-2) / wire_thickness
    height = h * 1e-2

    for nl in nl_values:
        if nl != 4:
            continue  # hybrid config only for 4 layers

        L_single = get_inductance(R, num_turns_per_layer, height)

        # Define branches
        L_branch1 = 3 * L_single
        L_branch2 = L_single
        turns_first_branch = num_turns_per_layer * 3
        turns_second_branch = num_turns_per_layer

        # Equivalent inductance for voltage/impedance
        Leq = get_eq_inductance(parallel=True, Li=L_branch1, Lj=L_branch2)

        for f in freq_values:
            # Impedances:
            X1 = 2 * np.pi * f * L_branch1
            X2 = 2 * np.pi * f * L_branch2
            Xeq = get_impedance(f, Leq)

            I_total = min(I_set, V_limit / Xeq)

            I1 = I_total * X2 / (X1 + X2)
            I2 = I_total * X1 / (X1 + X2)

            #Compute B-field for each branch
            _, dBx1, dBy1, dBz1 = get_integrand(R, turns_first_branch, height, I=I1)
            B1 = B(0, 0, height/2, dBx1, dBy1, dBz1, turns_first_branch)

            _, dBx2, dBy2, dBz2 = get_integrand(R, turns_second_branch, height, I=I2)
            B2 = B(0, 0, height/2, dBx2, dBy2, dBz2, turns_second_branch)

            B_total = B1 + B2
            B_mag = np.linalg.norm(B_total) * 1e+3  # mT

            Xeq = get_impedance(f, Leq)
            voltage = get_voltage(Xeq, irms)

            results["n_turns"].append(turns_first_branch + turns_second_branch)
            results["B"].append(B_mag)
            results["L"].append(Leq * 1e3)  # mH
            results["frequency"].append(f)
            results["height"].append(h)
            results["voltage"].append(voltage)
            results["config"].append("3-series || 1")
            results["I_total"].append(I_total)

# Convert results dict into DataFrame
df = pd.DataFrame(results)

# Ensure numeric
numeric_cols = ["n_turns", "B", "L", "frequency", "height", "voltage", "I_total"]
for c in numeric_cols:
    df[c] = pd.to_numeric(df[c], errors="coerce")

# Applying constraints:
V_LIMIT = 1500.0   # V
B_MIN = 9.0# mT

df_valid = df[(df["voltage"] <= V_LIMIT) & (df["B"] >= B_MIN)]

print(f"Found {len(df_valid)} valid coil configurations.")

#Plots:
fig_freq = go.Figure(data=[go.Scatter3d(
    x=df_valid["frequency"],
    y=df_valid["voltage"],
    z=df_valid["B"],
    mode="markers",
    marker=dict(
        size=df_valid["n_turns"] / 10,  # scale size
        color=df_valid["config"].astype('category').cat.codes,
        colorscale="Viridis",
        colorbar=dict(title="Config Code"),
        opacity=0.8
    ),
    text=df_valid.apply(lambda row:
        f"Config: {row['config']}<br>"
        f"Frequency: {row['frequency']} Hz<br>"
        f"Voltage: {row['voltage']:.1f} V<br>"
        f"B-field: {row['B']:.2f} mT<br>"
        f"Inductance: {row['L']:.2f} mH<br>"
        f"Height: {row['height']} cm<br>"
        f"Turns: {row['n_turns']}<br>"
        f"Layers: {row['n_turns'] // ((row['height']*1e-2)//wire_thickness):.0f}<br>"
        f"Current: {row['I_total']:.2f} A"
    , axis=1)
)])
fig_freq.update_layout(
    scene=dict(
        xaxis_title="Frequency (Hz)",
        yaxis_title="Voltage (V RMS)",
        zaxis_title="B-field (mT)"
    ),
    title="Frequency vs Voltage vs B-field (Full Info)"
)
fig_freq.show()

fig_height = go.Figure(data=[go.Scatter3d(
    x=df_valid["height"],
    y=df_valid["n_turns"],
    z=df_valid["B"],
    mode="markers",
    marker=dict(
        size=6,
        color=df_valid["voltage"],
        colorscale="Plasma",
        colorbar=dict(title="Voltage (V)"),
        opacity=0.8
    ),
    text=df_valid.apply(lambda row:
        f"Config: {row['config']}<br>"
        f"Frequency: {row['frequency']} Hz<br>"
        f"Voltage: {row['voltage']:.1f} V<br>"
        f"B-field: {row['B']:.2f} mT<br>"
        f"Inductance: {row['L']:.2f} mH<br>"
        f"Height: {row['height']} cm<br>"
        f"Turns: {row['n_turns']}<br>"
        f"Layers: {row['n_turns'] // ((row['height']*1e-2)//wire_thickness):.0f}<br>"
        f"Current: {row['I_total']:.2f} A"
    , axis=1)
)])
fig_height.update_layout(
    scene=dict(
        xaxis_title="Height (cm)",
        yaxis_title="Number of Turns",
        zaxis_title="B-field (mT)"
    ),
    title="Height vs Number of Turns vs B-field (Voltage as Color, Full Info)"
)
fig_height.show()

fig_inductance = go.Figure(data=[go.Scatter3d(
    x=df_valid["L"],
    y=df_valid["frequency"],
    z=df_valid["B"],
    mode="markers",
    marker=dict(
        size=6,
        color=df_valid["voltage"],
        colorscale="Viridis",
        colorbar=dict(title="Voltage (V)"),
        opacity=0.8
    ),
    text=df_valid.apply(lambda row:
        f"Config: {row['config']}<br>"
        f"Frequency: {row['frequency']} Hz<br>"
        f"Voltage: {row['voltage']:.1f} V<br>"
        f"B-field: {row['B']:.2f} mT<br>"
        f"Inductance: {row['L']:.2f} mH<br>"
        f"Height: {row['height']} cm<br>"
        f"Turns: {row['n_turns']}<br>"
        f"Layers: {row['n_turns'] // ((row['height']*1e-2)//wire_thickness):.0f}<br>"
        f"Current: {row['I_total']:.2f} A"
    , axis=1)
)])
fig_inductance.update_layout(
    scene=dict(
        xaxis_title="Inductance (mH)",
        yaxis_title="Frequency (Hz)",
        zaxis_title="B-field (mT)"
    ),
    title="Inductance vs Frequency vs B-field (Voltage as Color, Full Info)"
)
fig_inductance.show()

"""
fig_freq.write_html("Frequency vs Voltage vs B-field (Full Info).html")
fig_inductance.write_html("Height vs Number of Turns vs B-field (Voltage as Color, Full Info).html")
fig_height.write_html("Inductance vs Frequency vs B-field (Voltage as Color, Full Info).html")
"""