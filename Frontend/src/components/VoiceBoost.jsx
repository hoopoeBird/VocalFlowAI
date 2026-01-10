"use client";
import React from "react";
import { Link } from "react-router-dom";
import { useVoiceStream } from "./useVoiceStream";

export default function VoiceBoost({ data }) {
  const { status, previewUrl, start, stop, makePreview } = useVoiceStream();
  const isIdle = status === "idle";

  return (
    <div className="w-full lg:h-screen h-full flex items-center justify-center bg-gradient-to-br from-[#4b6cb7] to-[#1f345e] overflow-hidden">
      <div className="text-white backdrop-blur-xl bg-gradient-to-br bg-transparent hover:shadow-[0_0_25px_5px_rgba(255,255,255,0.4),0_0_40px_10px_rgba(0,255,255,0.3),0_0_80px_20px_rgba(0,160,255,0.35)] cursor-pointer from-[#a8c0ff] to-[#3f2b96] lg:w-[1440px] w-full  aspect-square lg:h-[1259px] flex flex-col items-center rounded-3xl shadow-2xl lg:gap-y-10 gap-y-8 py-8 lg:py-0 border-2 border-transparent">
        <div className="w-full flex justify-start">
          <Link
            to={"/aboutVoice"}
            className="pl-10 py-8 text-xl lg:text-2xl cursor-pointer underline-offset-8 underline tracking-wide"
          >
            AboutVoice
          </Link>
          <Link
            to={"/voiceConfidence"}
            className="pl-10 py-8 text-xl lg:text-2xl cursor-pointer underline-offset-8 underline tracking-wide"
          >
            VoiceConfidence
          </Link>
        </div>

        <h1 className=" text-5xl font-serif tracking-widest">{data.name}</h1>
        <p className="font-serif w-[230px] text-center text-base tracking-wider leading-7">
          {data.subtitle}
        </p>

        <div
          style={{ backgroundImage: data.circle }}
          className="pb-9 relative grid grid-cols-1 lg:w-[405px] w-auto aspect-square lg:h-[405px] bg-no-repeat bg-cover bg-center items-center justify-between"
        >
          <div className="flex flex-col items-center justify-center">
            <img
              className="pointer-events-none transition-transform translate-y-8"
              src="circleone.png"
              alt=""
            />
            <img className="pointer-events-none" src="Vector.png" alt="" />
          </div>

          <img
            className="pointer-events-none absolute right-1/2 transition-transform -translate-x-5/12"
            src="leftgroup.png"
            alt=""
          />
          <img
            className="pointer-events-none absolute left-1/2 transition-transform translate-x-5/12"
            src="rightgroup.png"
            alt=""
          />
        </div>

        {/* START / STOP */}
        <button
          type="button"
          onClick={() => {
            if (status === "idle") {
              start();
            } else {
              stop();
            }
          }}
          disabled={status === "starting" || status === "stopping"}
          className="relative z-50 cursor-pointer w-64 h-16 lg:w-80 lg:h-20 rounded-[67px] font-serif text-3xl tracking-wider font-medium text-white bg-gradient-to-r from-[#4facfe] to-[#00f2fe] shadow-xl shadow-blue-500/50 hover:scale-105 transition disabled:opacity-60 disabled:hover:scale-100"
        >
          {status === "idle" ? data.buttonName : "Stop"}
        </button>

        {/* <div className="flex flex-col gap-y-7">
          <p className="font-serif text-2xl font-thin tracking-wider text-center">
            {status === "running" ? data.listen : ""}
          </p>
          <p
            className="lg:w-[390px] w-80 mx-auto h-8 rounded-[67px]"
            style={{
              background:
                "linear-gradient(90deg, #FF0E23 0%, #EF5B12 33.17%, #E78109 54.5%, #FFB123 65.16%, #35B100 75.82%)",
            }}
          />
          <p className="lg:pl-80 pl-60 text-3xl">80%</p>
        </div> */}

        {/* PREVIEW */}
        <button
          type="button"
          onClick={makePreview}
          disabled={status === "running" || status === "starting"}

          className="relative z-50 font-serif font-medium text-2xl tracking-wider w-48 h-16 bg-gradient-to-r from-white/20 to-white/55 rounded-[67px] cursor-pointer shadow-lg shadow-black disabled:opacity-50"
          title={!isIdle ? "Stop first to preview" : ""}
        >
          {data.priview}
        </button>

        {previewUrl && (
          <div className="w-full flex flex-col items-center gap-y-3">
            <audio controls src={previewUrl} className="w-80 lg:w-[520px]" />
            <a
              href={previewUrl}
              download="enhanced.wav"
              className="underline underline-offset-4 text-white/90"
            >
              Download enhanced.wav
            </a>
          </div>
        )}
      </div>
    </div>
  );
}
