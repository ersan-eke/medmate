import { test } from "node:test";
import assert from "node:assert/strict";
import { buildSchedule, mouthFrame, findInteractions, loadMedicines, saveMedicines } from "./logic.js";

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
