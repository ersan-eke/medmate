// Starts recording the microphone; resolves to a function that stops and returns the audio Blob.
// Rejects if microphone permission is denied.
export async function startRecording() {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const recorder = new MediaRecorder(stream);
  const chunks = [];
  recorder.ondataavailable = (e) => chunks.push(e.data);
  recorder.start();
  return () => new Promise((resolve, reject) => {
    const release = () => stream.getTracks().forEach((t) => t.stop());
    recorder.onstop = () => {
      release();
      resolve(new Blob(chunks, { type: recorder.mimeType }));
    };
    // stop() throws if the recorder already died; release the mic and let the caller handle it.
    try { recorder.stop(); } catch (e) { release(); reject(e); }
  });
}
