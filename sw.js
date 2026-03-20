// D:/xampp/htdocs/gold-price-checker/sw.js
self.addEventListener('push', function(event) {
    if (event.data) {
        const data = event.data.json();
        const options = {
            body: data.body,
            icon: '/gold-price-checker/assets/img/icon.png', // ปรับ path ตามจริง
            badge: '/gold-price-checker/assets/img/badge.png',
            data: {
                url: data.url || '/gold-price-checker/'
            }
        };

        event.waitUntil(
            self.registration.showNotification(data.title, options)
        );
    }
});

self.addEventListener('notificationclick', function(event) {
    event.notification.close();
    event.waitUntil(
        clients.openWindow(event.notification.data.url)
    );
});
