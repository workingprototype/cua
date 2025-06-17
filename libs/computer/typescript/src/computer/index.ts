import { LumierComputer } from "./providers/lumier";
import type { BaseComputer } from "./providers/base";
import { CloudComputer } from "./providers/cloud";
import { LumeComputer } from "./providers/lume";
import {
  VMProviderType,
  type BaseComputerConfig,
  type CloudComputerConfig,
  type LumeComputerConfig,
  type LumierComputerConfig,
} from "./types";
import { applyDefaults } from "./defaults";

/**
 * Factory class for creating the appropriate Computer instance
 */
export class Computer {
  /**
   * Create a computer instance based on the provided configuration
   * @param config The computer configuration
   * @returns The appropriate computer instance based on the VM provider type
   */
  static create(
    config:
      | Partial<BaseComputerConfig>
      | Partial<CloudComputerConfig>
      | Partial<LumeComputerConfig>
      | Partial<LumierComputerConfig>
  ): BaseComputer {
    // Apply defaults to the configuration
    const fullConfig = applyDefaults(config);

    // Check the vmProvider property to determine which type of computer to create
    switch (fullConfig.vmProvider) {
      case VMProviderType.CLOUD:
        return new CloudComputer(fullConfig as CloudComputerConfig);
      case VMProviderType.LUME:
        return new LumeComputer(fullConfig as LumeComputerConfig);
      case VMProviderType.LUMIER:
        return new LumierComputer(fullConfig as LumierComputerConfig);
      default:
        throw new Error(
          `Unsupported VM provider type: ${fullConfig.vmProvider}`
        );
    }

    throw new Error(`Unsupported VM provider type`);
  }
}
