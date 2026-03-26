// admin/js/admin.js

document.addEventListener('DOMContentLoaded', async () => {
    
    // 1. Check Authentication & Admin Role
    try {
        const res = await fetch('/api/api/auth/check_session.php', { method: 'POST' });
        const data = await res.json();
        
        if (!data.authenticated || data.user.role !== 'admin') {
            alert('คุณไม่มีสิทธิ์เข้าถึงหน้านี้ (Admin Only)\nระบบจะพากลับไปหน้าผู้ใช้งานทั่วไป');
            window.location.href = '/';
            return;
        }

        // Update UI with Admin User Data
        document.querySelector('.user-name').innerText = data.user.name || 'Admin';
        document.querySelector('.user-role').innerText = data.user.role || 'Super Admin';
        document.querySelector('.avatar').src = `https://ui-avatars.com/api/?name=${encodeURIComponent(data.user.name || 'Admin')}&background=D4AF37&color=fff`;

    } catch (e) {
        console.error('Auth Check Error:', e);
        alert('เกิดข้อผิดพลาดในการตรวจสอบสิทธิ์');
        window.location.href = '/';
        return;
    }

    // 2. Load Dashboard KPIs
    async function loadDashboardStats() {
        try {
            const res = await fetch('/api/admin/stats');
            const result = await res.json();
            
            if (result.success && result.data) {
                const d = result.data;
                // Update Thai Gold Card
                const tbSellStr = (d.thai_gold.bar_sell || 0).toLocaleString();
                document.querySelectorAll('.kpi-value')[0].innerText = `฿${tbSellStr}`;
                
                // Update World Gold Card
                const wPriceStr = (d.world_gold.price || 0).toLocaleString();
                document.querySelectorAll('.kpi-value')[1].innerText = `$${wPriceStr}`;
                
                // Update Active Users Card
                const usersCount = (d.users_count || 0).toLocaleString();
                document.querySelectorAll('.kpi-value')[2].innerText = usersCount;
                
                // Alert System Status (mock for now, API says online)
                document.querySelectorAll('.kpi-value')[3].innerText = 'API Online';
            }
        } catch(e) {
            console.error('Failed to load stats:', e);
        }
    }
    loadDashboardStats();


    // 3. Sidebar Navigation Logic
    const navItems = document.querySelectorAll('.sidebar-nav .nav-item, .sidebar-footer .nav-item');
    const pageSections = document.querySelectorAll('.page-section');
    const pageTitle = document.getElementById('page-title');

    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            
            navItems.forEach(n => n.classList.remove('active'));
            item.classList.add('active');

            const targetId = item.getAttribute('data-target');
            pageSections.forEach(section => {
                section.classList.add('hidden');
                section.classList.remove('active');
            });
            
            const targetSection = document.getElementById(`section-${targetId}`);
            if (targetSection) {
                targetSection.classList.remove('hidden');
                setTimeout(() => targetSection.classList.add('active'), 10);
            }

            const titleText = item.querySelector('span').innerText;
            if (titleText === 'Dashboard') {
                pageTitle.innerText = 'Dashboard Overview';
                loadDashboardStats(); // reload numbers
            } else {
                pageTitle.innerText = titleText;
            }
        });
    });

    // Mock functionality: Add News Button
    const btnAddNews = document.getElementById('btn-add-news');
    if(btnAddNews) {
        btnAddNews.addEventListener('click', () => {
            alert("This will open a modal to add a new article. (Mockup functionality)");
        });
    }

});
