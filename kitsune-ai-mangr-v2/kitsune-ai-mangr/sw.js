// kitsune//ai-mangr service worker - just enough for "add to home screen".
// passthrough fetch: everything always hits the local server anyway.
self.addEventListener('install', e => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil(self.clients.claim()));
self.addEventListener('fetch', e => {});
