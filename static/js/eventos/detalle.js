const ambient = document.querySelector("[data-evento-ambient]");
const banner = document.querySelector("[data-evento-banner]");

const syncAmbient = () => {
  if (!ambient || !banner) return;
  const src = banner.currentSrc || banner.src;
  if (!src) return;
  ambient.style.backgroundImage = `url("${src}")`;
  ambient.style.backgroundPosition = "top";
};

if (banner) {
  if (banner.complete) {
    syncAmbient();
  } else {
    banner.addEventListener("load", syncAmbient, { once: true });
  }
}
