import { Coins, TrendingUp, TrendingDown } from 'lucide-react';

interface CoinBalanceProps {
  balance: number;
  showValue?: boolean;
  size?: 'sm' | 'md' | 'lg';
  change?: number;
}

const sizeConfig = {
  sm: {
    container: 'px-3 py-1.5',
    icon: 'w-4 h-4',
    balance: 'text-base',
    value: 'text-xs',
    change: 'text-xs',
  },
  md: {
    container: 'px-4 py-2',
    icon: 'w-5 h-5',
    balance: 'text-xl',
    value: 'text-sm',
    change: 'text-sm',
  },
  lg: {
    container: 'px-6 py-4',
    icon: 'w-8 h-8',
    balance: 'text-3xl',
    value: 'text-base',
    change: 'text-base',
  },
};

export function CoinBalance({ balance, showValue = true, size = 'md', change }: CoinBalanceProps) {
  const sizes = sizeConfig[size];
  const zarValue = (balance * 0.1).toFixed(2);

  return (
    <div className={`inline-flex items-center gap-3 bg-gradient-to-r from-primary-50 to-primary-100 border border-primary-200 rounded-xl ${sizes.container}`}>
      <div className="relative">
        <Coins className={`${sizes.icon} text-primary-600`} />
        <div className="absolute -top-1 -right-1 w-2 h-2 bg-primary-400 rounded-full animate-pulse" />
      </div>
      <div>
        <div className="flex items-center gap-2">
          <span className={`font-bold text-secondary-600 ${sizes.balance}`}>
            {balance.toLocaleString()}
          </span>
          {change !== undefined && change !== 0 && (
            <span className={`inline-flex items-center gap-0.5 ${sizes.change} ${change > 0 ? 'text-green-600' : 'text-red-600'}`}>
              {change > 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
              {Math.abs(change)}
            </span>
          )}
        </div>
        {showValue && (
          <p className={`text-secondary-400 ${sizes.value}`}>
            = R{zarValue}
          </p>
        )}
      </div>
    </div>
  );
}

export function MiniCoinBalance({ balance }: { balance: number }) {
  return (
    <div className="flex items-center gap-1.5 text-sm">
      <Coins className="w-4 h-4 text-primary-600" />
      <span className="font-semibold text-secondary-600">{balance.toLocaleString()}</span>
      <span className="text-secondary-400 text-xs">coins</span>
    </div>
  );
}

export default CoinBalance;
