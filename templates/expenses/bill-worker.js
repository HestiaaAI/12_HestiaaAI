self.addEventListener('push', event => {
  let data = {};
  try { data = event.data.json(); } catch (_) {}
  event.waitUntil(self.registration.showNotification(data.title || 'Hestia reminder', {
    body: data.body || 'Open Hestia to review your bill reminders.',
    icon: '/static/images/hestia-app-192.png', badge: '/static/images/hestia-app-192.png',
    tag: data.tag || 'hestia-bill', data: {url: '/expenses/reminders/'}
  }));
});
self.addEventListener('notificationclick', event => {
  event.notification.close();
  event.waitUntil(clients.openWindow('/expenses/reminders/'));
});
