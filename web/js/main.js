import { initChat } from "./chat.js";
import { initMedicines } from "./medicines.js";
import { initViews } from "./view.js";
import { initTopbar } from "./topbar.js";
import { initLeaflets } from "./leaflets.js";

initTopbar();

const views = initViews();
const leaflets = initLeaflets();
const medicines = initMedicines();
initChat(() => medicines.list, () => views.isShown("view-ask"));

fetch("/api/meta").then((r) => (r.ok ? r.json() : Promise.reject(r.status))).then((meta) => {
  document.querySelector("footer").textContent = meta.attribution;
  medicines.setMeta(meta);
  leaflets.show(meta.leaflets);
}, () => medicines.setUnavailable());
