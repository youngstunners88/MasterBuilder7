import { useState, useEffect } from 'react';

export const useDataSaver = () => {
  const [enabled, setEnabled] = useState(() => {
    // Default to true for South African users on mobile networks
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('data_saver');
      if (saved !== null) return saved === 'true';
      // Detect mobile connection
      const conn = (navigator as any).connection;
      return conn?.saveData || conn?.effectiveType?.includes('2g') || false;
    }
    return true;
  });

  useEffect(() => {
    localStorage.setItem('data_saver', String(enabled));
    // Dispatch event for other components to react
    window.dispatchEvent(new CustomEvent('dataSaverChange', { detail: { enabled } }));
  }, [enabled]);

  return { enabled, toggle: () => setEnabled((prev: boolean) => !prev) };
};
