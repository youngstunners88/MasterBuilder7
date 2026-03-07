import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.ihhashi.delivery',
  appName: 'iHhashi',
  webDir: 'dist',
  server: {
    // Enable live reload for development
    // Run 'npm run dev -- --host' then update this URL to your computer's IP
    // url: 'http://YOUR_IP:5173',
    cleartext: true,
  },
  android: {
    buildOptions: {
      keystorePath: 'android/ihhashi-new.keystore',
      keystoreAlias: 'ihhashi',
    },
  },
};

export default config;
