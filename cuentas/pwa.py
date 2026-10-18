"""App instalable (PWA): el mismo sistema web, con icono y pantalla completa en el celular.

- manifest: nombre, icono y colores que el celular usa al instalarla.
- service worker: guarda en el celular los archivos de diseño (letra, estilos, iconos) para que
  abra rápido, y muestra una página amable cuando no hay internet. Los DATOS (alertas, mapas,
  reportes) siempre se piden al servidor: nunca se muestra información vieja como si fuera actual.
  Se sirve desde la raíz del sitio para poder controlar todas las páginas.
"""
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.templatetags.static import static

VERSION = "odd-v1"


def manifest(request):
    return JsonResponse({
        "name": "Ojo de Dios · Vigilancia forestal",
        "short_name": "Ojo de Dios",
        "description": "Alertas de pérdida de bosque en tu concesión, con evidencia satelital.",
        "lang": "es-PE",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "orientation": "portrait",
        "background_color": "#0D1813",
        "theme_color": "#0A140F",
        "icons": [
            {"src": static("img/icono-192.png"), "sizes": "192x192", "type": "image/png"},
            {"src": static("img/icono-512.png"), "sizes": "512x512", "type": "image/png"},
            {"src": static("img/icono-512.png"), "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
    }, content_type="application/manifest+json", json_dumps_params={"ensure_ascii": False})


def service_worker(request):
    archivos = [static(r) for r in (
        "css/app.css", "js/app.js", "img/icono-192.png", "vendor/bootstrap/bootstrap.min.css",
        "vendor/bootstrap-icons/bootstrap-icons.min.css", "fonts/barlow-latin-400-normal.woff2",
        "fonts/barlow-latin-600-normal.woff2", "fonts/barlow-semi-condensed-latin-700-normal.woff2",
    )]
    codigo = f"""
const VERSION = "{VERSION}";
const ARCHIVOS = {archivos!r};
self.addEventListener("install", (e) => {{
  e.waitUntil(caches.open(VERSION).then((c) => c.addAll(ARCHIVOS.concat(["/sin-conexion/"]))));
  self.skipWaiting();
}});
self.addEventListener("activate", (e) => {{
  e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== VERSION).map((k) => caches.delete(k)))));
  self.clients.claim();
}});
self.addEventListener("fetch", (e) => {{
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin) return;
  if (e.request.mode === "navigate") {{
    // Paginas: siempre del servidor; sin internet, la pagina de aviso.
    e.respondWith(fetch(e.request).catch(() => caches.match("/sin-conexion/")));
  }} else if (url.pathname.startsWith("/static/")) {{
    // Diseno: primero lo guardado, si no esta se descarga.
    e.respondWith(caches.match(e.request).then((r) => r || fetch(e.request)));
  }}
}});
"""
    respuesta = HttpResponse(codigo, content_type="application/javascript")
    respuesta["Service-Worker-Allowed"] = "/"
    respuesta["Cache-Control"] = "no-cache"
    return respuesta


def sin_conexion(request):
    return render(request, "sin_conexion.html")
