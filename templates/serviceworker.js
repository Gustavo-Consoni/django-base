const CACHE_VERSION = "v1.0.0"
const staticCacheName = `spacepro-${CACHE_VERSION}`
const filesToCache = [
    "/offline",
]

self.addEventListener("install", event => {
    event.waitUntil(
        caches.open(staticCacheName).then(cache => cache.addAll(filesToCache))
    )
})

self.addEventListener("activate", event => {
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames
                .filter(cacheName => cacheName.startsWith("spacepro-"))
                .filter(cacheName => cacheName !== staticCacheName)
                .map(cacheName => caches.delete(cacheName))
            )
        }).then(() => self.clients.claim())
    )
})

self.addEventListener("fetch", event => {
    if (event.request.method !== "GET") return
    if (event.request.mode !== "navigate") return
    event.respondWith(
        fetch(event.request).catch(() => caches.match("/offline"))
    )
})

self.addEventListener("push", event => {
    if (!event.data) return
    const data = event.data.json()
    if (!data.title) return
    event.waitUntil(
        self.registration.showNotification(data.title, {
            icon: data.icon,
            badge: data.badge,
            body: data.body,
            data: data.data,
        })
    )
})

self.addEventListener("notificationclick", event => {
    event.notification.close()
    const url = event.notification.data?.url || "/entrar"
    event.waitUntil(
        clients.matchAll({ type: "window", includeUncontrolled: true }).then(clientList => {
            for (const client of clientList) {
                if (client.url.includes(url) && "focus" in client) return client.focus()
            }
            return clients.openWindow(url)
        })
    )
})
