import type { Display, ComputerConfig } from "../types";
import type { BaseComputerInterface } from "../interface/base";
import { InterfaceFactory } from "../interface/factory";
import type { BaseVMProvider } from "../providers/base";
import { VMProviderType } from "../providers/base";
import { VMProviderFactory } from "../providers/factory";
import pino from "pino";
import {
  recordComputerInitialization,
  recordVMStart,
  recordVMStop,
} from "../telemetry";
import { setDefaultComputer } from "../helpers";
import {
  parseDisplayString,
  parseImageString,
  sleep,
  withTimeout,
} from "../utils";
import sharp from "sharp";

export type OSType = "macos" | "linux" | "windows";

export interface ComputerOptions {
  display?: Display | { width: number; height: number } | string;
  memory?: string;
  cpu?: string;
  osType?: OSType;
  name?: string;
  image?: string;
  sharedDirectories?: string[];
  useHostComputerServer?: boolean;
  verbosity?: pino.Level;
  telemetryEnabled?: boolean;
  providerType?: VMProviderType | string;
  port?: number;
  noVNCPort?: number;
  host?: string;
  storage?: string;
  ephemeral?: boolean;
  apiKey?: string;
  experiments?: string[];
}

/**
 * Computer is the main class for interacting with the computer.
 */
export class Computer {
  private logger: pino.Logger;

  private image: string;
  private port?: number;
  private noVNCPort?: number;
  private host: string;
  private osType: OSType;
  private providerType: VMProviderType | string;
  private ephemeral: boolean;
  private apiKey?: string;
  private experiments: string[];
  private storage?: string;
  private sharedPath?: string;
  private sharedDirectories: string[];
  private _telemetryEnabled: boolean;
  private _initialized: boolean = false;
  private _running: boolean = false;

  private useHostComputerServer: boolean;
  private config?: ComputerConfig;
  private _providerContext?: BaseVMProvider;
  private _interface?: BaseComputerInterface;
  private _stopEvent?: Promise<void>;
  private _keepAliveTask?: Promise<void>;

  /**
   * Initialize a new Computer instance.
   *
   * @param options Configuration options for the Computer
   */
  constructor(options: ComputerOptions = {}) {
    const {
      display = "1024x768",
      memory = "8GB",
      cpu = "4",
      osType = "macos",
      name = "",
      image = "macos-sequoia-cua:latest",
      sharedDirectories = [],
      useHostComputerServer = false,
      verbosity = "info",
      telemetryEnabled = true,
      providerType = VMProviderType.LUME,
      port = 7777,
      noVNCPort = 8006,
      host = process.env.PYLUME_HOST || "localhost",
      storage,
      ephemeral = false,
      apiKey,
      experiments = [],
    } = options;

    this.logger = pino({ name: "cua.computer", level: verbosity });
    this.logger.info("Initializing Computer...");

    // Store original parameters
    this.image = image;
    this.port = port;
    this.noVNCPort = noVNCPort;
    this.host = host;
    this.osType = osType;
    this.providerType = providerType;
    this.ephemeral = ephemeral;
    this.apiKey = apiKey;
    this.experiments = experiments;

    if (this.experiments.includes("app-use")) {
      if (this.osType !== "macos") {
        throw new Error("App use experiment is only supported on macOS");
      }
    }

    // The default is currently to use non-ephemeral storage
    if (storage && ephemeral && storage !== "ephemeral") {
      throw new Error(
        "Storage path and ephemeral flag cannot be used together"
      );
    }
    this.storage = ephemeral ? "ephemeral" : storage;

    // For Lumier provider, store the first shared directory path to use
    // for VM file sharing
    this.sharedPath = undefined;
    if (sharedDirectories && sharedDirectories.length > 0) {
      this.sharedPath = sharedDirectories[0];
      this.logger.info(
        `Using first shared directory for VM file sharing: ${this.sharedPath}`
      );
    }

    // Store telemetry preference
    this._telemetryEnabled = telemetryEnabled;

    this.useHostComputerServer = useHostComputerServer;

    if (!useHostComputerServer) {
      const imageInfo = parseImageString(image);

      const vmName = name || image.replace(":", "_");

      // Convert display parameter to Display object
      let displayConfig: Display;
      if (typeof display === "string") {
        const { width, height } = parseDisplayString(display);
        displayConfig = { width, height };
      } else if ("width" in display && "height" in display) {
        displayConfig = display as Display;
      } else {
        displayConfig = display as Display;
      }

      this.config = {
        image: imageInfo.name,
        tag: imageInfo.tag,
        name: vmName,
        display: displayConfig,
        memory,
        cpu,
      };
    }

    // Store shared directories config
    this.sharedDirectories = sharedDirectories;

    // Record initialization in telemetry (if enabled)
    if (telemetryEnabled) {
      recordComputerInitialization();
    } else {
      this.logger.debug(
        "Telemetry disabled - skipping initialization tracking"
      );
    }
  }

  /**
   * Create a virtual desktop from a list of app names, returning a DioramaComputer
   * that proxies Diorama.Interface but uses diorama_cmds via the computer interface.
   *
   * @param apps List of application names to include in the desktop.
   * @returns A proxy object with the Diorama interface, but using diorama_cmds.
   */
  createDesktopFromApps(apps: string[]): any {
    if (!this.experiments.includes("app-use")) {
      throw new Error(
        "App Usage is an experimental feature. Enable it by passing experiments=['app-use'] to Computer()"
      );
    }
    // DioramaComputer would be imported and used here
    throw new Error("DioramaComputer not yet implemented");
  }

  /**
   * Start the computer (async context manager enter).
   */
  async __aenter__(): Promise<this> {
    await this.run();
    return this;
  }

  /**
   * Stop the computer (async context manager exit).
   */
  async __aexit__(excType: any, excVal: any, excTb: any): Promise<void> {
    await this.disconnect();
  }

  /**
   * Initialize the VM and computer interface.
   */
  async run(): Promise<string | undefined> {
    // If already initialized, just log and return
    if (this._initialized) {
      this.logger.info("Computer already initialized, skipping initialization");
      return;
    }

    this.logger.info("Starting computer...");
    const startTime = Date.now();

    try {
      let ipAddress: string;

      // If using host computer server
      if (this.useHostComputerServer) {
        this.logger.info("Using host computer server");
        ipAddress = "localhost";

        // Create the interface
        this._interface = InterfaceFactory.createInterfaceForOS(
          this.osType,
          ipAddress
        );

        this.logger.info("Waiting for host computer server to be ready...");
        await this._interface.waitForReady();
        this.logger.info("Host computer server ready");
      } else {
        // Start or connect to VM
        this.logger.info(`Starting VM: ${this.image}`);

        if (!this._providerContext) {
          try {
            const providerTypeName =
              typeof this.providerType === "object"
                ? this.providerType
                : this.providerType;

            this.logger.info(
              `Initializing ${providerTypeName} provider context...`
            );

            // Create VM provider instance with explicit parameters
            const providerOptions = {
              port: this.port,
              host: this.host,
              storage: this.storage,
              sharedPath: this.sharedPath,
              image: this.image,
              verbose:
                this.logger.level === "debug" || this.logger.level === "trace",
              ephemeral: this.ephemeral,
              noVNCPort: this.noVNCPort,
              apiKey: this.apiKey,
            };

            if (!this.config) {
              throw new Error("Computer config not initialized");
            }

            this.config.vm_provider = await VMProviderFactory.createProvider(
              this.providerType,
              providerOptions
            );

            this._providerContext = await this.config.vm_provider.__aenter__();
            this.logger.debug("VM provider context initialized successfully");
          } catch (error) {
            this.logger.error(
              `Failed to import provider dependencies: ${error}`
            );
            throw error;
          }
        }

        // Run the VM
        if (!this.config || !this.config.vm_provider) {
          throw new Error("VM provider not initialized");
        }

        const runOpts = {
          display: this.config.display,
          memory: this.config.memory,
          cpu: this.config.cpu,
          shared_directories: this.sharedDirectories,
        };

        this.logger.info(
          `Running VM ${this.config.name} with options:`,
          runOpts
        );

        if (this._telemetryEnabled) {
          recordVMStart(this.config.name, String(this.providerType));
        }

        const storageParam = this.ephemeral ? "ephemeral" : this.storage;

        try {
          await this.config.vm_provider.runVM(
            this.image,
            this.config.name,
            runOpts,
            storageParam
          );
        } catch (error: any) {
          if (error.message?.includes("already running")) {
            this.logger.info(`VM ${this.config.name} is already running`);
          } else {
            throw error;
          }
        }

        // Wait for VM to be ready
        try {
          this.logger.info("Waiting for VM to be ready...");
          await this.waitVMReady();

          // Get IP address
          ipAddress = await this.getIP();
          this.logger.info(`VM is ready with IP: ${ipAddress}`);
        } catch (error) {
          this.logger.error(`Error waiting for VM: ${error}`);
          throw new Error(`VM failed to become ready: ${error}`);
        }
      }

      // Initialize the interface
      try {
        // Verify we have a valid IP before initializing the interface
        if (!ipAddress || ipAddress === "unknown" || ipAddress === "0.0.0.0") {
          throw new Error(
            `Cannot initialize interface - invalid IP address: ${ipAddress}`
          );
        }

        this.logger.info(
          `Initializing interface for ${this.osType} at ${ipAddress}`
        );

        // Pass authentication credentials if using cloud provider
        if (
          this.providerType === VMProviderType.CLOUD &&
          this.apiKey &&
          this.config?.name
        ) {
          this._interface = InterfaceFactory.createInterfaceForOS(
            this.osType,
            ipAddress,
            this.apiKey,
            this.config.name
          );
        } else {
          this._interface = InterfaceFactory.createInterfaceForOS(
            this.osType,
            ipAddress
          );
        }

        // Wait for the WebSocket interface to be ready
        this.logger.info("Connecting to WebSocket interface...");

        try {
          await withTimeout(
            this._interface.waitForReady(),
            30000,
            `Could not connect to WebSocket interface at ${ipAddress}:8000/ws`
          );
          this.logger.info("WebSocket interface connected successfully");
        } catch (error) {
          this.logger.error(
            `Failed to connect to WebSocket interface at ${ipAddress}`
          );
          throw error;
        }

        // Create an event to keep the VM running in background if needed
        if (!this.useHostComputerServer) {
          // In TypeScript, we'll use a Promise instead of asyncio.Event
          let resolveStop: () => void;
          this._stopEvent = new Promise<void>((resolve) => {
            resolveStop = resolve;
          });
          this._keepAliveTask = this._stopEvent;
        }

        this.logger.info("Computer is ready");

        // Set the initialization flag
        this._initialized = true;

        // Set this instance as the default computer for remote decorators
        setDefaultComputer(this);

        this.logger.info("Computer successfully initialized");
      } catch (error) {
        throw error;
      } finally {
        // Log initialization time for performance monitoring
        const durationMs = Date.now() - startTime;
        this.logger.debug(
          `Computer initialization took ${durationMs.toFixed(2)}ms`
        );
      }
    } catch (error) {
      this.logger.error(`Failed to initialize computer: ${error}`);
      throw new Error(`Failed to initialize computer: ${error}`);
    }

    return;
  }

  /**
   * Disconnect from the computer's WebSocket interface.
   */
  async disconnect(): Promise<void> {
    if (this._interface) {
      // Note: The interface close method would need to be implemented
      // this._interface.close();
    }
  }

  /**
   * Disconnect from the computer's WebSocket interface and stop the computer.
   */
  async stop(): Promise<void> {
    const startTime = Date.now();

    try {
      this.logger.info("Stopping Computer...");

      // In VM mode, first explicitly stop the VM, then exit the provider context
      if (
        !this.useHostComputerServer &&
        this._providerContext &&
        this.config?.vm_provider
      ) {
        try {
          this.logger.info(`Stopping VM ${this.config.name}...`);
          await this.config.vm_provider.stopVM(this.config.name, this.storage);
        } catch (error) {
          this.logger.error(`Error stopping VM: ${error}`);
        }

        this.logger.info("Closing VM provider context...");
        await this.config.vm_provider.__aexit__(null, null, null);
        this._providerContext = undefined;
      }

      await this.disconnect();
      this.logger.info("Computer stopped");
    } catch (error) {
      this.logger.debug(`Error during cleanup: ${error}`);
    } finally {
      // Log stop time for performance monitoring
      const durationMs = Date.now() - startTime;
      this.logger.debug(
        `Computer stop process took ${durationMs.toFixed(2)}ms`
      );

      if (this._telemetryEnabled && this.config?.name) {
        recordVMStop(this.config.name, durationMs);
      }
    }
  }

  /**
   * Get the IP address of the VM or localhost if using host computer server.
   */
  async getIP(
    maxRetries: number = 15,
    retryDelay: number = 2
  ): Promise<string> {
    // For host computer server, always return localhost immediately
    if (this.useHostComputerServer) {
      return "127.0.0.1";
    }

    // Get IP from the provider
    if (!this.config?.vm_provider) {
      throw new Error("VM provider is not initialized");
    }

    // Log that we're waiting for the IP
    this.logger.info(
      `Waiting for VM ${this.config.name} to get an IP address...`
    );

    // Call the provider's get_ip method which will wait indefinitely
    const storageParam = this.ephemeral ? "ephemeral" : this.storage;

    // Log the image being used
    this.logger.info(`Running VM using image: ${this.image}`);

    // Call provider.getIP with explicit parameters
    const ip = await this.config.vm_provider.getIP(
      this.config.name,
      storageParam,
      retryDelay
    );

    // Log success
    this.logger.info(`VM ${this.config.name} has IP address: ${ip}`);
    return ip;
  }

  /**
   * Wait for VM to be ready with an IP address.
   */
  async waitVMReady(): Promise<Record<string, any> | undefined> {
    if (this.useHostComputerServer) {
      return undefined;
    }

    const timeout = 600; // 10 minutes timeout
    const interval = 2.0; // 2 seconds between checks
    const startTime = Date.now() / 1000;
    let lastStatus: string | undefined;
    let attempts = 0;

    this.logger.info(
      `Waiting for VM ${this.config?.name} to be ready (timeout: ${timeout}s)...`
    );

    while (Date.now() / 1000 - startTime < timeout) {
      attempts++;
      const elapsed = Date.now() / 1000 - startTime;

      try {
        // Keep polling for VM info
        if (!this.config?.vm_provider) {
          this.logger.error("VM provider is not initialized");
          return undefined;
        }

        const vm = await this.config.vm_provider.getVM(this.config.name);

        // Log full VM properties for debugging (every 30 attempts)
        if (attempts % 30 === 0) {
          this.logger.info(
            `VM properties at attempt ${attempts}: ${JSON.stringify(vm)}`
          );
        }

        // Get current status for logging
        const currentStatus = vm?.status;
        if (currentStatus !== lastStatus) {
          this.logger.info(
            `VM status changed to: ${currentStatus} (after ${elapsed.toFixed(
              1
            )}s)`
          );
          lastStatus = currentStatus;
        }

        // Check if VM is ready
        if (
          vm &&
          vm.status === "running" &&
          vm.ip_address &&
          vm.ip_address !== "0.0.0.0"
        ) {
          this.logger.info(
            `VM ${this.config.name} is ready with IP: ${vm.ip_address}`
          );
          return vm;
        }

        // Wait before next check
        await sleep(interval * 1000);
      } catch (error) {
        this.logger.error(`Error checking VM status: ${error}`);
        await sleep(interval * 1000);
      }
    }

    throw new Error(
      `VM ${this.config?.name} failed to become ready within ${timeout} seconds`
    );
  }

  /**
   * Update VM settings.
   */
  async update(cpu?: number, memory?: string): Promise<void> {
    if (this.useHostComputerServer) {
      this.logger.warn("Cannot update settings for host computer server");
      return;
    }

    if (!this.config?.vm_provider) {
      throw new Error("VM provider is not initialized");
    }

    await this.config.vm_provider.updateVM(
      this.config.name,
      cpu,
      memory,
      this.storage
    );
  }

  /**
   * Get the dimensions of a screenshot.
   */
  async getScreenshotSize(
    screenshot: Buffer
  ): Promise<{ width: number; height: number }> {
    const metadata = await sharp(screenshot).metadata();
    return {
      width: metadata.width || 0,
      height: metadata.height || 0,
    };
  }

  /**
   * Get the computer interface for interacting with the VM.
   */
  get interface(): BaseComputerInterface {
    if (!this._interface) {
      throw new Error("Computer interface not initialized. Call run() first.");
    }
    return this._interface;
  }

  /**
   * Check if telemetry is enabled for this computer instance.
   */
  get telemetryEnabled(): boolean {
    return this._telemetryEnabled;
  }

  /**
   * Convert normalized coordinates to screen coordinates.
   */
  toScreenCoordinates(x: number, y: number): [number, number] {
    if (!this.config?.display) {
      throw new Error("Display configuration not available");
    }
    return [x * this.config.display.width, y * this.config.display.height];
  }

  /**
   * Convert screen coordinates to screenshot coordinates.
   */
  async toScreenshotCoordinates(
    x: number,
    y: number
  ): Promise<[number, number]> {
    // In the Python version, this uses the interface to get screenshot dimensions
    // For now, we'll assume 1:1 mapping
    return [x, y];
  }

  /**
   * Install packages in a virtual environment.
   */
  async venvInstall(
    venvName: string,
    requirements: string[]
  ): Promise<[string, string]> {
    // This would be implemented using the interface to run commands
    // TODO: Implement venvInstall
    throw new Error("venvInstall not yet implemented");
  }

  /**
   * Execute a shell command in a virtual environment.
   */
  async venvCmd(venvName: string, command: string): Promise<[string, string]> {
    // This would be implemented using the interface to run commands
    // TODO: Implement venvCmd
    throw new Error("venvCmd not yet implemented");
  }

  /**
   * Execute function in a virtual environment using source code extraction.
   */
  async venvExec(
    venvName: string,
    pythonFunc: Function,
    ...args: any[]
  ): Promise<any> {
    // This would be implemented using the interface to run Python code
    // TODO: Implement venvExec
    throw new Error("venvExec not yet implemented");
  }
}
