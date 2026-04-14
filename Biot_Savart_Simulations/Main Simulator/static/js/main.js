document.getElementById('calc-form').addEventListener('submit', async function(e) {
    e.preventDefault();

    const btn = document.getElementById('submit-btn');
    const loading = document.getElementById('loading');

    btn.disabled = true;
    loading.classList.remove('hidden');

    const payload = {
        R: document.getElementById('r_val').value,
        L: document.getElementById('l_val').value,
        height: document.getElementById('height').value,
        num_layers: document.getElementById('num_layers').value,
        num_turns: document.getElementById('num_turns').value,
        wire_thickness: document.getElementById('wire_thickness').value,
        current: document.getElementById('current').value,
        x_min: document.getElementById('x_min').value,
        x_max: document.getElementById('x_max').value,
        y_min: document.getElementById('y_min').value,
        y_max: document.getElementById('y_max').value,
        z_min: document.getElementById('z_min').value,
        z_max: document.getElementById('z_max').value,
        grid_res: document.getElementById('grid_res').value,
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

        // Find the 95th percentile to use as a visual cap
        let sortedMags = [...mags].sort((a, b) => a - b);
        let p95 = sortedMags[Math.floor(sortedMags.length * 0.95)];

        let u_vis = [], v_vis = [], w_vis = [], hover_text = [];

        for (let i = 0; i < u_raw.length; i++) {
            let mag = mags[i];
            let scale = 1;

            // Cap the size to the 95th percentile to prevent vector blow-up
            if (mag > p95 && p95 > 0) {
                scale = p95 / mag;
            }

            u_vis.push(u_raw[i] * scale);
            v_vis.push(v_raw[i] * scale);
            w_vis.push(w_raw[i] * scale);

            // Format exact real values for the tooltip
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
            sizemode: 'scaled', // Dynamically scales to bounding box
            sizeref: 0.2, // 20% of bounding box
            colorscale: 'Viridis',
            colorbar: {title: 'Visual B-Field Magnitude'},
            name: 'B-Field'
        };
        traces.push(coneTrace);
    }

    // 2. Coil Geometry
    if (data.coil_paths && data.coil_paths.length > 0) {
        const pathData = data.coil_paths[0];
        const lineTrace = {
            type: 'scatter3d',
            mode: 'lines',
            x: pathData.x,
            y: pathData.y,
            z: pathData.z,
            line: { color: 'orange', width: 3, opacity: 0.8 },
            name: 'Winding',
            showlegend: true
        };
        traces.push(lineTrace);
    }

    const layout = {
        title: '3D Magnetic Field of Racetrack Coil',
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