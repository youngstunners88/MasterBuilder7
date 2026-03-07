import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  ArrowLeft,
  MapPin,
  CreditCard,
  HelpCircle,
  LogOut,
  Gift,
  ChevronRight,
  Coins,
  Loader2,
} from 'lucide-react';
import { useAuth } from '../../App';
import { rewardsAPI } from '../../lib/api';
import { TierBadgePill } from '../../components/rewards';

export default function Profile() {
  const { logout } = useAuth();

  const { data: rewardsData, isLoading: rewardsLoading } = useQuery({
    queryKey: ['rewards-profile'],
    queryFn: () => rewardsAPI.dashboard().then((r) => r.data),
  });

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white px-4 py-3 flex items-center border-b border-gray-100">
        <Link to="/" className="p-2 -ml-2">
          <ArrowLeft className="w-6 h-6" />
        </Link>
        <h1 className="text-lg font-semibold ml-2">Profile</h1>
      </header>

      {/* Profile Header */}
      <div className="bg-white px-4 py-6 mb-3">
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 rounded-full bg-secondary-600 flex items-center justify-center text-primary text-2xl font-bold">
            T
          </div>
          <div className="flex-1">
            <h2 className="font-bold text-lg text-secondary-600">Thandi Nkosi</h2>
            <p className="text-gray-500 text-sm">+27 82 123 4567</p>
            {/* Rewards Mini Display */}
            {rewardsLoading ? (
              <div className="mt-2">
                <Loader2 className="w-4 h-4 animate-spin text-primary-600" />
              </div>
            ) : rewardsData ? (
              <div className="flex items-center gap-3 mt-2">
                <TierBadgePill tier={rewardsData.current_tier} size="sm" />
                <div className="flex items-center gap-1 text-sm">
                  <Coins className="w-4 h-4 text-primary-600" />
                  <span className="font-semibold text-secondary-600">
                    {rewardsData.coin_balance.toLocaleString()}
                  </span>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="bg-white px-4 py-4 mb-3">
        <div className="grid grid-cols-3 text-center">
          <div>
            <p className="text-2xl font-bold text-primary-600">12</p>
            <p className="text-xs text-gray-500">Orders</p>
          </div>
          <div>
            <p className="text-2xl font-bold text-primary-600">R850</p>
            <p className="text-xs text-gray-500">Total Spent</p>
          </div>
          <div>
            <p className="text-2xl font-bold text-primary-600">4</p>
            <p className="text-xs text-gray-500">Addresses</p>
          </div>
        </div>
      </div>

      {/* Menu Items */}
      <div className="bg-white mb-3">
        {/* Rewards Section */}
        <Link
          to="/rewards"
          className="flex items-center gap-3 px-4 py-4 border-b border-gray-100 hover:bg-gray-50 transition-colors"
        >
          <div className="w-10 h-10 bg-primary-100 rounded-xl flex items-center justify-center flex-shrink-0">
            <Gift className="w-5 h-5 text-primary-600" />
          </div>
          <div className="flex-1 min-w-0">
            <span className="font-medium text-secondary-600">Rewards & Referrals</span>
            {rewardsData && (
              <p className="text-xs text-gray-400 truncate">
                {rewardsData.current_tier.name} Tier • {rewardsData.coin_balance} coins
              </p>
            )}
          </div>
          <ChevronRight className="w-5 h-5 text-gray-400 flex-shrink-0" />
        </Link>

        {/* Refer Friends - Quick Link */}
        <Link
          to="/rewards/referral"
          className="flex items-center gap-3 px-4 py-4 border-b border-gray-100 hover:bg-gray-50 transition-colors"
        >
          <div className="w-10 h-10 bg-green-100 rounded-xl flex items-center justify-center flex-shrink-0">
            <Coins className="w-5 h-5 text-green-600" />
          </div>
          <div className="flex-1 min-w-0">
            <span className="font-medium text-secondary-600">Invite Friends</span>
            <p className="text-xs text-gray-400 truncate">Earn 50 coins per friend who joins</p>
          </div>
          <ChevronRight className="w-5 h-5 text-gray-400 flex-shrink-0" />
        </Link>

        <Link
          to="/profile/addresses"
          className="flex items-center gap-3 px-4 py-4 border-b border-gray-100 hover:bg-gray-50 transition-colors"
        >
          <MapPin className="w-5 h-5 text-gray-400" />
          <span className="flex-1">Saved Addresses</span>
          <span className="text-gray-400 text-sm">4</span>
        </Link>
        <Link
          to="/profile/payments"
          className="flex items-center gap-3 px-4 py-4 border-b border-gray-100 hover:bg-gray-50 transition-colors"
        >
          <CreditCard className="w-5 h-5 text-gray-400" />
          <span className="flex-1">Payment Methods</span>
          <ChevronRight className="w-5 h-5 text-gray-400" />
        </Link>
        <Link
          to="/help"
          className="flex items-center gap-3 px-4 py-4 border-b border-gray-100 hover:bg-gray-50 transition-colors"
        >
          <HelpCircle className="w-5 h-5 text-gray-400" />
          <span className="flex-1">Help & Support</span>
          <ChevronRight className="w-5 h-5 text-gray-400" />
        </Link>
      </div>

      {/* Account Actions */}
      <div className="bg-white">
        <button
          onClick={() => logout()}
          className="flex items-center gap-3 px-4 py-4 w-full text-left text-red-500 hover:bg-red-50 transition-colors"
        >
          <LogOut className="w-5 h-5" />
          <span>Sign Out</span>
        </button>
      </div>

      {/* App Version */}
      <div className="text-center py-6">
        <p className="text-xs text-gray-400">iHhashi v1.0.0</p>
      </div>
    </div>
  );
}
