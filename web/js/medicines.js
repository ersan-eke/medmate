import { TIMES, buildSchedule, findInteractions, loadMedicines, saveMedicines } from "./logic.js";
import { el, leafletLink } from "./dom.js";

// The My medicines view: the form, the list, interaction warnings and Today.
export function initMedicines() {
  let medicines = loadMedicines(localStorage);
  let interactions = [];
  let editing = -1;  // index being edited, or -1 when adding
  const medForm = document.getElementById("med-form");
  const nameSelect = document.getElementById("med-name");
  const dose = document.getElementById("med-dose");
  const note = document.getElementById("med-note");
  const timeBoxes = [...medForm.querySelectorAll('input[name="times"]')];
  const saveButton = document.getElementById("med-save");
  const cancelButton = document.getElementById("med-cancel");

  const button = (text, label, onClick) => {
    const b = el("button", { type: "button", textContent: text });
    b.setAttribute("aria-label", label);
    b.addEventListener("click", onClick);
    return b;
  };
  const resetForm = () => {
    medForm.reset();
    editing = -1;
    saveButton.textContent = "Add medicine";
    cancelButton.hidden = true;
  };
  const render = () => {
    document.getElementById("warnings").replaceChildren(...findInteractions(medicines, interactions).map((i) => {
      const p = el("p");
      p.append(el("strong", { textContent: `${i.a} + ${i.b}` }), el("br"), i.warning, el("br"), "Source: ", leafletLink(i.source));
      return p;
    }));
    document.getElementById("meds").replaceChildren(...(medicines.length ? medicines.map((m, i) => {
      const li = el("li");
      const when = (m.times ?? []).join(", ");
      const details = el("span", { className: "med-details" });
      details.append(el("strong", { textContent: m.name }), " ",
        [m.dose, when && `(${when})`, m.note && `: ${m.note}`].filter(Boolean).join(" "));
      const actions = el("span", { className: "med-actions" });
      actions.append(
        button("Edit", `Edit ${m.name}`, () => {
          editing = i;
          nameSelect.value = m.name;
          dose.value = m.dose ?? "";
          note.value = m.note ?? "";
          timeBoxes.forEach((b) => { b.checked = (m.times ?? []).includes(b.value); });
          saveButton.textContent = "Save changes";
          cancelButton.hidden = false;
          nameSelect.focus();
        }),
        button("Remove", `Remove ${m.name}`, () => {
          medicines.splice(i, 1);
          saveMedicines(localStorage, medicines);
          resetForm();
          render();
        }),
      );
      li.append(details, actions);
      return li;
    }) : [el("li", { className: "empty", textContent: "No medicines yet. Add yours here so I can answer about them." })]));
    // One pill-box compartment per time of day that has a dose.
    const schedule = buildSchedule(medicines);
    const slots = TIMES.filter((t) => schedule[t].length).map((t) => {
      const slot = el("div", { className: "slot" });
      slot.dataset.time = t;
      const ul = el("ul");
      ul.append(...schedule[t].map((e) => el("li", { textContent: e })));
      slot.append(el("h3", { textContent: t[0].toUpperCase() + t.slice(1) }), ul);
      return slot;
    });
    document.getElementById("schedule").replaceChildren(
      ...(slots.length ? slots : [el("p", { className: "empty", textContent: "No doses added yet." })]));
  };
  medForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const entry = {
      name: nameSelect.value,
      dose: dose.value.trim(),
      times: timeBoxes.filter((b) => b.checked).map((b) => b.value),
      note: note.value.trim(),
    };
    if (editing >= 0) medicines[editing] = entry; else medicines.push(entry);
    saveMedicines(localStorage, medicines);
    resetForm();
    render();
  });
  cancelButton.addEventListener("click", resetForm);
  render();
  return {
    get list() { return medicines; },
    // Called once /api/meta has loaded.
    setMeta(meta) {
      nameSelect.replaceChildren(...meta.medicines.map((n) => new Option(n, n)));
      interactions = meta.interactions;
      render();
    },
    // Only a failed fetch lands here; the list itself keeps working.
    setUnavailable() {
      nameSelect.replaceChildren(new Option("Couldn't load medicines. Please reload.", ""));
    },
  };
}
