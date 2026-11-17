// The MedMate | My medicines switch: one toggle button, exactly one view is shown, and this toggle is the only way to change it.
export function initViews() {
  const toggle = document.getElementById("view-switch");
  const ask = document.getElementById("view-ask");
  const meds = document.getElementById("view-meds");
  toggle.addEventListener("click", () => {
    const showMeds = toggle.getAttribute("aria-checked") !== "true";
    toggle.setAttribute("aria-checked", String(showMeds));
    ask.hidden = showMeds;
    meds.hidden = !showMeds;
  });
  return { isShown: (id) => !document.getElementById(id).hidden };
}
