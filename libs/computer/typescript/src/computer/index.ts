import type { BaseComputer } from "./providers/base";
import { CloudComputer } from "./providers/cloud";
import { LumeComputer } from "./providers/lume";
import {
  VMProviderType,
  type BaseComputerConfig,
  type CloudComputerConfig,
  type LumeComputerConfig,
} from "./types";
import { applyDefaults } from "./defaults";
import pino from "pino";

export const logger = pino({ name: "computer" });

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
  ): BaseComputer {
    // Apply defaults to the configuration
    const fullConfig = applyDefaults(config);

    // Check the vmProvider property to determine which type of computer to create
    switch (fullConfig.vmProvider) {
      case VMProviderType.CLOUD:
        return new CloudComputer(fullConfig as CloudComputerConfig);
      case VMProviderType.LUME:
        return new LumeComputer(fullConfig as LumeComputerConfig);
      default:
        throw new Error(
          `Unsupported VM provider type: ${fullConfig.vmProvider}`
        );
    }

    throw new Error(`Unsupported VM provider type`);
  }
}
