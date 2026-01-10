// Fro  tend/src/components/useVoiceStream.js

import { useRef, useState, useEffect, useCallback } from "react";

// const WS_URL = "ws://localhost:8000/ws/audio";

const WS_URL = "wss://vocalflowai-production.up.railway.app/ws/audio";
const SAMPLE_RATE = 16000;
const FRAME_SAMPLES = 320; // 20ms при 16kHz

export function useVoiceStream() {
  const [status, setStatus] = useState("idle"); // idle, recording
  const [previewUrl, setPreviewUrl] = useState(null);

  const wsRef = useRef(null);
  const audioCtxRef = useRef(null);
  const sourceRef = useRef(null);
  const processorRef = useRef(null);
  const streamRef = useRef(null);

  const accumulatedInput = useRef([]); // для отправки на сервер
  const enhancedChunks = useRef([]); // собираем улучшенный звук от сервера

  // NEW: device state & UI helpers
  const [audioInputs, setAudioInputs] = useState([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState(null);
  const [deviceMessage, setDeviceMessage] = useState("");
  const [isRefreshing, setIsRefreshing] = useState(false);

  const refreshDevices = useCallback(async () => {
    console.debug("[useVoiceStream] refreshDevices");
    setIsRefreshing(true);
    setDeviceMessage("Refreshing devices...");
    if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) {
      setAudioInputs([]);
      setDeviceMessage("Device enumeration not available in this browser/context.");
      setIsRefreshing(false);
      return;
    }
    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      const inputs = devices.filter((d) => d.kind === "audioinput");
      setAudioInputs(inputs);
      if (!selectedDeviceId && inputs.length > 0) setSelectedDeviceId(inputs[0].deviceId);
      if (inputs.length === 0) {
        setDeviceMessage("No microphone found. Use your host browser and ensure a mic is connected.");
      } else if (inputs.every((d) => !d.label)) {
        setDeviceMessage("Microphones found but labels hidden. Click 'Test permission' to prompt for microphone access.");
      } else {
        setDeviceMessage("");
      }
      console.debug("[useVoiceStream] devices:", inputs);
    } catch (e) {
      console.error("[useVoiceStream] refreshDevices error", e);
      setAudioInputs([]);
      setDeviceMessage("Error enumerating devices. See console for details.");
    } finally {
      setIsRefreshing(false);
    }
  }, [selectedDeviceId]);

  const testPermissions = useCallback(async () => {
    console.debug("[useVoiceStream] testPermissions");
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      const msg = "getUserMedia not available. Use HTTPS or localhost.";
      setDeviceMessage(msg);
      return;
    }
    setIsRefreshing(true);
    setDeviceMessage("Requesting microphone permission...");
    try {
      const s = await navigator.mediaDevices.getUserMedia({ audio: true });
      s.getTracks().forEach((t) => t.stop());
      setDeviceMessage("Permission granted. Refreshing device list...");
      await refreshDevices();
    } catch (e) {
      console.error("[useVoiceStream] testPermissions error", e);
      if (e && e.name === "NotAllowedError") {
        setDeviceMessage("Microphone access denied. Allow microphone permissions in browser settings.");
      } else if (e && (e.name === "NotFoundError" || e.name === "DevicesNotFoundError")) {
        setDeviceMessage("Requested device not found. Connect a microphone and try again.");
      } else {
        setDeviceMessage("Permission request failed. See console for details.");
      }
    } finally {
      setIsRefreshing(false);
    }
  }, [refreshDevices]);

  useEffect(() => {
    // auto-refresh and listen for device changes
    refreshDevices();
    const onChange = () => {
      console.debug("[useVoiceStream] devicechange detected");
      refreshDevices();
    };
    if (navigator.mediaDevices && navigator.mediaDevices.addEventListener) {
      navigator.mediaDevices.addEventListener("devicechange", onChange);
      return () => navigator.mediaDevices.removeEventListener("devicechange", onChange);
    }
    if (navigator.mediaDevices) {
      navigator.mediaDevices.ondevicechange = onChange;
      return () => {
        try { navigator.mediaDevices.ondevicechange = null; } catch {}
      };
    }
    return undefined;
  }, [refreshDevices]);

  // Adjusted start() to use selectedDeviceId and better errors
  const start = async () => {
    try { 
      setStatus("recording");
      setPreviewUrl(null);
      accumulatedInput.current = [];
      enhancedChunks.current = [];

      // Check devices and constraints
      const devices = await navigator.mediaDevices.enumerateDevices();
      const inputs = devices.filter((d) => d.kind === "audioinput");
      setAudioInputs(inputs);
      if (inputs.length === 0) {
        setDeviceMessage("No microphone device found. Connect a microphone and retry.");
        setStatus("idle");
        return;
      }

      const deviceIdToUse = selectedDeviceId || (inputs[0] && inputs[0].deviceId);
      const constraints = deviceIdToUse ? { audio: { deviceId: { exact: deviceIdToUse } } } : { audio: true };

      let stream;
      try {
        stream = await navigator.mediaDevices.getUserMedia(constraints);
      } catch (e) {
        console.error("[useVoiceStream] getUserMedia error", e);
        if (e && (e.name === "NotFoundError" || e.name === "DevicesNotFoundError")) {
          setDeviceMessage("Requested audio device not found. Connect a microphone or choose a different device.");
          setStatus("idle");
          return;
        }
        if (e && e.name === "NotAllowedError") {
          setDeviceMessage("Microphone access denied. Allow microphone permissions in your browser.");
          setStatus("idle");
          return;
        }
        throw e;
      }

      streamRef.current = stream;

      const audioCtx = new AudioContext({ sampleRate: SAMPLE_RATE });
      audioCtxRef.current = audioCtx;

      const source = audioCtx.createMediaStreamSource(stream);
      sourceRef.current = source;

      const processor = audioCtx.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;

      // Глушим сырой звук полностью
      const gain = audioCtx.createGain();
      gain.gain.value = 0;
      processor.connect(gain);
      gain.connect(audioCtx.destination);

      processor.onaudioprocess = (e) => {
        const input = e.inputBuffer.getChannelData(0);
        const ws = wsRef.current;

        // Накапливаем для отправки по 320 сэмплов
        for (let i = 0; i < input.length; i++) {
          accumulatedInput.current.push(input[i]);
        }

        while (accumulatedInput.current.length >= FRAME_SAMPLES) {
          const frame = accumulatedInput.current.splice(0, FRAME_SAMPLES);
          const int16 = new Int16Array(frame.map(sample => {
            const s = Math.max(-1, Math.min(1, sample));
            return s < 0 ? s * 0x8000 : s * 0x7FFF;
          }));
          if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(int16.buffer);
          }
        }
      };

      source.connect(processor);

      // WebSocket
      const ws = new WebSocket(WS_URL);
      ws.binaryType = "arraybuffer";

      ws.onopen = () => console.log("WS connected");
      ws.onmessage = (msg) => {
        if (msg.data instanceof ArrayBuffer && msg.data.byteLength > 0) {
          enhancedChunks.current.push(new Int16Array(msg.data));
        }
      };
      ws.onclose = () => console.log("WS closed");
      ws.onerror = (e) => console.error("WS error", e);

      wsRef.current = ws;
    } catch (err) {
      console.error(err);
      setStatus("idle");
    }
  };

  const stop = () => {
    // Очистка
    if (wsRef.current) wsRef.current.close();
    if (processorRef.current) processorRef.current.disconnect();
    if (sourceRef.current) sourceRef.current.disconnect();
    if (streamRef.current) streamRef.current.getTracks().forEach(t => t.stop());
    if (audioCtxRef.current) audioCtxRef.current.close();

    wsRef.current = null;
    processorRef.current = null;
    sourceRef.current = null;
    streamRef.current = null;
    audioCtxRef.current = null;

    setStatus("idle");

    // Автоматически создаём preview
    makePreview();
  };

  const makePreview = () => {
    if (enhancedChunks.current.length === 0) {
      setPreviewUrl(null);
      return;
    }

    const totalSamples = enhancedChunks.current.reduce((sum, chunk) => sum + chunk.length, 0);
    const combined = new Int16Array(totalSamples);
    let offset = 0;
    for (const chunk of enhancedChunks.current) {
      combined.set(chunk, offset);
      offset += chunk.length;
    }

    // Простой WAV
    const buffer = new ArrayBuffer(44 + combined.length * 2);
    const view = new DataView(buffer);
    const writeString = (offset, str) => {
      for (let i = 0; i < str.length; i++) view.setUint8(offset + i, str.charCodeAt(i));
    };

    writeString(0, "RIFF");
    view.setUint32(4, 36 + combined.length * 2, true);
    writeString(8, "WAVE");
    writeString(12, "fmt ");
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, 1, true);
    view.setUint32(24, SAMPLE_RATE, true);
    view.setUint32(28, SAMPLE_RATE * 2, true);
    view.setUint16(32, 2, true);
    view.setUint16(34, 16, true);
    writeString(36, "data");
    view.setUint32(40, combined.length * 2, true);

    const pcmOffset = 44;
    for (let i = 0; i < combined.length; i++) {
      view.setInt16(pcmOffset + i * 2, combined[i], true);
    }

    const blob = new Blob([buffer], { type: "audio/wav" });
    setPreviewUrl(URL.createObjectURL(blob));
  };

  return {
    status,
    previewUrl,
    start,
    stop,
    makePreview,
    // NEW exports for device UI
    audioInputs,
    selectedDeviceId,
    selectDevice: (id) => setSelectedDeviceId(id),
    refreshDevices,
    testPermissions,
    deviceMessage,
    isRefreshing,
  };
}
