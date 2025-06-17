import { BaseComputer } from "./base";
import { applyDefaults } from "../defaults";
import type { Display, LumierComputerConfig } from "../types";
import { computerLogger } from "../../util/logger";

/**
 * Lumier-specific computer implementation
 */
export class LumierComputer extends BaseComputer {
  private display: string | Display;
  private memory: string;
  private cpu: number;
  private image: string;
  private sharedDirectories?: string[];
  private noVNCPort?: number;
  private storage?: string;
  private ephemeral: boolean;

  constructor(config: LumierComputerConfig) {
    super(config);

    const defaultConfig = applyDefaults(config);

    this.display = defaultConfig.display;
    this.memory = defaultConfig.memory;
    this.cpu = defaultConfig.cpu;
    this.image = defaultConfig.image;
    this.sharedDirectories = defaultConfig.sharedDirectories;
    this.noVNCPort = defaultConfig.noVNCPort;
    this.storage = defaultConfig.storage;
    this.ephemeral = defaultConfig.ephemeral;
  }

  /**
   * Lumier-specific method to start the container
   */
  async startContainer(): Promise<void> {
    computerLogger.info(
      `Starting Lumier container ${this.name} with ${this.memory} memory and ${this.cpu} CPUs`
    );
    computerLogger.info(
      `Using image ${this.image} with display ${
        typeof this.display === "string"
          ? this.display
          : `${this.display.width}x${this.display.height}`
      }`
    );
    // Lumier-specific implementation
  }

  /**
   * Lumier-specific method to execute a command in the container
   */
  async execCommand(command: string): Promise<string> {
    computerLogger.info(
      `Executing command in Lumier container ${this.name}: ${command}`
    );
    return "command output"; // Example implementation
  }
}
