import { mouthFrame } from "./logic.js";

// MedMate's drawn face, with the same interface as the canvas Avatar. The mouth follows the audio
// volume through a Web Audio analyser; the state shows in the status pill and the arch's ring.
const STATUS = { idle: "Ready to listen", listening: "Listening", thinking: "Thinking", speaking: "Speaking" };
const MOUTH = {
  idle: "M89 114C93 119 107 119 111 114",
  listening: "M92 114C95 117 105 117 108 114",
  half: "M89 113C93 120 107 120 111 113",
  open: "M90 112C94 128 106 128 110 112Z",
};

export class Avatar {
  constructor(root) {
    this.root = root;
    this.mouth = root.querySelector("#face-mouth");
    this.text = root.querySelector("#face-status-text");
    this.source = null;
    this.audio = new AudioContext();
    this.analyser = this.audio.createAnalyser();
    this.analyser.connect(this.audio.destination);
    this.samples = new Float32Array(this.analyser.fftSize);
    this.setState("idle");
  }

  setState(state) {
    this.state = state;
    this.root.dataset.state = state;
    this.text.textContent = STATUS[state];
    this.setMouth(state === "listening" ? MOUTH.listening : MOUTH.idle, false);
  }

  setMouth(d, filled) {
    this.mouth.setAttribute("d", d);
    this.mouth.setAttribute("fill", filled ? "#8C4A3C" : "none");
  }

  // Resolves when the audio ends or stop() is called.
  async speak(wav) {
    this.stop();
    await this.audio.resume();
    const source = this.audio.createBufferSource();
    source.buffer = await this.audio.decodeAudioData(wav);
    source.connect(this.analyser);
    this.source = source;
    this.setState("speaking");
    requestAnimationFrame(() => this.draw(source));
    await new Promise((resolve) => { source.onended = resolve; source.start(); });
    if (this.source === source) { this.source = null; this.setState("idle"); }
  }

  stop() {
    const source = this.source;
    this.source = null;
    if (source) { source.stop(); this.setState("idle"); }
  }

  // Only the animation frame loop of the source that is playing runs.
  draw(source) {
    if (this.source !== source) return;
    this.analyser.getFloatTimeDomainData(this.samples);
    const rms = Math.sqrt(this.samples.reduce((s, x) => s + x * x, 0) / this.samples.length);
    const frame = mouthFrame(rms);
    this.setMouth(frame === "closed" ? MOUTH.idle : MOUTH[frame], frame === "open");
    requestAnimationFrame(() => this.draw(source));
  }
}
