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

    // --- CITY PLANNER LOGIC ---
    const plannerCanvas = document.getElementById('planner-canvas');
    const ctx = plannerCanvas.getContext('2d');
    const plannerOverlay = document.getElementById('planner-overlay');
    const toolBtns = document.querySelectorAll('.tool-btn');
    const layerBtns = document.querySelectorAll('.layer-btn');
    const runPlannerBtn = document.getElementById('run-planner');
    const suggestBtn = document.getElementById('suggest-btn');
    const suggestionBox = document.getElementById('suggestion-box');
    const suggestionList = document.getElementById('suggestion-list');
    const presetSelect = document.getElementById('map-presets');

    let currentTool = 'building';
    let currentLayer = 'spl';
    let buildings = [];
    let sources = [];
    let lastSimData = null;

    // Leaflet Map Initialization
    let leafletMap = null;
    const initMap = () => {
        if (leafletMap) return;
        leafletMap = L.map('map', {
            zoomControl: false,
            attributionControl: false,
            dragging: false,
            scrollWheelZoom: false,
            doubleClickZoom: false,
            boxZoom: false,
            touchZoom: false
        }).setView([41.388, 2.163], 17);

        L.tileLayer('https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png', {
            maxZoom: 19
        }).addTo(leafletMap);
    };

    const setMapView = (city) => {
        if (!leafletMap) initMap();
        const mapDiv = document.getElementById('map');
        
        if (city === 'barcelona') {
            // Center is Hospital Clinic area
            // Rotate the map visually to match the mathematically rotated block extraction!
            // We extracted at -45 deg, meaning the streets mapped to X/Y. 
            // We rotate the visual map clockwise to make the streets horizontal/vertical.
            // Scale up slightly so the corners don't show empty background.
            mapDiv.style.transform = 'scale(1.5) rotate(45deg)';
            leafletMap.setView([41.3887, 2.1635], 17);
        } else if (city === 'kolkata') {
            mapDiv.style.transform = 'none';
            leafletMap.setView([22.5395, 88.3435], 17);
        }
    };

    // Map Presets Data
    // Barcelona & Kolkata buildings fetched from OSM Overpass API,
    // mapped to the exact 10x10 grid using the same center/zoom as Leaflet.
    // This ensures each red overlay block sits exactly on top of the real buildings.
    const PRESETS = {
        'empty': { buildings: [], sources: [] },
        'main-street': {
            buildings: [
                {x: 2, y: 0, h: 8, material: 'glass'}, {x: 2, y: 1, h: 8, material: 'glass'}, {x: 2, y: 2, h: 8, material: 'glass'},
                {x: 2, y: 3, h: 8, material: 'glass'}, {x: 2, y: 4, h: 8, material: 'glass'}, {x: 2, y: 5, h: 8, material: 'glass'},
                {x: 7, y: 0, h: 10, material: 'concrete'}, {x: 7, y: 1, h: 10, material: 'concrete'}, {x: 7, y: 2, h: 10, material: 'concrete'},
                {x: 7, y: 3, h: 10, material: 'concrete'}, {x: 7, y: 4, h: 10, material: 'concrete'}, {x: 7, y: 5, h: 10, material: 'concrete'}
            ],
            sources: [{x: 4, y: 2, intensity: 1200}, {x: 5, y: 4, intensity: 1200}]
        },
        'courtyard': {
            buildings: [
                {x: 3, y: 3, h: 4, material: 'vegetation'}, {x: 3, y: 4, h: 4, material: 'vegetation'}, {x: 3, y: 5, h: 4, material: 'vegetation'},
                {x: 6, y: 3, h: 4, material: 'vegetation'}, {x: 6, y: 4, h: 4, material: 'vegetation'}, {x: 6, y: 5, h: 4, material: 'vegetation'},
                {x: 4, y: 2, h: 6, material: 'concrete'}, {x: 5, y: 2, h: 6, material: 'concrete'},
                {x: 4, y: 6, h: 6, material: 'concrete'}, {x: 5, y: 6, h: 6, material: 'concrete'}
            ],
            sources: [{x: 4, y: 4, intensity: 800}]
        },
        'industrial': {
            buildings: [
                {x: 1, y: 1, h: 12, material: 'concrete'}, {x: 1, y: 2, h: 12, material: 'concrete'},
                {x: 8, y: 7, h: 15, material: 'glass'}, {x: 8, y: 8, h: 15, material: 'glass'},
                {x: 4, y: 4, h: 5, material: 'concrete'}
            ],
            sources: [{x: 2, y: 2, intensity: 2000}, {x: 7, y: 7, intensity: 2000}, {x: 5, y: 1, intensity: 1500}]
        },
        'barcelona': {
            buildings: [{"x": 0, "y": 2, "h": 15, "material": "concrete"}, {"x": 0, "y": 3, "h": 5, "material": "concrete"}, {"x": 0, "y": 4, "h": 15, "material": "concrete"}, {"x": 0, "y": 5, "h": 5, "material": "concrete"}, {"x": 0, "y": 6, "h": 5, "material": "concrete"}, {"x": 0, "y": 7, "h": 5, "material": "concrete"}, {"x": 1, "y": 2, "h": 15, "material": "concrete"}, {"x": 1, "y": 6, "h": 5, "material": "concrete"}, {"x": 2, "y": 0, "h": 15, "material": "concrete"}, {"x": 2, "y": 1, "h": 15, "material": "concrete"}, {"x": 2, "y": 2, "h": 15, "material": "concrete"}, {"x": 2, "y": 3, "h": 5, "material": "concrete"}, {"x": 2, "y": 4, "h": 15, "material": "concrete"}, {"x": 2, "y": 5, "h": 15, "material": "concrete"}, {"x": 2, "y": 6, "h": 5, "material": "concrete"}, {"x": 2, "y": 7, "h": 5, "material": "concrete"}, {"x": 2, "y": 8, "h": 5, "material": "concrete"}, {"x": 2, "y": 9, "h": 5, "material": "concrete"}, {"x": 3, "y": 0, "h": 15, "material": "concrete"}, {"x": 3, "y": 1, "h": 15, "material": "concrete"}, {"x": 3, "y": 2, "h": 5, "material": "concrete"}, {"x": 3, "y": 4, "h": 15, "material": "concrete"}, {"x": 3, "y": 5, "h": 5, "material": "concrete"}, {"x": 3, "y": 7, "h": 5, "material": "concrete"}, {"x": 3, "y": 8, "h": 5, "material": "concrete"}, {"x": 3, "y": 9, "h": 5, "material": "concrete"}, {"x": 4, "y": 0, "h": 15, "material": "concrete"}, {"x": 4, "y": 1, "h": 15, "material": "concrete"}, {"x": 4, "y": 2, "h": 5, "material": "concrete"}, {"x": 4, "y": 3, "h": 5, "material": "concrete"}, {"x": 4, "y": 4, "h": 5, "material": "concrete"}, {"x": 4, "y": 7, "h": 15, "material": "concrete"}, {"x": 4, "y": 8, "h": 15, "material": "concrete"}, {"x": 4, "y": 9, "h": 15, "material": "concrete"}, {"x": 5, "y": 0, "h": 15, "material": "concrete"}, {"x": 5, "y": 2, "h": 15, "material": "concrete"}, {"x": 5, "y": 3, "h": 5, "material": "concrete"}, {"x": 5, "y": 4, "h": 15, "material": "concrete"}, {"x": 5, "y": 6, "h": 5, "material": "concrete"}, {"x": 5, "y": 7, "h": 15, "material": "concrete"}, {"x": 5, "y": 9, "h": 15, "material": "concrete"}, {"x": 6, "y": 0, "h": 15, "material": "concrete"}, {"x": 6, "y": 2, "h": 5, "material": "concrete"}, {"x": 6, "y": 4, "h": 15, "material": "concrete"}, {"x": 6, "y": 8, "h": 15, "material": "concrete"}, {"x": 7, "y": 0, "h": 15, "material": "concrete"}, {"x": 7, "y": 2, "h": 15, "material": "concrete"}, {"x": 7, "y": 3, "h": 5, "material": "concrete"}, {"x": 7, "y": 4, "h": 15, "material": "concrete"}, {"x": 7, "y": 5, "h": 5, "material": "concrete"}, {"x": 7, "y": 6, "h": 5, "material": "concrete"}, {"x": 7, "y": 7, "h": 5, "material": "concrete"}, {"x": 7, "y": 8, "h": 5, "material": "concrete"}, {"x": 7, "y": 9, "h": 15, "material": "concrete"}, {"x": 8, "y": 2, "h": 5, "material": "concrete"}, {"x": 8, "y": 3, "h": 5, "material": "concrete"}, {"x": 8, "y": 7, "h": 5, "material": "concrete"}, {"x": 9, "y": 3, "h": 5, "material": "concrete"}, {"x": 9, "y": 4, "h": 5, "material": "concrete"}, {"x": 9, "y": 6, "h": 15, "material": "concrete"}, {"x": 9, "y": 7, "h": 15, "material": "concrete"}],
            sources: [{x: 3, y: 3, intensity: 1200}, {x: 7, y: 6, intensity: 1000}]
        },
        'kolkata': {
            buildings: [{"x": 0, "y": 2, "h": 5, "material": "concrete"}, {"x": 0, "y": 3, "h": 5, "material": "concrete"}, {"x": 0, "y": 6, "h": 5, "material": "concrete"}, {"x": 0, "y": 7, "h": 5, "material": "concrete"}, {"x": 0, "y": 8, "h": 5, "material": "hospital"}, {"x": 0, "y": 9, "h": 5, "material": "concrete"}, {"x": 1, "y": 3, "h": 5, "material": "concrete"}, {"x": 1, "y": 5, "h": 5, "material": "concrete"}, {"x": 1, "y": 6, "h": 5, "material": "concrete"}, {"x": 1, "y": 7, "h": 5, "material": "concrete"}, {"x": 1, "y": 8, "h": 5, "material": "concrete"}, {"x": 1, "y": 9, "h": 5, "material": "concrete"}, {"x": 2, "y": 4, "h": 5, "material": "concrete"}, {"x": 2, "y": 5, "h": 15, "material": "concrete"}, {"x": 2, "y": 6, "h": 12, "material": "concrete"}, {"x": 2, "y": 7, "h": 5, "material": "concrete"}, {"x": 2, "y": 8, "h": 5, "material": "concrete"}, {"x": 2, "y": 9, "h": 5, "material": "concrete"}, {"x": 3, "y": 2, "h": 5, "material": "concrete"}, {"x": 3, "y": 4, "h": 5, "material": "hospital"}, {"x": 3, "y": 6, "h": 5, "material": "concrete"}, {"x": 3, "y": 7, "h": 5, "material": "concrete"}, {"x": 3, "y": 8, "h": 5, "material": "concrete"}, {"x": 3, "y": 9, "h": 5, "material": "concrete"}, {"x": 4, "y": 2, "h": 5, "material": "concrete"}, {"x": 4, "y": 4, "h": 5, "material": "concrete"}, {"x": 4, "y": 6, "h": 5, "material": "concrete"}, {"x": 4, "y": 7, "h": 5, "material": "concrete"}, {"x": 4, "y": 8, "h": 5, "material": "concrete"}, {"x": 4, "y": 9, "h": 5, "material": "concrete"}, {"x": 5, "y": 1, "h": 5, "material": "concrete"}, {"x": 5, "y": 2, "h": 5, "material": "concrete"}, {"x": 5, "y": 3, "h": 5, "material": "concrete"}, {"x": 5, "y": 4, "h": 5, "material": "concrete"}, {"x": 5, "y": 7, "h": 5, "material": "concrete"}, {"x": 5, "y": 8, "h": 5, "material": "concrete"}, {"x": 5, "y": 9, "h": 5, "material": "concrete"}, {"x": 6, "y": 0, "h": 5, "material": "concrete"}, {"x": 6, "y": 2, "h": 5, "material": "concrete"}, {"x": 6, "y": 3, "h": 5, "material": "concrete"}, {"x": 6, "y": 4, "h": 5, "material": "concrete"}, {"x": 6, "y": 5, "h": 5, "material": "concrete"}, {"x": 6, "y": 7, "h": 5, "material": "concrete"}, {"x": 6, "y": 8, "h": 5, "material": "concrete"}, {"x": 6, "y": 9, "h": 5, "material": "concrete"}, {"x": 7, "y": 2, "h": 5, "material": "concrete"}, {"x": 7, "y": 3, "h": 5, "material": "concrete"}, {"x": 7, "y": 4, "h": 5, "material": "concrete"}, {"x": 7, "y": 5, "h": 5, "material": "concrete"}, {"x": 7, "y": 6, "h": 5, "material": "concrete"}, {"x": 7, "y": 7, "h": 5, "material": "concrete"}, {"x": 7, "y": 8, "h": 5, "material": "concrete"}, {"x": 7, "y": 9, "h": 5, "material": "hospital"}, {"x": 8, "y": 0, "h": 5, "material": "concrete"}, {"x": 8, "y": 1, "h": 5, "material": "concrete"}, {"x": 8, "y": 3, "h": 5, "material": "concrete"}, {"x": 8, "y": 4, "h": 5, "material": "concrete"}, {"x": 8, "y": 5, "h": 5, "material": "concrete"}, {"x": 8, "y": 6, "h": 5, "material": "concrete"}, {"x": 8, "y": 7, "h": 5, "material": "concrete"}, {"x": 8, "y": 8, "h": 5, "material": "concrete"}, {"x": 8, "y": 9, "h": 5, "material": "concrete"}, {"x": 9, "y": 1, "h": 5, "material": "concrete"}, {"x": 9, "y": 3, "h": 5, "material": "concrete"}, {"x": 9, "y": 4, "h": 5, "material": "concrete"}, {"x": 9, "y": 5, "h": 5, "material": "concrete"}, {"x": 9, "y": 6, "h": 5, "material": "concrete"}, {"x": 9, "y": 7, "h": 5, "material": "concrete"}, {"x": 9, "y": 8, "h": 5, "material": "concrete"}, {"x": 9, "y": 9, "h": 5, "material": "concrete"}],
            sources: [{x: 4, y: 7, intensity: 1500}, {x: 8, y: 5, intensity: 1200}, {x: 1, y: 9, intensity: 1000}]
        }
    };

    presetSelect.addEventListener('change', (e) => {
        const presetId = e.target.value;
        const preset = PRESETS[presetId];
        if (preset) {
            buildings = JSON.parse(JSON.stringify(preset.buildings));
            sources = JSON.parse(JSON.stringify(preset.sources));
            
            const isMapPreset = (presetId === 'barcelona' || presetId === 'kolkata');
            const mapDiv = document.getElementById('map');
            
            if (isMapPreset) {
                mapDiv.style.display = 'block';
                setMapView(presetId);
                plannerCanvas.style.backgroundColor = 'transparent';
            } else {
                mapDiv.style.display = 'none';
                plannerCanvas.style.backgroundColor = '#020617';
            }
            
            drawGrid(isMapPreset); // Pass parameter to control grid visibility
            plannerOverlay.innerHTML = '';
            lastSimData = null;
            suggestionBox.classList.add('hidden');
        }
    });

    // Canvas Constants
    const GRID_SIZE = 10;
    const CELL_PX = plannerCanvas.width / GRID_SIZE;

    const drawGrid = (isMap = false) => {
        ctx.clearRect(0, 0, plannerCanvas.width, plannerCanvas.height);
        
        if (!isMap) {
            ctx.strokeStyle = '#333';
            ctx.fillStyle = '#666';
            ctx.font = '12px Inter, sans-serif';

            for(let i=0; i<=GRID_SIZE; i++) {
                // Draw grid lines
                ctx.beginPath();
                ctx.moveTo(i * CELL_PX, 0);
                ctx.lineTo(i * CELL_PX, plannerCanvas.height);
                ctx.stroke();
                ctx.beginPath();
                ctx.moveTo(0, i * CELL_PX);
                ctx.lineTo(plannerCanvas.width, i * CELL_PX);
                ctx.stroke();

                // Add numbers
                if (i < GRID_SIZE) {
                    // X-axis (top)
                    ctx.fillText(i, i * CELL_PX + CELL_PX/2 - 4, 15);
                    // Y-axis (left)
                    ctx.fillText(i, 5, i * CELL_PX + CELL_PX/2 + 4);
                }
            }
        }


        buildings.forEach(b => {
            let hue = b.material === 'glass' ? 200 : b.material === 'concrete' ? 0 : b.material === 'hospital' ? 340 : 120;
            // Use 0.4 opactity in map mode to reveal the underlying OSM map, and 0.8 in grid mode
            const alpha = isMap ? 0.4 : 0.8;
            ctx.fillStyle = `hsla(${hue}, 70%, 50%, ${alpha})`;
            ctx.fillRect(b.x * CELL_PX + 5, b.y * CELL_PX + 5, CELL_PX - 10, CELL_PX - 10);
            
            // Text Color
            ctx.fillStyle = isMap ? '#fff' : '#fff';
            ctx.font = '10px Arial';
            ctx.fillText(`${b.h}m`, b.x * CELL_PX + 15, b.y * CELL_PX + CELL_PX - 15);
            
            // Draw H for Hospital
            if (b.material === 'hospital') {
                ctx.fillStyle = '#fff';
                ctx.font = 'bold 20px Arial';
                ctx.fillText('H', b.x * CELL_PX + CELL_PX/2 - 8, b.y * CELL_PX + CELL_PX/2 + 8);
            }
        });

        sources.forEach(s => {
            ctx.fillStyle = '#ff4b2b';
            ctx.beginPath();
            ctx.arc(s.x * CELL_PX + CELL_PX/2, s.y * CELL_PX + CELL_PX/2, 8, 0, Math.PI*2);
            ctx.fill();
            // Pulse effect
            ctx.strokeStyle = '#ff4b2b';
            ctx.beginPath();
            ctx.arc(s.x * CELL_PX + CELL_PX/2, s.y * CELL_PX + CELL_PX/2, 12, 0, Math.PI*2);
            ctx.stroke();
        });
    };

    plannerCanvas.addEventListener('mousedown', (e) => {
        handlePointer(e);
    });

    plannerCanvas.addEventListener('touchstart', (e) => {
        e.preventDefault();
        handlePointer(e.touches[0]);
    }, { passive: false });

    const handlePointer = (e) => {
        const rect = plannerCanvas.getBoundingClientRect();
        const scaleX = plannerCanvas.width / rect.width;
        const scaleY = plannerCanvas.height / rect.height;
        const x = Math.floor(((e.clientX - rect.left) * scaleX) / CELL_PX);
        const y = Math.floor(((e.clientY - rect.top) * scaleY) / CELL_PX);

        if (x < 0 || x >= GRID_SIZE || y < 0 || y >= GRID_SIZE) return;

        if (currentTool === 'eraser') {
            buildings = buildings.filter(b => b.x !== x || b.y !== y);
            sources = sources.filter(s => s.x !== x || s.y !== y);
        } else if (currentTool === 'building') {
            const h = document.getElementById('planner-h').value;
            const material = document.getElementById('planner-material').value;
            buildings = buildings.filter(b => b.x !== x || b.y !== y);
            buildings.push({ x, y, h: parseInt(h), material });
        } else if (currentTool === 'source') {
            sources = sources.filter(s => s.x !== x || s.y !== y);
            sources.push({ x, y, intensity: 500 }); // Adjusted intensity
        }
        drawGrid();
    };

    toolBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            toolBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentTool = btn.dataset.tool;
        });
    });

    layerBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            layerBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentLayer = btn.dataset.layer;
            if (lastSimData) renderPlannerHeatmap(lastSimData);
        });
    });

    const renderPlannerHeatmap = (data) => {
        plannerOverlay.innerHTML = '';
        const map = currentLayer === 'spl' ? data.spl : data.variance;
        // Adjusted ranges for better visual resolution
        const range = currentLayer === 'spl' ? [50, 85] : [0, 4];

        for(let i=0; i<GRID_SIZE; i++) {
            for(let j=0; j<GRID_SIZE; j++) {
                const val = map[j][i];
                const cell = document.createElement('div');
                cell.className = 'heatmap-cell';
                
                // Calculate ratio with slightly more contrast
                let ratio = (val - range[0]) / (range[1] - range[0]);
                ratio = Math.max(0, Math.min(1, ratio));
                
                // Noise (SPL): Green (120) -> Red (0)
                // Variance: Blue (240) -> Purple (280)
                const hue = currentLayer === 'spl' ? (1 - ratio) * 120 : 240 + (ratio * 40);
                const alpha = ratio * 0.7 + 0.1; // Make quiet areas more transparent
                
                cell.style.backgroundColor = `hsla(${hue}, 100%, 50%, ${alpha})`;
                plannerOverlay.appendChild(cell);
            }
        }
    };

    runPlannerBtn.addEventListener('click', async () => {
        const response = await fetch('/api/planner/simulate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ buildings, sources })
        });
        lastSimData = await response.json();
        renderPlannerHeatmap(lastSimData);
    });

    suggestBtn.addEventListener('click', async () => {
        if (!lastSimData) return;
        const response = await fetch('/api/planner/suggest', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                spl: lastSimData.spl, 
                variance: lastSimData.variance,
                buildings,
                sources
            })
        });
        const data = await response.json();
        
        suggestionBox.classList.remove('hidden');
        suggestionList.innerHTML = '';
        data.suggestions.forEach(s => {
            const li = document.createElement('li');
            li.innerHTML = `<strong>Block (${s.x}, ${s.y}):</strong> Suggested <i>${s.type}</i>. Reason: ${s.reason}`;
            suggestionList.appendChild(li);
        });
    });

    window.addEventListener('plannerVisible', () => {
        if (typeof L !== 'undefined' && document.getElementById('map')) {
            initMap();
            leafletMap.invalidateSize();
        }
    });
});

function showTab(tabId) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(t => t.classList.add('hidden'));
    // Show selected tab
    document.getElementById(`${tabId}-tab`).classList.remove('hidden');
    
    // If planner tab, init/refresh map
    if (tabId === 'planner') {
        const plannerEvent = new CustomEvent('plannerVisible');
        window.dispatchEvent(plannerEvent);
    }

    // Update nav links

    document.querySelectorAll('.nav-links a').forEach(a => a.classList.remove('active'));
    event.currentTarget.classList.add('active');
}
