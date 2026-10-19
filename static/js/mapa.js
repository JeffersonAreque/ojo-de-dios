// Utilidades de mapa (Leaflet) compartidas por todas las pantallas.
const COLOR_GRAVEDAD = { alta: "#EC4C86", media: "#F39C4A", baja: "#E8C547" };
const COLOR_LIMITE = "#F6E7A6";
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
  // Mosaico Sentinel-2 sin nubes (EOX, año 2023): el mismo satélite que usa Copernicus Browser,
  // más actual que el fondo de Esri en zonas de minería como La Pampa. Hasta zoom 15 aprox. (10 m/píxel).
  const sentinel = L.tileLayer(
    "https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2023_3857/default/g/{z}/{y}/{x}.jpg",
    { maxZoom: 19, maxNativeZoom: 15, attribution: "Sentinel-2 cloudless 2023 © EOX (datos Copernicus modificados)" }
  );
  if (opciones.base === "sentinel") {
    mapa.removeLayer(satelite);
    sentinel.addTo(mapa);
    // si el servicio no responde, se vuelve al satélite de Esri para no dejar el mapa en blanco
    sentinel.once("tileerror", () => {
      if (mapa.hasLayer(sentinel)) { mapa.removeLayer(sentinel); satelite.addTo(mapa).bringToBack(); }
    });
  }
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
    const poligono = L.polygon(aLatLng(c.limite), { color: COLOR_LIMITE, weight: 2.5, dashArray: "8 6", fillOpacity: 0 })
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
      color, weight: 2, fillOpacity: opciones.soloContorno ? 0 : 0.15, dashArray: pendiente ? "5 5" : null,
    }).bindPopup(popup).addTo(capaAlertas);
    L.circleMarker([a.lat, a.lon], {
      radius: 7, color: "#0D1813", weight: 2, fillColor: color, fillOpacity: 1,
    }).bindPopup(popup).addTo(capaAlertas);
    limites.extend([a.lat, a.lon]);
    aLatLng(a.poligono).forEach((p) => limitesAlertas.extend(p));
  });
  superpuestas["Alertas"] = capaAlertas;

  L.control.layers({ "Sentinel-2 (2023)": sentinel, "Satélite alta resolución": satelite, "Calles": calles }, superpuestas).addTo(mapa);

  const leyenda = L.control({ position: "bottomright" });
  leyenda.onAdd = () => {
    const div = L.DomUtil.create("div", "leyenda");
    div.innerHTML =
      `<span style="background:${COLOR_GRAVEDAD.alta}"></span>Gravedad alta<br>` +
      `<span style="background:${COLOR_GRAVEDAD.media}"></span>Gravedad media<br>` +
      `<span style="background:${COLOR_GRAVEDAD.baja}"></span>Gravedad baja<br>` +
      `<i class="linea-limite"></i>Límite de concesión`;
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
    div.innerHTML = '<input type="search" placeholder="Lugar o coordenadas (-12.98, -69.97)">';
    L.DomEvent.disableClickPropagation(div);
    L.DomEvent.disableScrollPropagation(div);
    const campo = div.querySelector("input");

    campo.addEventListener("keydown", async (e) => {
      if (e.key !== "Enter") return;
      e.preventDefault(); // el mapa a veces esta dentro de un formulario
      const texto = campo.value.trim();
      if (!texto) return;
      // Coordenadas "latitud, longitud" (como las muestra Copernicus o Google Maps): ir directo.
      const coords = texto.match(/^\s*(-?\d+(?:\.\d+)?)\s*[,;\s]\s*(-?\d+(?:\.\d+)?)\s*$/);
      if (coords) {
        const lat = Number(coords[1]), lon = Number(coords[2]);
        if (Math.abs(lat) <= 90 && Math.abs(lon) <= 180) {
          mapa.setView([lat, lon], 14);
          L.circleMarker([lat, lon], { radius: 6, color: "#F6E7A6", weight: 2, fillOpacity: 0.6 }).addTo(mapa);
          return;
        }
      }
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


// Letrero "Estás en…": distrito, provincia y coordenadas del centro del mapa, en vivo.
// Usa Nominatim (OpenStreetMap); se consulta como máximo una vez por segundo, al dejar de mover el mapa.
function agregarUbicacion(mapa) {
  const control = L.control({ position: "bottomleft" });
  control.onAdd = () => {
    const div = L.DomUtil.create("div", "ubicacion");
    div.innerHTML = '<span class="lugar">Ubicando…</span><span class="coords"></span>';
    return div;
  };
  control.addTo(mapa);
  const lugar = control.getContainer().querySelector(".lugar");
  const coords = control.getContainer().querySelector(".coords");
  let espera = null, consulta = 0;

  async function actualizar() {
    const c = mapa.getCenter();
    coords.textContent = `${c.lat.toFixed(5)}, ${c.lng.toFixed(5)}`;
    const n = ++consulta;
    try {
      const url = `https://nominatim.openstreetmap.org/reverse?format=json&zoom=10&accept-language=es&lat=${c.lat}&lon=${c.lng}`;
      const d = (await (await fetch(url)).json()).address || {};
      if (n !== consulta) return; // llegó una respuesta vieja
      const distrito = d.city || d.town || d.village || d.municipality || d.suburb || "";
      const partes = [distrito && `Distrito de ${distrito.replace(/^Distrito de /, "")}`,
                      d.county && `provincia de ${d.county.replace(/^Provincia de /, "")}`, d.state].filter(Boolean);
      lugar.textContent = partes.length ? "Estás en: " + partes.join(", ") : "Estás en: zona sin nombre registrado";
    } catch {
      lugar.textContent = "Estás en: (sin conexión para ubicar)";
    }
  }
  mapa.on("moveend", () => { clearTimeout(espera); espera = setTimeout(actualizar, 1000); });
  mapa.whenReady(() => setTimeout(actualizar, 300));
}
