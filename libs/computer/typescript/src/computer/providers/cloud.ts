import { BaseComputer } from "./base";
import type { CloudComputerConfig, VMProviderType } from "../types";
import {
  InterfaceFactory,
  type BaseComputerInterface,
} from "../../interface/index";
import pino from "pino";

const logger = pino({ name: "computer-cloud" });

/**
 * Cloud-specific computer implementation
 */
export class CloudComputer extends BaseComputer {
  protected apiKey: string;
  protected static vmProviderType: VMProviderType.CLOUD;
  private interface?: BaseComputerInterface;
  private initialized = false;

  constructor(config: CloudComputerConfig) {
    super(config);
    this.apiKey = config.apiKey;
  }

  get ip() {
    return `${this.name}.containers.cloud.trycua.com`;
  }

  /**
   * Initialize the cloud VM and interface
   */
  async run(): Promise<void> {
    if (this.initialized) {
      logger.info("Computer already initialized, skipping initialization");
      return;
    }

    logger.info("Starting cloud computer...");

    try {
      // For cloud provider, the VM is already running, we just need to connect
      const ipAddress = this.ip;
      logger.info(`Connecting to cloud VM at ${ipAddress}`);

      // Create the interface with API key authentication
      this.interface = InterfaceFactory.createInterfaceForOS(
        this.osType,
        ipAddress,
        this.apiKey,
        this.name
      );

      // Wait for the interface to be ready
      logger.info("Waiting for interface to be ready...");
      await this.interface.waitForReady();

      this.initialized = true;
      logger.info("Cloud computer ready");
    } catch (error) {
      logger.error(`Failed to initialize cloud computer: ${error}`);
      throw new Error(`Failed to initialize cloud computer: ${error}`);
    }
  }

  /**
   * Stop the cloud computer (disconnect interface)
   */
  async stop(): Promise<void> {
    logger.info("Stopping cloud computer...");

    if (this.interface) {
      this.interface.disconnect();
      this.interface = undefined;
    }

    this.initialized = false;
    logger.info("Cloud computer stopped");
  }

  /**
   * Get the computer interface
   */
  getInterface(): BaseComputerInterface {
    if (!this.interface) {
      throw new Error("Computer not initialized. Call run() first.");
    }
    return this.interface;
  }

  /**
   * Take a screenshot
   */
  async screenshot(): Promise<Buffer> {
    return this.getInterface().screenshot();
  }

  /**
   * Click at coordinates
   */
  async click(x?: number, y?: number): Promise<void> {
    return this.getInterface().leftClick(x, y);
  }

  /**
   * Type text
   */
  async type(text: string): Promise<void> {
    return this.getInterface().typeText(text);
  }

  /**
   * Press a key
   */
  async key(key: string): Promise<void> {
    return this.getInterface().pressKey(key);
  }

  /**
   * Press hotkey combination
   */
  async hotkey(...keys: string[]): Promise<void> {
    return this.getInterface().hotkey(...keys);
  }

  /**
   * Run a command
   */
  async runCommand(command: string): Promise<[string, string]> {
    return this.getInterface().runCommand(command);
  }

  /**
   * Disconnect from the cloud computer
   */
  async disconnect(): Promise<void> {
    await this.stop();
  }
}
