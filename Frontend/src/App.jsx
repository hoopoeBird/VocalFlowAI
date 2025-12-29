import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
// import TalkPage from "./components/Talk";
import { voiceBoost } from "../data/voiceBoost";
import { aboutVoice } from "../data/aboutVoice";
import { voiceConfidence } from "../data/voiceConfidence";
import VoiceBoost from "./components/VoiceBoost";
import AboutVoice from "./components/aboutVoice/AboutVoice";
import VoiceConfidence from "./components/voiceConfidence/VoiceConfidence";

export default function App() {
  return (
    <Router>
      <Routes>
      {/* <Route path="/talk" element={<TalkPage />} /> */}
        <Route path="/" element={<VoiceBoost data={voiceBoost} />} />
        <Route path="/aboutVoice" element={<AboutVoice data={aboutVoice}/>} />
        <Route path="/voiceConfidence" element={<VoiceConfidence data={voiceConfidence}/>} />
      </Routes>
    </Router>
  );
}
