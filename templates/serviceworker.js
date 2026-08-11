const CACHE_VERSION = "v1.0.0"
const VAPID_PUBLIC_KEY = "{{ vapid_public_key }}"
const staticCacheName = `dindinja-${CACHE_VERSION}`
const filesToCache = [
    "/offline",
]

function urlBase64ToUint8Array(base64String) {
    const padding = "=".repeat((4 - base64String.length % 4) % 4)
    const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/")
    const rawData = atob(base64)
    return Uint8Array.from([...rawData].map(c => c.charCodeAt(0)))
}

self.addEventListener("install", event => {
    self.skipWaiting()
    event.waitUntil(
        caches.open(staticCacheName).then(cache =>
            cache.addAll(filesToCache.map(url => 
                new Request(url, { cache: "reload" }))
            )
        )
    )
})

self.addEventListener("activate", event => {
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames
                .filter(cacheName => cacheName.startsWith("dindinja-"))
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
    const targetUrl = event.notification.data?.url || "/entrar"
    event.waitUntil(
        self.clients.matchAll({
            type: "window",
            includeUncontrolled: true,
        }).then(clientList => {
            for (const client of clientList) {
                if ("focus" in client && "navigate" in client) {
                    return client.navigate(targetUrl).then(navigatedClient => navigatedClient?.focus())
                }
            }
            return self.clients.openWindow(targetUrl)
        })
    )
})

self.addEventListener("pushsubscriptionchange", event => {
    event.waitUntil(
        self.registration.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: urlBase64ToUint8Array(VAPID_PUBLIC_KEY),
        }).then(newSubscription => fetch("/webpush/resubscribe", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                old_endpoint: event.oldSubscription?.endpoint,
                new_subscription: newSubscription,
            }),
        }))
    )
})
