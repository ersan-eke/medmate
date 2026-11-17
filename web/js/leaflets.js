import { el } from "./dom.js";

// "Your NHS leaflets": a native modal dialog, so the browser traps focus, closes it on Escape and gives focus back to the opener.
export function initLeaflets() {
  const dialog = document.getElementById("leaflets");
  const list = document.getElementById("leaflet-list");
  document.getElementById("leaflets-btn").addEventListener("click", () => dialog.showModal());
  document.getElementById("leaflets-close").addEventListener("click", () => dialog.close());
  dialog.addEventListener("click", (e) => { if (e.target === dialog) dialog.close(); });
  return {
    show(leaflets) {
      list.replaceChildren(...leaflets.map((l) => {
        const li = el("li");
        li.append(
          el("h3", { textContent: l.medicine }),
          el("p", { textContent: l.description }),
          el("a", { href: l.url, target: "_blank", rel: "noopener", textContent: `Read the ${l.medicine} leaflet on nhs.uk` }),
        );
        return li;
      }));
    },
  };
}
