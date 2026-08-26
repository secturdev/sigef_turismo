(function () {
  "use strict";

  const form = document.querySelector("[data-formulario-solicitud]");
  if (!form) return;

  const vacio = (valor) =>
    valor === null ||
    valor === undefined ||
    valor === "" ||
    (Array.isArray(valor) && valor.length === 0);

  const OPERADORES = {
    igual: (valor, esperado) => valor === esperado,
    diferente: (valor, esperado) => valor !== esperado,
    incluye: (valor, esperado) => Array.isArray(valor) && valor.includes(esperado),
    existe: (valor) => !vacio(valor),
    no_existe: (valor) => vacio(valor),
  };

  function leerValor(nombre) {
    const campo = form.elements[nombre];
    if (!campo) return null;

    if (typeof campo.length === "number" && !campo.tagName) {
      const valores = [];
      Array.prototype.forEach.call(campo, (nodo) => {
        if (nodo.checked) valores.push(nodo.value);
      });
      return valores;
    }
    if (campo.type === "checkbox") return campo.checked;
    return campo.value;
  }

  function evaluar(regla) {
    if (!regla) return true;
    const operador = OPERADORES[regla.operador || "igual"];
    if (!operador) return true;
    return operador(leerValor(regla.campo), regla.valor);
  }

  const contenedores = Array.prototype.slice.call(
    form.querySelectorAll("[data-condicion]")
  );

  function refrescar() {
    contenedores.forEach((contenedor) => {
      let regla;
      try {
        regla = JSON.parse(contenedor.getAttribute("data-condicion"));
      } catch (error) {
        return;
      }
      contenedor.classList.toggle("hidden", !evaluar(regla));
    });
  }

  form.addEventListener("change", refrescar);
  form.addEventListener("input", refrescar);
  refrescar();
})();
