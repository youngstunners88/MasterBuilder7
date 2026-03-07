import { useState, useEffect } from 'react'

export default function SplashScreen() {
  const [fade, setFade] = useState(false)
  const [loadingProgress, setLoadingProgress] = useState(0)

  useEffect(() => {
    // Simulate loading progress
    const progressInterval = setInterval(() => {
      setLoadingProgress(prev => {
        if (prev >= 100) {
          clearInterval(progressInterval)
          return 100
        }
        return prev + Math.random() * 15
      })
    }, 200)

    const fadeTimer = setTimeout(() => setFade(true), 2000)
    
    return () => {
      clearTimeout(fadeTimer)
      clearInterval(progressInterval)
    }
  }, [])

  return (
    <div 
      className={`fixed inset-0 bg-primary flex flex-col items-center justify-center z-50 transition-opacity duration-700 ${fade ? 'opacity-0 pointer-events-none' : 'opacity-100'}`}
    >
      {/* Logo Container with pulse animation */}
      <div className="flex flex-col items-center animate-pulse">
        {/* Black Horse Logo SVG */}
        <svg 
          width="120" 
          height="140" 
          viewBox="0 0 100 120" 
          fill="none" 
          xmlns="http://www.w3.org/2000/svg"
          className="mb-4"
        >
          {/* Horse body - rearing pose */}
          <path 
            d="M25 100C25 100 20 80 25 70C30 60 35 55 40 50C45 45 50 40 52 35C54 30 55 25 58 20C61 15 65 8 70 5C75 2 78 5 80 10C82 15 80 20 78 25C76 30 72 35 70 40C68 45 66 50 65 55C64 60 65 65 67 70C69 75 72 80 72 85C72 90 70 95 68 100C66 105 62 110 58 112C54 114 50 112 46 108C42 104 38 106 35 108C32 110 28 104 25 100Z" 
            fill="#1A1A1A"
          />
          {/* Mane */}
          <path 
            d="M52 35C52 35 48 25 50 18C52 12 58 15 60 22" 
            fill="#1A1A1A"
          />
          {/* Tail */}
          <path 
            d="M25 70C25 70 18 75 15 85C12 95 18 100 22 95" 
            fill="#1A1A1A"
          />
          {/* Eye */}
          <circle cx="72" cy="18" r="3" fill="white"/>
          {/* Big Smile/Teeth */}
          <path 
            d="M76 28C76 28 74 32 70 32C66 32 66 28 68 26" 
            stroke="white" 
            strokeWidth="2" 
            strokeLinecap="round" 
            fill="none"
          />
          {/* Teeth lines */}
          <line x1="70" y1="28" x2="70" y2="31" stroke="white" strokeWidth="1"/>
          <line x1="72" y1="28.5" x2="72" y2="31.5" stroke="white" strokeWidth="1"/>
          <line x1="68" y1="28" x2="68" y2="31" stroke="white" strokeWidth="1"/>
          {/* Hooves */}
          <ellipse cx="35" cy="108" rx="4" ry="3" fill="#1A1A1A"/>
          <ellipse cx="58" cy="112" rx="4" ry="3" fill="#1A1A1A"/>
        </svg>

        {/* iHhashi Text */}
        <h1 className="text-5xl font-black text-secondary tracking-tight">
          iHhashi
        </h1>
        
        {/* Tagline */}
        <p className="mt-2 text-secondary/70 text-sm font-medium tracking-wide uppercase">
          Delivering South Africa
        </p>
      </div>
      
      {/* Progress Bar */}
      <div className="mt-12 w-48">
        <div className="h-1 bg-secondary/20 rounded-full overflow-hidden">
          <div 
            className="h-full bg-secondary rounded-full transition-all duration-300 ease-out"
            style={{ width: `${Math.min(loadingProgress, 100)}%` }}
          />
        </div>
        <p className="text-center mt-2 text-secondary/50 text-xs">
          Loading...
        </p>
      </div>

      {/* Bouncing dots alternative */}
      <div className="mt-8 flex gap-2">
        <div className="w-2.5 h-2.5 bg-secondary rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
        <div className="w-2.5 h-2.5 bg-secondary rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
        <div className="w-2.5 h-2.5 bg-secondary rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
      </div>
    </div>
  )
}
