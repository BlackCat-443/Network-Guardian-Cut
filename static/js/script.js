// [file name]: static/js/script.js
// [file content begin]
// DOM Elements
const activeSection = document.querySelector('.active-section');
const navLinks = document.querySelectorAll('nav a');
const refreshBtn = document.getElementById('refresh-btn');
const refreshDevicesBtn = document.getElementById('refresh-devices-btn');
const saveSettingsBtn = document.getElementById('save-settings');
const lastUpdateTime = document.getElementById('last-update-time');
const deviceSearch = document.getElementById('device-search');
const scanInterval = document.getElementById('scan-interval');

// Stat Badges Elements
const totalDevicesBadge = document.getElementById('total-devices-badge')?.querySelector('.stat-value');
const onlineDevicesBadge = document.getElementById('online-devices-badge')?.querySelector('.stat-value');
const cutDevicesBadge = document.getElementById('cut-devices-badge')?.querySelector('.stat-value');
const offlineDevicesBadge = document.getElementById('offline-devices-badge')?.querySelector('.stat-value');
const trustedDevicesBadge = document.getElementById('trusted-devices-badge')?.querySelector('.stat-value');
const newDevicesBadge = document.getElementById('new-devices-badge')?.querySelector('.stat-value');

// Modal Elements
const confirmModal = document.getElementById('confirm-modal');
const modalTitle = document.getElementById('modal-title');
const modalMessage = document.getElementById('modal-message');
let modalConfirm = document.getElementById('modal-confirm');
const modalCancel = document.getElementById('modal-cancel');
const closeModal = document.querySelectorAll('.close-modal');

// Device detail drawer
const deviceDetailModal = document.getElementById('device-detail-modal');
let deviceDetailTimer = null;
let selectedDeviceIp = null;

// Rename Modal Elements
const renameModal = document.getElementById('rename-modal');
let renameConfirm = document.getElementById('rename-confirm');
const renameCancel = document.getElementById('rename-cancel');
const newHostnameInput = document.getElementById('new-hostname');

// NetCut Modal Elements
const netcutInfoModal = document.getElementById('netcut-info-modal');
const netcutInfoClose = document.getElementById('netcut-info-close');
const netcutViewLogs = document.getElementById('netcut-view-logs');
const netcutHelp = document.getElementById('netcut-help');

// Chart variables
let networkChart;
let chartDatasets = {
    download: [],
    upload: [],
    labels: []
};

// NetCut variables
let netcutStatus = {
    engine_active: false,
    active_cuts: [],
    total_cuts: 0,
    gateway_ip: '--',
    gateway_mac: '--',
    cut_targets: []
};

// =========================================================
// Guardian UX state
// =========================================================
const STORAGE_KEYS = {
    trusted: 'ng_trusted_devices_v1',
    history: 'ng_device_history_v1',
    known: 'ng_known_devices_v1',
    notifications: 'ng_notifications_v1'
};

let featureStateInitialized = false;
let latestDevices = [];

function readStorage(key, fallback) {
    try {
        const value = localStorage.getItem(key);
        return value ? JSON.parse(value) : fallback;
    } catch (error) {
        console.warn('Storage read failed:', key, error);
        return fallback;
    }
}

function writeStorage(key, value) {
    try {
        localStorage.setItem(key, JSON.stringify(value));
    } catch (error) {
        console.warn('Storage write failed:', key, error);
    }
}

function deviceStorageKey(device) {
    const mac = String(device?.mac || '').trim().toUpperCase();
    return mac && mac !== 'UNKNOWN' && mac !== '--' ? `mac:${mac}` : `ip:${device?.ip || ''}`;
}

function getTrustedDevices() {
    return readStorage(STORAGE_KEYS.trusted, {});
}

function isTrustedDevice(device) {
    const trusted = getTrustedDevices();
    return Boolean(trusted[deviceStorageKey(device)]);
}

function toggleTrustedDevice(device) {
    const trusted = getTrustedDevices();
    const key = deviceStorageKey(device);

    if (trusted[key]) {
        delete trusted[key];
        addNotification('info', 'Device untrusted', `${device.hostname || device.ip} is no longer marked as trusted.`);
        showToast(`${device.hostname || device.ip} removed from trusted devices`, 'info');
    } else {
        trusted[key] = {
            ip: device.ip,
            hostname: device.hostname || 'Unknown device',
            mac: device.mac || 'Unknown',
            trusted_at: new Date().toISOString()
        };
        addNotification('success', 'Device trusted', `${device.hostname || device.ip} was marked as trusted.`);
        showToast(`${device.hostname || device.ip} marked as trusted`, 'success');
    }

    writeStorage(STORAGE_KEYS.trusted, trusted);
    updateDeviceList();
    updateNetworkMap(latestDevices);
}

function addHistoryEntry(device, status) {
    if (!device?.ip) return;
    const allHistory = readStorage(STORAGE_KEYS.history, {});
    const key = deviceStorageKey(device);
    const entries = Array.isArray(allHistory[key]) ? allHistory[key] : [];

    const stamp = device.last_seen || new Date().toLocaleString();
    const last = entries[0];
    if (last && last.status === status) return;

    entries.unshift({
        status,
        time: stamp,
        hostname: device.hostname || 'Unknown device',
        ip: device.ip
    });

    allHistory[key] = entries.slice(0, 20);
    writeStorage(STORAGE_KEYS.history, allHistory);
}

function renderDeviceHistory(device) {
    const container = document.getElementById('detail-history');
    if (!container) return;

    const allHistory = readStorage(STORAGE_KEYS.history, {});
    const key = deviceStorageKey(device);
    const entries = Array.isArray(allHistory[key]) ? allHistory[key] : [];

    if (!entries.length) {
        container.innerHTML = '<div class="history-empty"><i class="fas fa-clock-rotate-left"></i><span>No history recorded yet.</span></div>';
        return;
    }

    container.innerHTML = '';
    entries.slice(0, 10).forEach(entry => {
        const row = document.createElement('div');
        row.className = 'history-row';

        const marker = document.createElement('span');
        marker.className = `history-marker ${entry.status === 'up' ? 'online' : entry.status === 'blocked' ? 'blocked' : 'offline'}`;

        const content = document.createElement('div');
        content.className = 'history-content';

        const title = document.createElement('strong');
        title.textContent = entry.status === 'up' ? 'Online' : entry.status === 'blocked' ? 'Blocked' : 'Offline';

        const time = document.createElement('span');
        time.textContent = entry.time || '--';

        content.appendChild(title);
        content.appendChild(time);
        row.appendChild(marker);
        row.appendChild(content);
        container.appendChild(row);
    });
}

function detectNewDevices(data) {
    const known = readStorage(STORAGE_KEYS.known, {});
    const currentKeys = {};
    let newCount = 0;

    data.forEach(device => {
        const key = deviceStorageKey(device);
        currentKeys[key] = true;
        addHistoryEntry(device, device.blocked ? 'blocked' : device.status);

        if (!featureStateInitialized) {
            return;
        }

        if (!known[key]) {
            newCount += 1;
            known[key] = {
                first_seen: device.first_seen || new Date().toISOString(),
                ip: device.ip,
                hostname: device.hostname || 'Unknown device'
            };

            addNotification(
                'warning',
                'New device detected',
                `${device.hostname || 'Unknown device'} · ${device.ip || '--'}`
            );
        }
    });

    // Keep known history, but remove nothing: a device coming back online is not "new" again.
    writeStorage(STORAGE_KEYS.known, known);

    const newBadge = document.getElementById('new-devices-badge')?.querySelector('.stat-value');
    if (newBadge) {
        newBadge.textContent = Object.keys(known).length;
    }

    return newCount;
}

function addNotification(type, title, message) {
    const list = readStorage(STORAGE_KEYS.notifications, []);

    list.unshift({
        id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        type,
        title,
        message,
        time: new Date().toISOString(),
        read: false
    });

    writeStorage(STORAGE_KEYS.notifications, list.slice(0, 40));
    renderNotifications();
}

function formatNotificationTime(value) {
    if (!value) return '--';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString([], {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function renderNotifications() {
    const listEl = document.getElementById('notification-list');
    const countEl = document.getElementById('notification-count');
    const summaryEl = document.getElementById('notification-summary');
    if (!listEl) return;

    const notifications = readStorage(STORAGE_KEYS.notifications, []);
    const unread = notifications.filter(item => !item.read);

    if (countEl) {
        countEl.textContent = unread.length > 99 ? '99+' : unread.length;
        countEl.hidden = unread.length === 0;
    }

    if (summaryEl) {
        summaryEl.textContent = unread.length ? `${unread.length} new alert${unread.length > 1 ? 's' : ''}` : 'No new alerts';
    }

    listEl.innerHTML = '';

    if (!notifications.length) {
        listEl.innerHTML = '<div class="notification-empty"><i class="fas fa-check-circle"></i><span>You\'re all caught up.</span></div>';
        return;
    }

    notifications.slice(0, 12).forEach(item => {
        const row = document.createElement('button');
        row.type = 'button';
        row.className = `notification-item ${item.read ? 'read' : 'unread'}`;

        const icon = document.createElement('span');
        icon.className = `notification-icon ${item.type || 'info'}`;
        icon.innerHTML = item.type === 'warning' ? '<i class="fas fa-triangle-exclamation"></i>' : item.type === 'success' ? '<i class="fas fa-check"></i>' : '<i class="fas fa-info"></i>';

        const body = document.createElement('span');
        body.className = 'notification-body';
        const title = document.createElement('strong');
        title.textContent = item.title || 'Notification';
        const message = document.createElement('span');
        message.textContent = item.message || '';
        const time = document.createElement('small');
        time.textContent = formatNotificationTime(item.time);

        body.appendChild(title);
        body.appendChild(message);
        body.appendChild(time);
        row.appendChild(icon);
        row.appendChild(body);

        row.addEventListener('click', () => {
            const all = readStorage(STORAGE_KEYS.notifications, []);
            const target = all.find(entry => entry.id === item.id);
            if (target) target.read = true;
            writeStorage(STORAGE_KEYS.notifications, all);
            renderNotifications();
        });

        listEl.appendChild(row);
    });
}

function markNotificationsRead() {
    const notifications = readStorage(STORAGE_KEYS.notifications, []);
    notifications.forEach(item => { item.read = true; });
    writeStorage(STORAGE_KEYS.notifications, notifications);
    renderNotifications();
}

function clearNotifications() {
    writeStorage(STORAGE_KEYS.notifications, []);
    renderNotifications();
}

function updateNetworkMap(data = latestDevices) {
    const canvas = document.getElementById('network-map-canvas');
    if (!canvas) return;

    const gateway = data.find(device => device.is_gateway);
    const local = data.find(device => device.is_local);
    const clients = data.filter(device => !device.is_gateway && !device.is_local);
    const unknown = clients.filter(device => !isTrustedDevice(device));

    const gatewayLabel = document.getElementById('map-gateway-label');
    const localLabel = document.getElementById('map-local-label');
    const clientCount = document.getElementById('map-client-count');
    const unknownCount = document.getElementById('map-unknown-count');

    if (gatewayLabel) gatewayLabel.textContent = gateway?.ip || '--';
    if (localLabel) localLabel.textContent = local?.ip || '--';
    if (clientCount) clientCount.textContent = clients.length;
    if (unknownCount) unknownCount.textContent = unknown.length;

    canvas.innerHTML = '';

    if (!gateway && !local && !clients.length) {
        canvas.innerHTML = '<div class="map-empty"><i class="fas fa-network-wired"></i><span>No devices available. Run a scan first.</span></div>';
        return;
    }

    const root = document.createElement('div');
    root.className = 'map-root';

    const gatewayNode = document.createElement('button');
    gatewayNode.type = 'button';
    gatewayNode.className = 'map-node gateway-node';
    gatewayNode.innerHTML = '<i class="fas fa-router"></i><strong>Gateway</strong><span>--</span>';
    const gatewayValue = gatewayNode.querySelector('span');
    if (gatewayValue) gatewayValue.textContent = gateway?.ip || 'Not detected';
    if (gateway?.ip) gatewayNode.addEventListener('click', () => openDeviceDetails(gateway.ip));
    root.appendChild(gatewayNode);

    const line = document.createElement('div');
    line.className = 'map-trunk';
    root.appendChild(line);

    const branch = document.createElement('div');
    branch.className = 'map-branch';

    const visibleClients = [local, ...clients].filter(Boolean);
    visibleClients.forEach(device => {
        const node = document.createElement('button');
        node.type = 'button';
        const trusted = isTrustedDevice(device);
        const isLocal = device.is_local;
        const state = device.status === 'up' ? 'online' : device.status === 'down' ? 'offline' : 'unknown';
        node.className = `map-node client-node ${trusted ? 'trusted-node' : 'unknown-node'} ${isLocal ? 'local-node' : ''} ${state}`;

        const icon = device.device_type?.toLowerCase().includes('phone') || device.device_type?.toLowerCase().includes('mobile') ? 'fa-mobile-screen' : device.device_type?.toLowerCase().includes('tv') ? 'fa-tv' : device.device_type?.toLowerCase().includes('router') ? 'fa-router' : 'fa-laptop';
        const badge = isLocal ? 'This device' : trusted ? 'Trusted' : 'Unknown';

        node.innerHTML = `<i class="fas ${icon}"></i><strong></strong><span></span><em>${badge}</em>`;
        node.querySelector('strong').textContent = device.hostname || 'Unknown device';
        node.querySelector('span').textContent = device.ip || '--';
        node.addEventListener('click', () => openDeviceDetails(device.ip));
        branch.appendChild(node);
    });

    root.appendChild(branch);
    canvas.appendChild(root);
}

// Function to format bytes into human-readable format
function formatBytes(bytes, decimals = 2) {
    if (bytes === 0 || bytes === undefined || bytes === null) return '0 Bytes';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

// Function to format bandwidth (bytes per second)
function formatBandwidth(bytesPerSec) {
    if (bytesPerSec === undefined || bytesPerSec === null) return '0 B/s';
    return formatBytes(bytesPerSec) + '/s';
}

// Function to update dashboard stats - FIXED VERSION
function updateDashboardStats() {
    fetch('/api/stats')
        .then(response => response.json())
        .then(data => {
            console.log('Stats data:', data); // Debug
            
            // Update stat cards di dashboard
            document.getElementById('network-status').textContent = data.netcut_active ? 'NetCut Active' : 'Online';
            document.getElementById('active-devices').textContent = data.active_devices || 0;
            document.getElementById('blocked-devices').textContent = data.blocked_devices || 0;
            document.getElementById('download-stats').textContent = formatBandwidth(data.download_rate);
            document.getElementById('upload-stats').textContent = formatBandwidth(data.upload_rate);
            document.getElementById('local-ip').textContent = data.local_ip || '--';
            document.getElementById('gateway-ip').textContent = data.gateway_ip || '--';
            document.getElementById('interface').textContent = data.interface || '--';
            document.getElementById('netcut-global-status').textContent = data.netcut_active ? 'Active' : 'Inactive';
            document.getElementById('system-hostname').textContent = data.hostname || '--';
            document.getElementById('last-scan-time').textContent = data.last_scan || '--';
            
            if (lastUpdateTime) {
                lastUpdateTime.textContent = data.timestamp || '--';
            }
            
            // Update system info jika ada
            fetch('/api/system-info')
                .then(res => res.json())
                .then(sysData => {
                    document.getElementById('system-platform').textContent = sysData.platform || '--';
                    
                    // Format uptime
                    const uptime = sysData.uptime || 0;
                    const days = Math.floor(uptime / 86400);
                    const hours = Math.floor((uptime % 86400) / 3600);
                    const minutes = Math.floor((uptime % 3600) / 60);
                    document.getElementById('system-uptime').textContent = 
                        `${days}d ${hours}h ${minutes}m`;
                })
                .catch(err => console.error('Error fetching system info:', err));
        })
        .catch(error => {
            console.error('Error fetching stats:', error);
            showToast('Error fetching network stats', 'error');
        });
}

// Function to update NetCut status - FIXED VERSION
function updateNetCutStatus() {
    fetch('/api/netcut/status')
        .then(response => response.json())
        .then(data => {
            console.log('NetCut status:', data); // Debug
            netcutStatus = data;
            
            // Update NetCut UI status di dashboard
            const netcutGlobalStatus = document.getElementById('netcut-global-status');
            if (netcutGlobalStatus) {
                netcutGlobalStatus.textContent = data.engine_active ? 'Active' : 'Inactive';
            }
            
            // Update NetCut engine status di section netcut
            const netcutEngineStatus = document.getElementById('netcut-engine-status');
            if (netcutEngineStatus) {
                if (data.engine_active) {
                    netcutEngineStatus.innerHTML = '<i class="fas fa-power-off"></i> NetCut Engine: ACTIVE';
                    netcutEngineStatus.className = 'netcut-status-active';
                } else {
                    netcutEngineStatus.innerHTML = '<i class="fas fa-power-off"></i> NetCut Engine: INACTIVE';
                    netcutEngineStatus.className = 'netcut-status-inactive';
                }
            }
            
            // Update gateway info di netcut section
            document.getElementById('netcut-gateway-ip').textContent = data.gateway_ip || '--';
            document.getElementById('netcut-gateway-mac').textContent = data.gateway_mac || '--';
            document.getElementById('netcut-interface').textContent = data.interface || '--';
            document.getElementById('netcut-local-ip').textContent = data.local_ip || '--';
            
            // Update active cuts count
            const activeCutsCount = document.getElementById('active-cuts-count');
            if (activeCutsCount) {
                activeCutsCount.textContent = data.total_cuts || 0;
            }
            
            // Update active cuts list
            updateActiveCutsList(data.cut_targets || []);
        })
        .catch(error => {
            console.error('Error fetching NetCut status:', error);
        });
}

// Function to update active cuts list
function updateActiveCutsList(cutTargets) {
    const container = document.getElementById('active-cuts-container');
    if (!container) return;
    
    if (cutTargets && cutTargets.length > 0) {
        container.innerHTML = '';
        cutTargets.forEach(target => {
            const cutItem = document.createElement('div');
            cutItem.className = 'cut-item';
            cutItem.innerHTML = `
                <div class="cut-info">
                    <div class="cut-ip">${target.ip}</div>
                    <div class="cut-mac">${target.mac || 'MAC unknown'}</div>
                    <div class="cut-time">Since: ${target.start_time || 'Unknown'}</div>
                </div>
                <button class="btn-restore-cut" data-ip="${target.ip}">
                    <i class="fas fa-wifi"></i> Restore
                </button>
            `;
            container.appendChild(cutItem);
            
            // Add event listener untuk restore button
            cutItem.querySelector('.btn-restore-cut').addEventListener('click', function() {
                const ip = this.getAttribute('data-ip');
                restoreSingleTarget(ip);
            });
        });
    } else {
        container.innerHTML = `
            <div class="no-cuts-message">
                <i class="fas fa-wifi"></i>
                <p>No active internet cuts</p>
            </div>
        `;
    }
}

function restoreSingleTarget(ip) {
    fetch('/api/netcut/restore', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ target_ip: ip })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            showToast(`Internet restored for ${ip}`, 'success');
            updateNetCutStatus();
            updateDeviceList();
            updateDashboardStats();
        } else {
            showToast(data.message || 'Failed to restore', 'error');
        }
    })
    .catch(error => {
        console.error('Error restoring target:', error);
        showToast('Failed to restore internet', 'error');
    });
}

// Function to update traffic chart - FIXED VERSION
function updateTrafficChart() {
    fetch('/api/traffic-history')
        .then(response => response.json())
        .then(data => {
            console.log('Traffic data:', data); // Debug
            
            if (!data.timestamps || data.timestamps.length === 0) {
                return;
            }
            
            const formattedLabels = data.timestamps.map(timestamp => {
                try {
                    const date = new Date(timestamp);
                    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
                } catch {
                    return timestamp;
                }
            });
            
            // Hitung rates
            const downloadRates = [];
            const uploadRates = [];
            
            for (let i = 1; i < data.download.length; i++) {
                const prevTime = new Date(data.timestamps[i - 1]);
                const currTime = new Date(data.timestamps[i]);
                const timeDiff = (currTime - prevTime) / 1000; // in seconds
                
                const downloadDiff = data.download[i] - data.download[i - 1];
                const uploadDiff = data.upload[i] - data.upload[i - 1];
                
                const downloadRate = timeDiff > 0 ? downloadDiff / timeDiff : 0;
                const uploadRate = timeDiff > 0 ? uploadDiff / timeDiff : 0;
                
                downloadRates.push(downloadRate / 1024); // Convert to KB/s
                uploadRates.push(uploadRate / 1024);
            }
            
            // Duplicate first value untuk alignment
            if (downloadRates.length > 0) {
                downloadRates.unshift(downloadRates[0]);
                uploadRates.unshift(uploadRates[0]);
            }
            
            chartDatasets.labels = formattedLabels;
            chartDatasets.download = downloadRates;
            chartDatasets.upload = uploadRates;
            
            updateChart();
        })
        .catch(error => {
            console.error('Error fetching traffic history:', error);
        });
}

// Function to initialize and update the chart - FIXED VERSION
function updateChart() {
    const ctx = document.getElementById('network-chart');
    if (!ctx) return;
    
    if (networkChart) {
        networkChart.data.labels = chartDatasets.labels;
        networkChart.data.datasets[0].data = chartDatasets.download;
        networkChart.data.datasets[1].data = chartDatasets.upload;
        networkChart.update();
    } else {
        networkChart = new Chart(ctx.getContext('2d'), {
            type: 'line',
            data: {
                labels: chartDatasets.labels,
                datasets: [
                    {
                        label: 'Download (KB/s)',
                        data: chartDatasets.download,
                        borderColor: 'rgba(52, 152, 219, 1)',
                        backgroundColor: 'rgba(52, 152, 219, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4
                    },
                    {
                        label: 'Upload (KB/s)',
                        data: chartDatasets.upload,
                        borderColor: 'rgba(46, 204, 113, 1)',
                        backgroundColor: 'rgba(46, 204, 113, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: {
                    duration: 1000,
                    easing: 'easeOutQuart'
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Speed (KB/s)'
                        },
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        }
                    },
                    x: {
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        }
                    }
                },
                plugins: {
                    legend: {
                        position: 'top'
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                if (context.parsed.y !== null) {
                                    label += parseFloat(context.parsed.y).toFixed(2) + ' KB/s';
                                }
                                return label;
                            }
                        }
                    }
                },
                interaction: {
                    mode: 'nearest',
                    axis: 'x',
                    intersect: false
                }
            }
        });
    }
}

// Device detail drawer -----------------------------------------------------
function setDetailText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value == null || value === '' ? '--' : value;
}

function formatMbps(value) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) return '--';
    const n = Number(value);
    if (n >= 1000) return `${(n / 1000).toFixed(2)} Gbps`;
    return `${n.toFixed(1)} Mbps`;
}

function formatSignal(value) {
    if (value === null || value === undefined) return '--';
    return `${Number(value).toFixed(0)} dBm`;
}

function formatFrequency(value) {
    if (value === null || value === undefined) return '--';
    const ghz = Number(value) / 1000;
    return `${ghz.toFixed(2)} GHz`;
}

function setDetailStatus(status) {
    const el = document.getElementById('detail-status-pill');
    if (!el) return;
    el.className = 'detail-status-pill';
    const normalized = String(status || '').toLowerCase();
    if (normalized === 'up') {
        el.classList.add('is-online');
        el.textContent = '● Online';
    } else if (normalized === 'blocked') {
        el.classList.add('is-blocked');
        el.textContent = '● Blocked';
    } else {
        el.classList.add('is-offline');
        el.textContent = '● Offline';
    }
}

function renderDeviceDetails(data) {
    const wifi = data.wifi || {};
    const traffic = data.traffic || {};

    setDetailText('device-detail-title', data.hostname || 'Unknown device');
    setDetailText('device-detail-subtitle', `${data.ip || '--'}${data.vendor && data.vendor !== 'Unknown' ? ` · ${data.vendor}` : ''}`);
    setDetailText('detail-hostname', data.hostname);
    setDetailText('detail-ip', data.ip);
    setDetailText('detail-mac', data.mac);
    setDetailText('detail-vendor', data.vendor);
    setDetailText('detail-type', data.device_type);
    setDetailText('detail-role', data.is_gateway ? 'Gateway' : (data.is_local ? 'This device' : 'Client'));
    setDetailText('detail-last-seen', `Last seen: ${data.last_seen || '--'}`);
    setDetailStatus(data.status);

    setDetailText('detail-wifi-tech', wifi.technology || 'Not exposed');
    setDetailText('detail-wifi-ssid', wifi.ssid || (wifi.available ? 'Connected network' : 'Not available'));
    setDetailText('detail-rx-rate', formatMbps(wifi.rx_bitrate_mbps));
    setDetailText('detail-tx-rate', formatMbps(wifi.tx_bitrate_mbps));
    setDetailText('detail-frequency', formatFrequency(wifi.frequency_mhz));
    setDetailText('detail-signal', formatSignal(wifi.signal_dbm));
    setDetailText('detail-wifi-note', wifi.note || 'Wi-Fi information unavailable.');

    if (traffic.rx_mbps !== null && traffic.rx_mbps !== undefined) {
        setDetailText('detail-traffic-rx', formatMbps(traffic.rx_mbps));
        const bar = document.getElementById('detail-traffic-bar');
        if (bar) bar.style.width = `${Math.min(100, Math.max(4, Number(traffic.rx_mbps) / 2))}%`;
    } else {
        setDetailText('detail-traffic-rx', 'Sampling…');
        const bar = document.getElementById('detail-traffic-bar');
        if (bar) bar.style.width = '8%';
    }
    setDetailText('detail-traffic-note', traffic.note || 'Per-device traffic is unavailable on this host.');

    renderDeviceHistory({
        ip: data.ip,
        hostname: data.hostname,
        mac: data.mac
    });
}

async function loadDeviceDetails(ip) {
    if (!ip) return;
    try {
        const response = await fetch(`/api/device/${encodeURIComponent(ip)}/details`, { cache: 'no-store' });
        const data = await response.json();
        if (!response.ok) throw new Error(data.message || 'Device details unavailable');
        renderDeviceDetails(data);
    } catch (error) {
        console.error('Device detail error:', error);
        const loading = document.getElementById('device-detail-loading');
        if (loading) {
            loading.innerHTML = '<i class="fas fa-triangle-exclamation"></i><span>Device details could not be loaded.</span>';
        }
    }
}

function openDeviceDetails(ip) {
    if (!deviceDetailModal || !ip) return;
    selectedDeviceIp = ip;
    deviceDetailModal.classList.add('open');
    deviceDetailModal.setAttribute('aria-hidden', 'false');
    document.body.classList.add('detail-drawer-open');

    const loading = document.getElementById('device-detail-loading');
    const content = document.getElementById('device-detail-content');
    if (loading) {
        loading.innerHTML = '<i class="fas fa-circle-notch fa-spin"></i><span>Loading device information…</span>';
        loading.hidden = false;
    }
    if (content) content.hidden = true;

    loadDeviceDetails(ip).finally(() => {
        if (loading) loading.hidden = true;
        if (content) content.hidden = false;
    });

    clearInterval(deviceDetailTimer);
    deviceDetailTimer = setInterval(() => {
        if (selectedDeviceIp && deviceDetailModal.classList.contains('open')) loadDeviceDetails(selectedDeviceIp);
    }, 2500);
}

function closeDeviceDetails() {
    if (!deviceDetailModal) return;
    deviceDetailModal.classList.remove('open');
    deviceDetailModal.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('detail-drawer-open');
    selectedDeviceIp = null;
    clearInterval(deviceDetailTimer);
}

if (deviceDetailModal) {
    deviceDetailModal.querySelectorAll('[data-close-device-detail]').forEach(el => {
        el.addEventListener('click', closeDeviceDetails);
    });
}

document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && deviceDetailModal?.classList.contains('open')) closeDeviceDetails();
});

// Function to update device list - enhanced UX version
function updateDeviceList() {
    fetch('/api/devices')
        .then(response => response.json())
        .then(data => {
            latestDevices = Array.isArray(data) ? data : [];

            const devicesList = document.getElementById('devices-list');
            if (!devicesList) return;

            const searchTerm = deviceSearch ? deviceSearch.value.trim().toLowerCase() : '';

            latestDevices.forEach(device => {
                if (netcutStatus.active_cuts && netcutStatus.active_cuts.includes(device.ip)) {
                    device.status = 'down';
                    device.blocked = true;
                }
            });

            const total = latestDevices.length;
            const online = latestDevices.filter(device => {
                const isCut = netcutStatus.active_cuts?.includes(device.ip);
                return !isCut && !device.blocked && device.status === 'up';
            }).length;
            const cut = latestDevices.filter(device => {
                const isCut = netcutStatus.active_cuts?.includes(device.ip);
                return isCut || device.blocked;
            }).length;
            const offline = Math.max(0, total - online - cut);
            const trusted = latestDevices.filter(device => isTrustedDevice(device)).length;

            const newCount = detectNewDevices(latestDevices);

            const filteredDevices = latestDevices.filter(device => {
                if (!searchTerm) return true;
                return (device.hostname || '').toLowerCase().includes(searchTerm) ||
                    (device.ip || '').toLowerCase().includes(searchTerm) ||
                    (device.mac || '').toLowerCase().includes(searchTerm) ||
                    (device.vendor || '').toLowerCase().includes(searchTerm) ||
                    (device.device_type || '').toLowerCase().includes(searchTerm);
            });

            devicesList.innerHTML = '';

            if (!filteredDevices.length) {
                const empty = document.createElement('tr');
                empty.innerHTML = '<td colspan="6" class="table-empty"><i class="fas fa-magnifying-glass"></i><strong>No devices found</strong><span>Try another hostname, IP, MAC, vendor or device type.</span></td>';
                devicesList.appendChild(empty);
            }

            filteredDevices.forEach(device => {
                const row = document.createElement('tr');
                const trustedDevice = isTrustedDevice(device);

                const statusCell = document.createElement('td');
                const statusDiv = document.createElement('div');
                statusDiv.className = 'device-status';
                const statusIndicator = document.createElement('span');
                statusIndicator.className = 'status-indicator';
                let statusText = 'Offline';

                if (netcutStatus.active_cuts?.includes(device.ip)) {
                    statusIndicator.classList.add('status-netcut');
                    statusText = 'No Internet';
                } else if (device.blocked) {
                    statusIndicator.classList.add('status-blocked');
                    statusText = 'Blocked';
                } else if (device.status === 'up') {
                    statusIndicator.classList.add('status-online');
                    statusText = 'Online';
                } else {
                    statusIndicator.classList.add('status-offline');
                }

                statusDiv.appendChild(statusIndicator);
                statusDiv.appendChild(document.createTextNode(statusText));
                statusCell.appendChild(statusDiv);
                row.appendChild(statusCell);

                const hostnameCell = document.createElement('td');
                const hostnameWrap = document.createElement('div');
                hostnameWrap.className = 'device-name-cell';
                const hostname = document.createElement('strong');
                hostname.textContent = device.hostname || 'Unknown';
                const meta = document.createElement('span');
                meta.textContent = device.vendor || device.device_type || 'Unknown device';
                hostnameWrap.appendChild(hostname);
                hostnameWrap.appendChild(meta);
                if (trustedDevice) {
                    const trustBadge = document.createElement('span');
                    trustBadge.className = 'inline-badge trusted-badge';
                    trustBadge.innerHTML = '<i class="fas fa-shield-check"></i> Trusted';
                    hostnameWrap.appendChild(trustBadge);
                } else {
                    const unknownBadge = document.createElement('span');
                    unknownBadge.className = 'inline-badge unknown-badge';
                    unknownBadge.textContent = 'Unknown';
                    hostnameWrap.appendChild(unknownBadge);
                }
                hostnameCell.appendChild(hostnameWrap);
                row.appendChild(hostnameCell);

                const ipCell = document.createElement('td');
                const ipButton = document.createElement('button');
                ipButton.type = 'button';
                ipButton.className = 'ip-link';
                ipButton.textContent = device.ip || '--';
                ipButton.title = 'Open device details';
                ipButton.addEventListener('click', () => openDeviceDetails(device.ip));
                ipCell.appendChild(ipButton);
                row.appendChild(ipCell);

                const macCell = document.createElement('td');
                macCell.textContent = device.mac || '--';
                macCell.className = 'mono-cell';
                row.appendChild(macCell);

                const lastSeenCell = document.createElement('td');
                lastSeenCell.textContent = device.last_seen || '--';
                lastSeenCell.className = 'last-seen-cell';
                row.appendChild(lastSeenCell);

                const actionsCell = document.createElement('td');
                const actionsDiv = document.createElement('div');
                actionsDiv.className = 'device-actions';

                const detailsBtn = document.createElement('button');
                detailsBtn.className = 'action-btn btn-details';
                detailsBtn.innerHTML = '<i class="fas fa-eye"></i> Details';
                detailsBtn.addEventListener('click', () => openDeviceDetails(device.ip));

                const trustBtn = document.createElement('button');
                trustBtn.className = `action-btn ${trustedDevice ? 'btn-untrust' : 'btn-trust'}`;
                trustBtn.innerHTML = trustedDevice ? '<i class="fas fa-shield"></i> Untrust' : '<i class="fas fa-shield-check"></i> Trust';
                trustBtn.addEventListener('click', () => toggleTrustedDevice(device));

                const blockBtn = document.createElement('button');
                blockBtn.className = 'action-btn';
                if (netcutStatus.active_cuts?.includes(device.ip) || device.blocked) {
                    blockBtn.classList.add('btn-netcut-unblock');
                    blockBtn.innerHTML = '<i class="fas fa-wifi"></i> Restore';
                    blockBtn.addEventListener('click', () => showConfirmModal('unblock', device));
                } else {
                    blockBtn.classList.add('btn-netcut-block');
                    blockBtn.innerHTML = '<i class="fas fa-wifi-slash"></i> Cut';
                    blockBtn.addEventListener('click', () => showConfirmModal('block', device));
                }

                const renameBtn = document.createElement('button');
                renameBtn.className = 'action-btn btn-rename';
                renameBtn.innerHTML = '<i class="fas fa-edit"></i> Rename';
                renameBtn.addEventListener('click', () => showRenameModal(device));

                actionsDiv.appendChild(detailsBtn);
                actionsDiv.appendChild(trustBtn);
                actionsDiv.appendChild(blockBtn);
                actionsDiv.appendChild(renameBtn);

                // Keep Kick available, but less visually dominant than Details/Trust.
                const kickBtn = document.createElement('button');
                kickBtn.className = 'action-btn btn-netcut-kick';
                kickBtn.innerHTML = '<i class="fas fa-power-off"></i> Kick';
                kickBtn.addEventListener('click', () => showConfirmModal('kick', device));
                actionsDiv.appendChild(kickBtn);

                actionsCell.appendChild(actionsDiv);
                row.appendChild(actionsCell);
                devicesList.appendChild(row);
            });

            if (totalDevicesBadge) totalDevicesBadge.textContent = total;
            if (onlineDevicesBadge) onlineDevicesBadge.textContent = online;
            if (cutDevicesBadge) cutDevicesBadge.textContent = cut;
            if (offlineDevicesBadge) offlineDevicesBadge.textContent = offline;
            if (trustedDevicesBadge) trustedDevicesBadge.textContent = trusted;
            if (newDevicesBadge) newDevicesBadge.textContent = newCount;

            const activeDevices = document.getElementById('active-devices');
            const blockedDevices = document.getElementById('blocked-devices');
            if (activeDevices) activeDevices.textContent = online;
            if (blockedDevices) blockedDevices.textContent = cut;

            updateNetworkMap(latestDevices);
            renderNotifications();
            featureStateInitialized = true;
        })
        .catch(error => {
            console.error('Error fetching devices:', error);
            showToast('Error fetching device list', 'error');
        });
}

// Function to show confirmation modal
function showConfirmModal(action, device) {
    if (!confirmModal) return;
    
    let title, message;
    
    if (action === 'block') {
        title = 'Cut Internet (NetCut)';
        message = `Cut internet connection for ${device.hostname || device.ip} (${device.ip})?`;
    } else if (action === 'unblock') {
        title = 'Restore Internet';
        message = `Restore internet connection for ${device.hostname || device.ip} (${device.ip})?`;
    } else if (action === 'kick') {
        title = 'Kick Device';
        message = `Temporarily disconnect ${device.hostname || device.ip} (${device.ip}) for 30 seconds?`;
    }
    
    modalTitle.textContent = title;
    modalMessage.textContent = message;
    confirmModal.style.display = 'block';
    
    // Setup confirm button
    const confirmBtn = document.getElementById('modal-confirm');
    const newConfirmBtn = confirmBtn.cloneNode(true);
    confirmBtn.parentNode.replaceChild(newConfirmBtn, confirmBtn);
    
    newConfirmBtn.addEventListener('click', () => {
        confirmModal.style.display = 'none';
        
        if (action === 'block') {
            fetch('/api/netcut/cut', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ target_ip: device.ip })
            })
            .then(res => res.json())
            .then(data => {
                if (data.status === 'success') {
                    showToast(`Internet cut for ${device.hostname || device.ip}`, 'success');
                    updateDeviceList();
                    updateDashboardStats();
                    updateNetCutStatus();
                } else {
                    showToast(data.message || 'Failed to cut internet', 'error');
                }
            })
            .catch(err => {
                console.error('Error:', err);
                showToast('Failed to cut internet', 'error');
            });
            
        } else if (action === 'unblock') {
            fetch('/api/netcut/restore', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ target_ip: device.ip })
            })
            .then(res => res.json())
            .then(data => {
                if (data.status === 'success') {
                    showToast(`Internet restored for ${device.hostname || device.ip}`, 'success');
                    updateDeviceList();
                    updateDashboardStats();
                    updateNetCutStatus();
                } else {
                    showToast(data.message || 'Failed to restore', 'error');
                }
            })
            .catch(err => {
                console.error('Error:', err);
                showToast('Failed to restore internet', 'error');
            });
            
        } else if (action === 'kick') {
            fetch('/api/kick-device', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ identifier: device.ip })
            })
            .then(res => res.json())
            .then(data => {
                if (data.status === 'success') {
                    showToast(`${device.hostname || device.ip} kicked for 30 seconds`, 'success');
                    updateDeviceList();
                    updateDashboardStats();
                    updateNetCutStatus();
                    
                    setTimeout(() => {
                        updateDeviceList();
                        updateNetCutStatus();
                    }, 31000);
                } else {
                    showToast(data.message || 'Failed to kick', 'error');
                }
            })
            .catch(err => {
                console.error('Error:', err);
                showToast('Failed to kick device', 'error');
            });
        }
    });
}

// Function to show rename modal
function showRenameModal(device) {
    if (!renameModal) return;
    
    renameModal.style.display = 'block';
    newHostnameInput.value = device.hostname || '';
    
    const confirmBtn = document.getElementById('rename-confirm');
    const newConfirmBtn = confirmBtn.cloneNode(true);
    confirmBtn.parentNode.replaceChild(newConfirmBtn, confirmBtn);
    
    newConfirmBtn.addEventListener('click', () => {
        const newHostname = newHostnameInput.value.trim();
        if (newHostname) {
            renameDevice(device.ip, newHostname);
            renameModal.style.display = 'none';
        } else {
            showToast('Hostname cannot be empty', 'error');
        }
    });
}

// Function to rename a device
function renameDevice(ip, newHostname) {
    fetch('/api/rename-device', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ip, newHostname })
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'success') {
            showToast(data.message, 'success');
            updateDeviceList();
        } else {
            showToast(data.message || 'Failed to rename', 'error');
        }
    })
    .catch(err => {
        console.error('Error:', err);
        showToast('Failed to rename device', 'error');
    });
}

// Function to show toast notification
function showToast(message, type = 'info') {
    let toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container';
        document.body.appendChild(toastContainer);
    }
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    let icon;
    switch (type) {
        case 'success': icon = 'fas fa-check-circle'; break;
        case 'error': icon = 'fas fa-exclamation-circle'; break;
        case 'warning': icon = 'fas fa-exclamation-triangle'; break;
        default: icon = 'fas fa-info-circle';
    }
    
    toast.innerHTML = `
        <div class="toast-content">
            <span class="toast-icon"><i class="${icon}"></i></span>
            <span>${message}</span>
        </div>
        <span class="toast-close"><i class="fas fa-times"></i></span>
    `;
    
    toastContainer.appendChild(toast);
    
    toast.querySelector('.toast-close').addEventListener('click', () => {
        toast.remove();
    });
    
    setTimeout(() => {
        toast.remove();
    }, 3000);
}

// Function to refresh all data
function refreshAll() {
    if (refreshBtn) {
        refreshBtn.classList.add('loading');
    }
    
    fetch('/api/scan')
        .then(res => res.json())
        .then(data => {
            console.log('Scan triggered:', data);
            setTimeout(() => {
                updateDashboardStats();
                updateDeviceList();
                updateNetCutStatus();
                updateTrafficChart();
                
                if (refreshBtn) {
                    refreshBtn.classList.remove('loading');
                }
                showToast('Dashboard refreshed', 'success');
            }, 1000);
        })
        .catch(err => {
            console.error('Error:', err);
            if (refreshBtn) {
                refreshBtn.classList.remove('loading');
            }
            showToast('Failed to refresh', 'error');
        });
}

// Function to refresh devices only
function refreshDevices() {
    if (refreshDevicesBtn) {
        refreshDevicesBtn.classList.add('loading');
    }
    
    fetch('/api/scan')
        .then(res => res.json())
        .then(data => {
            console.log('Devices scan triggered:', data);
            setTimeout(() => {
                updateDeviceList();
                updateNetCutStatus();
                
                if (refreshDevicesBtn) {
                    refreshDevicesBtn.classList.remove('loading');
                }
                showToast('Device list refreshed', 'success');
            }, 1000);
        })
        .catch(err => {
            console.error('Error:', err);
            if (refreshDevicesBtn) {
                refreshDevicesBtn.classList.remove('loading');
            }
            showToast('Failed to refresh devices', 'error');
        });
}

// Function to save settings
function saveSettings() {
    if (!scanInterval) return;
    
    const newInterval = parseInt(scanInterval.value);
    if (isNaN(newInterval) || newInterval < 30) {
        showToast('Scan interval must be at least 30 seconds', 'warning');
        return;
    }
    
    fetch('/api/update-settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scan_interval: newInterval })
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'success') {
            showToast('Settings saved successfully', 'success');
        } else {
            showToast(data.message || 'Failed to save', 'error');
        }
    })
    .catch(err => {
        console.error('Error:', err);
        showToast('Failed to save settings', 'error');
    });
}

// Navigation functionality
navLinks.forEach(link => {
    link.addEventListener('click', (e) => {
        e.preventDefault();
        
        navLinks.forEach(navLink => {
            navLink.parentElement.classList.remove('active');
        });
        
        document.querySelectorAll('section').forEach(section => {
            section.classList.remove('active-section');
        });
        
        link.parentElement.classList.add('active');
        
        const targetId = link.getAttribute('href').substring(1);
        const targetSection = document.getElementById(targetId);
        if (targetSection) {
            targetSection.classList.add('active-section');
            
            if (targetId === 'devices') {
                updateDeviceList();
            } else if (targetId === 'network-map') {
                updateNetworkMap(latestDevices);
                updateDeviceList();
            } else if (targetId === 'netcut') {
                updateNetCutStatus();
            }
        }
    });
});

// Event listeners
if (refreshBtn) refreshBtn.addEventListener('click', refreshAll);
if (refreshDevicesBtn) refreshDevicesBtn.addEventListener('click', refreshDevices);
if (saveSettingsBtn) saveSettingsBtn.addEventListener('click', saveSettings);
if (deviceSearch) deviceSearch.addEventListener('input', updateDeviceList);

// Modal close buttons
closeModal.forEach(btn => {
    btn.addEventListener('click', function() {
        if (confirmModal) confirmModal.style.display = 'none';
        if (renameModal) renameModal.style.display = 'none';
        if (netcutInfoModal) netcutInfoModal.style.display = 'none';
    });
});

if (modalCancel) {
    modalCancel.addEventListener('click', () => {
        if (confirmModal) confirmModal.style.display = 'none';
    });
}

if (renameCancel) {
    renameCancel.addEventListener('click', () => {
        if (renameModal) renameModal.style.display = 'none';
    });
}

// Close modals when clicking outside
window.addEventListener('click', (e) => {
    if (e.target === confirmModal) {
        confirmModal.style.display = 'none';
    }
    if (e.target === renameModal) {
        renameModal.style.display = 'none';
    }
    if (e.target === netcutInfoModal) {
        netcutInfoModal.style.display = 'none';
    }
});

// NetCut quick actions
if (document.getElementById('netcut-restore-all')) {
    document.getElementById('netcut-restore-all').addEventListener('click', () => {
        if (confirm('Restore internet for ALL devices?')) {
            fetch('/api/netcut/restore', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({})
            })
            .then(res => res.json())
            .then(data => {
                if (data.status === 'success') {
                    showToast('All internet connections restored', 'success');
                    updateDeviceList();
                    updateDashboardStats();
                    updateNetCutStatus();
                }
            })
            .catch(err => {
                console.error('Error:', err);
                showToast('Failed to restore all', 'error');
            });
        }
    });
}

if (document.getElementById('netcut-test')) {
    document.getElementById('netcut-test').addEventListener('click', () => {
        fetch('/api/netcut/test')
            .then(res => res.json())
            .then(data => {
                if (data.status === 'success') {
                    showToast('NetCut Engine is running', 'info');
                    updateNetCutStatus();
                }
            })
            .catch(err => {
                console.error('Error:', err);
                showToast('NetCut test failed', 'error');
            });
    });
}

if (document.getElementById('netcut-cleanup')) {
    document.getElementById('netcut-cleanup').addEventListener('click', () => {
        if (confirm('Cleanup all NetCut cuts and restore internet?')) {
            fetch('/api/netcut/flush-all')
                .then(res => res.json())
                .then(data => {
                    if (data.status === 'success') {
                        showToast('All cuts cleaned up', 'success');
                        updateDeviceList();
                        updateDashboardStats();
                        updateNetCutStatus();
                    }
                })
                .catch(err => {
                    console.error('Error:', err);
                    showToast('Cleanup failed', 'error');
                });
        }
    });
}

if (netcutHelp) {
    netcutHelp.addEventListener('click', () => {
        if (netcutInfoModal) {
            netcutInfoModal.style.display = 'block';
        }
    });
}

if (netcutInfoClose) {
    netcutInfoClose.addEventListener('click', () => {
        if (netcutInfoModal) {
            netcutInfoModal.style.display = 'none';
        }
    });
}

// Handle mass rename from JSON file
const renameMassBtn = document.getElementById('rename-mass-btn');
const renameMassUpload = document.getElementById('rename-mass-upload');

if (renameMassBtn && renameMassUpload) {
    renameMassBtn.addEventListener('click', () => {
        const file = renameMassUpload.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (e) => {
                try {
                    const jsonData = JSON.parse(e.target.result);
                    processMassRename(jsonData);
                } catch (err) {
                    showToast('Invalid JSON file', 'error');
                }
            };
            reader.readAsText(file);
        } else {
            showToast('Please select a JSON file', 'error');
        }
    });
}

function processMassRename(jsonData) {
    if (!Array.isArray(jsonData)) {
        showToast('JSON must be an array of {ip, newHostname}', 'error');
        return;
    }
    
    fetch('/api/devices')
        .then(res => res.json())
        .then(devices => {
            const validData = [];
            const invalidIPs = [];
            
            jsonData.forEach(item => {
                if (!item.ip || !item.newHostname) return;
                
                const exists = devices.some(d => d.ip === item.ip);
                if (exists) {
                    validData.push({ ip: item.ip, newHostname: item.newHostname });
                } else {
                    invalidIPs.push(item.ip);
                }
            });
            
            if (validData.length > 0) {
                fetch('/api/rename-devices-mass', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(validData)
                })
                .then(res => res.json())
                .then(data => {
                    if (data.status === 'success') {
                        showToast(data.message, 'success');
                        updateDeviceList();
                    } else {
                        showToast(data.message || 'Failed to rename', 'error');
                    }
                })
                .catch(err => {
                    console.error('Error:', err);
                    showToast('Failed to rename devices', 'error');
                });
            }
            
            if (invalidIPs.length > 0) {
                showToast(`IPs not found: ${invalidIPs.join(', ')}`, 'warning');
            }
        })
        .catch(err => {
            console.error('Error:', err);
            showToast('Failed to fetch devices', 'error');
        });
}

// Notification and map controls
const notificationBtn = document.getElementById('notification-btn');
const notificationPanel = document.getElementById('notification-panel');
const notificationClear = document.getElementById('notification-clear');
const mapRefreshBtn = document.getElementById('map-refresh-btn');

if (notificationBtn && notificationPanel) {
    notificationBtn.addEventListener('click', (event) => {
        event.stopPropagation();
        const opening = notificationPanel.hidden;
        notificationPanel.hidden = !opening;
        notificationBtn.setAttribute('aria-expanded', opening ? 'true' : 'false');
    });
}

if (notificationClear) {
    notificationClear.addEventListener('click', () => {
        clearNotifications();
    });
}

if (mapRefreshBtn) {
    mapRefreshBtn.addEventListener('click', () => {
        mapRefreshBtn.classList.add('loading');
        updateDeviceList();
        setTimeout(() => mapRefreshBtn.classList.remove('loading'), 700);
    });
}

window.addEventListener('click', (event) => {
    if (!notificationPanel || !notificationBtn) return;
    if (!notificationPanel.contains(event.target) && !notificationBtn.contains(event.target)) {
        notificationPanel.hidden = true;
        notificationBtn.setAttribute('aria-expanded', 'false');
    }
});

renderNotifications();

// Initialize dashboard
document.addEventListener('DOMContentLoaded', () => {
    console.log('Dashboard initializing...');
    
    // Initial updates
    updateDashboardStats();
    updateTrafficChart();
    updateDeviceList();
    updateNetCutStatus();
    
    // Set auto-refresh intervals
    setInterval(() => {
        updateDashboardStats();
        updateTrafficChart();
    }, 10000);
    
    setInterval(() => {
        updateNetCutStatus();
    }, 5000);
    
    setInterval(() => {
        updateDeviceList();
    }, 15000);
    
    // Update current time di footer
    setInterval(() => {
        const currentTimeEl = document.getElementById('current-time');
        if (currentTimeEl) {
            const now = new Date();
            currentTimeEl.textContent = now.toLocaleTimeString();
        }
    }, 1000);
});
// [file content end]