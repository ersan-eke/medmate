import { TIMES, buildSchedule, countLabel, findInteractions, loadMedicines, reinsertAt, saveMedicines, todayLabel } from "./logic.js";
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

  const button = (text, label, onClick, className = "btn-stone") => {
    const b = el("button", { type: "button", className, textContent: text });
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
  const undo = document.getElementById("undo");
  let undoTimer;
  const hideUndo = () => { clearTimeout(undoTimer); undo.replaceChildren(); };
  const showUndo = (removed, index) => {
    clearTimeout(undoTimer);
    undo.replaceChildren(`Removed ${removed.name}.`, button("Undo", `Undo removing ${removed.name}`, () => {
      hideUndo();
      medicines = reinsertAt(medicines, removed, index);
      saveMedicines(localStorage, medicines);
      render();
    }, "btn-stone undo-btn"));
    undoTimer = setTimeout(hideUndo, 6000);
  };
  document.getElementById("today-date").textContent = todayLabel(new Date());
  const render = () => {
    document.getElementById("med-count").textContent = countLabel(medicines.length);
    document.getElementById("warnings").replaceChildren(...findInteractions(medicines, interactions).map((i) => {
      const p = el("p");
      p.append(el("strong", { textContent: `${i.a} + ${i.b}` }), el("br"), i.warning, el("br"), "Source: ", leafletLink(i.source));
      return p;
    }));
    document.getElementById("meds").replaceChildren(...(medicines.length ? medicines.map((m, i) => {
      const li = el("li");
      const details = el("span", { className: "med-details" });
      const title = el("span", { className: "med-title" });
      title.append(el("strong", { textContent: m.name }));
      if (m.times?.length) title.append(` (${m.times.join(", ")})`);
      if (m.dose) title.append(el("span", { className: "dose", textContent: m.dose }));
      details.append(title);
      if (m.times?.length) {
        const chips = el("span", { className: "chips" });
        chips.append(...m.times.map((t) => el("span", { className: "chip", textContent: t[0].toUpperCase() + t.slice(1) })));
        details.append(chips);
      }
      if (m.note) details.append(el("span", { className: "note", textContent: `Note: ${m.note}` }));
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
          showUndo(m, i);
        }),
      );
      li.append(details, actions);
      return li;
    }) : [el("li", { className: "empty", textContent: "No medicines yet. Add yours here so I can answer about them." })]));
    // Four slot cards always show; each takes its icon from the form's matching checkbox.
    const schedule = buildSchedule(medicines);
    document.getElementById("schedule").replaceChildren(...TIMES.map((t) => {
      const slot = el("div", { className: "slot" });
      slot.dataset.time = t;
      const head = el("h4");
      head.append(medForm.querySelector(`label[data-time="${t}"] .when-icon`).cloneNode(true), t[0].toUpperCase() + t.slice(1));
      const items = schedule[t].length ? el("ul") : el("p", { className: "empty", textContent: "No medicines" });
      items.append(...schedule[t].map((e) => el("li", { textContent: e })));
      slot.append(head, items);
      return slot;
    }));
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
