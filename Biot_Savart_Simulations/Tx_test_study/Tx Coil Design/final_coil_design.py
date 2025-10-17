"""
This script will simulate all the ranges for the specific coil design that we agreed on.
"""
import numpy as np
import plotly.express as px
import sympy as sp
import pandas as pd
from scipy.integrate import quad
import plotly.graph_objects as go
import plotly.io as pio
import matplotlib.pyplot as plt
import scipy.optimize as optimize

pio.renderers.default = 'browser'
#Constants:
R = 8 * 1e-2 # the radius of the coil, assuming 90th percentile to be no bigger than 20 (overestimation)
mu0 = 4 * np.pi * 1e-7
wire_thickness = 3 * 1e-3
H = 11 * 1e-2 #11 cm based on efficient_comparison.py
nl = 4 #4 layers based on efficient_comparison.py

num_turns_per_layer = H/wire_thickness

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
def get_integrand(radius, n_turns, height, I=1.0):
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
freq_range = [5000, 40000]
z_range = [H/2, H+10*1e-2] #from the center of the coil to 10 cm above the coil
dps = 100

freq_values = np.linspace(freq_range[0], freq_range[1], dps*2)
z_values = np.linspace(z_range[0], z_range[1], dps)

results = {
    "frequency" : [],
    "B" : [],
    "voltage": [],
    "I_total": [],
    "loc_z":[]
}

I_set = 30 #Arms max
V_limit = 1500 #Vrms max --> if this is exceeded, I_set is decreased

#Getting inductances:
L1 = get_inductance(radius=R, n_turns=num_turns_per_layer, height=H)
L2 = get_inductance(radius=R+wire_thickness, n_turns=num_turns_per_layer, height=H)
L3 = get_inductance(radius=R+2*wire_thickness, n_turns=num_turns_per_layer, height=H)
L4 = get_inductance(radius=R+3*wire_thickness, n_turns=num_turns_per_layer, height=H)

Leq1 = L1 +L2
Leq2 = L3 +L4

Leq = get_eq_inductance(parallel=True, Li=Leq1, Lj=Leq2)
print(f"Inductance: {Leq}")

for f in freq_values:
    Xeq = get_impedance(f, Leq) #reactance of coil

    #Allowed current based on voltage limit:
    i_total = min(I_set, V_limit/Xeq)

    i_layer = i_total/2

    # B-field for one "active winding"
    _, dBx, dBy, dBz = get_integrand(R, num_turns_per_layer*2, H, I=i_layer)

    #Evaluate at various points in space:
    for z in z_values:
        B_vec_layer = B(0, 0, z, dBx, dBy, dBz, num_turns_per_layer*2)
        B_vec_total = B_vec_layer * 2 #2 branches in parallel with approximately the same effect
        B_mag = np.linalg.norm(B_vec_total)

        # Actual voltage across the whole coil
        voltage = get_voltage(Xeq, i_total)

        # Save results
        results["B"].append(float(B_mag) * 1e3)  # to mT
        results["frequency"].append(f)
        results["voltage"].append(voltage)
        results["I_total"].append(i_total)
        results["loc_z"].append(z)

theta = np.linspace(0, 2*np.pi*num_turns_per_layer*nl, 10000)
x_coil = (R) * np.cos(theta)
y_coil = (R) * np.sin(theta)
z_coil = (H/(2*np.pi*num_turns_per_layer*nl)) * theta

fig1 = go.Figure()

# Add coil line
fig1.add_trace(go.Scatter3d(
    x=x_coil, y=y_coil, z=z_coil,
    mode="lines",
    line=dict(color="black", width=3),
    name="Coil"
))

df = pd.DataFrame(results)

# Add B-field points
fig1.add_trace(go.Scatter3d(
    x=np.zeros(len(df)),
    y=np.zeros(len(df)),
    z=df["loc_z"],
    mode="markers",
    marker=dict(
        size=5,
        color=df["B"], # color by B-field intensity
        colorscale="viridis",
        colorbar=dict(title="B [mT]")
    ),
    name="B-field"
))

fig1.update_layout(
    title="3D Coil with Magnetic Field Sampling",
    scene=dict(
        xaxis_title="X [m]",
        yaxis_title="Y [m]",
        zaxis_title="Z [m]"
    )
)

#Voltage vs Current vs frequency
fig2 = px.scatter_3d(
    df,
    x="voltage", y="I_total", z="frequency",
    color="loc_z",
    color_continuous_scale="plasma",
    title="Voltage vs Current vs Frequency (colored by Z location)"
)
fig2.update_traces(marker=dict(size=4))

#Heatmap of B vs frequency:
pivot = df.pivot_table(
    index="loc_z", columns="frequency", values="B"
)

fig3 = go.Figure(
    data=go.Heatmap(
        z=pivot.values,
        x=pivot.columns,
        y=pivot.index,
        colorscale="viridis",
        colorbar=dict(title="B [mT]")
    )
)
fig3.update_layout(
    title="Magnetic Field Intensity vs Frequency & Z-location",
    xaxis_title="Frequency [Hz]",
    yaxis_title="Z-location [m]"
)

#B vs Frequency vs Height
fig4 = px.scatter_3d(
    df,
    x="B", y="frequency", z="loc_z",
    color="B",
    color_continuous_scale="plasma",
    title="Magnetic Field Intensity vs Frequency & Z-location (3D)"
)
fig4.update_traces(marker=dict(size=4))

# Show figures
fig1.show()
fig2.show()
fig3.show()
fig4.show()

"""
fig1.write_html("Magnetic Field in Space at 40kHz.html")
fig2.write_html("Voltage vs Current vs Frequency .html")
fig3.write_html("Magnetic Field Intensity vs Frequency & Z_location (Heatmap).html")
fig4.write_html("Magnetic Field Intensity vs Frequency & Z_location (3D).html")
"""

plt.plot(df["frequency"], df["voltage"])
plt.grid()
plt.xlabel("Frequency [Hz]")
plt.ylabel("Voltage [V]")
plt.title("Voltage vs Frequency")
plt.show()