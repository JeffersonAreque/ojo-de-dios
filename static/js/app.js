// App instalable: registra el service worker y muestra el boton "Instalar app" cuando el navegador lo permite.
if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/sw.js", { scope: "/" }).catch(() => {});
}
let pedidoInstalar = null;
window.addEventListener("beforeinstallprompt", (e) => {
  e.preventDefault();
  pedidoInstalar = e;
  const boton = document.getElementById("instalar");
  if (boton) boton.hidden = false;
});
document.addEventListener("click", async (e) => {
  const boton = e.target.closest("#instalar");
  if (!boton || !pedidoInstalar) return;
  pedidoInstalar.prompt();
  await pedidoInstalar.userChoice;
  pedidoInstalar = null;
  boton.hidden = true;
});
window.addEventListener("appinstalled", () => {
  const boton = document.getElementById("instalar");
  if (boton) boton.hidden = true;
});
