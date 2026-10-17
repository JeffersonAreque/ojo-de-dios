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

  // nombres de paises, departamentos, ciudades y rios encima del satelite
  const nombres = L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
    { maxZoom: 19 }
  ).addTo(mapa);

  const encuadre = L.featureGroup().addTo(mapa);
  const superpuestas = { "Nombres y límites": nombres };

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
  const limitesAlertas = L.latLngBounds([]);
  leerDatos("mapa-alertas").forEach((a) => {
    const color = COLOR_GRAVEDAD[a.gravedad];
    const pendiente = a.estado === "pendiente";
    const popup =
      `<b>${esc(a.tipo)}</b><br>${esc(a.concesion)}<br>Detectada: ${a.fecha}<br>` +
      `Área: ${Math.round(a.area).toLocaleString()} m²<br>` +
      `Estado: ${a.estado}<br><a href="/alertas/${a.id}/">Ver detalle</a>`;
    L.polygon(aLatLng(a.poligono), {
      color, weight: 2, fillOpacity: opciones.soloContorno ? 0 : 0.35, dashArray: pendiente ? "5 5" : null,
    }).bindPopup(popup).addTo(capaAlertas);
    L.circleMarker([a.lat, a.lon], {
      radius: 7, color: "#fff", weight: 2, fillColor: color, fillOpacity: 1,
    }).bindPopup(popup).addTo(capaAlertas);
    limites.extend([a.lat, a.lon]);
    aLatLng(a.poligono).forEach((p) => limitesAlertas.extend(p));
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
  agregarBuscador(mapa);

  if (opciones.encuadrarAlertas && limitesAlertas.isValid()) {
    mapa.fitBounds(limitesAlertas, { padding: [60, 60], maxZoom: 16 });
  } else if (opciones.centro) {
    mapa.setView(opciones.centro, opciones.zoom || 16);
  } else if (limites.isValid()) {
    mapa.fitBounds(limites, { padding: [30, 30], maxZoom: 16 });
  } else {
    mapa.setView(CENTRO_PUERTO_MALDONADO, 10);
  }
  // la imagen se agrega despues de fijar la vista; antes Leaflet no puede posicionarla
  if (imagenes.length) imagenes[0].addTo(mapa).bringToBack();
  mapa.imagenes = imagenes;
  return mapa;
}

// Buscador de lugares con OpenStreetMap (Nominatim), limitado a Peru.
function agregarBuscador(mapa) {
  const control = L.control({ position: "topright" });
  control.onAdd = () => {
    const div = L.DomUtil.create("div", "buscador");
    div.innerHTML = '<input type="search" placeholder="Buscar lugar (ej. Puerto Maldonado)">';
    L.DomEvent.disableClickPropagation(div);
    L.DomEvent.disableScrollPropagation(div);
    const campo = div.querySelector("input");

    campo.addEventListener("keydown", async (e) => {
      if (e.key !== "Enter") return;
      e.preventDefault(); // el mapa a veces esta dentro de un formulario
      const texto = campo.value.trim();
      if (!texto) return;
      campo.disabled = true;
      try {
        const url = "https://nominatim.openstreetmap.org/search?format=json&limit=1&countrycodes=pe&q=" +
          encodeURIComponent(texto);
        const resultados = await (await fetch(url)).json();
        if (!resultados.length) {
          campo.classList.add("sin-resultado");
          return;
        }
        const [sur, norte, oeste, este] = resultados[0].boundingbox.map(Number);
        mapa.fitBounds([[sur, oeste], [norte, este]], { maxZoom: 14 });
      } catch {
        campo.classList.add("sin-resultado");
      } finally {
        campo.disabled = false;
      }
    });
    campo.addEventListener("input", () => campo.classList.remove("sin-resultado"));
    return div;
  };
  control.addTo(mapa);
}

// Muestra solo una de las imagenes del mapa (0 = despues, 1 = antes) para compararlas.
function mostrarImagen(mapa, indice, boton) {
  mapa.imagenes.forEach((capa, i) => {
    if (i === indice) capa.addTo(mapa).bringToBack();
    else capa.remove();
  });
  if (boton) {
    boton.parentElement.querySelectorAll("button").forEach((b) => b.classList.remove("active"));
    boton.classList.add("active");
  }
}
