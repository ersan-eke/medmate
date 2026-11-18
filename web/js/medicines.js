import { TIMES, buildSchedule, countLabel, findInteractions, loadMedicines, loadTaken, reinsertAt, saveMedicines, store, saveTaken, todayLabel } from "./logic.js";
import { el, leafletLink } from "./dom.js";

// The My medicines view: the form, the list, interaction warnings and Today.
export function initMedicines() {
  const local = store("localStorage");
  let medicines = loadMedicines(local);
  let interactions = [];
  const day = new Date().toDateString();
  const taken = loadTaken(local, day);
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
  // Saved medicines drive the schedule, so a save the browser refuses is said out loud.
  const save = () => {
    if (!saveMedicines(local, medicines)) undo.append(el("p", { textContent: "Couldn't save on this device. Your medicines will be lost when you close this page." }));
  };
  const showUndo = (removed, index) => {
    clearTimeout(undoTimer);
    undo.replaceChildren(`Removed ${removed.name}.`, button("Undo", `Undo removing ${removed.name}`, () => {
      hideUndo();
      medicines = reinsertAt(medicines, removed, index);
      save();
      render();
    }, "btn-stone undo-btn"));
    undoTimer = setTimeout(hideUndo, 6000);
  };
  document.getElementById("today-date").textContent = todayLabel(new Date());
  const render = () => {
    // Alphabetical so repeats of one medicine stay together; the sort is stable and the indexes below follow it.
    medicines.sort((a, b) => a.name.localeCompare(b.name));
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
        chips.append(...m.times.map((t) => {
          const chip = el("span", { className: "chip", textContent: t[0].toUpperCase() + t.slice(1) });
          chip.dataset.time = t;
          return chip;
        }));
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
          resetForm();
          render();
          showUndo(m, i);
          save();
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
      items.append(...schedule[t].map(({ id, text }) => {
        const key = `${t}|${id}|${day}`;
        const box = el("input", { type: "checkbox", checked: taken.has(key) });
        box.addEventListener("change", () => {
          if (box.checked) taken.add(key); else taken.delete(key);
          saveTaken(local, day, taken);
        });
        const label = el("label");
        label.append(box, text);
        const li = el("li");
        li.append(label);
        return li;
      }));
      slot.append(head, items);
      return slot;
    }));
  };
  medForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const entry = {
      id: editing >= 0 ? medicines[editing].id : crypto.randomUUID(),
      name: nameSelect.value,
      dose: dose.value.trim(),
      times: timeBoxes.filter((b) => b.checked).map((b) => b.value),
      note: note.value.trim(),
    };
    if (editing >= 0) medicines[editing] = entry; else medicines.push(entry);
    save();
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
