interface VerificationBadgeProps {
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

export default function VerificationBadge({ size = 'md', className = '' }: VerificationBadgeProps) {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-5 h-5',
    lg: 'w-6 h-6'
  }

  return (
    <div 
      className={`${sizeClasses[size]} ${className}`}
      title="iHhashi Verified"
    >
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
        {/* Blue circle background */}
        <circle cx="50" cy="50" r="48" fill="#3B82F6" stroke="#2563EB" strokeWidth="2"/>
        {/* White checkmark */}
        <path 
          d="M30 50L45 65L70 35" 
          stroke="white" 
          strokeWidth="6" 
          strokeLinecap="round" 
          strokeLinejoin="round"
          fill="none"
        />
        {/* Horse silhouette in center */}
        <path 
          d="M45 60C45 60 42 52 45 47C48 42 50 40 53 37C56 34 58 32 61 29C64 26 67 24 70 24C73 24 76 26 76 29C76 32 73 35 70 38C67 41 64 43 63 46C62 49 63 52 64 55C65 58 67 61 67 64" 
          fill="white"
          opacity="0.9"
        />
      </svg>
    </div>
  )
}
