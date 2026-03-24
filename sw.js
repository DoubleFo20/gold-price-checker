// D:/xampp/htdocs/gold-price-checker/sw.js
self.addEventListener('push', function(event) {
    if (event.data) {
        const data = event.data.json();
        const defaultUrl = new URL(self.registration.scope).pathname || '/';
        const options = {
            body: data.body,
            data: {
                url: data.url || defaultUrl
            }
        };

        if (data.icon) options.icon = data.icon;
        if (data.badge) options.badge = data.badge;

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
