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

// The Menu button opens a disclosure of the three tools; Escape or a click elsewhere closes it and returns focus to the button.
// It stays open behind the leaflets dialog so focus can return to the button that opened it.
function initMenu() {
  const button = document.getElementById("menu-btn");
  const tools = document.getElementById("tools");
  const set = (open) => {
    tools.hidden = !open;
    button.setAttribute("aria-expanded", String(open));
  };
  button.addEventListener("click", () => set(tools.hidden));
  document.getElementById("reset").addEventListener("click", () => set(false));
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !document.querySelector("dialog[open]") && !tools.hidden) { set(false); button.focus(); }
  });
  document.addEventListener("click", (e) => {
    if (!tools.hidden && !button.contains(e.target) && !tools.contains(e.target) && !e.target.closest("dialog")) set(false);
  });
}

// On narrow screens the face lives in the top bar (between the wordmark and Menu); otherwise it goes back to the ask view's side column.
function initFacePlacement() {
  const face = document.getElementById("avatar");
  const home = document.querySelector("#view-ask .side");
  const narrow = matchMedia("(max-width: 47.99em)");
  const place = () => (narrow.matches ? document.querySelector(".topbar").insertBefore(face, document.getElementById("menu-btn")) : home.prepend(face));
  narrow.addEventListener("change", place);
  place();
}

export function initTopbar() {
  initFacePlacement();
  initTextSize();
  initMenu();
}
