import { mouthFrame } from "./logic.js";

// A drawn face whose mouth follows the audio volume through a Web Audio analyser.
// With web/avatar/{portrait,mouth_half,mouth_open,eyes_closed}.png present it shows those frames;
// if any is missing it draws a simple face instead.
const FRAMES = { closed: "portrait", half: "mouth_half", open: "mouth_open", blink: "eyes_closed" };
const loadFrames = () => Promise.all(Object.entries(FRAMES).map(([key, name]) => new Promise((resolve, reject) => {
  const img = new Image();
  img.onload = () => resolve([key, img]);
  img.onerror = reject;
  img.src = `/avatar/${name}.png`;
}))).then(Object.fromEntries, () => null);

export class Avatar {
  constructor(canvas) {
    this.ctx = canvas.getContext("2d");
    this.canvas = canvas;
    this.state = "idle";
    this.rms = 0;
    this.blinkUntil = 0;
    this.source = null;
    this.audio = new AudioContext();
    this.analyser = this.audio.createAnalyser();
    this.analyser.connect(this.audio.destination);
    this.samples = new Float32Array(this.analyser.fftSize);
    this.frames = null;
    loadFrames().then((frames) => { this.frames = frames; });
    this.scheduleBlink();
    requestAnimationFrame(() => this.draw());
  }

  setState(state) { this.state = state; }

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
    const { ctx, canvas } = this;
    const w = canvas.width, h = canvas.height;
    ctx.clearRect(0, 0, w, h);
    if (this.frames) {
      const blinking = performance.now() < this.blinkUntil;
      ctx.drawImage(this.frames[blinking ? "blink" : mouthFrame(this.rms)], 0, 0, w, h);
      return requestAnimationFrame(() => this.draw());
    }
    ctx.fillStyle = "#f3d3b5";
    ctx.beginPath();
    ctx.arc(w / 2, h / 2, w * 0.45, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = ctx.strokeStyle = "#222";
    ctx.lineWidth = 3;
    const blinking = performance.now() < this.blinkUntil;
    for (const x of [0.35, 0.65]) {
      ctx.beginPath();
      if (blinking) { ctx.moveTo(w * x - 8, h * 0.4); ctx.lineTo(w * x + 8, h * 0.4); ctx.stroke(); }
      else { ctx.arc(w * x, h * 0.4, 6, 0, Math.PI * 2); ctx.fill(); }
    }
    const open = { closed: 0.02, half: 0.07, open: 0.14 }[mouthFrame(this.rms)];
    ctx.beginPath();
    ctx.ellipse(w / 2, h * 0.68, w * 0.12, h * open, 0, 0, Math.PI * 2);
    ctx.fill();
    if (this.state === "thinking") {
      ctx.font = "32px sans-serif";
      ctx.fillText("…", w * 0.75, h * 0.2);
    }
    requestAnimationFrame(() => this.draw());
  }
}
