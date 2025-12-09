import matplotlib.pyplot as plt
import numpy as np

#At 25kHz: Used in powerpoint presentation
#frequency = 25 #kHz (for the title only)
#l = np.array([26, 48, 60, 74.25])
#esr = np.array([5, 9.6, 12.05, 15.2]) #mohm

#At 40kHz: Used in final report
frequency = 40 #kHz (for the title only)
l = np.array([6.75, 7.75, 13.75, 19.4, 27.6])
esr = np.array([2.92, 3.15, 3.9, 4.7, 5.93])

#Trendline:
m, c = np.polyfit(l, esr, 1)
trend_line = m*l + c

fig, ax = plt.subplots()
#r,g,b = 242, 245, 247 #for powerpoint background matching
r,g,b = 255, 255, 255 #for simple white background
fig.patch.set_facecolor((r/255, g/255, b/255))  # RGB tuple, values 0–1
ax.set_facecolor((r/255, g/255, b/255))
ax.set_xlabel("Length [in]", fontsize=18, fontname="Times New Roman")
ax.set_ylabel("ESR [m\u2126]", fontsize=18, fontname="Times New Roman")
ax.set_title(f"Equivalent Series Resistance Per Unit Length at {frequency}kHz",
             fontsize=18,
             fontname="Times New Roman",
             fontweight="bold")
ax.plot(l, esr, 'o', color='black')
ax.plot(l, trend_line, 'r--', color='blue', label=f"{m:.2f} * Length - {abs(c):.2f}")
ax.grid()
ax.legend()

plt.show()

# Calibration H_I data:
I_dc_bottom_top = np.arange(0, 1.1, 0.1)
#I_dc_center = np.array([0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 2, 3])
I_dc_center = I_dc_bottom_top

Bz_bottom = np.array([127, 155, 188, 225, 248, 280, 337, 367, 404, 416, 443])
#Bz_center = np.array([122, 164, 210, 257, 294, 330, 367, 404, 448, 485, 522, 973, 1380])
Bz_top = np.array([130, 157, 194, 224, 257, 285, 327, 357, 402, 421, 448])
Bz_center = np.array([122, 164, 210, 257, 294, 330, 367, 404, 448, 485, 522])

#trendlines:
m_bottom, c_bottom = np.polyfit(I_dc_bottom_top, Bz_bottom, 1)
m_top, c_top = np.polyfit(I_dc_bottom_top, Bz_top, 1)
m_center, c_center = np.polyfit(I_dc_center, Bz_center, 1)
tl_bottom = m_bottom * I_dc_bottom_top + c_bottom
tl_center = m_center * I_dc_center + c_center
tl_top = m_top * I_dc_bottom_top + c_top

#Plotting:
#First Plot:
fig2, ax2 = plt.subplots()
fig2.patch.set_facecolor((r/255, g/255, b/255))  # RGB tuple, values 0–1
ax2.set_facecolor((r/255, g/255, b/255))
ax2.grid()

ax2.plot(I_dc_bottom_top, Bz_top, 'o', label="Top", color='green')

ax2.plot(I_dc_bottom_top, tl_top, '--', label=f"{m_top:.2f} * I + {c_top:.2f}", color='green')

ax2.legend()

ax2.set_xlabel("I [A]", fontsize=18, fontname="Times New Roman")
ax2.set_ylabel("μ₀H [µT]", fontsize=18, fontname="Times New Roman")
ax2.set_title("Field Intensity Calibration at the Top", fontsize=18, fontname="Times New Roman", fontweight="bold")

#Second plot:
fig3, ax3 = plt.subplots()
fig3.patch.set_facecolor((r/255, g/255, b/255))  # RGB tuple, values 0–1
ax3.set_facecolor((r/255, g/255, b/255))
ax3.grid()

ax3.plot(I_dc_center, Bz_center, 'o', label="Center", color='blue')
ax3.plot(I_dc_center, tl_center, '--', label=f"{m_center:.2f} * I + {c_center:.2f}", color='blue')

ax3.legend()

ax3.set_xlabel("I [A]", fontsize=18, fontname="Times New Roman")
ax3.set_ylabel("μ₀H [µT]", fontsize=18, fontname="Times New Roman")
ax3.set_title("Field Intensity Calibration at the Center", fontsize=18, fontname="Times New Roman", fontweight="bold")

#third plot:
fig4, ax4 = plt.subplots()
fig4.patch.set_facecolor((r/255, g/255, b/255))  # RGB tuple, values 0–1
ax4.set_facecolor((r/255, g/255, b/255))
ax4.grid()

ax4.plot(I_dc_bottom_top, Bz_bottom, 'o', label="Bottom", color='black')
ax4.plot(I_dc_bottom_top, tl_bottom, '--', label=f"{m_bottom:.2f} * I + {c_bottom:.2f}", color='black')

ax4.legend()

ax4.set_xlabel("I [A]", fontsize=18, fontname="Times New Roman")
ax4.set_ylabel("μ₀H [µT]", fontsize=18, fontname="Times New Roman")
ax4.set_title("Field Intensity Calibration at the Bottom", fontsize=18, fontname="Times New Roman", fontweight="bold")

#Last Plot:
fig1, ax1 = plt.subplots()
fig1.patch.set_facecolor((r/255, g/255, b/255))  # RGB tuple, values 0–1
ax1.set_facecolor((r/255, g/255, b/255))
ax1.grid()

ax1.plot(I_dc_bottom_top, Bz_top, 's', label="Top", color=(255/255, 0/255, 255/255))
ax1.plot(I_dc_center, Bz_center, 'o', label="Center", color='green')
ax1.plot(I_dc_bottom_top, Bz_bottom, '^', label="Bottom", color='black')

ax1.plot(I_dc_bottom_top, tl_top, '--', label=f"{m_top:.2f} * I + {c_top:.2f}", color=(255/255, 0/255, 255/255))
ax1.plot(I_dc_center, tl_center, '--', label=f"{m_center:.2f} * I + {c_center:.2f}", color='green')
ax1.plot(I_dc_bottom_top, tl_bottom, '--', label=f"{m_bottom:.2f} * I + {c_bottom:.2f}", color='black')

ax1.legend()

ax1.set_xlabel("I [A]", fontsize=18, fontname="Times New Roman")
ax1.set_ylabel("μ₀H [µT]", fontsize=18, fontname="Times New Roman")
ax1.set_title("Field Intensity Calibration", fontsize=18, fontname="Times New Roman", fontweight="bold")

plt.show()
