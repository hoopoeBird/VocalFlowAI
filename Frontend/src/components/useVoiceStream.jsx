"use client";
import { useState, useRef, useEffect } from "react";

const SERVER = (typeof window !== "undefined" && window.location && `${window.location.protocol}//${window.location.hostname}:8000`) || "http://localhost:8000";
const TARGET_SAMPLE_RATE = 16000;

function downsampleBuffer(buffer, sampleRate, outRate) {
  if (outRate === sampleRate) return buffer;
  const ratio = sampleRate / outRate;
  const newLength = Math.round(buffer.length / ratio);
  const result = new Float32Array(newLength);
  let offsetResult = 0;
  let offsetBuffer = 0;
  while (offsetResult < newLength) {
    const nextOffsetBuffer = Math.round((offsetResult + 1) * ratio);
    let accum = 0, count = 0;
    for (let i = Math.round(offsetBuffer); i < nextOffsetBuffer && i < buffer.length; i++) {
      accum += buffer[i];
      count++;
    }
    result[offsetResult] = count ? accum / count : 0;
    offsetResult++;
    offsetBuffer = nextOffsetBuffer;
  }
  return result;
}

function floatTo16BitPCM(float32Array) {
  const l = float32Array.length;
  const buf = new ArrayBuffer(l * 2);
  const view = new DataView(buf);
  for (let i = 0; i < l; i++) {
    let s = Math.max(-1, Math.min(1, float32Array[i]));
    view.setInt16(i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }
  return new Uint8Array(buf);
}

export function useVoiceStream() {
  const [status, setStatus] = useState("idle"); // idle, starting, running, stopping
  const [previewUrl, setPreviewUrl] = useState(null);
  const [audioInputs, setAudioInputs] = useState([]); // list of available microphones
  const [selectedDeviceId, setSelectedDeviceId] = useState(null);
  const [deviceMessage, setDeviceMessage] = useState(""); // helpful guidance for the user
  const audioCtxRef = useRef(null);
  const mediaStreamRef = useRef(null);
  const processorRef = useRef(null);
  const controllerRef = useRef(null);
  const fetchAbortRef = useRef(null);
  const fetchPromiseRef = useRef(null);

  async function refreshDevices() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) {
      console.warn("[useVoiceStream] enumerateDevices not available");
      setAudioInputs([]);
      setDeviceMessage("Device enumeration not available in this browser/context.");
      return;
    }
    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      const inputs = devices.filter((d) => d.kind === "audioinput");
      setAudioInputs(inputs);
      if (!selectedDeviceId && inputs.length > 0) {
        setSelectedDeviceId(inputs[0].deviceId);
      }
      // If devices exist but labels are empty, ask for permission to reveal labels
      if (inputs.length === 0) {
        setDeviceMessage("No microphone found. If you're in a container/VM, use your host browser and ensure a mic is connected.");
      } else if (inputs.every((d) => !d.label)) {
        setDeviceMessage("Microphones found but labels hidden. Click 'Test permission' to prompt for microphone access.");
      } else {
        setDeviceMessage("");
      }
      console.debug("[useVoiceStream] devices refreshed", inputs);
    } catch (e) {
      console.error("[useVoiceStream] refreshDevices error", e);
      setAudioInputs([]);
      setDeviceMessage("Error enumerating devices. See console for details.");
    }
  }

  async function testPermissions() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      const msg = "getUserMedia is not available in this browser / context. Use HTTPS or localhost.";
      console.error("[useVoiceStream] " + msg);
      setDeviceMessage(msg);
      return;
    }
    try {
      // prompt permission and immediately close the stream
      const s = await navigator.mediaDevices.getUserMedia({ audio: true });
      s.getTracks().forEach((t) => t.stop());
      setDeviceMessage("Permission granted. Refreshing device list...");
      await refreshDevices();
    } catch (e) {
      console.error("[useVoiceStream] testPermissions error", e);
      if (e && e.name === "NotAllowedError") {
        setDeviceMessage("Microphone access denied. Allow microphone permissions in your browser settings.");
      } else if (e && (e.name === "NotFoundError" || e.name === "DevicesNotFoundError")) {
        setDeviceMessage("Requested device not found. Connect a microphone and try again.");
      } else {
        setDeviceMessage("Permission request failed. See console for details.");
      }
    }
  }

  useEffect(() => {
    // initial device refresh + listen for device changes
    refreshDevices();
    const onChange = () => refreshDevices();
    if (navigator.mediaDevices && navigator.mediaDevices.addEventListener) {
      navigator.mediaDevices.addEventListener("devicechange", onChange);
      return () => navigator.mediaDevices.removeEventListener("devicechange", onChange);
    }
    return undefined;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function start() {
    console.debug("[useVoiceStream] start() called, status=", status);
    if (status !== "idle") {
      console.debug("[useVoiceStream] start aborted, not idle");
      return;
    }
    setStatus("starting");
    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        const msg = "getUserMedia is not available in this browser / context. Use HTTPS or localhost.";
        console.error("[useVoiceStream] " + msg);
        alert(msg);
        setStatus("idle");
        return;
      }

      // enumerate devices and check availability
      const devices = await navigator.mediaDevices.enumerateDevices();
      const inputs = devices.filter((d) => d.kind === "audioinput");
      setAudioInputs(inputs);
      if (inputs.length === 0) {
        const msg = "No microphone device found. Connect a microphone and retry.";
        console.error("[useVoiceStream] " + msg);
        alert(msg);
        setStatus("idle");
        return;
      }

      const deviceIdToUse = selectedDeviceId || (inputs[0] && inputs[0].deviceId);
      const constraints = deviceIdToUse ? { audio: { deviceId: { exact: deviceIdToUse } } } : { audio: true };

      let stream;
      try {
        stream = await navigator.mediaDevices.getUserMedia(constraints);
      } catch (e) {
        if (e && (e.name === "NotFoundError" || e.name === "DevicesNotFoundError")) {
          alert("Requested audio device not found. Connect a microphone or choose a different device.");
          setStatus("idle");
          return;
        }
        if (e && e.name === "NotAllowedError") {
          alert("Microphone access denied. Allow microphone permissions in your browser.");
          setStatus("idle");
          return;
        }
        throw e;
      }

      console.debug("[useVoiceStream] obtained media stream", stream);
      mediaStreamRef.current = stream;
      const ac = new (window.AudioContext || window.webkitAudioContext)();
      audioCtxRef.current = ac;
      const source = ac.createMediaStreamSource(stream);
      const processor = ac.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;

      // Setup ReadableStream and fetch
      const r = new ReadableStream({
        start(ctrl) {
          controllerRef.current = ctrl;
        },
        cancel(reason) {
          // stream cancelled by consumer
        },
      });

      const streamId = `browser-${Date.now()}`;
      const abort = new AbortController();
      fetchAbortRef.current = abort;

      // Start fetch (it will complete when stream is closed)
      const p = fetch(`${SERVER}/streams/${streamId}/confidence`, {
        method: "POST",
        headers: { "Content-Type": "application/octet-stream" },
        body: r,
        signal: abort.signal,
      })
        .then(async (res) => {
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          const data = await res.json();
          if (data && data.processed_audio_b64) {
            const bytes = Uint8Array.from(atob(data.processed_audio_b64), (c) => c.charCodeAt(0));
            const blob = new Blob([bytes], { type: "audio/wav" });
            const url = URL.createObjectURL(blob);
            setPreviewUrl(url);
          }
          return data;
        })
        .catch((err) => {
          console.error("stream fetch error", err);
        })
        .finally(() => {
          // ensure we set idle if not already
          setStatus((s) => (s === "stopping" ? "idle" : s));
        });

      fetchPromiseRef.current = p;

      processor.onaudioprocess = (evt) => {
        try {
          const input = evt.inputBuffer.getChannelData(0);
          const down = downsampleBuffer(input, ac.sampleRate, TARGET_SAMPLE_RATE);
          const pcmBytes = floatTo16BitPCM(down);
          // Enqueue chunk
          if (controllerRef.current && controllerRef.current.enqueue) {
            controllerRef.current.enqueue(pcmBytes);
          }
        } catch (e) {
          console.error("audio proc error", e);
        }
      };

      source.connect(processor);
      // Not connecting processor to destination to avoid feedback
      processor.connect(ac.destination);
      setStatus("running");
    } catch (e) {
      console.error("[useVoiceStream] start error", e);
      alert("Unable to access microphone. Check permissions and secure context (HTTPS or localhost). See console for details.");
      setStatus("idle");
    }
  }

  async function stop() {
    console.debug("[useVoiceStream] stop() called, status=", status);
    if (status !== "running") return;
    setStatus("stopping");
    try {
      // stop microphone
      const stream = mediaStreamRef.current;
      if (stream) {
        stream.getTracks().forEach((t) => t.stop());
        mediaStreamRef.current = null;
      }
      // disconnect nodes
      if (processorRef.current) {
        try {
          processorRef.current.disconnect();
        } catch {}
        processorRef.current = null;
      }
      if (audioCtxRef.current) {
        try {
          audioCtxRef.current.close();
        } catch {}
        audioCtxRef.current = null;
      }
      // close the ReadableStream to let server process and respond
      if (controllerRef.current && controllerRef.current.close) {
        controllerRef.current.close();
      }
      // wait for fetch to finish
      if (fetchPromiseRef.current) {
        await fetchPromiseRef.current;
      }
    } catch (e) {
      console.error("stop error", e);
    } finally {
      setStatus("idle");
      controllerRef.current = null;
      fetchAbortRef.current = null;
      fetchPromiseRef.current = null;
    }
  }

  async function makePreview(durationMs = 1000) {
    console.debug("[useVoiceStream] makePreview() called, status=", status);
    if (status !== "idle") return; // avoid clashing with running stream
    setStatus("starting");
    let localStream = null;
    let localAc = null;
    let localProcessor = null;
    try {
      localStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      localAc = new (window.AudioContext || window.webkitAudioContext)();
      const source = localAc.createMediaStreamSource(localStream);
      localProcessor = localAc.createScriptProcessor(4096, 1, 1);
      const chunks = [];

      localProcessor.onaudioprocess = (evt) => {
        const input = evt.inputBuffer.getChannelData(0);
        const down = downsampleBuffer(input, localAc.sampleRate, TARGET_SAMPLE_RATE);
        const pcm = floatTo16BitPCM(down);
        chunks.push(pcm);
      };

      source.connect(localProcessor);
      localProcessor.connect(localAc.destination);

      await new Promise((resolve) => setTimeout(resolve, durationMs));

      // stop and cleanup
      localProcessor.disconnect();
      source.disconnect();
      localStream.getTracks().forEach((t) => t.stop());
      await localAc.close();

      // assemble bytes
      const totalLen = chunks.reduce((s, c) => s + c.byteLength, 0);
      const buf = new Uint8Array(totalLen);
      let o = 0;
      for (const c of chunks) {
        buf.set(c, o);
        o += c.byteLength;
      }

      // send single POST
      const streamId = `browser-preview-${Date.now()}`;
      const resp = await fetch(`${SERVER}/streams/${streamId}/confidence`, {
        method: "POST",
        headers: { "Content-Type": "application/octet-stream" },
        body: buf,
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      if (data && data.processed_audio_b64) {
        const bytes = Uint8Array.from(atob(data.processed_audio_b64), (c) => c.charCodeAt(0));
        const blob = new Blob([bytes], { type: "audio/wav" });
        const url = URL.createObjectURL(blob);
        setPreviewUrl(url);
      }
    } catch (e) {
      console.error("makePreview error", e);
    } finally {
      setStatus("idle");
      if (localProcessor) localProcessor = null;
      if (localAc) localAc = null;
      if (localStream) localStream = null;
    }
  }

  return {
    status,
    previewUrl,
    start,
    stop,
    makePreview,
    audioInputs,
    selectedDeviceId,
    selectDevice: (id) => setSelectedDeviceId(id),
    refreshDevices,
    testPermissions,
    deviceMessage,
  };
}

export default useVoiceStream;
