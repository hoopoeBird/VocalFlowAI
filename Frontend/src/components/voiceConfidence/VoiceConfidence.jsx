import React from 'react'
import { Link } from 'react-router-dom'

export default function VoiceConfidence({ data }) {
  return (
    <div className="w-full lg:h-screen h-full flex items-center justify-center bg-gradient-to-br from-[#4b6cb7] to-[#1f345e] overflow-hidden">
        <div className="text-white backdrop-blur-xl bg-gradient-to-br bg-transparent hover:shadow-[0_0_25px_5px_rgba(255,255,255,0.4),0_0_40px_10px_rgba(0,255,255,0.3),0_0_80px_20px_rgba(0,160,255,0.35)] cursor-pointer from-[#a8c0ff] to-[#3f2b96] lg:w-[1440px] w-full  aspect-square lg:h-[1000px] flex flex-col items-center rounded-3xl shadow-2xl lg:gap-y-8 gap-y-8 py-8 lg:py-0 border-2 border-transparent">
            <div className='w-full flex justify-start'>
              <Link to={"/"} className='pl-10 lg:py-8 py-0 lg:text-3xl text-xl font-serif cursor-pointer underline-offset-8 underline tracking-widest'>Home</Link>
            </div> 
            <h1 className='lg:text-6xl text-5xl font-serif tracking-widest'>{data.name}</h1>
            <p className=' font-serif text-center lg:text-xl text-base tracking-wider'>{data.subtitle}</p>
            <p className='lg:text-9xl text-7xl mt-4 font-serif'>80%</p>
            <p className='w-60 text-center leading-8 text-xl tracking-wider  font-serif'>{data.info}</p>
            <div className='flex flex-col gap-y-10 mt-10'>    
              <button className="cursor-pointer lg:w-80 w-64 h-16 lg:h-20 rounded-full border-2 border-transparent bg-gradient-to-tl from-[#6ccef5] to-[#0e7bc3] text-white text-2xl font-serif tracking-wider hover:scale-105 transition-all"> {data.try} </button>
              <button className='cursor-pointer lg:w-80 w-64 h-16 lg:h-20 bg-gradient-to-tl from-[#016FB9] to-[#84d4e8] border-2 border-transparent rounded-full text-white text-2xl font-serif tracking-wider hover:scale-105 transition-all'>{data.share}</button>
            </div>
        </div>
    </div>
  )
}