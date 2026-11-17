import { initChat } from "./chat.js";
import { initMedicines } from "./medicines.js";
import { initViews } from "./view.js";

const SIZES = [20, 24, 28];
const SIZE_KEY = "medmate.textSize";
const applySize = (px) => { document.documentElement.style.fontSize = `${px}px`; };
const saved = Number(localStorage.getItem(SIZE_KEY));
let size = SIZES.includes(saved) ? saved : SIZES[0];
applySize(size);
document.getElementById("text-size").addEventListener("click", () => {
  size = SIZES[(SIZES.indexOf(size) + 1) % SIZES.length];
  localStorage.setItem(SIZE_KEY, size);
  applySize(size);
});

const views = initViews();
const medicines = initMedicines();
initChat(() => medicines.list, () => views.isShown("view-ask"));

fetch("/api/meta").then((r) => (r.ok ? r.json() : Promise.reject(r.status))).then((meta) => {
  document.querySelector("footer").textContent = meta.attribution;
  medicines.setMeta(meta);
}, () => medicines.setUnavailable());
