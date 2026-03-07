import { Medal, Award, Crown, Diamond } from 'lucide-react';
import type { TierInfo } from '../../lib/api';

interface TierBadgeProps {
  tier: TierInfo | string;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
}

const tierConfig: Record<string, {
  icon: typeof Medal;
  gradient: string;
  textColor: string;
  bgColor: string;
  label: string;
}> = {
  Bronze: {
    icon: Medal,
    gradient: 'from-amber-700 to-amber-600',
    textColor: 'text-amber-700',
    bgColor: 'bg-amber-50',
    label: 'Bronze',
  },
  Silver: {
    icon: Award,
    gradient: 'from-gray-400 to-gray-300',
    textColor: 'text-gray-600',
    bgColor: 'bg-gray-50',
    label: 'Silver',
  },
  Gold: {
    icon: Crown,
    gradient: 'from-yellow-400 to-yellow-300',
    textColor: 'text-yellow-700',
    bgColor: 'bg-yellow-50',
    label: 'Gold',
  },
  Platinum: {
    icon: Diamond,
    gradient: 'from-purple-500 to-pink-400',
    textColor: 'text-purple-700',
    bgColor: 'bg-purple-50',
    label: 'Platinum',
  },
};

const sizeConfig = {
  sm: {
    container: 'w-8 h-8',
    icon: 'w-4 h-4',
    text: 'text-xs',
    badge: 'px-2 py-0.5 text-xs',
  },
  md: {
    container: 'w-12 h-12',
    icon: 'w-6 h-6',
    text: 'text-sm',
    badge: 'px-3 py-1 text-sm',
  },
  lg: {
    container: 'w-16 h-16',
    icon: 'w-8 h-8',
    text: 'text-base',
    badge: 'px-4 py-1.5 text-base',
  },
};

export function TierBadge({ tier, size = 'md', showLabel = true }: TierBadgeProps) {
  const tierName = typeof tier === 'string' ? tier : tier.name;
  const config = tierConfig[tierName] || tierConfig.Bronze;
  const Icon = config.icon;
  const sizes = sizeConfig[size];

  return (
    <div className="flex items-center gap-2">
      <div className={`${sizes.container} rounded-full bg-gradient-to-br ${config.gradient} flex items-center justify-center shadow-lg`}>
        <Icon className={`${sizes.icon} text-white`} />
      </div>
      {showLabel && (
        <span className={`font-semibold ${config.textColor} ${sizes.text}`}>
          {config.label}
        </span>
      )}
    </div>
  );
}

export function TierBadgePill({ tier, size = 'md' }: TierBadgeProps) {
  const tierName = typeof tier === 'string' ? tier : tier.name;
  const config = tierConfig[tierName] || tierConfig.Bronze;
  const Icon = config.icon;
  const sizes = sizeConfig[size];

  return (
    <div className={`inline-flex items-center gap-1.5 ${sizes.badge} rounded-full ${config.bgColor} ${config.textColor} font-medium`}>
      <Icon className="w-3.5 h-3.5" />
      <span>{config.label}</span>
    </div>
  );
}

export default TierBadge;
