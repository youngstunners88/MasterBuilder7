import { useState } from 'react';
import { Copy, Check, Share2, Users, Gift } from 'lucide-react';

interface ReferralCardProps {
  referralCode: string;
  referralLink: string;
  successfulReferrals?: number;
  coinsPerReferral?: number;
  compact?: boolean;
}

export function ReferralCard({
  referralCode,
  referralLink,
  successfulReferrals = 0,
  coinsPerReferral = 50,
  compact = false,
}: ReferralCardProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(referralLink);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const handleShare = async () => {
    const shareData = {
      title: 'Join iHhashi - Get R25 worth of Hashi Coins!',
      text: `Use my referral code ${referralCode} to join iHhashi and get ${coinsPerReferral} Hashi Coins (R25 value)! 🎉`,
      url: referralLink,
    };

    if (navigator.share) {
      try {
        await navigator.share(shareData);
      } catch (err) {
        console.error('Share failed:', err);
      }
    } else {
      handleCopy();
    }
  };

  if (compact) {
    return (
      <div className="bg-white rounded-xl p-4 shadow-card border border-gray-100">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-gray-500">Your Referral Code</span>
          <div className="flex items-center gap-1 text-sm text-primary-600">
            <Users className="w-4 h-4" />
            <span>{successfulReferrals} referrals</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex-1 bg-gray-50 rounded-lg px-3 py-2 font-mono text-lg font-semibold text-secondary-600 tracking-wider">
            {referralCode}
          </div>
          <button
            onClick={handleCopy}
            className="p-2 bg-primary-100 text-primary-700 rounded-lg hover:bg-primary-200 transition-colors"
            title="Copy referral link"
          >
            {copied ? <Check className="w-5 h-5" /> : <Copy className="w-5 h-5" />}
          </button>
          <button
            onClick={handleShare}
            className="p-2 bg-secondary-600 text-primary rounded-lg hover:bg-secondary-700 transition-colors"
            title="Share"
          >
            <Share2 className="w-5 h-5" />
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gradient-to-br from-secondary-600 to-secondary-700 rounded-2xl p-6 text-white shadow-card">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="font-bold text-lg flex items-center gap-2">
            <Gift className="w-5 h-5 text-primary" />
            Invite Friends, Earn Rewards
          </h3>
          <p className="text-gray-300 text-sm mt-1">
            Share your code and earn {coinsPerReferral} coins per friend who joins
          </p>
        </div>
        <div className="bg-primary/20 rounded-xl p-3 text-center">
          <p className="text-2xl font-bold text-primary">{successfulReferrals}</p>
          <p className="text-xs text-gray-300">friends joined</p>
        </div>
      </div>

      <div className="bg-white/10 rounded-xl p-4 mb-4">
        <p className="text-sm text-gray-300 mb-2">Your Referral Code</p>
        <div className="flex items-center gap-3">
          <div className="flex-1 bg-white rounded-lg px-4 py-3">
            <span className="font-mono text-xl font-bold text-secondary-600 tracking-wider">
              {referralCode}
            </span>
          </div>
          <button
            onClick={handleCopy}
            className="bg-primary text-secondary-600 px-4 py-3 rounded-lg font-semibold hover:bg-primary-400 transition-colors flex items-center gap-2"
          >
            {copied ? <Check className="w-5 h-5" /> : <Copy className="w-5 h-5" />}
            {copied ? 'Copied!' : 'Copy'}
          </button>
        </div>
      </div>

      <button
        onClick={handleShare}
        className="w-full bg-primary text-secondary-600 py-3 rounded-xl font-semibold hover:bg-primary-400 transition-colors flex items-center justify-center gap-2"
      >
        <Share2 className="w-5 h-5" />
        Share with Friends
      </button>
    </div>
  );
}

export default ReferralCard;
