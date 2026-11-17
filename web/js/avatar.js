import { mouthFrame } from "./logic.js";

// MedMate's portrait: the mouth follows the audio volume through a Web Audio analyser and the eyes blink.
// The frames are web/avatar/{portrait,mouth_half,mouth_open,eyes_closed}.png; the state shows in the status pill and the arch's ring.
const STATUS = { idle: "Ready to listen", listening: "Listening", thinking: "Thinking", speaking: "Speaking" };
const FRAMES = { closed: "portrait", half: "mouth_half", open: "mouth_open", blink: "eyes_closed" };
const loadFrames = () => Promise.all(Object.entries(FRAMES).map(([key, name]) => new Promise((resolve, reject) => {
  const img = new Image();
  img.onload = () => resolve([key, img]);
  img.onerror = reject;
  img.src = `/avatar/${name}.png`;
}))).then(Object.fromEntries, () => null);

export class Avatar {
  constructor(root) {
    this.root = root;
    this.canvas = root.querySelector("canvas");
    this.ctx = this.canvas.getContext("2d");
    this.text = root.querySelector("#face-status-text");
    this.rms = 0;
    this.halo = 0;
    this.blinkUntil = 0;
    this.source = null;
    this.audio = new AudioContext();
    this.analyser = this.audio.createAnalyser();
    this.analyser.connect(this.audio.destination);
    this.samples = new Float32Array(this.analyser.fftSize);
    this.frames = null;
    loadFrames().then((frames) => { this.frames = frames; });
    this.scheduleBlink();
    this.setState("idle");
    requestAnimationFrame(() => this.draw());
  }

  setState(state) {
    this.state = state;
    this.root.dataset.state = state;
    this.text.textContent = STATUS[state];
  }

  scheduleBlink() {
    setTimeout(() => {
      this.blinkUntil = performance.now() + 150;
      this.scheduleBlink();
    }, 3000 + Math.random() * 3000);
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
    await new Promise((resolve) => { source.onended = resolve; source.start(); });
    if (this.source === source) { this.source = null; this.setState("idle"); }
  }

  stop() {
    const source = this.source;
    this.source = null;
    if (source) { source.stop(); this.setState("idle"); }
  }

  draw() {
    if (this.state === "speaking") {
      this.analyser.getFloatTimeDomainData(this.samples);
      this.rms = Math.sqrt(this.samples.reduce((s, x) => s + x * x, 0) / this.samples.length);
    } else {
      this.rms = 0;
    }
    // The halo follows the volume: quick to swell, slow to settle, so it breathes with the voice.
    this.halo += (Math.min(this.rms * 6, 1) - this.halo) * (this.rms > this.halo / 6 ? 0.4 : 0.1);
    this.root.style.setProperty("--halo", this.halo.toFixed(3));
    const { ctx, canvas } = this;
    const w = canvas.width, h = canvas.height;
    ctx.clearRect(0, 0, w, h);
    if (this.frames) {
      const blinking = performance.now() < this.blinkUntil;
      ctx.drawImage(this.frames[blinking ? "blink" : mouthFrame(this.rms)], 0, 0, w, h);
    }
    requestAnimationFrame(() => this.draw());
  }
}
