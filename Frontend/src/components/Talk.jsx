import { useRef, useState } from "react";

const WS_URL = "ws://localhost:8000/ws/audio";
const SAMPLE_RATE = 16000;
const FRAME_SAMPLES = 320; // 20ms @ 16kHz
const FRAME_MS = 20;
const PREBUFFER_FRAMES = 6; // 6*20ms = 120ms (можешь 4-8)
export default function Talk() {
    const recvQueueRef = useRef([]); // ✅ внутри компонента
    const [x, setX] = useState(0);   // ✅ внутри компонента
  
    return <div>...</div>;
  }

console.log("TalkPage render ✅");
const [previewUrl, setPreviewUrl] = useState("");


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

export default function TalkPage() {
  const [status, setStatus] = useState("idle");

  const wsRef = useRef(null);
  const ctxRef = useRef(null);
  const streamRef = useRef(null);
  const sourceRef = useRef(null);
  const procRef = useRef(null);

  const accumRef = useRef([]);         // float accumulator
  const playQueueRef = useRef([]);     // received chunks
  const playingRef = useRef(false);

  const sentFramesRef = useRef(0);
  const recvFramesRef = useRef(0);

  async function start() {
    console.log("START CLICK ✅");

    setStatus("starting...");

    // 1) WS
    const ws = new WebSocket(WS_URL);
    ws.binaryType = "arraybuffer";
    wsRef.current = ws;

    // 2) AudioContext (ВАЖНО: по клику!)
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    const audioCtx = new AudioCtx({ sampleRate: SAMPLE_RATE });
    ctxRef.current = audioCtx;

    // Авто-политика: нужно явно resume() по user gesture
    await audioCtx.resume();

    // 3) Mic
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: { channelCount: 1, echoCancellation: true }
    });
    streamRef.current = stream;

    const source = audioCtx.createMediaStreamSource(stream);
    sourceRef.current = source;

    // 4) Processor (MVP)
    const processor = audioCtx.createScriptProcessor(1024, 1, 1);
    procRef.current = processor;

    processor.onaudioprocess = (e) => {
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

      const input = e.inputBuffer.getChannelData(0); // Float32Array
      const accum = accumRef.current;

      // копим
      for (let i = 0; i < input.length; i++) accum.push(input[i]);

      // режем ровно по 320
      while (accum.length >= FRAME_SAMPLES) {
        const frame = accum.splice(0, FRAME_SAMPLES);
        const pcm16 = floatToInt16(frame);
        wsRef.current.send(pcm16.buffer);
        sentFramesRef.current += 1;

        if (sentFramesRef.current % 50 === 0) {
          console.log("sent frames:", sentFramesRef.current);
        }
      }
    };

    // 5) Receive + play
    ws.onopen = () => {
      console.log("WS OPEN");
      setStatus("connected");
    };
    
    ws.onmessage = (msg) => {
      const pcm16 = new Int16Array(msg.data);
      enqueueEnhancedChunk(pcm16);

      recvFramesRef.current += 1;

      if (recvFramesRef.current % 50 === 0) {
        console.log("recv frames:", recvFramesRef.current, "bytes:", msg.data.byteLength);
      }

      playQueueRef.current.push(pcm16);
      if (!playingRef.current) pumpPlayback();
    };

    ws.onerror = (e) => {
      console.log("WS ERROR", e);
      setStatus("ws error");
    };

    ws.onclose = () => {
      console.log("WS CLOSE");
      setStatus("closed");
    };

    source.connect(processor);
    // важно: processor должен быть подключён в граф, иначе onAudioProcess может не тикать
    processor.connect(audioCtx.destination);

    setStatus("running");
  }

  function enqueueEnhancedChunk(pcm16) {
    recvQueueRef.current.push(pcm16);
  
    // сохраняем для Preview (улучшенный звук)
    enhancedChunksRef.current.push(pcm16);
  
    if (!isPlayingRef.current && recvQueueRef.current.length >= PREBUFFER_FRAMES) {
      isPlayingRef.current = true;
  
      const ctx = ctxRef.current;
      // стартуем чуть впереди текущего времени, чтобы точно успеть поставить ноды
      nextPlayTimeRef.current = ctx.currentTime + 0.05;
  
      scheduleLoop();
    }
  }
  
  function scheduleLoop() {
    const ctx = ctxRef.current;
    if (!ctx) return;
  
    // планируем несколько фреймов вперед за один тик (чтобы не отставать)
    let scheduled = 0;
    while (recvQueueRef.current.length > 0 && scheduled < 8) {
      const pcm16 = recvQueueRef.current.shift();
      const f32 = int16ToFloat32(pcm16);
  
      const buffer = ctx.createBuffer(1, f32.length, ctx.sampleRate);
      buffer.copyToChannel(f32, 0);
  
      const src = ctx.createBufferSource();
      src.buffer = buffer;
      src.connect(ctx.destination);
  
      // если вдруг отстали — подтягиваемся
      if (nextPlayTimeRef.current < ctx.currentTime + 0.01) {
        nextPlayTimeRef.current = ctx.currentTime + 0.01;
      }
  
      src.start(nextPlayTimeRef.current);
  
      // следующий старт через длительность фрейма
      nextPlayTimeRef.current += buffer.duration;
      scheduled++;
    }
  
    // если очередь пустая — ждём, но не стопаем мгновенно (пускай догрузит)
    if (recvQueueRef.current.length === 0) {
      // если тишина долго — можно остановить, но для MVP оставим простое ожидание
      setTimeout(() => {
        if (recvQueueRef.current.length === 0) {
          isPlayingRef.current = false;
        } else {
          scheduleLoop();
        }
      }, 20);
      return;
    }
  
    // крутим scheduler каждые ~20ms
    setTimeout(scheduleLoop, 20);
  }
  
  function stop() {
    setStatus("stopping...");
    wsRef.current?.close();

    procRef.current?.disconnect();
    sourceRef.current?.disconnect();

    streamRef.current?.getTracks().forEach((t) => t.stop());
    ctxRef.current?.close();

    accumRef.current = [];
    playQueueRef.current = [];
    sentFramesRef.current = 0;
    recvFramesRef.current = 0;
    playingRef.current = false;

    setStatus("idle");
    function makePreview() {
        const all = concatInt16(enhancedChunksRef.current);
        const wav = pcm16ToWavBlob(all, SAMPLE_RATE, 1);
        const url = URL.createObjectURL(wav);
        setPreviewUrl(url);
      }
      
  }

  ws.onclose = (e) => {
    console.log("WS CLOSE code=", e.code, "reason=", e.reason);
  };
  ws.onerror = (e) => console.log("WS ERROR", e);
  
    
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
    view.setUint32(16, 16, true);          // PCM
    view.setUint16(20, 1, true);           // format = 1 PCM
    view.setUint16(22, numChannels, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, byteRate, true);
    view.setUint16(32, blockAlign, true);
    view.setUint16(34, 16, true);          // bits
  
    writeStr(36, "data");
    view.setUint32(40, dataSize, true);
  
    // PCM data
    let offset = 44;
    for (let i = 0; i < pcm16.length; i++, offset += 2) {
      view.setInt16(offset, pcm16[i], true);
    }
  
    return new Blob([view], { type: "audio/wav" });
  }
  
  return (
    <div style={{ padding: 24 }}>
      <button onClick={status === "idle" ? start : stop}>
        {status === "idle" ? "Talk" : "Stop"}
      </button>

      <div style={{ marginTop: 12, opacity: 0.8 }}>
        status: {status}
      </div>
      <div style={{ marginTop: 6, opacity: 0.6 }}>
        sent: {sentFramesRef.current} frames | recv: {recvFramesRef.current} frames
      </div>
    </div>
  );
}
