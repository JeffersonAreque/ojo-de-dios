// Utilidades de mapa (Leaflet) compartidas por todas las pantallas.
const COLOR_GRAVEDAD = { alta: "#c0392b", media: "#e67e22", baja: "#d4ac0d" };
const CENTRO_PUERTO_MALDONADO = [-12.6, -69.19];

function esc(texto) {
  return String(texto).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function leerDatos(id) {
  const nodo = document.getElementById(id);
  return nodo ? JSON.parse(nodo.textContent) : [];
}

function aLatLng(coords) {
  return coords.map(([lon, lat]) => [lat, lon]);
}

function crearMapa(idContenedor, opciones = {}) {
  const mapa = L.map(idContenedor);
  const satelite = L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    { maxZoom: 19, attribution: "Imágenes © Esri" }
  ).addTo(mapa);
  const calles = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19, attribution: "© OpenStreetMap",
  });

  const encuadre = L.featureGroup().addTo(mapa);
  const superpuestas = {};

  const limites = L.latLngBounds([]);
  const imagenes = leerDatos("mapa-imagenes").map((img) => {
    const capa = L.imageOverlay(img.url, img.limites, { opacity: 0.9 });
    superpuestas["Imagen: " + (img.nombre || "vuelo")] = capa;
    limites.extend(img.limites);
    return capa;
  });

  leerDatos("mapa-concesiones").forEach((c) => {
    const poligono = L.polygon(aLatLng(c.limite), { color: "#7CFC00", weight: 2, fillOpacity: 0.04 })
      .bindTooltip(esc(c.nombre))
      .addTo(encuadre);
    limites.extend(poligono.getBounds());
  });

  const capaAlertas = L.layerGroup().addTo(mapa);
  leerDatos("mapa-alertas").forEach((a) => {
    const color = COLOR_GRAVEDAD[a.gravedad];
    const pendiente = a.estado === "pendiente";
    const popup =
      `<b>${esc(a.tipo)}</b><br>${esc(a.concesion)}<br>Detectada: ${a.fecha}<br>` +
      `Área: ${Math.round(a.area).toLocaleString()} m²<br>` +
      `Estado: ${a.estado}<br><a href="/alertas/${a.id}/">Ver detalle</a>`;
    L.polygon(aLatLng(a.poligono), {
      color, weight: 2, fillOpacity: 0.35, dashArray: pendiente ? "5 5" : null,
    }).bindPopup(popup).addTo(capaAlertas);
    L.circleMarker([a.lat, a.lon], {
      radius: 7, color: "#fff", weight: 2, fillColor: color, fillOpacity: 1,
    }).bindPopup(popup).addTo(capaAlertas);
    limites.extend([a.lat, a.lon]);
  });
  superpuestas["Alertas"] = capaAlertas;

  L.control.layers({ "Satélite": satelite, "Calles": calles }, superpuestas).addTo(mapa);

  const leyenda = L.control({ position: "bottomright" });
  leyenda.onAdd = () => {
    const div = L.DomUtil.create("div", "leyenda");
    div.innerHTML =
      '<span style="background:#c0392b"></span>Alta<br>' +
      '<span style="background:#e67e22"></span>Media<br>' +
      '<span style="background:#d4ac0d"></span>Baja<br>' +
      '<span style="background:#7CFC00"></span>Límite de concesión';
    return div;
  };
  leyenda.addTo(mapa);

  if (opciones.centro) {
    mapa.setView(opciones.centro, opciones.zoom || 16);
  } else if (limites.isValid()) {
    mapa.fitBounds(limites, { padding: [30, 30], maxZoom: 16 });
  } else {
    mapa.setView(CENTRO_PUERTO_MALDONADO, 10);
  }
  // la imagen se agrega despues de fijar la vista; antes Leaflet no puede posicionarla
  if (imagenes.length) imagenes[0].addTo(mapa).bringToBack();
  return mapa;
}
