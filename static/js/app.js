import { events } from "./core/events.js";
import { http } from "./core/http.js";

const isDev = window.location.hostname === "localhost";

window.App = { events, http, isDev };

if (isDev) {
  window.addEventListener("error", (event) => {
    console.error("Error global:", event.error);
  });

  window.addEventListener("unhandledrejection", (event) => {
    console.error("Promise rechazada:", event.reason);
  });
}

export { events, http };
