import { Avatar } from "./face.js";
import { startRecording } from "./voice.js";
import { el, leafletLink } from "./dom.js";
import { loadThread, saveThread, clearThread, replyCard, medicinesTag, showSuggestions } from "./logic.js";

// The MedMate view: ask by text or voice, show the reply. `meds()` gives the current medicines list
// and `isShown()` says whether this view is the visible one (Space must not start the mic from the other view).
export function initChat(meds, isShown) {
  const thread = document.getElementById("thread");
  const empty = document.getElementById("empty");
  const avatar = new Avatar(document.getElementById("avatar"));
  let entries = loadThread(sessionStorage);
  let pending = null;  // the "One moment…" card while a request is out

  // A section with no text shows no heading.
  const section = (title, items, cls = "") => {
    items = [].concat(items).filter((t) => t && t.trim());
    if (!items.length) return [];
    const sec = el("section", { className: cls });
    const ul = el("ul");
    ul.append(...items.map((t) => el("li", { textContent: t })));
    sec.append(el("h2", { textContent: title }), ul);
    return [sec];
  };
  const replyNode = (r) => {
    const { tone, title, icon } = replyCard(r.kind);
    const node = el("article", { className: "label msg medmate" });
    node.dataset.kind = r.kind;
    node.dataset.tone = tone;
    node.dataset.icon = icon;
    node.append(el("p", { className: "label-title", textContent: title }), el("div", { className: "answer", textContent: r.answer }));
    if (r.kind !== "loading") node.append(el("button", { type: "button", className: "read-aloud", textContent: "Read aloud", onclick: () => speak(r.answer) }));
    const cardSections = r.card ? [
      ...section("Summary", r.card.summary),
      ...section("What to do", r.card.what_to_do),
      ...section("Get help if", r.card.get_help_if, "help"),
    ] : [];
    if (cardSections.length) node.append(el("div", { className: "card" }, cardSections));
    if (r.sources?.length) {
      const list = el("ul");
      list.append(...r.sources.map((s) => {
        const li = el("li");
        li.append(leafletLink(s));
        return li;
      }));
      const box = el("div", { className: "sources" });
      box.append(el("p", { className: "sources-title", textContent: "From the NHS leaflets" }), list);
      const tag = medicinesTag(r.sources, meds());
      if (tag) box.append(el("p", { className: "tag", textContent: tag }));
      node.append(box);
    }
    return node;
  };
  const entryNode = (e) => (e.role === "user" ? el("div", { className: "msg user", textContent: e.text }) : replyNode(e));
  // Puts a node at the end of the thread and brings it into view; the new reply "prints out".
  const place = (node) => {
    thread.append(node);
    node.classList.add("print");
    thread.scrollTop = thread.scrollHeight;
  };
  const draw = () => {
    pending = null;
    thread.replaceChildren(empty, ...entries.map(entryNode));
    empty.hidden = !showSuggestions(entries);
    thread.scrollTop = thread.scrollHeight;
  };
  const add = (entry) => {
    entries.push(entry);
    saveThread(sessionStorage, entries);
    empty.hidden = !showSuggestions(entries);
    pending?.remove();
    pending = null;
    place(entryNode(entry));
  };
  // A waiting card has no entry: it is never saved, and the real reply replaces it.
  const wait = (text) => {
    pending?.remove();
    pending = replyNode({ kind: "loading", answer: text });
    place(pending);
  };
  const show = (kind, answer) => add({ role: "medmate", kind, answer, sources: [] });
  draw();  // restore the saved thread on load
  // Speaks the reply; if every TTS engine fails the caption is already on screen, so just stay silent.
  // Only the newest request may play or reset the face: an older fetch that finishes late is dropped.
  let speechId = 0;
  const stopSpeech = () => { speechId++; avatar.stop(); };
  const speak = async (text) => {
    stopSpeech();
    const id = speechId;
    try {
      const res = await fetch("/api/tts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      const wav = res.ok && await res.arrayBuffer();
      if (wav && id === speechId) await avatar.speak(wav);
    } catch {}
    if (id === speechId) avatar.setState("idle");
  };
  const heard = document.getElementById("heard");
  const input = document.getElementById("q");
  const send = document.getElementById("send");
  const reset = document.getElementById("reset");
  let busy = false;  // one request at a time: a second Send or recording is ignored until this one ends
  const exclusive = async (fn) => {
    if (busy) return;
    busy = true;
    send.disabled = reset.disabled = true;
    try { await fn(); } finally { busy = false; send.disabled = reset.disabled = false; }
  };
  const ask = (question) => exclusive(() => { heard.textContent = ""; return askQuestion(question); });
  document.getElementById("form").addEventListener("submit", (e) => {
    e.preventDefault();
    ask(input.value);
  });
  // The question box wraps long questions, but Enter still sends like a one-line box.
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
      e.preventDefault();
      e.target.form.requestSubmit();
    }
  });
  // On a phone the keyboard shrinks the thread after focus; keep the newest message above it.
  const toBottom = () => { thread.scrollTop = thread.scrollHeight; };
  input.addEventListener("focus", toBottom);
  window.addEventListener("resize", () => { if (document.activeElement === input) toBottom(); });
  // The example questions in the empty state ask themselves.
  empty.addEventListener("click", (e) => {
    const example = e.target.closest(".example");
    if (example) ask(example.textContent);
  });
  reset.addEventListener("click", () => {
    stopSpeech();
    entries = [];
    clearThread(sessionStorage);
    draw();
  });

  const mics = [...document.querySelectorAll(".talk")];  // the big button and the small one share one recorder
  const bigText = document.querySelector("#mic .talk-text");
  let stopRecording = null;
  let starting = false;   // waiting for getUserMedia
  const showListening = (on) => {
    for (const m of mics) {
      m.toggleAttribute("data-listening", on);
      m.setAttribute("aria-label", on ? "Stop listening" : m.id === "mic" ? "Tap to talk" : "Talk");
    }
    bigText.textContent = on ? "Stop listening" : "Tap to talk";
  };
  const startMic = async () => {
    stopSpeech();
    if (busy || starting) return;
    starting = true;
    try {
      stopRecording = await startRecording();
    } catch {
      show("type_instead", "Microphone not available. Please type your question.");
      input.focus();
      return;
    } finally {
      starting = false;
    }
    showListening(true);
    avatar.setState("listening");
  };
  const stopMic = () => {
    const stop = stopRecording;
    stopRecording = null;
    showListening(false);
    exclusive(async () => {
      avatar.setState("thinking");
      wait("Working out what you said…");
      const body = new FormData();
      body.append("audio", await stop(), "question.webm");
      const res = await fetch("/api/transcribe", { method: "POST", body }).catch(() => null);
      if (!res?.ok) {
        avatar.setState("idle");
        show("type_instead", "Sorry, I couldn't hear that. Please type your question.");
        input.focus();
        return;
      }
      const { text } = await res.json();
      // #heard is a hidden live region so screen readers still hear it.
      // A blank question gets the "didn't catch that" reply from /api/chat.
      if (text.trim()) {
        heard.textContent = `You asked: ${text}`;
        await speak(`You asked about ${text}.`);
      } else {
        heard.textContent = "";
      }
      await askQuestion(text);
    });
  };
  const toggleMic = () => (stopRecording ? stopMic() : startMic());
  for (const m of mics) m.addEventListener("click", toggleMic);
  // Space toggles the mic anywhere on the page except where Space already does something (typing,
  // ticking a box, pressing a button or link; the talk buttons toggle themselves on Space).
  document.addEventListener("keydown", (e) => {
    if (e.key !== " " || !isShown() || e.target.closest("input, textarea, select, button, a, [contenteditable]")) return;
    e.preventDefault();
    if (!e.repeat) toggleMic();
  });

  async function askQuestion(question) {
    stopSpeech();
    avatar.setState("thinking");
    input.value = "";
    // A blank question gets the "didn't catch that" reply without a bubble of its own.
    if (question.trim()) add({ role: "user", text: question });
    wait("One moment…");
    let data;
    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, medicines: meds() }),
      });
      if (!res.ok) throw new Error(res.status);
      data = await res.json();
    } catch {
      avatar.setState("idle");
      show("error", "Sorry, something went wrong. Please try again.");
      return;
    }
    add({ role: "medmate", kind: data.kind, answer: data.answer, card: data.card, sources: data.sources });
    await speak(data.answer);
  }
}
