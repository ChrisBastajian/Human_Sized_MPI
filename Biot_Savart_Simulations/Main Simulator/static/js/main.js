// Toggle UI logic for Coil cards
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

    // Gather active coils
    const coils = [];
    for (let i = 1; i <= 3; i++) {
        if (document.getElementById(`c${i}_active`).checked) {
            coils.push({
                name: `Coil ${i}`,
                active: true,
                cx: document.getElementById(`c${i}_cx`).value,
                cy: document.getElementById(`c${i}_cy`).value,
                cz: document.getElementById(`c${i}_cz`).value,
                R: document.getElementById(`c${i}_r`).value,
                L: document.getElementById(`c${i}_l`).value,
                height: document.getElementById(`c${i}_h`).value,
                current: document.getElementById(`c${i}_i`).value,
                num_layers: document.getElementById(`c${i}_lay`).value,
                num_turns: document.getElementById(`c${i}_trn`).value,
                wire_thickness: document.getElementById(`c${i}_w`).value,
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

        const data = await response.json();
        renderPlot(data);

    } catch (error) {
        console.error("Error fetching data:", error);
        alert("An error occurred. Check the console.");
    } finally {
        btn.disabled = false;
        loading.classList.add('hidden');
    }
});

function renderPlot(data) {
    const plotDiv = document.getElementById('plot');
    plotDiv.innerHTML = '';

    const traces = [];

    // 1. Vector Field Processing
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

            if (mag > p95 && p95 > 0) {
                scale = p95 / mag;
            }

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

        const coneTrace = {
            type: 'cone',
            x: data.grid.x,
            y: data.grid.y,
            z: data.grid.z,
            u: u_vis,
            v: v_vis,
            w: w_vis,
            text: hover_text,
            hovertemplate: 'X: %{x:.2f}, Y: %{y:.2f}, Z: %{z:.2f}<br>%{text}<extra></extra>',
            sizemode: 'scaled',
            sizeref: 0.2,
            colorscale: 'Viridis',
            colorbar: {title: 'Visual B-Field Mag'},
            name: 'B-Field'
        };
        traces.push(coneTrace);
    }

    // 2. Coil Geometries
    const colorPalette = ['#e67e22', '#3498db', '#e74c3c']; // Orange, Blue, Red
    if (data.coil_paths && data.coil_paths.length > 0) {
        data.coil_paths.forEach((pathData, index) => {
            const lineTrace = {
                type: 'scatter3d',
                mode: 'lines',
                x: pathData.x,
                y: pathData.y,
                z: pathData.z,
                line: {
                    color: colorPalette[index % colorPalette.length],
                    width: 3,
                    opacity: 0.8
                },
                name: pathData.name,
                showlegend: true
            };
            traces.push(lineTrace);
        });
    }

    const layout = {
        title: '3D Magnetic Field System Visualization',
        scene: {
            aspectmode: 'data',
            xaxis: {title: 'X (m)'},
            yaxis: {title: 'Y (m)'},
            zaxis: {title: 'Z (m)'}
        },
        margin: {l: 0, r: 0, b: 0, t: 40}
    };

    Plotly.newPlot(plotDiv, traces, layout);
}