import { Avatar } from "./avatar.js";
import { startRecording } from "./voice.js";
import { el, leafletLink } from "./dom.js";

// The MedMate view: ask by text or voice, show the reply. `meds()` gives the current medicines list
// and `isShown()` says whether this view is the visible one (Space must not start the mic from the other view).
export function initChat(meds, isShown) {
  const answer = document.getElementById("answer");
  const sources = document.getElementById("sources");
  const card = document.getElementById("card");
  const reply = document.getElementById("reply");
  const replyTitle = document.getElementById("reply-title");
  const avatar = new Avatar(document.getElementById("avatar"));
  // Every reply kind but a plain answer gets a visible title (and an icon in CSS), so meaning never rests on colour alone.
  const TITLES = {
    loading: "Looking in your leaflets",
    emergency: "Call 999 now",
    not_covered: "Not in my leaflets",
    off_topic: "Medicines only",
    fallback: "Check with your pharmacist",
    not_heard: "Let's try again",
    type_instead: "Please type instead",
    error: "Let's try again",
  };
  // Shows a new reply and clears the previous answer's card and sources.
  const show = (kind, text) => {
    reply.dataset.kind = kind;
    replyTitle.textContent = TITLES[kind] ?? "";
    answer.textContent = text;
    answer.className = kind;
    card.replaceChildren();
    sources.replaceChildren();
    reply.classList.remove("print");
    void reply.offsetWidth;  // restart the print-out animation
    reply.classList.add("print");
  };
  // Speaks the reply; if every TTS engine fails the caption is already on screen, so just stay silent.
  const speak = async (text) => {
    try {
      const res = await fetch("/api/tts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      if (res.ok) await avatar.speak(await res.arrayBuffer());
    } catch {}
    avatar.setState("idle");
  };
  const heard = document.getElementById("heard");
  const input = document.getElementById("q");
  const send = document.getElementById("send");
  let busy = false;  // one request at a time: a second Send or recording is ignored until this one ends
  const exclusive = async (fn) => {
    if (busy) return;
    busy = true;
    send.disabled = true;
    try { await fn(); } finally { busy = false; send.disabled = false; }
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
  // The example questions in the empty state ask themselves.
  answer.addEventListener("click", (e) => {
    const example = e.target.closest(".example");
    if (!example) return;
    input.value = example.textContent;
    ask(example.textContent);
  });

  const mic = document.getElementById("mic");
  let stopRecording = null;
  let starting = false;   // waiting for getUserMedia
  let released = false;   // the button came up while starting
  const startMic = async () => {
    avatar.stop();
    if (busy || stopRecording || starting) return;
    starting = true;
    released = false;
    try {
      stopRecording = await startRecording();
    } catch {
      show("type_instead", "Microphone not available. Please type your question.");
      input.focus();
      return;
    } finally {
      starting = false;
    }
    mic.setAttribute("aria-pressed", "true");
    mic.textContent = "Listening…";
    if (released) stopMic();  // let go before the microphone opened
  };
  const stopMic = () => {
    const stop = stopRecording;
    if (!stop) { released = true; return; }
    stopRecording = null;
    mic.setAttribute("aria-pressed", "false");
    mic.textContent = "Hold to talk";
    exclusive(async () => {
      avatar.setState("thinking");
      show("loading", "Working out what you said…");
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
      // The transcript lands in the question box, as if typed, then is sent;
      // #heard is a hidden live region so screen readers still hear it.
      input.value = text;
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
  mic.addEventListener("pointerdown", (e) => { e.preventDefault(); startMic(); });
  for (const ev of ["pointerup", "pointercancel"]) mic.addEventListener(ev, stopMic);
  // Keyboard users press Space to start and again to stop, anywhere on the page except where Space
  // already does something (typing, ticking a box, pressing another button or link).
  const spaceIsTaken = (t) => t !== mic && t.closest("input, textarea, select, button, a, [contenteditable]");
  document.addEventListener("keydown", (e) => {
    if (e.key !== " " || !isShown() || spaceIsTaken(e.target)) return;
    e.preventDefault();
    if (e.repeat) return;
    if (stopRecording) stopMic(); else startMic();
  });
  mic.addEventListener("keyup", (e) => { if (e.key === " ") e.preventDefault(); });

  async function askQuestion(question) {
    avatar.stop();
    avatar.setState("thinking");
    show("loading", "One moment…");
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
    show(data.kind, data.answer);
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
    card.replaceChildren(...(data.card ? [
      ...section("Summary", data.card.summary),
      ...section("What to do", data.card.what_to_do),
      ...section("Get help if", data.card.get_help_if, "help"),
    ] : []));
    sources.replaceChildren(...data.sources.map((s) => {
      const li = el("li");
      li.append(leafletLink(s));
      return li;
    }));
    await speak(data.answer);
  }
}
