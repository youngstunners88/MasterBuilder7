/**
 * EliteSquad Shared Configuration
 */

export const KOFI_ZO = "kofi.zo.space";
export const YOUNGSTUNNERS_ZO = "youngstunners.zo.space";
export const KIMI_HOST = "35.235.249.249:4200";

export const BRIDGE_NODES = {
  kofi: `https://${KOFI_ZO}/api/kimi-bridge`,
  youngstunners: `https://${YOUNGSTUNNERS_ZO}/api/elite-bridge`,
  kimi: `http://${KIMI_HOST}/api/v1/health`
} as const;

export const SYNC_INTERVAL = 60000;
export const TIMEOUT = 10000;
export const MAX_RETRIES = 3;
