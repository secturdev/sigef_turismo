import { events } from "./core/events.js";
import { http } from "./core/http.js";

const isDev = window.location.hostname === "localhost";

const loading = {
  start() {
    window.Alpine?.store("loading")?.start();
  },
  stop() {
    window.Alpine?.store("loading")?.stop();
  },
};

window.App = { events, http, isDev, loading };

if (isDev) {
  window.addEventListener("error", (event) => {
    console.error("Error global:", event.error);
  });

  window.addEventListener("unhandledrejection", (event) => {
    console.error("Promise rechazada:", event.reason);
  });
}

const nativeFetch = window.fetch.bind(window);

window.fetch = async (...args) => {
  loading.start();
  try {
    return await nativeFetch(...args);
  } finally {
    loading.stop();
  }
};

document.addEventListener("submit", (event) => {
  queueMicrotask(() => {
    if (!event.defaultPrevented) loading.start();
  });
});

const nativeFormSubmit = HTMLFormElement.prototype.submit;
HTMLFormElement.prototype.submit = function submitWithLoading() {
  loading.start();
  return nativeFormSubmit.call(this);
};

window.addEventListener("pageshow", () => {
  window.Alpine?.store("loading")?.reset();
});


export { events, http };
