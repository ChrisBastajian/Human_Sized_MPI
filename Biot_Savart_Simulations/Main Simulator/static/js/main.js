let simulationData = null;
let unitFields = null; // Stores the 1A nominal fields
let activeCurrents = {}; // Stores the slider values

function toggleCoilBody(coilNum) {
    const isActive = document.getElementById(`c${coilNum}_active`).checked;
    const body = document.getElementById(`c${coilNum}_body`);
    const card = document.getElementById(`coil-card-${coilNum}`);

    if (isActive) {
        body.classList.remove('hidden');
        card.classList.add('active');
    } else {
        body.classList.add('hidden');
        card.classList.remove('active');
    }
}

document.getElementById('calc-form').addEventListener('submit', async function(e) {
    e.preventDefault();
    const btn = document.getElementById('submit-btn');
    const loading = document.getElementById('loading');

    btn.disabled = true;
    loading.classList.remove('hidden');

    const coils = [];
    activeCurrents = {};

    for (let i = 1; i <= 3; i++) {
        if (document.getElementById(`c${i}_active`).checked) {
            let id = `c${i}`;
            let initialCurrent = document.getElementById(`${id}_i`).value;
            activeCurrents[id] = parseFloat(initialCurrent);

            coils.push({
                id: id,
                name: `Coil ${i}`,
                active: true,
                cx: document.getElementById(`${id}_cx`).value,
                cy: document.getElementById(`${id}_cy`).value,
                cz: document.getElementById(`${id}_cz`).value,
                R: document.getElementById(`${id}_r`).value,
                L: document.getElementById(`${id}_l`).value,
                height: document.getElementById(`${id}_h`).value,
                num_layers: document.getElementById(`${id}_lay`).value,
                num_turns: document.getElementById(`${id}_trn`).value,
                wire_thickness: document.getElementById(`${id}_w`).value,
            });
        }
    }

    const payload = {
        coils: coils,
        grid: {
            x_min: document.getElementById('x_min').value,
            x_max: document.getElementById('x_max').value,
            y_min: document.getElementById('y_min').value,
            y_max: document.getElementById('y_max').value,
            z_min: document.getElementById('z_min').value,
            z_max: document.getElementById('z_max').value,
            x_res: document.getElementById('x_res').value,
            y_res: document.getElementById('y_res').value,
            z_res: document.getElementById('z_res').value,
        }
    };

    try {
        const response = await fetch('/api/calculate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const rawData = await response.json();

        // Save the geometries and unit fields
        simulationData = {
            grid: rawData.grid,
            coil_paths: rawData.coil_paths
        };
        unitFields = rawData.unit_fields;

        if (simulationData.grid && simulationData.grid.z.length > 0) {
            let uniqueZs = [...new Set(simulationData.grid.z.map(v => Number(v.toFixed(6))))].sort((a,b) => a-b);
            let slider = document.getElementById('z_slider');
            slider.max = Math.max(0, uniqueZs.length - 1);
            slider.value = Math.floor((uniqueZs.length - 1) / 2);
        }

        buildRealTimeSliders();
        calculateSuperposition(); // Perform initial scaling

    } catch (error) {
        console.error("Error fetching data:", error);
        alert("An error occurred. Check the console.");
    } finally {
        btn.disabled = false;
        loading.classList.add('hidden');
    }
});

function buildRealTimeSliders() {
    const container = document.getElementById('real-time-controls');
    container.innerHTML = '';

    for (const [coilId, currentVal] of Object.entries(activeCurrents)) {
        let div = document.createElement('div');
        div.className = 'form-group';
        div.style.marginBottom = '10px';

        let label = document.createElement('label');
        label.innerHTML = `<b>${coilId.toUpperCase()}</b> Current: <span id="${coilId}_val_display">${currentVal}</span> A`;

        let slider = document.createElement('input');
        slider.type = 'range';
        slider.min = '-100';
        slider.max = '100';
        slider.step = '1';
        slider.value = currentVal;

        slider.oninput = (e) => {
            let val = parseFloat(e.target.value);
            document.getElementById(`${coilId}_val_display`).innerText = val;
            activeCurrents[coilId] = val;
            calculateSuperposition(); // Update the field!
        };

        div.appendChild(label);
        div.appendChild(slider);
        container.appendChild(div);
    }
}

// THIS IS THE MAGIC: Multiply the 1A fields by slider values!
function calculateSuperposition() {
    if (!unitFields || !simulationData.grid) return;

    let numPoints = simulationData.grid.x.length;
    let U_total = new Array(numPoints).fill(0);
    let V_total = new Array(numPoints).fill(0);
    let W_total = new Array(numPoints).fill(0);

    for (const [coilId, currentVal] of Object.entries(activeCurrents)) {
        if (unitFields[coilId]) {
            let u_unit = unitFields[coilId].u;
            let v_unit = unitFields[coilId].v;
            let w_unit = unitFields[coilId].w;

            for (let i = 0; i < numPoints; i++) {
                U_total[i] += u_unit[i] * currentVal;
                V_total[i] += v_unit[i] * currentVal;
                W_total[i] += w_unit[i] * currentVal;
            }
        }
    }

    simulationData.grid.u = U_total;
    simulationData.grid.v = V_total;
    simulationData.grid.w = W_total;

    updateVisualization();
}

function updateVisualization() {
    if (!simulationData || !simulationData.grid.u) return;

    const mode = document.querySelector('input[name="vis_mode"]:checked').value;
    const zSliderContainer = document.getElementById('z_slider_container');
    const plotDiv = document.getElementById('plot');
    plotDiv.innerHTML = '';

    if (mode === 'vector') {
        zSliderContainer.classList.add('hidden');
        render3DVectorPlot(plotDiv, simulationData);
    } else {
        zSliderContainer.classList.remove('hidden');
        render2DHeatmapPlot(plotDiv, simulationData);
    }
}

function render3DVectorPlot(plotDiv, data) {
    const traces = [];

    if (data.grid && data.grid.x.length > 0) {
        let u_raw = data.grid.u;
        let v_raw = data.grid.v;
        let w_raw = data.grid.w;

        let mags = [];
        for (let i = 0; i < u_raw.length; i++) {
            mags.push(Math.sqrt(u_raw[i]**2 + v_raw[i]**2 + w_raw[i]**2));
        }

        let sortedMags = [...mags].sort((a, b) => a - b);
        let p95 = sortedMags[Math.floor(sortedMags.length * 0.95)];

        let u_vis = [], v_vis = [], w_vis = [], hover_text = [];

        for (let i = 0; i < u_raw.length; i++) {
            let mag = mags[i];
            let scale = 1;

            if (mag > p95 && p95 > 0) scale = p95 / mag;

            u_vis.push(u_raw[i] * scale);
            v_vis.push(v_raw[i] * scale);
            w_vis.push(w_raw[i] * scale);

            hover_text.push(
                `<b>Exact B-Field:</b> ${mag.toExponential(3)} T<br>` +
                `Bx: ${u_raw[i].toExponential(2)} T<br>` +
                `By: ${v_raw[i].toExponential(2)} T<br>` +
                `Bz: ${w_raw[i].toExponential(2)} T`
            );
        }

        traces.push({
            type: 'cone',
            x: data.grid.x, y: data.grid.y, z: data.grid.z,
            u: u_vis, v: v_vis, w: w_vis,
            text: hover_text,
            hovertemplate: 'X: %{x:.2f}, Y: %{y:.2f}, Z: %{z:.2f}<br>%{text}<extra></extra>',
            sizemode: 'scaled', sizeref: 0.2,
            colorscale: 'Viridis',
            colorbar: {title: 'Visual B-Field Mag'},
            name: 'B-Field'
        });
    }

    const colorPalette = ['#e67e22', '#3498db', '#e74c3c'];
    if (data.coil_paths) {
        data.coil_paths.forEach((pathData, index) => {
            traces.push({
                type: 'scatter3d', mode: 'lines',
                x: pathData.x, y: pathData.y, z: pathData.z,
                line: { color: colorPalette[index % colorPalette.length], width: 3, opacity: 0.8 },
                name: pathData.name, showlegend: true
            });
        });
    }

    if (data.null_line && data.null_line.x.length > 0) {
        traces.push({
            type: 'scatter3d',
            mode: 'lines',
            x: data.null_line.x,
            y: data.null_line.y,
            z: data.null_line.z,
            line: { color: 'black', width: 8 },
            name: 'Field-Free Line (B≈0)',
            hovertemplate: 'X: %{x:.3f} m<br>Y: %{y:.3f} m<br>Z: %{z:.3f} m<extra>Null Line</extra>'
        });
    }

    // Dynamic Field-Free Region Approximation
    let null_x = [], null_y = [], null_z = [];
    let threshold = 0.0005; // 0.5 mT threshold

    for (let i = 0; i < data.grid.x.length; i++) {
        let mag = Math.sqrt(data.grid.u[i]**2 + data.grid.v[i]**2 + data.grid.w[i]**2);
        if (mag < threshold) {
            null_x.push(data.grid.x[i]);
            null_y.push(data.grid.y[i]);
            null_z.push(data.grid.z[i]);
        }
    }

    if (null_x.length > 0) {
        traces.push({
            type: 'scatter3d',
            mode: 'markers',
            x: null_x, y: null_y, z: null_z,
            marker: { size: 4, color: 'black', symbol: 'circle' },
            name: `Field ≈ 0 (<${threshold*1000}mT)`
        });
    }

    Plotly.newPlot(plotDiv, traces, {
        title: '3D Magnetic Field Vector Visualization',
        scene: { aspectmode: 'data', xaxis: {title: 'X (m)'}, yaxis: {title: 'Y (m)'}, zaxis: {title: 'Z (m)'} },
        margin: {l: 0, r: 0, b: 0, t: 40}
    });
}

function render2DHeatmapPlot(plotDiv, data) {
    if (!data.grid || data.grid.x.length === 0) return;

    let uniqueXs = [...new Set(data.grid.x.map(v => Number(v.toFixed(6))))].sort((a,b) => a-b);
    let uniqueYs = [...new Set(data.grid.y.map(v => Number(v.toFixed(6))))].sort((a,b) => a-b);
    let uniqueZs = [...new Set(data.grid.z.map(v => Number(v.toFixed(6))))].sort((a,b) => a-b);

    let slider = document.getElementById('z_slider');
    slider.max = Math.max(0, uniqueZs.length - 1);
    let targetIndex = parseInt(slider.value);
    let targetZ = uniqueZs[targetIndex];

    document.getElementById('z_slice_val').innerText = targetZ;

    let z_2d = Array.from({ length: uniqueYs.length }, () => new Array(uniqueXs.length).fill(null));

    for (let i = 0; i < data.grid.x.length; i++) {
        let current_z = Number(data.grid.z[i].toFixed(6));

        if (current_z === targetZ) {
            let current_x = Number(data.grid.x[i].toFixed(6));
            let current_y = Number(data.grid.y[i].toFixed(6));

            let x_idx = uniqueXs.indexOf(current_x);
            let y_idx = uniqueYs.indexOf(current_y);

            if (x_idx >= 0 && y_idx >= 0) {
                let mag = Math.sqrt(data.grid.u[i]**2 + data.grid.v[i]**2 + data.grid.w[i]**2);
                z_2d[y_idx][x_idx] = mag;
            }
        }
    }

    const traces = [{
        type: 'contour',
        x: uniqueXs,
        y: uniqueYs,
        z: z_2d,
        colorscale: 'Viridis',
        colorbar: {title: 'Magnitude (T)'},
        contours: {
            coloring: 'heatmap',
            showlines: false
        },
        hovertemplate: 'X: %{x:.3f} m<br>Y: %{y:.3f} m<br>Mag: %{z:.3e} T<extra></extra>'
    }];

    if (data.null_line && data.null_line.x.length > 0) {
        let lx = [], ly = [];
        let z_tolerance = 0.01;

        for (let i = 0; i < data.null_line.z.length; i++) {
            if (Math.abs(data.null_line.z[i] - targetZ) < z_tolerance) {
                lx.push(data.null_line.x[i]);
                ly.push(data.null_line.y[i]);
            }
        }

        if (lx.length > 0) {
            traces.push({
                type: 'scatter',
                mode: 'lines+markers',
                x: lx,
                y: ly,
                line: { color: 'black', width: 4, dash: 'dot' },
                marker: { size: 8, color: 'black' },
                name: 'Null Line Plane Intersection'
            });
        }
    }

    Plotly.newPlot(plotDiv, traces, {
        title: `2D Interpolated B-Field (Z = ${targetZ} m)`,
        xaxis: {title: 'X (m)', scaleanchor: 'y', scaleratio: 1},
        yaxis: {title: 'Y (m)'},
        margin: {l: 50, r: 50, b: 50, t: 50}
    });
}

function downloadData() {
    if (!unitFields) return alert("No data to export!");

    const exportObj = {
        grid: simulationData.grid, // coordinates
        unit_fields: unitFields    // the 1A field arrays
    };

    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(exportObj));
    const downloadAnchorNode = document.createElement('a');
    downloadAnchorNode.setAttribute("href", dataStr);
    downloadAnchorNode.setAttribute("download", "magnetic_field_data.json");
    document.body.appendChild(downloadAnchorNode);
    downloadAnchorNode.click();
    downloadAnchorNode.remove();
}