import { useState } from 'react';
import { Truck, Ticket, Coins, Loader2, CheckCircle } from 'lucide-react';
import type { CoinTransaction } from '../../lib/api';

interface RedeemOption {
  id: string;
  name: string;
  description: string;
  coinCost: number;
  icon: typeof Truck;
  color: string;
  value: string;
}

const redeemOptions: RedeemOption[] = [
  {
    id: 'free-delivery',
    name: 'Free Delivery',
    description: 'Get free delivery on your next order',
    coinCost: 100,
    icon: Truck,
    color: 'from-blue-500 to-blue-600',
    value: 'R15-25 saved',
  },
  {
    id: 'discount-15',
    name: 'R15 Discount',
    description: 'R15 off your next order',
    coinCost: 150,
    icon: Ticket,
    color: 'from-green-500 to-green-600',
    value: 'R15 off',
  },
  {
    id: 'discount-30',
    name: 'R30 Discount',
    description: 'R30 off your next order',
    coinCost: 300,
    icon: Ticket,
    color: 'from-purple-500 to-purple-600',
    value: 'R30 off',
  },
];

interface RedeemOptionsProps {
  coinBalance: number;
  onRedeem: (optionId: string) => Promise<void>;
}

export function RedeemOptions({ coinBalance, onRedeem }: RedeemOptionsProps) {
  const [redeeming, setRedeeming] = useState<string | null>(null);
  const [redeemed, setRedeemed] = useState<string | null>(null);

  const handleRedeem = async (option: RedeemOption) => {
    if (coinBalance < option.coinCost) return;

    setRedeeming(option.id);
    try {
      await onRedeem(option.id);
      setRedeemed(option.id);
      setTimeout(() => setRedeemed(null), 3000);
    } catch (error) {
      console.error('Redeem failed:', error);
    } finally {
      setRedeeming(null);
    }
  };

  return (
    <div className="space-y-3">
      {redeemOptions.map((option) => {
        const Icon = option.icon;
        const canAfford = coinBalance >= option.coinCost;
        const isRedeeming = redeeming === option.id;
        const isRedeemed = redeemed === option.id;

        return (
          <div
            key={option.id}
            className={`bg-white rounded-xl p-4 shadow-card border transition-all ${
              canAfford ? 'border-gray-100 hover:shadow-card-hover' : 'border-gray-100 opacity-60'
            }`}
          >
            <div className="flex items-start gap-4">
              <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${option.color} flex items-center justify-center flex-shrink-0`}>
                <Icon className="w-6 h-6 text-white" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h4 className="font-semibold text-secondary-600">{option.name}</h4>
                    <p className="text-sm text-gray-500">{option.description}</p>
                  </div>
                  <span className="text-sm font-bold text-green-600 whitespace-nowrap">
                    {option.value}
                  </span>
                </div>
                <div className="flex items-center justify-between mt-3">
                  <div className="flex items-center gap-1 text-sm">
                    <Coins className="w-4 h-4 text-primary-600" />
                    <span className={`font-semibold ${canAfford ? 'text-secondary-600' : 'text-red-500'}`}>
                      {option.coinCost}
                    </span>
                    <span className="text-gray-400">coins</span>
                  </div>
                  <button
                    onClick={() => handleRedeem(option)}
                    disabled={!canAfford || isRedeeming || !!isRedeemed}
                    className={`px-4 py-2 rounded-lg font-medium text-sm transition-all ${
                      isRedeemed
                        ? 'bg-green-100 text-green-700'
                        : canAfford
                        ? 'bg-secondary-600 text-primary hover:bg-secondary-700'
                        : 'bg-gray-100 text-gray-400 cursor-not-allowed'
                    }`}
                  >
                    {isRedeeming ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : isRedeemed ? (
                      <span className="flex items-center gap-1">
                        <CheckCircle className="w-4 h-4" />
                        Redeemed!
                      </span>
                    ) : (
                      'Redeem'
                    )}
                  </button>
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function CoinHistory({ transactions }: { transactions: CoinTransaction[] }) {
  return (
    <div className="space-y-2">
      {transactions.length === 0 ? (
        <div className="text-center py-8 text-gray-400">
          <Coins className="w-12 h-12 mx-auto mb-2 opacity-30" />
          <p>No transactions yet</p>
        </div>
      ) : (
        transactions.map((tx) => (
          <div
            key={tx.id}
            className="flex items-center justify-between py-3 px-4 bg-gray-50 rounded-xl"
          >
            <div className="flex items-center gap-3">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                tx.type === 'earned' || tx.type === 'bonus'
                  ? 'bg-green-100 text-green-600'
                  : 'bg-red-100 text-red-600'
              }`}>
                {tx.type === 'earned' || tx.type === 'bonus' ? '+' : '-'}
              </div>
              <div>
                <p className="text-sm font-medium text-secondary-600">{tx.description}</p>
                <p className="text-xs text-gray-400">
                  {new Date(tx.created_at).toLocaleDateString('en-ZA', {
                    day: 'numeric',
                    month: 'short',
                  })}
                </p>
              </div>
            </div>
            <span className={`font-semibold ${
              tx.type === 'earned' || tx.type === 'bonus'
                ? 'text-green-600'
                : 'text-red-600'
            }`}>
              {tx.type === 'earned' || tx.type === 'bonus' ? '+' : '-'}{tx.amount}
            </span>
          </div>
        ))
      )}
    </div>
  );
}

export default RedeemOptions;
