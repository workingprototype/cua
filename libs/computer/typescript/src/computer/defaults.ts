import { OSType, VMProviderType } from "./types";
import type { BaseComputerConfig, Display } from "./types";

/**
 * Default configuration values for Computer
 */
export const DEFAULT_CONFIG: Partial<BaseComputerConfig> = {
  name: "",
  osType: OSType.MACOS,
  vmProvider: VMProviderType.CLOUD,
  display: "1024x768",
  memory: "8GB",
  cpu: 4,
  image: "macos-sequoia-cua:latest",
  sharedDirectories: [],
  useHostComputerServer: false,
  telemetryEnabled: true,
  port: 7777,
  noVNCPort: 8006,
  host: "localhost",
  ephemeral: false,
};

/**
 * Apply default values to a computer configuration
 * @param config Partial configuration
 * @returns Complete configuration with defaults applied
 */
export function applyDefaults<T extends BaseComputerConfig>(
  config: Partial<T>
): T {
  return {
    ...DEFAULT_CONFIG,
    ...config,
  } as T;
}
