import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeft,
  Gift,
  History,
  Users,
  ChevronRight,
  Loader2,
  Share2,
} from 'lucide-react';
import { rewardsAPI } from '../../lib/api';
import {
  TierBadge,
  CoinBalance,
  ReferralCard,
  RedeemOptions,
  CoinHistory,
  ProgressBar,
  TierBenefits,
} from '../../components/rewards';

export default function RewardsDashboard() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<'redeem' | 'history'>('redeem');

  const { data: dashboardData, isLoading: dashboardLoading } = useQuery({
    queryKey: ['rewards-dashboard'],
    queryFn: () => rewardsAPI.dashboard().then((r) => r.data),
  });

  const { data: coinHistoryData, isLoading: historyLoading } = useQuery({
    queryKey: ['coin-history'],
    queryFn: () => rewardsAPI.coinHistory({ limit: 10 }).then((r) => r.data),
  });

  const { data: referralHistoryData } = useQuery({
    queryKey: ['referral-history'],
    queryFn: () => rewardsAPI.referralHistory({ limit: 5 }).then((r) => r.data),
  });

  const redeemMutation = useMutation({
    mutationFn: async (optionId: string) => {
      if (optionId === 'free-delivery') {
        return rewardsAPI.redeemFreeDelivery();
      } else if (optionId === 'discount-15') {
        return rewardsAPI.redeemDiscount(15);
      } else if (optionId === 'discount-30') {
        return rewardsAPI.redeemDiscount(30);
      }
      throw new Error('Invalid option');
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rewards-dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['coin-history'] });
    },
  });

  const handleRedeem = async (optionId: string) => {
    await redeemMutation.mutateAsync(optionId);
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
        <p className="text-gray-500">Unable to load rewards data</p>
        <Link to="/" className="text-primary-600 font-medium">
          Back to Home
        </Link>
      </div>
    );
  }

  const {
    current_tier,
    coin_balance,
    referral_code,
    referral_link,
    successful_referrals,
    referrals_to_next_tier,
    next_tier,
  } = dashboardData;

  return (
    <div className="min-h-screen bg-gray-50 pb-8">
      {/* Header */}
      <header className="bg-secondary-600 text-white sticky top-0 z-10">
        <div className="max-w-lg mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <Link to="/profile" className="flex items-center gap-2">
              <ArrowLeft className="w-6 h-6" />
              <h1 className="text-lg font-semibold">Rewards</h1>
            </Link>
            <Link
              to="/rewards/referral"
              className="p-2 bg-white/10 rounded-full hover:bg-white/20 transition-colors"
            >
              <Share2 className="w-5 h-5" />
            </Link>
          </div>
        </div>
      </header>

      <div className="max-w-lg mx-auto px-4 py-4 space-y-4">
        {/* Tier Badge & Coin Balance */}
        <div className="bg-white rounded-2xl p-5 shadow-card border border-gray-100">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500 mb-1">Current Tier</p>
              <TierBadge tier={current_tier} size="lg" showLabel />
            </div>
            <div className="text-right">
              <p className="text-sm text-gray-500 mb-1">Hashi Coins</p>
              <CoinBalance balance={coin_balance} size="lg" showValue={false} />
              <p className="text-xs text-gray-400 mt-1">= R{(coin_balance * 0.1).toFixed(2)} value</p>
            </div>
          </div>
        </div>

        {/* Progress Bar */}
        <ProgressBar
          currentTier={current_tier}
          nextTier={next_tier}
          successfulReferrals={successful_referrals}
          referralsToNextTier={referrals_to_next_tier}
        />

        {/* Tier Benefits */}
        <TierBenefits tier={current_tier} />

        {/* Referral Card */}
        <ReferralCard
          referralCode={referral_code}
          referralLink={referral_link}
          successfulReferrals={successful_referrals}
          compact
        />

        {/* Quick Stats */}
        <div className="grid grid-cols-2 gap-3">
          <Link
            to="/rewards/referral"
            className="bg-white rounded-xl p-4 shadow-card border border-gray-100 hover:shadow-card-hover transition-shadow"
          >
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-primary-100 rounded-xl flex items-center justify-center">
                <Users className="w-5 h-5 text-primary-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-secondary-600">{successful_referrals}</p>
                <p className="text-xs text-gray-500">Friends Invited</p>
              </div>
            </div>
          </Link>
          <div className="bg-white rounded-xl p-4 shadow-card border border-gray-100">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-green-100 rounded-xl flex items-center justify-center">
                <Gift className="w-5 h-5 text-green-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-secondary-600">
                  {referralHistoryData?.referrals?.filter((r) => r.status === 'completed').length || 0}
                </p>
                <p className="text-xs text-gray-500">Successful</p>
              </div>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="bg-white rounded-xl shadow-card border border-gray-100 overflow-hidden">
          <div className="flex border-b border-gray-100">
            <button
              onClick={() => setActiveTab('redeem')}
              className={`flex-1 py-3 text-sm font-medium flex items-center justify-center gap-2 transition-colors ${
                activeTab === 'redeem'
                  ? 'text-primary-600 border-b-2 border-primary-600 bg-primary-50'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              <Gift className="w-4 h-4" />
              Redeem
            </button>
            <button
              onClick={() => setActiveTab('history')}
              className={`flex-1 py-3 text-sm font-medium flex items-center justify-center gap-2 transition-colors ${
                activeTab === 'history'
                  ? 'text-primary-600 border-b-2 border-primary-600 bg-primary-50'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              <History className="w-4 h-4" />
              History
            </button>
          </div>

          <div className="p-4">
            {activeTab === 'redeem' ? (
              <RedeemOptions coinBalance={coin_balance} onRedeem={handleRedeem} />
            ) : (
              <>
                {historyLoading ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="w-6 h-6 animate-spin text-primary-600" />
                  </div>
                ) : (
                  <CoinHistory transactions={coinHistoryData?.transactions || []} />
                )}
                {(coinHistoryData?.transactions?.length || 0) > 0 && (
                  <button className="w-full mt-4 py-2 text-sm text-primary-600 font-medium hover:bg-primary-50 rounded-lg transition-colors flex items-center justify-center gap-1">
                    View All Transactions
                    <ChevronRight className="w-4 h-4" />
                  </button>
                )}
              </>
            )}
          </div>
        </div>

        {/* Referral History Preview */}
        {(referralHistoryData?.referrals?.length || 0) > 0 && (
          <div className="bg-white rounded-xl p-4 shadow-card border border-gray-100">
            <h3 className="font-semibold text-secondary-600 mb-4 flex items-center gap-2">
              <Users className="w-5 h-5 text-primary-600" />
              Recent Referrals
            </h3>
            <div className="space-y-2">
              {referralHistoryData?.referrals?.slice(0, 3).map((referral) => (
                <div
                  key={referral.id}
                  className="flex items-center justify-between py-2 px-3 bg-gray-50 rounded-lg"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-secondary-100 rounded-full flex items-center justify-center">
                      <span className="text-sm font-semibold text-secondary-600">
                        {referral.referred_name.charAt(0)}
                      </span>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-secondary-600">
                        {referral.referred_name}
                      </p>
                      <p className="text-xs text-gray-400">{referral.referred_phone}</p>
                    </div>
                  </div>
                  <span
                    className={`text-xs font-medium px-2 py-1 rounded-full ${
                      referral.status === 'completed'
                        ? 'bg-green-100 text-green-700'
                        : 'bg-yellow-100 text-yellow-700'
                    }`}
                  >
                    {referral.status === 'completed' ? 'Completed' : 'Pending'}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
