import { Avatar } from "./avatar.js";
import { startRecording } from "./voice.js";
import { el, leafletLink } from "./dom.js";
import { store, loadThread, saveThread, clearThread, replyCard, medicinesTag, showSuggestions } from "./logic.js";

// The MedMate view: ask by text or voice, show the reply. `meds()` gives the current medicines list
// and `isShown()` says whether this view is the visible one (Space must not start the mic from the other view).
export function initChat(meds, isShown) {
  const thread = document.getElementById("thread");
  const empty = document.getElementById("empty");
  const notice = document.getElementById("notice");
  const avatar = new Avatar(document.getElementById("avatar"));
  const session = store("sessionStorage");
  let entries = loadThread(session);
  let pending = null;  // the "One moment…" card while a request is out

  // A section with no text shows no heading.
  const section = (title, items, cls = "") => {
    items = [].concat(items).filter((t) => t && t.trim());
    if (!items.length) return [];
    const sec = el(cls ? "aside" : "section", { className: cls });
    if (cls) sec.setAttribute("aria-label", `Important safety warning: ${title}`);
    const ul = el("ul");
    ul.append(...items.map((t) => el("li", { textContent: t })));
    sec.append(el("h3", { textContent: title }), ul);
    return [sec];
  };
  const replyNode = (r) => {
    const { tone, title, icon } = replyCard(r.kind);
    const node = el("article", { className: "msg medmate reply" });
    node.dataset.kind = r.kind;
    node.dataset.tone = tone;
    node.dataset.icon = icon;
    const head = el("header", { className: "reply-head" });
    const who = el("div", { className: "reply-id" });
    const name = el("div");
    name.append(el("span", { className: "reply-name", textContent: "MedMate" }), el("span", { className: "reply-sub", textContent: title }));
    who.append(el("span", { className: "mini-avatar" }), name);
    head.append(who);
    if (r.kind !== "loading") head.append(el("button", { type: "button", className: "read-aloud btn-stone", textContent: "Read aloud", onclick: () => speak(r.answer) }));
    node.append(head);
    const tag = r.sources?.length && medicinesTag(r.sources, meds());
    if (tag) node.append(el("p", { className: tag.startsWith("Not") ? "tag not-listed" : "tag", textContent: tag }));
    node.append(el(r.kind === "answer" ? "blockquote" : "p", { className: "answer", textContent: r.answer }));
    const cardSections = r.card ? [
      ...section("Summary", r.card.summary, ""),
      ...section("What to do", r.card.what_to_do),
      ...section("Get help if", r.card.get_help_if, "help"),
    ] : [];
    node.append(...cardSections);
    if (r.sources?.length) {
      const pills = el("div", { className: "pills" });
      pills.append(...r.sources.map((s) => Object.assign(leafletLink(s), { className: "btn-stone pill" })));
      const box = el("div", { className: "sources" });
      box.append(el("p", { className: "sources-title", textContent: "From the NHS leaflets:" }), pills);
      node.append(box);
    }
    return node;
  };
  const entryNode = (e) => {
    if (e.role !== "user") return replyNode(e);
    const bubble = el("div", { className: "msg user" });
    bubble.append(el("p", { className: "user-tag", textContent: "You asked" }), el("p", { className: "user-text", textContent: `“${e.text}”` }));
    return bubble;
  };
  // Puts a node at the end of the thread and brings it into view; the new reply "prints out".
  const place = (node) => {
    notice.before(node);
    node.classList.add("print");
    thread.scrollTop = thread.scrollHeight;
  };
  const draw = () => {
    pending = null;
    thread.replaceChildren(empty, ...entries.map(entryNode), notice);
    empty.hidden = !showSuggestions(entries);
    thread.scrollTop = thread.scrollHeight;
  };
  // "Didn't hear you" cards go away once a real answer arrives, so they don't stack up.
  const NOT_HEARD = ["not_heard", "type_instead"];
  const add = (entry) => {
    if (entry.role === "medmate" && !NOT_HEARD.includes(entry.kind) && entry.kind !== "error" && entries.some((e) => NOT_HEARD.includes(e.kind))) {
      entries = entries.filter((e) => !NOT_HEARD.includes(e.kind));
      draw();
    }
    entries.push(entry);
    saveThread(session, entries);
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
    clearThread(session);
    draw();
  });

  const mics = [...document.querySelectorAll(".talk")];  // the big button and the small one share one recorder
  const bigText = document.querySelector("#mic .talk-text");
  const bigSub = document.querySelector("#mic .talk-sub");
  const MAX_RECORDING_MS = 28_000;  // under the server's 30 s (MAX_AUDIO_SECONDS) to leave room for recorder start/stop lag
  let stopRecording = null;
  let limitTimer = null;
  let starting = false;   // waiting for getUserMedia
  const showListening = (on) => {
    for (const m of mics) {
      m.toggleAttribute("data-listening", on);
      m.setAttribute("aria-label", on ? "Stop listening" : m.id === "mic" ? "Tap to talk" : "Talk");
    }
    bigText.textContent = on ? "Listening... tap to send" : "Tap to talk";
    bigSub.textContent = on ? "Speak clearly at your own pace" : "Tap once to start, tap again to send";
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
    limitTimer = setTimeout(stopMic, MAX_RECORDING_MS);
  };
  const stopMic = () => {
    clearTimeout(limitTimer);
    const stop = stopRecording;
    stopRecording = null;
    showListening(false);
    exclusive(async () => {
      avatar.setState("thinking");
      wait("Working out what you said…");
      let text;
      try {
        const body = new FormData();
        body.append("audio", await stop(), "question.webm");
        const res = await fetch("/api/transcribe", { method: "POST", body });
        if (!res.ok) throw new Error(res.status);
        ({ text } = await res.json());
      } catch {
        avatar.setState("idle");
        show("type_instead", "Sorry, I couldn't hear that. Please type your question.");
        input.focus();
        return;
      }
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
        // Only name and dose answer a question; the note and times stay in the browser.
        body: JSON.stringify({ question, medicines: meds().map(({ name, dose }) => ({ name, dose })) }),
      });
      if (!res.ok) throw new Error(res.status);
      data = await res.json();
    } catch (e) {
      avatar.setState("idle");
      show("error", e.message === "503" ? "MedMate is busy with another question. Please try again in a moment."
                                        : "Sorry, something went wrong. Please try again.");
      return;
    }
    add({ role: "medmate", kind: data.kind, answer: data.answer, card: data.card, sources: data.sources });
    await speak(data.answer);
  }
}
