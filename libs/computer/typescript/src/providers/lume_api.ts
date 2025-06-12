/**
 * Lume API utilities for interacting with the Lume VM API.
 * This module provides low-level API functions used by the Lume provider.
 */

import { exec, execSync } from "child_process";
import { promisify } from "util";

const execAsync = promisify(exec);

export let HAS_CURL = false;

// Check for curl availability
try {
  execSync("which curl", { stdio: "ignore" });
  HAS_CURL = true;
} catch {
  HAS_CURL = false;
}

/**
 * Parse memory string to bytes.
 * Supports formats like "2GB", "512MB", "1024KB", etc.
 * Defaults to 1GB
 */
export function parseMemory(memory = "1GB"): number {
  const match = memory.match(/^(\d+(?:\.\d+)?)\s*([KMGT]?B?)$/i);
  if (!match) {
    throw new Error(`Invalid memory format: ${memory}`);
  }

  const value = parseFloat(match[1]!);
  const unit = match[2]!.toUpperCase();

  const multipliers: Record<string, number> = {
    B: 1,
    KB: 1024,
    MB: 1024 * 1024,
    GB: 1024 * 1024 * 1024,
    TB: 1024 * 1024 * 1024 * 1024,
    K: 1024,
    M: 1024 * 1024,
    G: 1024 * 1024 * 1024,
    T: 1024 * 1024 * 1024 * 1024,
  };

  return Math.floor(value * (multipliers[unit] || 1));
}

/**
 * Execute a curl command and return the result.
 */
async function executeCurl(
  command: string
): Promise<{ stdout: string; stderr: string }> {
  try {
    const { stdout, stderr } = await execAsync(command);
    return { stdout, stderr };
  } catch (error: any) {
    throw new Error(`Curl command failed: ${error.message}`);
  }
}

/**
 * Get VM information using Lume API.
 */
export async function lumeApiGet(
  vmName: string = "",
  storage?: string,
  host: string = "localhost",
  port: number = 7777,
  debug: boolean = false
): Promise<Record<string, any>> {
  let url = `http://${host}:${port}/vms`;
  if (vmName) {
    url += `/${encodeURIComponent(vmName)}`;
  }

  const params = new URLSearchParams();
  if (storage) {
    params.append("storage", storage);
  }

  if (params.toString()) {
    url += `?${params.toString()}`;
  }

  const command = `curl -s -X GET "${url}"`;

  if (debug) {
    console.log(`Executing: ${command}`);
  }

  const { stdout } = await executeCurl(command);

  try {
    return JSON.parse(stdout);
  } catch (error) {
    throw new Error(`Failed to parse API response: ${stdout}`);
  }
}

/**
 * Options for running a VM using the Lume API.
 */
export interface LumeRunOptions {
  /** CPU cores to allocate to the VM */
  cpu?: number;
  /** Memory to allocate to the VM (e.g., "8GB", "512MB") */
  memory?: string;
  /** Display configuration for the VM */
  display?: {
    width?: number;
    height?: number;
    dpi?: number;
    color_depth?: number;
  };
  /** Environment variables to set in the VM */
  env?: Record<string, string>;
  /** Directories to share with the VM */
  shared_directories?: Record<string, string>;
  /** Network configuration */
  network?: {
    type?: string;
    bridge?: string;
    nat?: boolean;
  };
  /** Whether to run the VM in headless mode */
  headless?: boolean;
  /** Whether to enable GPU acceleration */
  gpu?: boolean;
  /** Storage location for the VM */
  storage?: string;
  /** Custom VM configuration options */
  vm_options?: Record<string, any>;
  /** Additional provider-specific options */
  [key: string]: any;
}

/**
 * Run a VM using Lume API.
 */
export async function lumeApiRun(
  image: string,
  name: string,
  runOpts: LumeRunOptions,
  storage?: string,
  host: string = "localhost",
  port: number = 7777,
  debug: boolean = false
): Promise<Record<string, any>> {
  const url = `http://${host}:${port}/vms/run`;

  const body: LumeRunOptions = {
    image,
    name,
    ...runOpts,
  };

  if (storage) {
    body.storage = storage;
  }

  const command = `curl -s -X POST "${url}" -H "Content-Type: application/json" -d '${JSON.stringify(
    body
  )}'`;

  if (debug) {
    console.log(`Executing: ${command}`);
  }

  const { stdout } = await executeCurl(command);

  try {
    return JSON.parse(stdout);
  } catch (error) {
    throw new Error(`Failed to parse API response: ${stdout}`);
  }
}

/**
 * Stop a VM using Lume API.
 */
export async function lumeApiStop(
  vmName: string,
  storage?: string,
  host: string = "localhost",
  port: number = 7777,
  debug: boolean = false
): Promise<void> {
  const url = `http://${host}:${port}/vms/${encodeURIComponent(vmName)}/stop`;

  const params = new URLSearchParams();
  if (storage) {
    params.append("storage", storage);
  }

  const fullUrl = params.toString() ? `${url}?${params.toString()}` : url;
  const command = `curl -s -X POST "${fullUrl}"`;

  if (debug) {
    console.log(`Executing: ${command}`);
  }

  await executeCurl(command);
}

/**
 * Update VM settings using Lume API.
 */
export async function lumeApiUpdate(
  vmName: string,
  cpu?: number,
  memory?: string,
  storage?: string,
  host: string = "localhost",
  port: number = 7777,
  debug: boolean = false
): Promise<void> {
  const url = `http://${host}:${port}/vms/${encodeURIComponent(vmName)}/update`;

  const body: LumeRunOptions = {};
  if (cpu !== undefined) {
    body.cpu = cpu;
  }
  if (memory !== undefined) {
    body.memory = memory;
  }
  if (storage) {
    body.storage = storage;
  }

  const command = `curl -s -X POST "${url}" -H "Content-Type: application/json" -d '${JSON.stringify(
    body
  )}'`;

  if (debug) {
    console.log(`Executing: ${command}`);
  }

  await executeCurl(command);
}

/**
 * Pull a VM image using Lume API.
 */
export async function lumeApiPull(
  image: string,
  host: string = "localhost",
  port: number = 7777,
  debug: boolean = false
): Promise<void> {
  const url = `http://${host}:${port}/images/pull`;

  const body: LumeRunOptions = { image };
  const command = `curl -s -X POST "${url}" -H "Content-Type: application/json" -d '${JSON.stringify(
    body
  )}'`;

  if (debug) {
    console.log(`Executing: ${command}`);
  }

  await executeCurl(command);
}
