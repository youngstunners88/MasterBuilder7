import { Target, ChevronRight } from 'lucide-react';
import type { TierInfo } from '../../lib/api';
import { TierBadgePill } from './TierBadge';

interface ProgressBarProps {
  currentTier: TierInfo;
  nextTier?: TierInfo;
  successfulReferrals: number;
  referralsToNextTier: number;
}

export function ProgressBar({
  currentTier,
  nextTier,
  successfulReferrals,
  referralsToNextTier,
}: ProgressBarProps) {
  const isMaxTier = !nextTier;
  const progress = isMaxTier
    ? 100
    : Math.min(
        100,
        ((successfulReferrals - currentTier.min_referrals) /
          (nextTier.min_referrals - currentTier.min_referrals)) *
          100
      );

  return (
    <div className="bg-white rounded-xl p-5 shadow-card border border-gray-100">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="font-semibold text-secondary-600 flex items-center gap-2">
            <Target className="w-5 h-5 text-primary-600" />
            Tier Progress
          </h3>
          <p className="text-sm text-gray-500 mt-1">
            {isMaxTier ? (
              <span className="text-primary-600 font-medium">🎉 You've reached the highest tier!</span>
            ) : (
              <>
                <span className="font-semibold text-secondary-600">{referralsToNextTier}</span> more{' '}
                {referralsToNextTier === 1 ? 'referral' : 'referrals'} to reach{' '}
                <TierBadgePill tier={nextTier} size="sm" />
              </>
            )}
          </p>
        </div>
        <div className="text-right">
          <p className="text-2xl font-bold text-secondary-600">{successfulReferrals}</p>
          <p className="text-xs text-gray-400">referrals</p>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="relative">
        <div className="h-3 bg-gray-100 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-primary to-primary-400 rounded-full transition-all duration-500 ease-out"
            style={{ width: `${progress}%` }}
          />
        </div>

        {/* Tier Markers */}
        <div className="flex justify-between mt-2">
          <TierBadgePill tier={currentTier} size="sm" />
          {nextTier ? (
            <>
              <ChevronRight className="w-4 h-4 text-gray-300" />
              <TierBadgePill tier={nextTier} size="sm" />
            </>
          ) : (
            <span className="text-xs text-gray-400">Max tier reached!</span>
          )}
        </div>
      </div>
    </div>
  );
}

interface TierBenefitsProps {
  tier: TierInfo;
}

export function TierBenefits({ tier }: TierBenefitsProps) {
  const benefits = [
    { icon: '🏷️', text: `${tier.discount_percent}% off all orders` },
    { icon: '🚚', text: `${tier.free_deliveries_per_month} free ${tier.free_deliveries_per_month === 1 ? 'delivery' : 'deliveries'}/month` },
    { icon: '🎧', text: `${tier.support_level} support` },
    ...(tier.early_access ? [{ icon: '⭐', text: 'Early access to new features' }] : []),
  ];

  return (
    <div className="bg-gradient-to-br from-gray-50 to-gray-100 rounded-xl p-5">
      <h3 className="font-semibold text-secondary-600 mb-4 flex items-center gap-2">
        <span className="text-xl">✨</span>
        {tier.name} Benefits
      </h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {benefits.map((benefit, index) => (
          <div
            key={index}
            className="flex items-center gap-3 bg-white rounded-lg p-3 shadow-sm"
          >
            <span className="text-xl">{benefit.icon}</span>
            <span className="text-sm font-medium text-secondary-600">{benefit.text}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default ProgressBar;
