// Comparador deslizable: la imagen "antes" se recorta con clip-path segun la posicion del tirador.
document.querySelectorAll("[data-comparador]").forEach((comp) => {
  const tirador = comp.querySelector(".tirador");
  const casilla = comp.parentElement.querySelector("[data-zonas]");

  function mover(pct) {
    pct = Math.min(100, Math.max(0, pct));
    comp.style.setProperty("--corte", pct + "%");
    tirador.setAttribute("aria-valuenow", Math.round(pct));
  }
  const porcentaje = (x) => {
    const r = comp.getBoundingClientRect();
    return ((x - r.left) / r.width) * 100;
  };

  let arrastrando = false;
  comp.addEventListener("pointerdown", (e) => {
    arrastrando = true;
    comp.setPointerCapture(e.pointerId);
    mover(porcentaje(e.clientX));
  });
  comp.addEventListener("pointermove", (e) => arrastrando && mover(porcentaje(e.clientX)));
  comp.addEventListener("pointerup", () => (arrastrando = false));
  comp.addEventListener("pointercancel", () => (arrastrando = false));

  tirador.addEventListener("keydown", (e) => {
    const actual = Number(tirador.getAttribute("aria-valuenow"));
    if (e.key === "ArrowLeft") { mover(actual - 5); e.preventDefault(); }
    if (e.key === "ArrowRight") { mover(actual + 5); e.preventDefault(); }
  });

  if (casilla) {
    casilla.addEventListener("change", () => comp.classList.toggle("sin-zonas", !casilla.checked));
  }
});
