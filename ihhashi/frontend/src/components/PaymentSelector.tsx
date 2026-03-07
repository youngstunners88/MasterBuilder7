import { useState } from 'react';

const PAYMENT_METHODS = [
  { id: 'cash', name: 'Cash on Delivery', icon: '💵', fee: 0, popular: true },
  { id: 'ozow', name: 'Ozow Instant EFT', icon: '🏦', fee: 0, popular: true },
  { id: 'payfast', name: 'PayFast', icon: '⚡', fee: 0, popular: false },
  { id: 'snapscan', name: 'SnapScan', icon: '📱', fee: 0, popular: false },
  { id: 'card', name: 'Credit/Debit Card', icon: '💳', fee: 0, popular: false },
] as const;

interface PaymentSelectorProps {
  onSelect: (method: string) => void;
}

export const PaymentSelector = ({ onSelect }: PaymentSelectorProps) => {
  const [selected, setSelected] = useState('cash'); // Default to cash for SA

  const handleSelect = (id: string) => {
    setSelected(id);
    onSelect(id);
  };

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-gray-900">Payment Method</h3>
      
      <div className="space-y-2">
        {PAYMENT_METHODS.map((method) => (
          <button
            key={method.id}
            onClick={() => handleSelect(method.id)}
            className={`flex items-center w-full p-4 border-2 rounded-xl text-left transition-all ${
              selected === method.id
                ? 'border-red-600 bg-red-50 ring-2 ring-red-200'
                : 'border-gray-200 hover:border-gray-300'
            }`}
          >
            <span className="text-2xl mr-3">{method.icon}</span>
            <div className="flex-1">
              <div className="font-medium text-gray-900">{method.name}</div>
              {method.popular && (
                <span className="text-xs text-red-600 font-medium">
                  Most popular in SA
                </span>
              )}
            </div>
            {selected === method.id && (
              <svg className="w-5 h-5 text-red-600" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
            )}
          </button>
        ))}
      </div>
      
      <p className="text-sm text-gray-500 bg-gray-50 p-3 rounded-lg">
        💡 Cash on delivery is available in all areas. Digital payments require internet connectivity.
      </p>
    </div>
  );
};
