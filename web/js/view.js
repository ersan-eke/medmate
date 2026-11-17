// The MedMate | My medicines switch: exactly one view is shown, and this switch is the only way to change it.
export function initViews() {
  const views = [
    { button: document.getElementById("tab-ask"), view: document.getElementById("view-ask") },
    { button: document.getElementById("tab-meds"), view: document.getElementById("view-meds") },
  ];
  const show = (chosen) => {
    for (const v of views) {
      const on = v === chosen;
      v.button.setAttribute("aria-pressed", String(on));
      v.view.hidden = !on;
    }
  };
  for (const v of views) v.button.addEventListener("click", () => show(v));
  return { isShown: (id) => !document.getElementById(id).hidden };
}
