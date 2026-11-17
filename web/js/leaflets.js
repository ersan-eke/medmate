import { el } from "./dom.js";

// "Your NHS leaflets": a native modal dialog, so the browser traps focus, closes it on Escape and gives focus back to the opener.
export function initLeaflets() {
  const dialog = document.getElementById("leaflets");
  const list = document.getElementById("leaflet-list");
  document.getElementById("leaflets-btn").addEventListener("click", () => dialog.showModal());
  for (const id of ["leaflets-close", "leaflets-done"]) document.getElementById(id).addEventListener("click", () => dialog.close());
  dialog.addEventListener("click", (e) => { if (e.target === dialog) dialog.close(); });
  return {
    show(leaflets) {
      document.getElementById("leaflets-title").textContent = `Your NHS leaflets (${leaflets.length})`;
      document.getElementById("leaflet-names").textContent = `NHS leaflets: ${leaflets.map((l) => l.medicine).join(", ")}`;
      list.replaceChildren(...leaflets.map((l) => {
        const li = el("li");
        const text = el("div");
        text.append(el("h3", { textContent: l.medicine }), el("p", { textContent: l.description }));
        li.append(text, el("a", { className: "btn-blue", href: l.url, target: "_blank", rel: "noopener", textContent: "Open leaflet ↗" }));
        return li;
      }));
    },
  };
}
