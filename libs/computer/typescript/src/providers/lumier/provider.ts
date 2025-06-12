/**
 * Lumier VM provider implementation.
 *
 * This provider uses Docker containers running the Lumier image to create
 * macOS and Linux VMs. It handles VM lifecycle operations through Docker
 * commands and container management.
 */

import { exec } from "child_process";
import { promisify } from "util";
import { BaseVMProviderImpl, VMProviderType } from "../base";
import {
  lumeApiGet,
  lumeApiRun,
  lumeApiStop,
  lumeApiUpdate,
} from "../lume_api";

const execAsync = promisify(exec);

export interface LumierProviderOptions {
  port?: number;
  host?: string;
  storage?: string;
  sharedPath?: string;
  image?: string;
  verbose?: boolean;
  ephemeral?: boolean;
  noVNCPort?: number;
}

export class LumierProvider extends BaseVMProviderImpl {
  readonly providerType = VMProviderType.LUMIER;

  private host: string;
  private apiPort: number;
  private vncPort?: number;
  private ephemeral: boolean;
  private storage?: string;
  private sharedPath?: string;
  private image: string;
  private verbose: boolean;
  private containerName?: string;
  private containerId?: string;

  constructor(options: LumierProviderOptions = {}) {
    super();

    this.host = options.host || "localhost";
    this.apiPort = options.port || 7777;
    this.vncPort = options.noVNCPort;
    this.ephemeral = options.ephemeral || false;

    // Handle ephemeral storage
    if (this.ephemeral) {
      this.storage = "ephemeral";
    } else {
      this.storage = options.storage;
    }

    this.sharedPath = options.sharedPath;
    this.image = options.image || "macos-sequoia-cua:latest";
    this.verbose = options.verbose || false;
  }

  /**
   * Parse memory string to MB integer.
   */
  private parseMemory(memoryStr: string | number): number {
    if (typeof memoryStr === "number") {
      return memoryStr;
    }

    const match = memoryStr.match(/^(\d+)([A-Za-z]*)$/);
    if (match) {
      const value = parseInt(match[1] || "0");
      const unit = match[2]?.toUpperCase() || "";

      if (unit === "GB" || unit === "G") {
        return value * 1024;
      } else if (unit === "MB" || unit === "M" || unit === "") {
        return value;
      }
    }

    console.warn(
      `Could not parse memory string '${memoryStr}', using 8GB default`
    );
    return 8192; // Default to 8GB
  }

  /**
   * Check if a Docker container exists.
   */
  private async containerExists(name: string): Promise<boolean> {
    try {
      await execAsync(`docker inspect ${name}`);
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Get container status.
   */
  private async getContainerStatus(name: string): Promise<string> {
    try {
      const { stdout } = await execAsync(
        `docker inspect -f '{{.State.Status}}' ${name}`
      );
      return stdout.trim();
    } catch {
      return "not_found";
    }
  }

  /**
   * Start the Lumier container.
   */
  private async startContainer(
    name: string,
    cpu: number = 4,
    memory: string = "8GB",
    runOpts: Record<string, any> = {}
  ): Promise<void> {
    const memoryMB = this.parseMemory(memory);

    // Build Docker run command
    let dockerCmd = `docker run -d --name ${name}`;

    // Add resource limits
    dockerCmd += ` --cpus=${cpu}`;
    dockerCmd += ` --memory=${memoryMB}m`;

    // Add port mappings
    dockerCmd += ` -p ${this.apiPort}:7777`;
    if (this.vncPort) {
      dockerCmd += ` -p ${this.vncPort}:8006`;
    }

    // Add storage volume if not ephemeral
    if (this.storage && this.storage !== "ephemeral") {
      dockerCmd += ` -v ${this.storage}:/storage`;
    }

    // Add shared path if specified
    if (this.sharedPath) {
      dockerCmd += ` -v ${this.sharedPath}:/shared`;
    }

    // Add environment variables
    if (runOpts.env) {
      for (const [key, value] of Object.entries(runOpts.env)) {
        dockerCmd += ` -e ${key}=${value}`;
      }
    }

    // Add the image
    dockerCmd += ` ${this.image}`;

    if (this.verbose) {
      console.log(`Starting container with command: ${dockerCmd}`);
    }

    try {
      const { stdout } = await execAsync(dockerCmd);
      this.containerId = stdout.trim();
      this.containerName = name;
    } catch (error: any) {
      throw new Error(`Failed to start container: ${error.message}`);
    }
  }

  /**
   * Wait for the API to be ready.
   */
  private async waitForAPI(maxRetries: number = 30): Promise<void> {
    for (let i = 0; i < maxRetries; i++) {
      try {
        await lumeApiGet("", undefined, this.host, this.apiPort, false);
        return;
      } catch {
        if (i === maxRetries - 1) {
          throw new Error("API failed to become ready");
        }
        await new Promise((resolve) => setTimeout(resolve, 1000));
      }
    }
  }

  async getVM(name: string, storage?: string): Promise<Record<string, any>> {
    // First check if container exists
    const containerStatus = await this.getContainerStatus(
      this.containerName || name
    );

    if (containerStatus === "not_found") {
      throw new Error(`Container ${name} not found`);
    }

    // If container is not running, return basic status
    if (containerStatus !== "running") {
      return {
        name,
        status: containerStatus,
        ip: "",
        cpu: 0,
        memory: "0MB",
      };
    }

    // Get VM info from API
    return lumeApiGet(
      name,
      storage || this.storage,
      this.host,
      this.apiPort,
      this.verbose
    );
  }

  async listVMs(): Promise<Array<Record<string, any>>> {
    // Check if our container is running
    if (!this.containerName) {
      return [];
    }

    const containerStatus = await this.getContainerStatus(this.containerName);
    if (containerStatus !== "running") {
      return [];
    }

    // Get VMs from API
    const response = await lumeApiGet(
      "",
      this.storage,
      this.host,
      this.apiPort,
      this.verbose
    );

    if (Array.isArray(response)) {
      return response;
    }

    if (response.vms && Array.isArray(response.vms)) {
      return response.vms;
    }

    return [];
  }

  async runVM(
    image: string,
    name: string,
    runOpts: Record<string, any>,
    storage?: string
  ): Promise<Record<string, any>> {
    // Check if container already exists
    const exists = await this.containerExists(name);

    if (exists) {
      const status = await this.getContainerStatus(name);
      if (status === "running") {
        // Container already running, just run VM through API
        return lumeApiRun(
          image,
          name,
          runOpts,
          storage || this.storage,
          this.host,
          this.apiPort,
          this.verbose
        );
      } else {
        // Start existing container
        await execAsync(`docker start ${name}`);
      }
    } else {
      // Create and start new container
      await this.startContainer(
        name,
        runOpts.cpu || 4,
        runOpts.memory || "8GB",
        runOpts
      );
    }

    // Wait for API to be ready
    await this.waitForAPI();

    // Run VM through API
    return lumeApiRun(
      image,
      name,
      runOpts,
      storage || this.storage,
      this.host,
      this.apiPort,
      this.verbose
    );
  }

  async stopVM(name: string, storage?: string): Promise<void> {
    // First stop VM through API
    try {
      await lumeApiStop(
        name,
        storage || this.storage,
        this.host,
        this.apiPort,
        this.verbose
      );
    } catch (error) {
      if (this.verbose) {
        console.log(`Failed to stop VM through API: ${error}`);
      }
    }

    // Stop the container
    if (this.containerName) {
      try {
        await execAsync(`docker stop ${this.containerName}`);

        // Remove container if ephemeral
        if (this.ephemeral) {
          await execAsync(`docker rm ${this.containerName}`);
          if (this.verbose) {
            console.log(
              `Container ${this.containerName} stopped and removed (ephemeral mode)`
            );
          }
        }
      } catch (error: any) {
        throw new Error(`Failed to stop container: ${error.message}`);
      }
    }
  }

  async getIP(
    name: string,
    storage?: string,
    retryDelay: number = 1
  ): Promise<string> {
    const maxRetries = 30;

    for (let i = 0; i < maxRetries; i++) {
      try {
        const vmInfo = await this.getVM(name, storage);

        if (vmInfo.ip && vmInfo.ip !== "") {
          return vmInfo.ip;
        }

        if (vmInfo.status === "stopped" || vmInfo.status === "error") {
          throw new Error(`VM ${name} is in ${vmInfo.status} state`);
        }
      } catch (error) {
        if (i === maxRetries - 1) {
          throw error;
        }
      }

      await new Promise((resolve) => setTimeout(resolve, retryDelay * 1000));
    }

    throw new Error(
      `Failed to get IP for VM ${name} after ${maxRetries} retries`
    );
  }

  async updateVM(
    name: string,
    cpu?: number,
    memory?: string,
    storage?: string
  ): Promise<void> {
    await lumeApiUpdate(
      name,
      cpu,
      memory,
      storage || this.storage,
      this.host,
      this.apiPort,
      this.verbose
    );
  }

  async __aexit__(excType: any, excVal: any, excTb: any): Promise<void> {
    // Clean up container if ephemeral
    if (this.ephemeral && this.containerName) {
      try {
        await execAsync(`docker stop ${this.containerName}`);
        await execAsync(`docker rm ${this.containerName}`);
      } catch {
        // Ignore errors during cleanup
      }
    }
  }
}
