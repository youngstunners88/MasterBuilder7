import { useState, useEffect } from 'react';

interface LoadSheddingStatus {
  isLoadShedding: boolean;
  stage: number;
  nextUpdate: Date;
  area: string;
}

// Mock EskomSePush integration - replace with actual API
const checkLoadSheddingStatus = async (area: string): Promise<LoadSheddingStatus> => {
  // In production: fetch from EskomSePush API or your backend cache
  // For now, return mock data
  return {
    isLoadShedding: Math.random() > 0.7, // 30% chance for demo
    stage: Math.floor(Math.random() * 6) + 1,
    nextUpdate: new Date(Date.now() + 30 * 60 * 1000), // 30 mins
    area,
  };
};

export const useLoadShedding = (areaCode: string) => {
  const [status, setStatus] = useState<LoadSheddingStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    
    const fetchStatus = async () => {
      try {
        const data = await checkLoadSheddingStatus(areaCode);
        if (mounted) setStatus(data);
      } catch (error) {
        console.warn('Failed to fetch load shedding status:', error);
      } finally {
        if (mounted) setLoading(false);
      }
    };

    fetchStatus();
    // Poll every 15 minutes
    const interval = setInterval(fetchStatus, 15 * 60 * 1000);
    
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, [areaCode]);

  return { status, loading, isAffected: status?.isLoadShedding };
};
