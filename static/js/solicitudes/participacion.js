(function () {
  "use strict";

  const form = document.querySelector("form[enctype='multipart/form-data']");
  if (!form) return;

  const giro = form.elements.giro;
  const subgiro = form.elements.subgiro;
  const programas = form.querySelectorAll("input[name='programa_especial']");
  const folio = form.querySelector("[data-social-folio]");

  function actualizarSubgiros() {
    if (!giro || !subgiro) return;
    const giroLabel = giro.options[giro.selectedIndex]?.text || "";
    Array.from(subgiro.querySelectorAll("optgroup")).forEach((group) => {
      group.hidden = group.label !== giroLabel;
    });
    Array.from(subgiro.options).forEach((option) => {
      const grupo = option.parentElement && option.parentElement.tagName === "OPTGROUP" ? option.parentElement : null;
      option.hidden = Boolean(grupo && grupo.hidden);
    });
    const elegida = subgiro.options[subgiro.selectedIndex];
    if (elegida && elegida.hidden) subgiro.value = "";
  }

  function actualizarPrograma() {
    if (!folio) return;
    const seleccionado = form.querySelector("input[name='programa_especial']:checked");
    const requiereFolio = Boolean(seleccionado && seleccionado.value !== "NINGUNO");
    folio.hidden = !requiereFolio;
    const input = folio.querySelector("input");
    if (input) input.required = requiereFolio;
  }

  giro?.addEventListener("change", actualizarSubgiros);
  programas.forEach((radio) => radio.addEventListener("change", actualizarPrograma));
  actualizarSubgiros();
  actualizarPrograma();
})();
