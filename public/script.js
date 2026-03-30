document.addEventListener('DOMContentLoaded', () => {
    const simulateBtn = document.getElementById('simulate-btn');
    const numRaysInput = document.getElementById('num-rays');
    const maxBouncesInput = document.getElementById('max-bounces');
    const valRays = document.getElementById('val-rays');
    const valBounces = document.getElementById('val-bounces');
    
    const statusBox = document.getElementById('status-box');
    const statusText = document.getElementById('status-text');
    
    const rayPlot = document.getElementById('ray-plot');
    const heatmapPlot = document.getElementById('heatmap-plot');
    const irPlot = document.getElementById('ir-plot');
    
    const statsPanel = document.getElementById('stats-panel');
    const statEnergy = document.getElementById('stat-energy');
    const statPoints = document.getElementById('stat-points');

    // Update value displays
    numRaysInput.addEventListener('input', (e) => valRays.innerText = e.target.value);
    maxBouncesInput.addEventListener('input', (e) => valBounces.innerText = e.target.value);

    simulateBtn.addEventListener('click', async () => {
        const numRays = numRaysInput.value;
        const maxBounces = maxBouncesInput.value;

        // Reset UI
        statusBox.classList.remove('hidden');
        statusText.innerText = "Initializing Monte Carlo Engine...";
        simulateBtn.disabled = true;
        simulateBtn.style.opacity = "0.5";
        
        try {
            statusText.innerText = "Tracing stochastic rays in irregular mesh...";
            const response = await fetch('/api/simulate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    num_rays: numRays,
                    max_bounces: maxBounces
                })
            });

            const data = await response.json();

            if (data.status === 'success') {
                statusText.innerText = "Calculating Markov transitions...";
                
                // Update images with base64 data
                rayPlot.src = data.plots.ray_paths;
                heatmapPlot.src = data.plots.heatmap;
                irPlot.src = data.plots.impulse_response;
                
                // Update stats
                statEnergy.innerText = data.stats.avg_energy;
                statPoints.innerText = data.stats.data_points;
                statsPanel.classList.remove('hidden');
                
                statusText.innerText = "Simulation Complete.";
                setTimeout(() => statusBox.classList.add('hidden'), 2000);
            } else {
                statusText.innerText = `Simulation Error: ${data.message}`;
            }
        } catch (error) {
            console.error(error);
            statusText.innerText = "Connection failed.";
        } finally {
            simulateBtn.disabled = false;
            simulateBtn.style.opacity = "1";
        }
    });

    // --- STREET CANYON TAB LOGIC ---
    const canyonHW = document.getElementById('canyon-hw');
    const canyonAF = document.getElementById('canyon-af');
    const canyonAG = document.getElementById('canyon-ag');
    const canyonMU = document.getElementById('canyon-mu');
    const canyonLW = document.getElementById('canyon-lw');
    
    const valHW = document.getElementById('val-hw');
    const valAF = document.getElementById('val-af');
    const valAG = document.getElementById('val-ag');
    const valMU = document.getElementById('val-mu');
    const valLW = document.getElementById('val-lw');

    const canyonSPL = document.getElementById('canyon-spl');
    const matrixHeatmap = document.getElementById('matrix-heatmap');
    
    let distChart = null;

    const updateCanyon = async () => {
        valHW.innerText = canyonHW.value;
        valAF.innerText = canyonAF.value;
        valAG.innerText = canyonAG.value;
        valMU.innerText = canyonMU.value;
        valLW.innerText = canyonLW.value;

        const response = await fetch('/api/canyon', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                h_w: canyonHW.value,
                alpha_f: canyonAF.value,
                alpha_g: canyonAG.value,
                mu: canyonMU.value,
                lw: canyonLW.value
            })
        });
        const data = await response.json();
        
        canyonSPL.innerText = data.spl;
        renderMatrix(data.matrix);
        renderDistChart(data.distribution);
    };

    const renderMatrix = (matrix) => {
        matrixHeatmap.innerHTML = '';
        matrix.forEach((row, i) => {
            row.forEach((val, j) => {
                const cell = document.createElement('div');
                cell.className = 'matrix-cell';
                const alpha = Math.min(val * 1.5, 1.0);
                cell.style.backgroundColor = `rgba(79, 172, 254, ${alpha})`;
                cell.innerText = val.toFixed(2);
                matrixHeatmap.appendChild(cell);
            });
        });
    };

    const renderDistChart = (dist) => {
        const labels = ['L. Facade', 'R. Facade', 'Ground', 'Sky', 'Receiver'];
        if (distChart) {
            distChart.data.datasets[0].data = dist;
            distChart.update();
        } else {
            const ctx = document.getElementById('dist-chart').getContext('2d');
            distChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Stationary Distribution π',
                        data: dist,
                        backgroundColor: 'rgba(79, 172, 254, 0.6)',
                        borderColor: '#4facfe',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    scales: { y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.05)' } } }
                }
            });
        }
    };

    [canyonHW, canyonAF, canyonAG, canyonMU, canyonLW].forEach(el => el.addEventListener('input', updateCanyon));
    updateCanyon();

    // --- CONVERGENCE TAB LOGIC ---
    const runConvBtn = document.getElementById('run-convergence');
    const convN = document.getElementById('conv-n');
    const convCI = document.getElementById('conv-ci');
    let convChart = null;
    let ciDecayChart = null;

    runConvBtn.addEventListener('click', async () => {
        const response = await fetch('/api/convergence', { method: 'POST' });
        const data = await response.json();
        
        animateConvergence(data);
    });

    const animateConvergence = (data) => {
        let i = 0;
        const interval = setInterval(() => {
            if (i >= data.n.length) {
                clearInterval(interval);
                return;
            }

            const subN = data.n.slice(0, i + 1);
            const subMeans = data.means.slice(0, i + 1);
            const subCI = data.ci.slice(0, i + 1);
            
            convN.innerText = data.n[i];
            convCI.innerText = data.ci[i].toFixed(2);

            updateConvCharts(subN, subMeans, subCI, data.true_mean);
            i++;
        }, 200);
    };

    const updateConvCharts = (n, means, ci, trueMean) => {
        const ctx1 = document.getElementById('convergence-chart').getContext('2d');
        const upper = means.map((m, idx) => m + ci[idx]);
        const lower = means.map((m, idx) => m - ci[idx]);

        if (convChart) {
            convChart.data.labels = n;
            convChart.data.datasets[0].data = means;
            convChart.data.datasets[1].data = upper;
            convChart.data.datasets[2].data = lower;
            convChart.update('none');
        } else {
            convChart = new Chart(ctx1, {
                type: 'line',
                data: {
                    labels: n,
                    datasets: [
                        { label: 'Running Mean SPL', data: means, borderColor: '#4facfe', fill: false, tension: 0.1 },
                        { label: '95% CI Upper', data: upper, borderColor: 'transparent', backgroundColor: 'rgba(79, 172, 254, 0.1)', fill: '+1', pointRadius: 0 },
                        { label: '95% CI Lower', data: lower, borderColor: 'transparent', pointRadius: 0, fill: false },
                        { label: 'True Mean', data: n.map(() => trueMean), borderColor: '#ff4b2b', borderDash: [5, 5], fill: false, pointRadius: 0 }
                    ]
                },
                options: { responsive: true, scales: { x: { type: 'logarithmic' } } }
            });
        }

        const ctx2 = document.getElementById('ci-decay-chart').getContext('2d');
        if (ciDecayChart) {
            ciDecayChart.data.labels = n;
            ciDecayChart.data.datasets[0].data = ci;
            ciDecayChart.update('none');
        } else {
            ciDecayChart = new Chart(ctx2, {
                type: 'line',
                data: {
                    labels: n,
                    datasets: [{ label: 'CI Width', data: ci, borderColor: '#f0abfc', fill: true, backgroundColor: 'rgba(240, 171, 252, 0.1)' }]
                },
                options: { responsive: true, scales: { x: { type: 'logarithmic' }, y: { type: 'logarithmic' } } }
            });
        }
    };

    // --- URBAN GRID TAB LOGIC ---
    const refreshGridBtn = document.getElementById('refresh-grid');
    const profileBtns = document.querySelectorAll('.profile-btn');
    const gridSplMap = document.getElementById('grid-spl-map');
    const gridCiMap = document.getElementById('grid-ci-map');
    let currentProfile = 'Mixed';

    profileBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            profileBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentProfile = btn.dataset.profile;
            updateGrid();
        });
    });

    const updateGrid = async () => {
        const response = await fetch('/api/grid', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ profile: currentProfile })
        });
        const data = await response.json();
        
        renderGrid(gridSplMap, data.spl_grid, [55, 75], 'dB');
        renderGrid(gridCiMap, data.ci_grid, [0.5, 3.0], 'dB CI');
    };

    const renderGrid = (container, grid, range, unit) => {
        container.innerHTML = '';
        grid.forEach(row => {
            row.forEach(val => {
                const cell = document.createElement('div');
                cell.className = 'grid-cell';
                const ratio = (val - range[0]) / (range[1] - range[0]);
                const hue = container.id.includes('spl') ? (1 - ratio) * 120 : 280; // Green to Red or Purple
                cell.style.backgroundColor = `hsla(${hue}, 70%, 50%, 0.3)`;
                cell.style.borderColor = `hsla(${hue}, 70%, 50%, 0.6)`;
                cell.innerHTML = `<span class="val">${val.toFixed(1)}</span><span class="unit">${unit}</span>`;
                container.appendChild(cell);
            });
        });
    };

    refreshGridBtn.addEventListener('click', updateGrid);
    updateGrid();
});

function showTab(tabId) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(t => t.classList.add('hidden'));
    // Show selected tab
    document.getElementById(`${tabId}-tab`).classList.remove('hidden');
    
    // Update nav links
    document.querySelectorAll('.nav-links a').forEach(a => a.classList.remove('active'));
    event.currentTarget.classList.add('active');
}
