const SIZES = [20, 24, 28];
const SIZE_KEY = "medmate.textSize";

// The three-dot text-size button: each click goes to the next size, and the choice is remembered.
function initTextSize() {
  const button = document.getElementById("text-size");
  const saved = Number(localStorage.getItem(SIZE_KEY));
  let size = SIZES.includes(saved) ? saved : SIZES[0];
  const apply = () => {
    document.documentElement.style.fontSize = `${size}px`;
    button.setAttribute("aria-label", `Text size ${size} pixels. Press to change.`);
    [...button.querySelectorAll(".size-dots i")].forEach((dot, i) => dot.classList.toggle("on", i <= SIZES.indexOf(size)));
  };
  apply();
  button.addEventListener("click", () => {
    size = SIZES[(SIZES.indexOf(size) + 1) % SIZES.length];
    localStorage.setItem(SIZE_KEY, size);
    apply();
  });
}

// Under 1024 px the tools collapse into the ⋯ menu: a disclosure that Escape or a click elsewhere closes.
// It stays open behind the leaflets dialog so focus can return to the button that opened it.
function initMenu() {
  const topbar = document.querySelector(".topbar");
  const button = document.getElementById("menu-btn");
  const set = (open) => {
    topbar.classList.toggle("menu-open", open);
    button.setAttribute("aria-expanded", String(open));
  };
  button.addEventListener("click", () => set(button.getAttribute("aria-expanded") !== "true"));
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !document.querySelector("dialog[open]") && topbar.classList.contains("menu-open")) { set(false); button.focus(); }
  });
  document.addEventListener("click", (e) => {
    if (!topbar.contains(e.target) && !e.target.closest("dialog")) set(false);
  });
}

export function initTopbar() {
  initTextSize();
  initMenu();
}
