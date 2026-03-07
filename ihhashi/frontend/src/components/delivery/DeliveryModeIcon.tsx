type DeliveryMode = 'walking' | 'skateboard' | 'bicycle' | 'motorbike'

interface DeliveryModeIconProps {
  mode: DeliveryMode
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

export default function DeliveryModeIcon({ mode, size = 'md', className = '' }: DeliveryModeIconProps) {
  const sizeClasses = {
    sm: 'w-8 h-8',
    md: 'w-12 h-12',
    lg: 'w-16 h-16'
  }

  const icons = {
    walking: (
      <svg viewBox="0 0 200 200" fill="none" xmlns="http://www.w3.org/2000/svg">
        {/* Walking horse delivery icon - black silhouette on yellow */}
        <rect width="200" height="200" fill="#FFD700" rx="20"/>
        {/* Horse body walking */}
        <path 
          d="M60 140C60 140 55 120 60 110C65 100 70 95 75 90C80 85 85 80 90 75C95 70 100 65 105 65C110 65 115 70 115 75C115 80 110 85 105 90C100 95 95 100 93 105C91 110 93 115 95 120C97 125 100 130 100 135C100 140 95 145 90 145C85 145 80 140 75 135C70 130 65 135 60 140Z" 
          fill="#1A1A1A"
        />
        {/* Delivery backpack */}
        <rect x="55" y="95" width="25" height="30" rx="5" fill="#1A1A1A"/>
        <text x="67" y="115" fontSize="10" fill="#FFD700" textAnchor="middle" fontWeight="bold">H</text>
        {/* Legs walking */}
        <path d="M75 130L70 160" stroke="#1A1A1A" strokeWidth="6" strokeLinecap="round"/>
        <path d="M95 130L100 160" stroke="#1A1A1A" strokeWidth="6" strokeLinecap="round"/>
        {/* Eye */}
        <circle cx="108" cy="78" r="3" fill="white"/>
        {/* Smile */}
        <path d="M112 85C112 85 110 88 108 88C106 88 106 85 108 83" stroke="white" strokeWidth="1.5" fill="none"/>
      </svg>
    ),
    skateboard: (
      <svg viewBox="0 0 200 200" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect width="200" height="200" fill="#FFD700" rx="20"/>
        {/* Horse on skateboard */}
        <path 
          d="M60 120C60 120 55 100 60 90C65 80 70 75 75 70C80 65 85 60 90 55C95 50 100 45 105 45C110 45 115 50 115 55C115 60 110 65 105 70C100 75 95 80 93 85C91 90 93 95 95 100" 
          fill="#1A1A1A"
        />
        {/* Delivery backpack */}
        <rect x="55" y="75" width="25" height="30" rx="5" fill="#1A1A1A"/>
        <text x="67" y="95" fontSize="10" fill="#FFD700" textAnchor="middle" fontWeight="bold">H</text>
        {/* Skateboard */}
        <ellipse cx="100" cy="145" rx="50" ry="8" fill="#1A1A1A"/>
        <circle cx="70" cy="148" r="6" fill="#333"/>
        <circle cx="130" cy="148" r="6" fill="#333"/>
        {/* Eye */}
        <circle cx="108" cy="58" r="3" fill="white"/>
        {/* Smile */}
        <path d="M112 65C112 65 110 68 108 68C106 68 106 65 108 63" stroke="white" strokeWidth="1.5" fill="none"/>
      </svg>
    ),
    bicycle: (
      <svg viewBox="0 0 200 200" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect width="200" height="200" fill="#FFD700" rx="20"/>
        {/* Bicycle wheels */}
        <circle cx="55" cy="140" r="30" stroke="#1A1A1A" strokeWidth="6" fill="none"/>
        <circle cx="145" cy="140" r="30" stroke="#1A1A1A" strokeWidth="6" fill="none"/>
        {/* Bicycle frame */}
        <path d="M55 140L85 100L115 140L145 140" stroke="#1A1A1A" strokeWidth="5" fill="none"/>
        <path d="M85 100L100 80" stroke="#1A1A1A" strokeWidth="4"/>
        {/* Horse rider */}
        <path 
          d="M85 100C85 100 80 85 85 75C90 65 95 60 100 55C105 50 110 45 115 45C120 45 125 50 125 55C125 60 120 65 115 70C110 75 105 80 103 85" 
          fill="#1A1A1A"
        />
        {/* Delivery box */}
        <rect x="45" y="95" width="30" height="25" rx="4" fill="#1A1A1A"/>
        <text x="60" y="112" fontSize="10" fill="#FFD700" textAnchor="middle" fontWeight="bold">H</text>
        {/* Eye */}
        <circle cx="118" cy="58" r="3" fill="white"/>
        {/* Smile */}
        <path d="M122 65C122 65 120 68 118 68C116 68 116 65 118 63" stroke="white" strokeWidth="1.5" fill="none"/>
      </svg>
    ),
    motorbike: (
      <svg viewBox="0 0 200 200" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect width="200" height="200" fill="#FFD700" rx="20"/>
        {/* Motorbike wheels */}
        <circle cx="55" cy="140" r="28" stroke="#1A1A1A" strokeWidth="6" fill="none"/>
        <circle cx="145" cy="140" r="22" stroke="#1A1A1A" strokeWidth="5" fill="none"/>
        {/* Motorbike body */}
        <path 
          d="M55 140C55 140 70 110 100 110C130 110 145 130 145 140" 
          stroke="#1A1A1A" 
          strokeWidth="8" 
          fill="none"
          strokeLinecap="round"
        />
        {/* Handlebars and front */}
        <path d="M135 110L145 90" stroke="#1A1A1A" strokeWidth="4"/>
        <circle cx="148" cy="85" r="5" fill="#1A1A1A"/>
        {/* Horse rider */}
        <path 
          d="M95 105C95 105 90 90 95 80C100 70 105 65 110 60C115 55 120 50 125 50C130 50 135 55 135 60C135 65 130 70 125 75C120 80 115 85 113 90" 
          fill="#1A1A1A"
        />
        {/* Delivery box on back */}
        <rect x="40" y="95" width="35" height="28" rx="4" fill="#1A1A1A"/>
        <text x="57" y="114" fontSize="10" fill="#FFD700" textAnchor="middle" fontWeight="bold">H</text>
        {/* Eye */}
        <circle cx="128" cy="63" r="3" fill="white"/>
        {/* Smile */}
        <path d="M132 70C132 70 130 73 128 73C126 73 126 70 128 68" stroke="white" strokeWidth="1.5" fill="none"/>
      </svg>
    )
  }

  return (
    <div className={`${sizeClasses[size]} ${className}`}>
      {icons[mode]}
    </div>
  )
}
