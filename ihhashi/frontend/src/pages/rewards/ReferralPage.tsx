import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  ArrowLeft,
  Share2,
  Users,
  Gift,
  CheckCircle,
  Clock,
  MessageCircle,
  Link as LinkIcon,
  Loader2,
  Copy,
  Check,
  Mail,
  Send,
} from 'lucide-react';
import { rewardsAPI } from '../../lib/api';
import { CoinBalance } from '../../components/rewards';

const shareOptions = [
  {
    id: 'whatsapp',
    name: 'WhatsApp',
    icon: MessageCircle,
    color: 'bg-green-500',
    getUrl: (link: string, code: string) =>
      `https://wa.me/?text=${encodeURIComponent(`Join me on iHhashi! Use my code ${code} for 25 Hashi Coins bonus: ${link}`)}`,
  },
  {
    id: 'telegram',
    name: 'Telegram',
    icon: Send,
    color: 'bg-blue-500',
    getUrl: (link: string, code: string) =>
      `https://t.me/share/url?url=${encodeURIComponent(link)}&text=${encodeURIComponent(`Join me on iHhashi! Use my code ${code} for 25 Hashi Coins bonus.`)}`,
  },
  {
    id: 'email',
    name: 'Email',
    icon: Mail,
    color: 'bg-red-500',
    getUrl: (link: string, code: string) =>
      `mailto:?subject=${encodeURIComponent('Join me on iHhashi!')}&body=${encodeURIComponent(`Hi!\n\nI thought you'd love iHhashi - it's the best food delivery app in South Africa!\n\nUse my referral code ${code} when you sign up and you'll get 25 Hashi Coins (R2.50 value) as a welcome bonus.\n\n${link}\n\nCheers!`)}`,
  },
];

const howItWorks = [
  {
    icon: Share2,
    title: 'Share Your Code',
    description: 'Send your unique referral code to friends and family via WhatsApp, social media, or email.',
  },
  {
    icon: Users,
    title: 'They Sign Up',
    description: 'Your friend downloads iHhashi and creates an account using your referral code.',
  },
  {
    icon: Gift,
    title: 'You Both Win',
    description: 'You get 50 Hashi Coins, they get 25 Hashi Coins. Everyone saves on their orders!',
  },
];

export default function ReferralPage() {
  const [copied, setCopied] = useState(false);

  const { data: dashboardData, isLoading: dashboardLoading } = useQuery({
    queryKey: ['rewards-dashboard'],
    queryFn: () => rewardsAPI.dashboard().then((r) => r.data),
  });

  const { data: referralHistoryData, isLoading: historyLoading } = useQuery({
    queryKey: ['referral-history'],
    queryFn: () => rewardsAPI.referralHistory({ limit: 20 }).then((r) => r.data),
  });

  const handleCopy = async () => {
    if (!dashboardData?.referral_link) return;
    try {
      await navigator.clipboard.writeText(dashboardData.referral_link);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const handleShare = async () => {
    if (!dashboardData) return;
    const shareData = {
      title: 'Join iHhashi - Get R25 worth of Hashi Coins!',
      text: `Use my referral code ${dashboardData.referral_code} to join iHhashi and get 25 Hashi Coins (R25 value)! 🎉`,
      url: dashboardData.referral_link,
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

  if (dashboardLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
      </div>
    );
  }

  if (!dashboardData) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center gap-4 text-center px-6">
        <Gift className="w-12 h-12 text-gray-300" />
        <p className="text-gray-500">Unable to load referral data</p>
        <Link to="/" className="text-primary-600 font-medium">
          Back to Home
        </Link>
      </div>
    );
  }

  const { referral_code, referral_link, successful_referrals, coin_balance } = dashboardData;
  const totalCoinsEarned = (referralHistoryData?.referrals || []).reduce(
    (sum, r) => sum + (r.status === 'completed' ? r.coins_earned : 0),
    0
  );

  return (
    <div className="min-h-screen bg-gray-50 pb-8">
      {/* Header */}
      <header className="bg-secondary-600 text-white sticky top-0 z-10">
        <div className="max-w-lg mx-auto px-4 py-4">
          <div className="flex items-center gap-2">
            <Link to="/rewards" className="p-2 -ml-2 hover:bg-white/10 rounded-full transition-colors">
              <ArrowLeft className="w-6 h-6" />
            </Link>
            <h1 className="text-lg font-semibold">Invite Friends</h1>
          </div>
        </div>
      </header>

      <div className="max-w-lg mx-auto px-4 py-4 space-y-4">
        {/* Hero Card */}
        <div className="bg-gradient-to-br from-primary to-primary-400 rounded-2xl p-6 text-center shadow-card">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-white/20 rounded-full mb-4">
            <Gift className="w-8 h-8 text-secondary-600" />
          </div>
          <h2 className="text-2xl font-bold text-secondary-600 mb-2">
            Earn R50 Per Friend!
          </h2>
          <p className="text-secondary-500 mb-4">
            Share your code and earn <span className="font-bold">50 Hashi Coins</span> for each friend who joins
          </p>
          <CoinBalance balance={coin_balance} size="md" />
        </div>

        {/* Referral Code Card */}
        <div className="bg-white rounded-2xl p-6 shadow-card border border-gray-100">
          <p className="text-sm text-gray-500 text-center mb-3">Your Referral Code</p>
          <div className="bg-gradient-to-r from-gray-50 to-gray-100 rounded-xl p-4 mb-4">
            <p className="text-3xl font-mono font-bold text-secondary-600 text-center tracking-wider">
              {referral_code}
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleCopy}
              className="flex-1 py-3 bg-secondary-600 text-primary rounded-xl font-semibold hover:bg-secondary-700 transition-colors flex items-center justify-center gap-2"
            >
              {copied ? <Check className="w-5 h-5" /> : <Copy className="w-5 h-5" />}
              {copied ? 'Copied!' : 'Copy Code'}
            </button>
            <button
              onClick={handleShare}
              className="flex-1 py-3 bg-primary text-secondary-600 rounded-xl font-semibold hover:bg-primary-400 transition-colors flex items-center justify-center gap-2"
            >
              <Share2 className="w-5 h-5" />
              Share
            </button>
          </div>
          <div className="mt-4 flex items-center justify-center gap-2 text-sm text-gray-500">
            <LinkIcon className="w-4 h-4" />
            <span className="truncate max-w-[200px]">{referral_link}</span>
          </div>
        </div>

        {/* Social Share Buttons */}
        <div className="grid grid-cols-3 gap-3">
          {shareOptions.map((option) => {
            const Icon = option.icon;
            return (
              <a
                key={option.id}
                href={option.getUrl(referral_link, referral_code)}
                target="_blank"
                rel="noopener noreferrer"
                className="flex flex-col items-center gap-2 p-4 bg-white rounded-xl shadow-card border border-gray-100 hover:shadow-card-hover transition-shadow"
              >
                <div className={`w-12 h-12 ${option.color} rounded-xl flex items-center justify-center`}>
                  <Icon className="w-6 h-6 text-white" />
                </div>
                <span className="text-sm font-medium text-secondary-600">{option.name}</span>
              </a>
            );
          })}
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-white rounded-xl p-4 shadow-card border border-gray-100 text-center">
            <p className="text-3xl font-bold text-secondary-600">{successful_referrals}</p>
            <p className="text-sm text-gray-500">Friends Joined</p>
          </div>
          <div className="bg-white rounded-xl p-4 shadow-card border border-gray-100 text-center">
            <p className="text-3xl font-bold text-primary-600">{totalCoinsEarned}</p>
            <p className="text-sm text-gray-500">Coins Earned</p>
          </div>
        </div>

        {/* How It Works */}
        <div className="bg-white rounded-2xl p-6 shadow-card border border-gray-100">
          <h3 className="font-bold text-secondary-600 mb-4 text-center">How It Works</h3>
          <div className="space-y-4">
            {howItWorks.map((step, index) => {
              const Icon = step.icon;
              return (
                <div key={index} className="flex items-start gap-4">
                  <div className="flex-shrink-0 w-10 h-10 bg-primary-100 rounded-xl flex items-center justify-center">
                    <Icon className="w-5 h-5 text-primary-600" />
                  </div>
                  <div>
                    <h4 className="font-semibold text-secondary-600">{step.title}</h4>
                    <p className="text-sm text-gray-500">{step.description}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Referral History */}
        <div className="bg-white rounded-2xl p-6 shadow-card border border-gray-100">
          <h3 className="font-bold text-secondary-600 mb-4 flex items-center gap-2">
            <Users className="w-5 h-5 text-primary-600" />
            Your Referrals
          </h3>
          {historyLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin text-primary-600" />
            </div>
          ) : (referralHistoryData?.referrals?.length || 0) === 0 ? (
            <div className="text-center py-8">
              <Users className="w-12 h-12 text-gray-200 mx-auto mb-2" />
              <p className="text-gray-500">No referrals yet</p>
              <p className="text-sm text-gray-400 mt-1">Share your code to start earning!</p>
            </div>
          ) : (
            <div className="space-y-3">
              {referralHistoryData?.referrals?.map((referral) => (
                <div
                  key={referral.id}
                  className="flex items-center justify-between py-3 px-4 bg-gray-50 rounded-xl"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-secondary-100 rounded-full flex items-center justify-center">
                      <span className="font-semibold text-secondary-600">
                        {referral.referred_name.charAt(0)}
                      </span>
                    </div>
                    <div>
                      <p className="font-medium text-secondary-600">{referral.referred_name}</p>
                      <p className="text-xs text-gray-400">{referral.referred_phone}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    {referral.status === 'completed' ? (
                      <>
                        <p className="font-semibold text-green-600">+{referral.coins_earned}</p>
                        <p className="text-xs text-green-600 flex items-center gap-1">
                          <CheckCircle className="w-3 h-3" />
                          Completed
                        </p>
                      </>
                    ) : (
                      <>
                        <p className="font-semibold text-gray-400">--</p>
                        <p className="text-xs text-yellow-600 flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          Pending
                        </p>
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
