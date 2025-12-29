import { useRef, useState } from "react";
const WS_URL = "ws://localhost:8000/ws/audio";
const SAMPLE_RATE = 16000;
const FRAME_SAMPLES = 320; // 20ms @ 16kHz
const PREBUFFER_FRAMES = 6;

function floatToInt16(float32) {
  const out = new Int16Array(float32.length);
  for (let i = 0; i < float32.length; i++) {
    let s = Math.max(-1, Math.min(1, float32[i]));
    out[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }
  return out;
}

function int16ToFloat32(int16) {
  const out = new Float32Array(int16.length);
  for (let i = 0; i < int16.length; i++) out[i] = int16[i] / 0x8000;
  return out;
}

function concatInt16(chunks) {
  const total = chunks.reduce((s, a) => s + a.length, 0);
  const out = new Int16Array(total);
  let offset = 0;
  for (const a of chunks) {
    out.set(a, offset);
    offset += a.length;
  }
  return out;
}

function pcm16ToWavBlob(pcm16, sampleRate = 16000, numChannels = 1) {
  const bytesPerSample = 2;
  const blockAlign = numChannels * bytesPerSample;
  const byteRate = sampleRate * blockAlign;
  const dataSize = pcm16.length * bytesPerSample;

  const buffer = new ArrayBuffer(44 + dataSize);
  const view = new DataView(buffer);

  function writeStr(offset, str) {
    for (let i = 0; i < str.length; i++) view.setUint8(offset + i, str.charCodeAt(i));
  }

  writeStr(0, "RIFF");
  view.setUint32(4, 36 + dataSize, true);
  writeStr(8, "WAVE");

  writeStr(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, numChannels, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, byteRate, true);
  view.setUint16(32, blockAlign, true);
  view.setUint16(34, 16, true);

  writeStr(36, "data");
  view.setUint32(40, dataSize, true);

  let off = 44;
  for (let i = 0; i < pcm16.length; i++, off += 2) {
    view.setInt16(off, pcm16[i], true);
  }

  return new Blob([view], { type: "audio/wav" });
}

export function useVoiceStream() {
  
  const manualStopRef = useRef(false);

  const [status, setStatus] = useState("idle");
  const [previewUrl, setPreviewUrl] = useState("");

  const wsRef = useRef(null);
  const ctxRef = useRef(null);
  const streamRef = useRef(null);
  const sourceRef = useRef(null);
  const procRef = useRef(null);

  const accumRef = useRef([]);
  const recvQueueRef = useRef([]);
  const nextPlayTimeRef = useRef(0);
  const isPlayingRef = useRef(false);

  const enhancedChunksRef = useRef([]);

  function resetBuffers() {
    accumRef.current = [];
    recvQueueRef.current = [];
    nextPlayTimeRef.current = 0;
    isPlayingRef.current = false;
    enhancedChunksRef.current = [];
    setPreviewUrl("");
  }

  function scheduleLoop() {
    const ctx = ctxRef.current;
    if (!ctx) return;

    let scheduled = 0;

    while (recvQueueRef.current.length > 0 && scheduled < 10) {
      const pcm16 = recvQueueRef.current.shift();
      if (!pcm16 || pcm16.length === 0) {
        continue; // или return; но лучше continue
      }
      
      const f32 = int16ToFloat32(pcm16);

      const buffer = ctx.createBuffer(1, f32.length, ctx.sampleRate);
      buffer.copyToChannel(f32, 0);

      const src = ctx.createBufferSource();
      src.buffer = buffer;
      src.connect(ctx.destination);

      if (nextPlayTimeRef.current < ctx.currentTime + 0.01) {
        nextPlayTimeRef.current = ctx.currentTime + 0.01;
      }

      src.start(nextPlayTimeRef.current);
      nextPlayTimeRef.current += buffer.duration;
      scheduled++;
    }

    if (recvQueueRef.current.length === 0) {
      setTimeout(() => {
        if (recvQueueRef.current.length === 0) isPlayingRef.current = false;
        else scheduleLoop();
      }, 20);
      return;
    }

    setTimeout(scheduleLoop, 20);
  }

  function enqueue(pcm16) {
    recvQueueRef.current.push(pcm16);
    enhancedChunksRef.current.push(pcm16);

    if (!isPlayingRef.current && recvQueueRef.current.length >= PREBUFFER_FRAMES) {
      const ctx = ctxRef.current;
      if (!ctx) return;

      isPlayingRef.current = true;
      nextPlayTimeRef.current = ctx.currentTime + 0.05;
      scheduleLoop();
    }
  }

  async function start() {
    try {
      manualStopRef.current = false;

      console.log("HOOK start() ✅");
      setStatus("starting");
      resetBuffers();

      const ws = new WebSocket(WS_URL);
      ws.binaryType = "arraybuffer";
      wsRef.current = ws;

      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      const audioCtx = new AudioCtx({ sampleRate: SAMPLE_RATE });
      ctxRef.current = audioCtx;
      await audioCtx.resume();

      console.log("Request mic ✅");
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { channelCount: 1, echoCancellation: true },
      });
      console.log("Mic OK ✅");

      streamRef.current = stream;

      const source = audioCtx.createMediaStreamSource(stream);
      sourceRef.current = source;

      const processor = audioCtx.createScriptProcessor(1024, 1, 1);
      procRef.current = processor;

      processor.onaudioprocess = (e) => {
        const sock = wsRef.current;
        if (!sock || sock.readyState !== WebSocket.OPEN) return;

        const input = e.inputBuffer.getChannelData(0);
        const accum = accumRef.current;

        for (let i = 0; i < input.length; i++) accum.push(input[i]);

        while (accum.length >= FRAME_SAMPLES) {
          const frame = accum.splice(0, FRAME_SAMPLES);
          const pcm16 = floatToInt16(frame);
          sock.send(pcm16.buffer);
        }
      };

      ws.onopen = () => {
        console.log("WS OPEN ✅");
        ws.send(
          JSON.stringify({
            type: "start",
            sample_rate: 16000,
            frame_size_ms: 20,
            format: "pcm_s16le",
            channels: 1,
          })
        );
        setStatus("running");
      };

      ws.onmessage = (msg) => {
        // иногда прилетает пустой arraybuffer — пропускаем
        if (!msg.data || msg.data.byteLength === 0) return;
      
        const pcm16 = new Int16Array(msg.data);
        if (pcm16.length === 0) return;
      
        enqueue(pcm16);
      };
      

      ws.onerror = (e) => {
        console.log("WS ERROR", e);
        setStatus("ws error");
      };

      ws.onclose = (e) => {
        console.log("WS CLOSE", e.code, e.reason);
      
        // если закрыли сами — НЕ трогаем статус
        if (manualStopRef.current) return;
      
        setStatus("closed");
      };
      
      

      source.connect(processor);
      processor.connect(audioCtx.destination);
    } catch (e) {
      console.error("start() error:", e);
      setStatus("error");
    }
  }

  function stop() {
    console.log("STOP BTN ✅");
  
    manualStopRef.current = true;
  
    try { wsRef.current?.close(); } catch {}
    try { procRef.current?.disconnect(); } catch {}
    try { sourceRef.current?.disconnect(); } catch {}
    try { streamRef.current?.getTracks().forEach(t => t.stop()); } catch {}
    try { ctxRef.current?.close(); } catch {}
  
    wsRef.current = null;
    procRef.current = null;
    sourceRef.current = null;
    streamRef.current = null;
    ctxRef.current = null;
  
    isPlayingRef.current = false;
  
    // ВАЖНО — вручную возвращаем idle
    setStatus("idle");
  }
  
  

  function makePreview() {
    const all = concatInt16(enhancedChunksRef.current);
    if (all.length === 0) return;
    const wav = pcm16ToWavBlob(all, SAMPLE_RATE, 1);
    const url = URL.createObjectURL(wav);
    setPreviewUrl(url);
  }

  return { status, previewUrl, start, stop, makePreview };
}

