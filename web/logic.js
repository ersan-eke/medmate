// Pure page logic, kept free of the DOM so `node --test web/` can run it.
const KEY = "medmate.medicines";
export const TIMES = ["morning", "midday", "evening", "bedtime"];

export function loadMedicines(storage) {
  try {
    const list = JSON.parse(storage.getItem(KEY) ?? "[]");
    if (Array.isArray(list)) return list.filter((m) => typeof m?.name === "string" && m.name).map(clean);
  } catch {}
  storage.removeItem(KEY);
  return [];
}

// Hand-edited or stale entries would otherwise break the schedule or get the chat request rejected.
const text = (v) => (typeof v === "string" ? v : "");
const clean = (m) => ({
  name: m.name,
  dose: text(m.dose),
  times: Array.isArray(m.times) ? m.times.filter((t) => TIMES.includes(t)) : [],
  note: text(m.note),
});

export function saveMedicines(storage, list) {
  storage.setItem(KEY, JSON.stringify(list));
}

export function buildSchedule(list) {
  return Object.fromEntries(
    TIMES.map((t) => [t, list.filter((m) => m.times?.includes(t)).map((m) => `${m.name} ${m.dose}`.trim())]),
  );
}

// A missing or non-array interaction list must not break the sidebar, so it counts as none (rows are checked at startup, #35).
export function findInteractions(list, interactions) {
  if (!Array.isArray(interactions)) return [];
  const have = new Set(list.filter((m) => typeof m?.name === "string").map((m) => m.name.toLowerCase()));
  return interactions.filter((i) => have.has(i.a.toLowerCase()) && have.has(i.b.toLowerCase()));
}

// Mouth frame from audio volume (RMS of the waveform, 0..1).
export function mouthFrame(rms) {
  return rms < 0.02 ? "closed" : rms < 0.08 ? "half" : "open";
}
