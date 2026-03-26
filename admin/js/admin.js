// admin/js/admin.js

document.addEventListener('DOMContentLoaded', () => {
    
    // Sidebar Navigation Logic
    const navItems = document.querySelectorAll('.sidebar-nav .nav-item, .sidebar-footer .nav-item');
    const pageSections = document.querySelectorAll('.page-section');
    const pageTitle = document.getElementById('page-title');

    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            
            // Remove active class from all nav items
            navItems.forEach(n => n.classList.remove('active'));
            // Add active class to clicked nav item
            item.classList.add('active');

            // Find target section
            const targetId = item.getAttribute('data-target');
            
            // Hide all sections
            pageSections.forEach(section => {
                section.classList.add('hidden');
                section.classList.remove('active');
            });
            
            // Show target section
            const targetSection = document.getElementById(`section-${targetId}`);
            if (targetSection) {
                targetSection.classList.remove('hidden');
                // Small delay to allow display:block to apply before animating opacity
                setTimeout(() => {
                    targetSection.classList.add('active');
                }, 10);
            }

            // Update Header Title
            const titleText = item.querySelector('span').innerText;
            if (titleText === 'Dashboard') {
                pageTitle.innerText = 'Dashboard Overview';
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
