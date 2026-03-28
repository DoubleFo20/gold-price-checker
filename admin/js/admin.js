// admin/js/admin.js v3 — real API connections

const API = {
    checkSession: '/api/api/auth/check_session.php',
    thaiPrice:    '/api/thai-gold-price',
    worldPrice:   '/api/world-gold-price',
    adminStats:   '/api/admin/stats',
    adminAlerts:  '/api/admin/alerts',
    adminUsers:   '/api/admin/users',
    adminForecasts: '/api/admin/forecasts',
    runJob:       '/api/jobs/run',
    news:         '/api/news',
};

let dashChart = null;
let usersList = [];

/* ===========================
   INIT
   =========================== */
document.addEventListener('DOMContentLoaded', async () => {
    await checkAuth();
    setupNav();
    setupTopbar();
    loadDashboard();
});

/* ===========================
   AUTH CHECK
   =========================== */
async function checkAuth() {
    try {
        const res  = await fetch(API.checkSession, { method: 'POST', credentials: 'include' });
        const data = await res.json();
        if (!data.authenticated || data.user?.role !== 'admin') {
            window.location.href = '/';
            return;
        }
        const name = data.user.name || 'Admin';
        document.getElementById('user-name-display').textContent = name;
        document.getElementById('user-avatar').textContent = name.charAt(0).toUpperCase();
        document.getElementById('settings-user-info').textContent =
            `${name} — ${data.user.email || ''}  (role: ${data.user.role})`;
    } catch (e) {
        console.error('Auth error', e);
        window.location.href = '/';
    }
}

/* ===========================
   SIDEBAR NAVIGATION
   =========================== */
function setupNav() {
    const links   = document.querySelectorAll('.nav-link[data-target]');
    const sections = document.querySelectorAll('.page-section');
    const pageTitle = document.getElementById('page-title');

    links.forEach(link => {
        link.addEventListener('click', e => {
            e.preventDefault();
            links.forEach(l => l.classList.remove('active'));
            link.classList.add('active');
            const target = link.dataset.target;
            sections.forEach(s => {
                s.classList.remove('active');
                s.classList.add('hidden');
            });
            const sec = document.getElementById(`section-${target}`);
            if (sec) { sec.classList.remove('hidden'); sec.classList.add('active'); }
            pageTitle.textContent = link.querySelector('span')?.textContent || target;
            loadSection(target);

            // close mobile sidebar
            document.getElementById('sidebar')?.classList.remove('open');
        });
    });

    // Mobile toggle
    document.getElementById('sidebarToggle')?.addEventListener('click', () => {
        document.getElementById('sidebar').classList.toggle('open');
    });

    // Refresh all
    document.getElementById('btn-refresh-all')?.addEventListener('click', loadDashboard);
}

/* ===========================
   TOPBAR USER MENU
   =========================== */
function setupTopbar() {
    document.getElementById('btn-logout-topbar')?.addEventListener('click', async e => {
        e.preventDefault();
        localStorage.clear();
        fetch('/api/api/auth/logout.php', { method: 'POST', credentials: 'include' }).catch(() => {});
        window.location.href = '/';
    });
}

/* ===========================
   SECTION LOADER
   =========================== */
function loadSection(target) {
    switch (target) {
        case 'dashboard':  loadDashboard();  break;
        case 'gold-price': loadGoldPrice();  break;
        case 'news':       loadNews();       break;
        case 'alerts':     loadAlerts();     break;
        case 'users':      loadUsers();      break;
        case 'forecast':   loadForecasts();  break;
        case 'logs':       loadLogs();       break;
        case 'settings':   setupSettings();  break;
    }
}

/* ===========================
   DASHBOARD
   =========================== */
async function loadDashboard() {
    loadThaiPrice();
    loadWorldPrice();
    loadAdminStats();
    loadDashChart();
}

async function loadThaiPrice() {
    try {
        const res  = await fetch(API.thaiPrice);
        const data = await res.json();
        document.getElementById('kv-thai-bar-sell').textContent = `฿${Number(data.bar_sell || 0).toLocaleString()}`;
        const diff = data.change_baht ?? null;
        if (diff !== null) {
            const sign = diff >= 0 ? '+' : '';
            document.getElementById('kv-thai-change').textContent = `${sign}${Number(diff).toLocaleString()} วันนี้`;
        } else {
            document.getElementById('kv-thai-change').textContent = 'อัปเดตล่าสุด: ' + (data.date || '—');
        }
        // also fill price live grid on dashboard
        renderPriceLiveGrid('price-live-grid', data);
        // also for fetch button
        document.getElementById('btn-fetch-price')?.addEventListener('click', loadThaiPrice);
    } catch (e) {
        document.getElementById('kv-thai-bar-sell').textContent = 'Error';
        console.error(e);
    }
}

async function loadWorldPrice() {
    try {
        const res  = await fetch(API.worldPrice);
        const data = await res.json();
        const price = data.price_usd_per_ounce ?? data.price ?? 0;
        document.getElementById('kv-world-price').textContent = `$${Number(price).toLocaleString(undefined, {maximumFractionDigits:2})}`;
        document.getElementById('kv-world-change').textContent = data.source_note || 'XAUUSD';
    } catch(e) {
        document.getElementById('kv-world-price').textContent = 'Error';
    }
}

async function loadAdminStats() {
    try {
        const res  = await fetch(API.adminStats, { credentials: 'include' });
        const data = await res.json();
        if (data.success && data.data) {
            const d = data.data;
            document.getElementById('kv-users').textContent = Number(d.users_count).toLocaleString();
            document.getElementById('kv-alerts-count').textContent = `Alerts: ${d.alerts_count}`;
            document.getElementById('badge-users').textContent = d.users_count;
            document.getElementById('badge-alerts').textContent = d.alerts_count;
        }
    } catch(e) { console.error('stats error', e); }

    // ping for status
    try {
        const t0 = Date.now();
        await fetch('/ping');
        const ms = Date.now() - t0;
        document.getElementById('kv-status').textContent = 'API Online';
        document.getElementById('kv-status-time').textContent = `Response: ${ms}ms`;
    } catch(e) {
        document.getElementById('kv-status').textContent = 'API Offline';
        document.getElementById('kv-status').classList.replace('green-text', 'red-text');
    }
}

async function loadDashChart() {
    try {
        const res  = await fetch('/api/historical?days=7');
        const data = await res.json();
        document.getElementById('chart-source').textContent = data.source || 'Historical';
        const ctx = document.getElementById('dash-chart').getContext('2d');
        if (dashChart) dashChart.destroy();
        dashChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.labels || [],
                datasets: [{
                    label: 'ราคาทองแท่ง (THB)',
                    data: data.thai_values || [],
                    borderColor: '#d4a843',
                    backgroundColor: 'rgba(212,168,67,0.08)',
                    borderWidth: 2,
                    tension: 0.4,
                    pointRadius: 3,
                    pointBackgroundColor: '#d4a843',
                    fill: true,
                }]
            },
            options: {
                responsive: true,
                plugins: { legend: { display: false } },
                scales: {
                    x: { ticks: { color: '#555e72', font: { size: 11 } }, grid: { color: '#232737' } },
                    y: { ticks: { color: '#555e72', font: { size: 11 }, callback: v => `฿${v.toLocaleString()}` }, grid: { color: '#232737' } }
                }
            }
        });
    } catch(e) { document.getElementById('chart-source').textContent = 'Error loading chart'; }
}

/* ===========================
   GOLD PRICE SECTION
   =========================== */
async function loadGoldPrice() {
    document.getElementById('price-last-update').textContent = 'กำลังดึงข้อมูล...';
    try {
        const res  = await fetch(API.thaiPrice);
        const data = await res.json();
        document.getElementById('price-last-update').textContent = `อัปเดตล่าสุด: ${data.date || '—'}  แหล่งข้อมูล: ${data.source || 'GTA'}`;
        renderPriceLiveGrid('price-detail-grid', data, true);
    } catch(e) { document.getElementById('price-last-update').textContent = 'Error loading price'; }

    // Fetch latest button
    document.getElementById('btn-fetch-latest')?.addEventListener('click', loadGoldPrice);

    // Price history table
    try {
        const res  = await fetch('/api/admin/price-history', { credentials: 'include' });
        const data = await res.json();
        if (data.success && data.items?.length) {
            const fmt = v => v ? Number(v).toLocaleString() : '—';
            document.getElementById('price-history-tbody').innerHTML = data.items.map(r => `
                <tr>
                    <td>${r.date || '—'}</td>
                    <td class="text-gold">฿${fmt(r.bar_buy)}</td>
                    <td class="text-gold">฿${fmt(r.bar_sell)}</td>
                    <td>฿${fmt(r.ornament_buy)}</td>
                    <td>฿${fmt(r.ornament_sell)}</td>
                </tr>`).join('');
        } else {
            document.getElementById('price-history-tbody').innerHTML =
                '<tr><td colspan="5" class="text-center text-sub">ยังไม่มีประวัติราคา</td></tr>';
        }
    } catch(e) { console.error(e); }
}

function renderPriceLiveGrid(id, data, lg = false) {
    const el = document.getElementById(id);
    if (!el) return;
    const fmt = v => v ? Number(v).toLocaleString() : '—';
    el.innerHTML = `
        <div class="price-tile"><div class="price-tile-label">ทองแท่ง 96.5% — รับซื้อ</div><div class="price-tile-value buy">฿${fmt(data.bar_buy)}</div></div>
        <div class="price-tile"><div class="price-tile-label">ทองแท่ง 96.5% — ขายออก</div><div class="price-tile-value sell">฿${fmt(data.bar_sell)}</div></div>
        <div class="price-tile"><div class="price-tile-label">ทองรูปพรรณ 90% — รับซื้อ</div><div class="price-tile-value buy">฿${fmt(data.ornament_buy)}</div></div>
        <div class="price-tile"><div class="price-tile-label">ทองรูปพรรณ 90% — ขายออก</div><div class="price-tile-value sell">฿${fmt(data.ornament_sell)}</div></div>
    `;
    el.className = `price-live-grid${lg ? ' lg' : ''}`;
}

/* ===========================
   NEWS SECTION
   =========================== */
async function loadNews() {
    try {
        const res  = await fetch(API.news);
        const items = await res.json();
        if (!Array.isArray(items) || !items.length) {
            document.getElementById('news-tbody').innerHTML =
                '<tr><td colspan="4" class="text-center text-sub">ไม่มีข่าว</td></tr>';
            return;
        }
        document.getElementById('news-tbody').innerHTML = items.slice(0, 30).map(n => `
            <tr>
                <td style="max-width:300px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${esc(n.title || '—')}</td>
                <td><span class="pill pill-gold">${esc(n.source || '—')}</span></td>
                <td class="text-sub">${n.published_at ? n.published_at.slice(0,16) : '—'}</td>
                <td>${n.link ? `<a href="${n.link}" target="_blank" style="color:var(--gold);font-size:12px;">เปิดอ่าน</a>` : '—'}</td>
            </tr>`).join('');
    } catch(e) {
        document.getElementById('news-tbody').innerHTML =
            '<tr><td colspan="4" class="text-center text-sub">Error: ' + e.message + '</td></tr>';
    }
    document.getElementById('btn-fetch-news')?.addEventListener('click', loadNews);
}

/* ===========================
   ALERTS SECTION
   =========================== */
async function loadAlerts() {
    try {
        const res  = await fetch(API.adminAlerts, { credentials: 'include' });
        const data = await res.json();
        const items = data.items || [];
        const pending   = items.filter(a => !a.triggered).length;
        const triggered = items.filter(a =>  a.triggered).length;
        document.getElementById('alerts-pending-count').textContent  = `รอแจ้งเตือน: ${pending}`;
        document.getElementById('alerts-triggered-count').textContent = `แจ้งเตือนแล้ว: ${triggered}`;

        const goldTypeLabel = t => t === 'ornament' ? 'รูปพรรณ' : t === 'world' ? 'โลก(USD)' : 'แท่ง';
        const alertTypeLabel = t => t === 'above' ? '≥ ราคา' : '≤ ราคา';

        document.getElementById('alerts-tbody').innerHTML = items.length
            ? items.map(a => `<tr>
                <td>${esc(a.email || '—')}</td>
                <td>${goldTypeLabel(a.gold_type)}</td>
                <td>${alertTypeLabel(a.alert_type)}</td>
                <td class="text-gold">฿${Number(a.target_price).toLocaleString()}</td>
                <td>${a.triggered
                    ? '<span class="pill pill-green">แจ้งเตือนแล้ว</span>'
                    : '<span class="pill pill-gold">รอแจ้งเตือน</span>'}</td>
                <td class="text-sub">${a.created_at ? a.created_at.slice(0,16) : '—'}</td>
              </tr>`).join('')
            : '<tr><td colspan="6" class="text-center text-sub">ยังไม่มีการแจ้งเตือน</td></tr>';
    } catch(e) {
        document.getElementById('alerts-tbody').innerHTML =
            `<tr><td colspan="6" class="text-center text-sub">Error: ${e.message}</td></tr>`;
    }
}

/* ===========================
   USERS SECTION (CRUD)
   =========================== */
async function loadUsers() {
    try {
        const res  = await fetch(API.adminUsers, { credentials: 'include' });
        const data = await res.json();
        usersList  = data.users || [];
        document.getElementById('users-total-count').textContent = `ทั้งหมด: ${usersList.length}`;
        document.getElementById('users-tbody').innerHTML = usersList.length
            ? usersList.map(u => `<tr>
                <td>${esc(u.name || '—')}</td>
                <td>${esc(u.email || '—')}</td>
                <td><span class="pill ${u.role === 'admin' ? 'pill-gold' : 'pill-blue'}">${esc(u.role)}</span></td>
                <td>${u.is_active ? '<span class="pill pill-green">Active</span>' : '<span class="pill pill-red">Inactive</span>'}</td>
                <td class="text-sub">${u.created_at ? u.created_at.slice(0,10) : '—'}</td>
                <td>
                    <button class="btn-xs btn-outline" style="color:var(--blue); border-color:var(--blue);" onclick="openUserModal(${u.id})"><i class="fas fa-edit"></i></button>
                    <button class="btn-xs btn-outline" style="color:var(--red); border-color:var(--red);" onclick="deleteUser(${u.id}, '${esc(u.name)}')"><i class="fas fa-trash"></i></button>
                </td>
              </tr>`).join('')
            : '<tr><td colspan="6" class="text-center text-sub">ไม่มีผู้ใช้งาน</td></tr>';
    } catch(e) {
        document.getElementById('users-tbody').innerHTML =
            `<tr><td colspan="6" class="text-center text-sub">Error: ${e.message}</td></tr>`;
    }
}

document.getElementById('btn-add-user')?.addEventListener('click', () => {
    openUserModal();
});

function openUserModal(id = null) {
    document.getElementById('um-error').textContent = '';
    const isEdit = id !== null;
    document.getElementById('userModalTitle').textContent = isEdit ? 'แก้ไขผู้ใช้งาน' : 'เพิ่มผู้ใช้งาน';
    
    // reset form
    document.getElementById('um-id').value = id || '';
    document.getElementById('um-name').value = '';
    document.getElementById('um-email').value = '';
    document.getElementById('um-password').value = '';
    document.getElementById('um-role').value = 'user';
    document.getElementById('um-status').value = '1';

    // edit configuration
    if (isEdit) {
        const user = usersList.find(u => u.id === id);
        if (user) {
            document.getElementById('um-name').value = user.name || '';
            document.getElementById('um-email').value = user.email || '';
            document.getElementById('um-role').value = user.role || 'user';
            document.getElementById('um-status').value = user.is_active ? '1' : '0';
        }
        document.getElementById('um-name-group').style.display = 'none';
        document.getElementById('um-email-group').style.display = 'none';
        document.getElementById('um-password-group').style.display = 'none';
    } else {
        document.getElementById('um-name-group').style.display = 'flex';
        document.getElementById('um-email-group').style.display = 'flex';
        document.getElementById('um-password-group').style.display = 'flex';
    }

    document.getElementById('userModal').classList.remove('hidden');
}

function closeUserModal() {
    document.getElementById('userModal').classList.add('hidden');
}

document.getElementById('btn-save-user')?.addEventListener('click', async () => {
    const id = document.getElementById('um-id').value;
    const isEdit = id !== '';
    const errEl = document.getElementById('um-error');
    const btn = document.getElementById('btn-save-user');
    
    errEl.textContent = '';
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> กำลังบันทึก...';

    const payload = isEdit 
        ? { role: document.getElementById('um-role').value, is_active: parseInt(document.getElementById('um-status').value) }
        : { 
            name: document.getElementById('um-name').value, 
            email: document.getElementById('um-email').value, 
            password: document.getElementById('um-password').value, 
            role: document.getElementById('um-role').value 
        };

    try {
        const url = isEdit ? `${API.adminUsers}/${id}` : API.adminUsers;
        const method = isEdit ? 'PUT' : 'POST';
        const res = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
            credentials: 'include'
        });
        const data = await res.json();
        if (data.success) {
            closeUserModal();
            loadUsers();
            loadAdminStats(); // update count
        } else {
            errEl.textContent = data.message || 'เกิดข้อผิดพลาด';
        }
    } catch(e) {
        errEl.textContent = 'Error: ' + e.message;
    } finally {
        btn.disabled = false;
        btn.innerHTML = 'บันทึกข้อมูล';
    }
});

async function deleteUser(id, name) {
    if (!confirm(`คุณแน่ใจหรือไม่ว่าต้องการลบผู้ใช้ "${name}"?\nข้อมูลฟอเรคาสต์และการเตือนที่ผูกไว้จะถูกลบไปด้วย (หรือเป็นกำพร้า) การกระทำนี้ไม่สามารถยกเลิกได้!`)) {
        return;
    }
    try {
        const res = await fetch(`${API.adminUsers}/${id}`, { method: 'DELETE', credentials: 'include' });
        const data = await res.json();
        if (data.success) {
            loadUsers();
            loadAdminStats(); // update count
        } else {
            alert(data.message || 'ไม่สามารถลบผู้ใช้ได้');
        }
    } catch(e) {
        alert('Error: ' + e.message);
    }
}

/* ===========================
   FORECAST SECTION
   =========================== */
async function loadForecasts() {
    try {
        const res  = await fetch(API.adminForecasts, { credentials: 'include' });
        const data = await res.json();
        const items = data.items || [];
        const fmt = v => v ? Number(v).toLocaleString() : '—';
        document.getElementById('forecast-tbody').innerHTML = items.length
            ? items.map(f => `<tr>
                <td>${esc(f.email || '—')}</td>
                <td>${f.target_date ? f.target_date.slice(0,10) : '—'}</td>
                <td>฿${fmt(f.max_price)}</td>
                <td>฿${fmt(f.min_price)}</td>
                <td><span class="pill pill-blue">${esc(f.trend || '—')}</span></td>
                <td class="text-sub">${f.created_at ? f.created_at.slice(0,10) : '—'}</td>
              </tr>`).join('')
            : '<tr><td colspan="6" class="text-center text-sub">ยังไม่มีการพยากรณ์</td></tr>';
    } catch(e) {
        document.getElementById('forecast-tbody').innerHTML =
            `<tr><td colspan="6" class="text-center text-sub">Error: ${e.message}</td></tr>`;
    }
}

/* ===========================
   LOGS SECTION
   =========================== */
async function loadLogs() {
    const terminal = document.getElementById('log-terminal');
    terminal.innerHTML = '<span class="log-line text-sub">กำลังดึง logs...</span>';
    try {
        const res  = await fetch('/api/admin/logs', { credentials: 'include' });
        const data = await res.json();
        const lines = data.lines || [];
        if (!lines.length) { terminal.innerHTML = '<span class="log-line text-sub">ไม่มี logs</span>'; return; }
        terminal.innerHTML = lines.map(l => {
            const isErr = /error|exception|fail/i.test(l);
            return `<span class="log-line ${isErr ? 'log-err' : ''}">${esc(l)}</span>`;
        }).join('');
        terminal.scrollTop = terminal.scrollHeight;
    } catch(e) {
        terminal.innerHTML = `<span class="log-line log-err">Error loading logs: ${e.message}</span>`;
    }
    document.getElementById('btn-refresh-logs')?.addEventListener('click', loadLogs);
}

/* ===========================
   SETTINGS / RUN JOB
   =========================== */
function setupSettings() {
    const btn = document.getElementById('btn-run-job');
    const status = document.getElementById('job-status');
    if (!btn) return;
    btn.addEventListener('click', async () => {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Running...';
        status.textContent = '';
        try {
            const JOB_TOKEN = prompt('กรุณาใส่ JOB_TOKEN เพื่อรัน Job:', '');
            if (!JOB_TOKEN) { btn.disabled = false; btn.innerHTML = '<i class="fas fa-play"></i> Run Job Now'; return; }
            const res  = await fetch(API.runJob, { method: 'POST', headers: {'Authorization': `Bearer ${JOB_TOKEN}`} });
            const data = await res.json();
            status.textContent = data.message || (data.ok ? 'Job สำเร็จ ✓' : 'Job ล้มเหลว');
        } catch(e) {
            status.textContent = 'Error: ' + e.message;
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-play"></i> Run Job Now';
        }
    });
}

/* ===========================
   HELPER
   =========================== */
function esc(str) {
    return String(str ?? '').replace(/[<>&"']/g, m =>
        ({ '<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;',"'":'&#39;' }[m]));
}
