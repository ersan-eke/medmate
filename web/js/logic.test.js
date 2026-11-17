import { test } from "node:test";
import assert from "node:assert/strict";
import {
  buildSchedule, mouthFrame, findInteractions, loadMedicines, saveMedicines,
  replyCard, medicinesTag, loadThread, saveThread, showSuggestions,
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
  const list = [{ name: "Metformin", dose: "500 mg", times: ["morning", "evening"], note: "with food" }];
  saveMedicines(s, list);
  assert.deepEqual(loadMedicines(s), list);
});

test("schedule groups doses by time of day, in list order", () => {
  const list = [
    { name: "Metformin", dose: "500 mg", times: ["morning", "evening"], note: "" },
    { name: "Amlodipine", dose: "5 mg", times: ["morning"], note: "" },
    { name: "Warfarin", dose: "", times: [], note: "" },
  ];
  assert.deepEqual(buildSchedule(list), {
    morning: ["Metformin 500 mg", "Amlodipine 5 mg"],
    midday: [],
    evening: ["Metformin 500 mg"],
    bedtime: [],
  });
});

test("malformed entries are dropped or repaired, not passed on", () => {
  const saved = [null, 7, { dose: "5 mg" }, { name: "Metformin", dose: 500, times: ["morning", "noon", 3], note: null }];
  assert.deepEqual(loadMedicines(fakeStorage({ [KEY]: JSON.stringify(saved) })), [
    { name: "Metformin", dose: "", times: ["morning"], note: "" },
  ]);
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
  assert.equal(replyCard("emergency").title, "Call 999 now");
  assert.equal(replyCard("not_covered").title, "Not in my leaflets");
  assert.equal(replyCard("off_topic").title, "Medicines only");
  assert.equal(replyCard("fallback").title, "Check with your pharmacist");
  assert.equal(replyCard("type_instead").title, "Please type instead");
  assert.deepEqual(replyCard("something_new"), replyCard("error"));
});

test("medicines tag: listed, unlisted and no sources", () => {
  const list = [{ name: "metformin" }, { name: "Warfarin" }];
  assert.equal(medicinesTag([{ medicine: "Metformin" }], list), "In your medicines");
  assert.equal(medicinesTag([{ medicine: "Ramipril" }, { medicine: "Warfarin" }], list), "In your medicines");
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
