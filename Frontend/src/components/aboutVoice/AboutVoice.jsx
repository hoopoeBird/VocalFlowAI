import React from 'react'
import { Link } from 'react-router-dom'

export default function AboutVoice({ data }) {
  return (
      <div className="w-full h-screen flex items-center justify-center bg-gradient-to-br from-[#4b6cb7] to-[#1f345e] overflow-hidden">
        <div className="text-white backdrop-blur-xl bg-gradient-to-br bg-transparent hover:shadow-[0_0_25px_5px_rgba(255,255,255,0.4),0_0_40px_10px_rgba(0,255,255,0.3),0_0_80px_20px_rgba(0,160,255,0.35)] cursor-pointer from-[#a8c0ff] to-[#3f2b96] lg:w-[1440px] w-full  aspect-square lg:h-[1000px] flex flex-col items-center rounded-3xl shadow-2xl lg:gap-y-16 gap-y-8 py-12 lg:py-0 border-2 border-transparent">
            <div className='w-full flex justify-start'>
              <Link to={"/"} className='pl-10 lg:py-8 py-0 lg:text-3xl text-xl font-head font-serif cursor-pointer underline-offset-8 underline tracking-widest'>Home</Link>
            </div>         
            <h1 className=' lg:text-6xl text-4xl font-serif tracking-widest'>{data.title}</h1>
            <p className=' font-serif w-[230px] text-center lg:text-xl text-base tracking-wider leading-7'>{data.subtitle}</p>
            <div className='grid grid-cols-2 justify-items-center gap-14 mx-auto'>
              <div className='flex flex-col items-center gap-y-6'>
                <img className='w-44 h-20' src='leftgroup.png'></img>
                <p className='text-2xl  font-serif tracking-widest'>Before</p>
              </div>  
              <div className='flex flex-col items-center gap-y-6'>
                <img className='w-44 h-20' src='rightgroup.png'></img>
                <p className='text-2xl  font-serif tracking-widest'>After</p> 
              </div>
            </div>
           <div className="lg:w-[360px] w-[300px] lg:h-20 h-16 rounded-full flex items-center overflow-hidden text-black shadow-lg shadow-black mt-4">
            <button className="cursor-pointer  flex-1 h-full text-2xl font-serif bg-gray-300">
              Before
            </button>
            <p className='border-2 border-black h-20 rotate-0 '></p>
            <button className="cursor-pointer flex-1 h-full text-2xl font-serif bg-gray-200">
              After
            </button>
          </div>
        </div>
    </div>
  )
}
