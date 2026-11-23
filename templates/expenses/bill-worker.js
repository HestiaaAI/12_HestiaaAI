self.addEventListener('push', event => {
  let data;
  try { data = event.data.json(); } catch (_) { return; }
  if (!Number.isSafeInteger(data?.reminder_id) || data.reminder_id < 1) return;
  event.waitUntil((async () => {
    try {
      const response = await fetch(`/expenses/push/visible/${data.reminder_id}/`, {
        credentials: 'same-origin', cache: 'no-store', redirect: 'error'
      });
      if (response.status !== 204) return;
      await self.registration.showNotification('Hestia · bill reminder', {
        body: 'You have an upcoming or overdue bill. Open Hestia to review it.',
        icon: '/static/images/hestia-app-192.png',
        badge: '/static/images/hestia-app-192.png',
        tag: `bill-${data.reminder_id}`,
        data: {url: '/expenses/reminders/'}
      });
    } catch (_) {
      // Without an authorized session, nothing is displayed on the device.
    }
  })());
});
self.addEventListener('notificationclick', event => {
  event.notification.close();
  event.waitUntil(clients.openWindow('/expenses/reminders/'));
});
