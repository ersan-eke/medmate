import { test } from "node:test";
import assert from "node:assert/strict";
import {
  buildSchedule, mouthFrame, findInteractions, loadMedicines, saveMedicines,
  replyCard, medicinesTag, loadThread, saveThread, showSuggestions,
  countLabel, todayLabel, reinsertAt, store, loadTaken, saveTaken,
} from "./logic.js";

const KEY = "medmate.medicines";
const fakeStorage = (init = {}) => {
  const m = new Map(Object.entries(init));
  return {
    getItem: (k) => (m.has(k) ? m.get(k) : null),
    setItem: (k, v) => m.set(k, String(v)),
    removeItem: (k) => m.delete(k),
    has: (k) => m.has(k),
  };
};

test("missing list loads empty", () => {
  assert.deepEqual(loadMedicines(fakeStorage()), []);
});

for (const [label, saved] of [["bad JSON", "{not json"], ["an object", '{"name":"Metformin"}'], ["null", "null"]]) {
  test(`${label} resets to empty and is removed`, () => {
    const s = fakeStorage({ [KEY]: saved });
    assert.deepEqual(loadMedicines(s), []);
    assert.equal(s.has(KEY), false);
  });
}

test("save then load round-trips", () => {
  const s = fakeStorage();
  const list = [{ id: "m", name: "Metformin", dose: "500 mg", times: ["morning", "evening"], note: "with food" }];
  saveMedicines(s, list);
  assert.deepEqual(loadMedicines(s), list);
});

test("schedule groups doses by time of day, in list order", () => {
  const list = [
    { id: "m", name: "Metformin", dose: "500 mg", times: ["morning", "evening"], note: "" },
    { id: "a", name: "Amlodipine", dose: "5 mg", times: ["morning"], note: "" },
    { id: "w", name: "Warfarin", dose: "", times: [], note: "" },
  ];
  assert.deepEqual(buildSchedule(list), {
    morning: [{ id: "m", text: "Metformin 500 mg" }, { id: "a", text: "Amlodipine 5 mg" }],
    midday: [],
    evening: [{ id: "m", text: "Metformin 500 mg" }],
    bedtime: [],
  });
});

test("malformed entries are dropped or repaired, not passed on", () => {
  const saved = [null, 7, { dose: "5 mg" }, { name: "Metformin", dose: 500, times: ["morning", "noon", 3], note: null }];
  const [m] = loadMedicines(fakeStorage({ [KEY]: JSON.stringify(saved) }));
  assert.deepEqual({ ...m, id: "x" }, { id: "x", name: "Metformin", dose: "", times: ["morning"], note: "" });
});

test("long text is clipped to what the server accepts", () => {
  const [m] = loadMedicines(fakeStorage({ [KEY]: JSON.stringify([{ id: "m", name: "Metformin", dose: "x".repeat(200) }]) }));
  assert.equal(m.dose.length, 100);
});

test("ticks load for the same day only", () => {
  const s = fakeStorage();
  saveTaken(s, "Mon", new Set(["morning|m|Mon"]));
  assert.deepEqual([...loadTaken(s, "Mon")], ["morning|m|Mon"]);
  assert.equal(loadTaken(s, "Tue").size, 0);
});

test("entries without an id get one that is saved, so it survives a reload", () => {
  const s = fakeStorage({ [KEY]: JSON.stringify([{ name: "Metformin", dose: "", times: [], note: "" }]) });
  const [m] = loadMedicines(s);
  assert.ok(m.id);
  assert.equal(loadMedicines(s)[0].id, m.id);
});

test("interactions match either order, ignoring case", () => {
  const row = { a: "Warfarin", b: "Ibuprofen", warning: "w", source: {} };
  assert.deepEqual(findInteractions([{ name: "warfarin" }, { name: "Ibuprofen" }], [row]), [row]);
  assert.deepEqual(findInteractions([{ name: "IBUPROFEN" }, { name: "Warfarin" }], [row]), [row]);
  assert.deepEqual(findInteractions([{ name: "Metformin" }], [row]), []);
});

test("interactions skip entries without a usable name and tolerate a bad list", () => {
  const row = { a: "Warfarin", b: "Ibuprofen", warning: "w", source: {} };
  const list = [{}, { name: 7 }, null, { name: "Warfarin" }, { name: "Ibuprofen" }];
  assert.deepEqual(findInteractions(list, [row]), [row]);
  assert.deepEqual(findInteractions(list, []), []);
  assert.deepEqual(findInteractions(list, undefined), []);
  assert.deepEqual(findInteractions(list, { a: "Warfarin" }), []);
});

test("mouthFrame follows the volume", () => {
  assert.equal(mouthFrame(0), "closed");
  assert.equal(mouthFrame(0.05), "half");
  assert.equal(mouthFrame(0.3), "open");
});

test("every reply kind has a title and an icon, and only some are red or blue", () => {
  const want = {
    answer: "answer", emergency: "emergency", not_covered: "amber", off_topic: "amber",
    fallback: "amber", not_heard: "amber", type_instead: "amber", error: "amber",
  };
  for (const [kind, tone] of Object.entries(want)) {
    const c = replyCard(kind);
    assert.equal(c.tone, tone, kind);
    assert.ok(c.title && c.icon, kind);
  }
  assert.equal(replyCard("answer").title, "From your NHS leaflets");
  assert.equal(replyCard("emergency").title, "Call 999 now");
  assert.equal(replyCard("not_covered").title, "Not in my leaflets");
  assert.equal(replyCard("off_topic").title, "Medicines only");
  assert.equal(replyCard("fallback").title, "Check with your pharmacist");
  assert.equal(replyCard("type_instead").title, "Please type instead");
  assert.deepEqual(replyCard("something_new"), replyCard("error"));
});

test("medicines tag: listed with and without times, unlisted and no sources", () => {
  const list = [{ name: "metformin", times: ["morning", "evening"] }, { name: "Warfarin", times: [] }];
  assert.equal(medicinesTag([{ medicine: "Metformin" }], list), "In your medicines: metformin (Morning, Evening)");
  assert.equal(medicinesTag([{ medicine: "Ramipril" }, { medicine: "Warfarin" }], list), "In your medicines: Warfarin");
  assert.equal(medicinesTag([{ medicine: "Ramipril" }], list), "Not in your medicines");
  assert.equal(medicinesTag([{ medicine: "Ramipril" }], []), "Not in your medicines");
  assert.equal(medicinesTag([], list), null);
  assert.equal(medicinesTag(undefined, list), null);
});

const THREAD_KEY = "medmate.thread";
test("thread round-trips, and a missing value is empty", () => {
  const s = fakeStorage();
  assert.deepEqual(loadThread(s), []);
  const thread = [
    { role: "user", text: "When should I take metformin?" },
    { role: "medmate", kind: "answer", answer: "With food.", card: { summary: "s" }, sources: [{ medicine: "Metformin" }] },
    { role: "medmate", kind: "error", answer: "Sorry.", sources: [] },
  ];
  saveThread(s, thread);
  assert.deepEqual(loadThread(s), thread);
});

for (const [label, saved] of [["bad JSON", "{not json"], ["an object", '{"role":"user"}'], ["null", "null"]]) {
  test(`thread: ${label} loads empty and is removed`, () => {
    const s = fakeStorage({ [THREAD_KEY]: saved });
    assert.deepEqual(loadThread(s), []);
    assert.equal(s.has(THREAD_KEY), false);
  });
}

test("thread drops malformed entries and defaults missing sources", () => {
  const saved = [null, 7, { role: "user" }, { role: "medmate", kind: "answer" }, { role: "medmate", kind: "answer", answer: "x" }];
  const s = fakeStorage({ [THREAD_KEY]: JSON.stringify(saved) });
  assert.deepEqual(loadThread(s), [{ role: "medmate", kind: "answer", answer: "x", sources: [] }]);
});

test("a blocked store does not stop saving or loading", () => {
  const broken = { getItem() { throw new Error("no"); }, setItem() { throw new Error("no"); }, removeItem() { throw new Error("no"); } };
  assert.deepEqual(loadThread(broken), []);
  saveThread(broken, [{ role: "user", text: "hi" }]);
});

test("suggestions show only for an empty thread", () => {
  assert.equal(showSuggestions([]), true);
  assert.equal(showSuggestions([{ role: "user", text: "hi" }]), false);
});

test("the count reads naturally for none, one and many", () => {
  assert.deepEqual([0, 1, 3].map(countLabel), ["0 medicines", "1 medicine", "3 medicines"]);
});

test("today's date is written out in full", () => {
  assert.equal(todayLabel(new Date(2026, 10, 17)), "Tuesday 17 November");
});

test("an undone medicine goes back to its old position, clamped to the list", () => {
  assert.deepEqual(reinsertAt(["a", "c"], "b", 1), ["a", "b", "c"]);
  assert.deepEqual(reinsertAt(["a"], "b", 5), ["a", "b"]);
  assert.deepEqual(reinsertAt([], "b", 0), ["b"]);
});

test("stored entries over the server's limits are cut on load, so chat is never refused", () => {
  const long = "x".repeat(101);
  const many = Array.from({ length: 51 }, (_, i) => ({ id: `m${i}`, name: "Metformin", dose: "", times: [], note: "" }));
  const [first] = loadMedicines(fakeStorage({ [KEY]: JSON.stringify([{ id: "a", name: long, dose: long, times: [], note: long }]) }));
  assert.deepEqual([first.name.length, first.dose.length, first.note.length], [100, 100, 100]);
  assert.equal(loadMedicines(fakeStorage({ [KEY]: JSON.stringify(many) })).length, 50);
});

test("a blocked browser store is replaced by one that works until the page closes", () => {
  const blocked = { get localStorage() { throw new DOMException("denied", "SecurityError"); } };
  const s = store("localStorage", blocked);
  assert.equal(s.getItem("k"), null);
  s.setItem("k", "v");
  assert.equal(s.getItem("k"), "v");
  s.removeItem("k");
  assert.equal(s.getItem("k"), null);
});

test("an available browser store is used as it is", () => {
  const real = fakeStorage();
  assert.equal(store("localStorage", { localStorage: real }), real);
});

const full = () => ({ getItem: () => null, setItem() { throw new DOMException("full", "QuotaExceededError"); }, removeItem() { throw new Error("no"); } });

test("saving medicines says whether it worked", () => {
  assert.equal(saveMedicines(fakeStorage(), []), true);
  assert.equal(saveMedicines(full(), []), false);
});

test("loading medicines survives a store that refuses to clean up", () => {
  const bad = { getItem: () => "{not json", removeItem() { throw new Error("no"); }, setItem() {} };
  assert.deepEqual(loadMedicines(bad), []);
});

test("thread keeps the answer but drops a card or sources it cannot draw", () => {
  const saved = [
    { role: "medmate", kind: "answer", answer: "a", card: { summary: 5, what_to_do: ["ok", null], get_help_if: "help" }, sources: [null, { medicine: "Metformin" }, { medicine: 3 }] },
    { role: "medmate", kind: "answer", answer: "b", card: "text" },
    { role: "medmate", kind: "answer", answer: "c", card: null, sources: "x" },
  ];
  const s = fakeStorage({ [THREAD_KEY]: JSON.stringify(saved) });
  assert.deepEqual(loadThread(s), [
    { role: "medmate", kind: "answer", answer: "a", card: { summary: "", what_to_do: ["ok"], get_help_if: "help" }, sources: [{ medicine: "Metformin" }] },
    { role: "medmate", kind: "answer", answer: "b", sources: [] },
    { role: "medmate", kind: "answer", answer: "c", sources: [] },
  ]);
});
