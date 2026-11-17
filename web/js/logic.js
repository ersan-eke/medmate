// Pure page logic, kept free of the DOM so `node --test web/logic.test.js` can run it.
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

// How each reply kind is drawn: card tone, visible title and icon name (meaning never rests on colour alone).
// The page styles `data-tone` and `data-icon`; an unknown kind from a newer server is shown like an error.
const CARDS = {
  answer: { tone: "answer", title: "From your leaflets", icon: "doc" },
  emergency: { tone: "emergency", title: "Call 999 now", icon: "phone" },
  not_covered: { tone: "amber", title: "Not in my leaflets", icon: "person" },
  off_topic: { tone: "amber", title: "Medicines only", icon: "person" },
  fallback: { tone: "amber", title: "Check with your pharmacist", icon: "question" },
  not_heard: { tone: "amber", title: "Let's try again", icon: "mic" },
  type_instead: { tone: "amber", title: "Please type instead", icon: "keyboard" },
  error: { tone: "amber", title: "Let's try again", icon: "retry" },
  loading: { tone: "answer", title: "Looking in your leaflets", icon: "search" },  // shown while waiting, never saved
};
export const replyCard = (kind) => CARDS[kind] ?? CARDS.error;

// "In your medicines" when a source leaflet is for a medicine on the list; no tag for a reply without sources.
export function medicinesTag(sources, list) {
  if (!Array.isArray(sources) || !sources.length) return null;
  const have = new Set(list.filter((m) => typeof m?.name === "string").map((m) => m.name.toLowerCase()));
  return sources.some((s) => have.has(String(s.medicine).toLowerCase())) ? "In your medicines" : "Not in your medicines";
}

// The chat thread: entries are { role: "user", text } or { role: "medmate", kind, answer, card, sources }.
// It lives in sessionStorage, so a reload keeps it and a new tab starts empty.
const THREAD_KEY = "medmate.thread";
const isEntry = (e) =>
  e?.role === "user" ? typeof e.text === "string" : e?.role === "medmate" && typeof e.kind === "string" && typeof e.answer === "string";

export function loadThread(storage) {
  try {
    const thread = JSON.parse(storage.getItem(THREAD_KEY) ?? "[]");
    if (Array.isArray(thread)) {
      return thread.filter(isEntry).map((e) => (e.role === "medmate" ? { ...e, sources: Array.isArray(e.sources) ? e.sources : [] } : e));
    }
    storage.removeItem(THREAD_KEY);
  } catch {
    try { storage.removeItem(THREAD_KEY); } catch {}
  }
  return [];
}

// Saving is best effort: a full or blocked store must not stop the chat.
export function saveThread(storage, thread) {
  try { storage.setItem(THREAD_KEY, JSON.stringify(thread)); } catch {}
}

export const showSuggestions = (thread) => thread.length === 0;
