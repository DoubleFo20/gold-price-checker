// D:/xampp/htdocs/gold-price-checker/sw.js
self.addEventListener('push', function(event) {
    let data = {};
    const defaultUrl = new URL(self.registration.scope).pathname || '/';

    if (event.data) {
        try {
            data = event.data.json();
        } catch (e) {
            try {
                const text = event.data.text();
                data = {
                    title: 'Gold Price Today',
                    body: text || 'มีการอัปเดตราคาทองคำใหม่',
                    url: defaultUrl
                };
            } catch (textErr) {
                data = {
                    title: 'Gold Price Today',
                    body: 'มีการอัปเดตราคาทองคำใหม่',
                    url: defaultUrl
                };
            }
        }
    } else {
        data = {
            title: 'Gold Price Today',
            body: 'มีการอัปเดตราคาทองคำใหม่',
            url: defaultUrl
        };
    }

    const title = data.title || 'Gold Price Today';
    const options = {
        body: data.body || 'มีการอัปเดตราคาทองคำใหม่',
        icon: data.icon || '/img/logo.png',
        badge: data.badge || '/img/logo.png',
        data: {
            url: data.url || defaultUrl
        }
    };

    event.waitUntil(
        self.registration.showNotification(title, options)
    );
});

self.addEventListener('notificationclick', function(event) {
    event.notification.close();
    const targetUrl = (event.notification.data && event.notification.data.url)
        ? event.notification.data.url
        : (new URL(self.registration.scope).pathname || '/');

    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function(clientList) {
            for (let i = 0; i < clientList.length; i++) {
                const client = clientList[i];
                if (client.url && 'focus' in client) {
                    return client.focus();
                }
            }
            if (clients.openWindow) {
                return clients.openWindow(targetUrl);
            }
        })
    );
});

