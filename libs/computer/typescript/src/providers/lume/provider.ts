/**
 * Lume VM provider implementation using curl commands.
 * 
 * This provider uses direct curl commands to interact with the Lume API,
 * removing the dependency on the pylume Python package.
 */

import { BaseVMProviderImpl, VMProviderType } from '../base';
import type { LumeRunOptions } from '../lume_api';
import {
  HAS_CURL,
  lumeApiGet,
  lumeApiRun,
  lumeApiStop,
  lumeApiUpdate,
  lumeApiPull,
  parseMemory
} from '../lume_api';

export interface LumeProviderOptions {
  port?: number;
  host?: string;
  storage?: string;
  verbose?: boolean;
  ephemeral?: boolean;
}

export class LumeProvider extends BaseVMProviderImpl {
  readonly providerType = VMProviderType.LUME;
  
  private host: string;
  private port: number;
  private storage?: string;
  private verbose: boolean;
  private ephemeral: boolean;
  
  constructor(options: LumeProviderOptions = {}) {
    super();
    
    if (!HAS_CURL) {
      throw new Error(
        'curl is required for LumeProvider. ' +
        'Please ensure it is installed and in your PATH.'
      );
    }
    
    this.host = options.host || 'localhost';
    this.port = options.port || 7777;
    this.storage = options.storage;
    this.verbose = options.verbose || false;
    this.ephemeral = options.ephemeral || false;
  }
  
  async getVM(name: string, storage?: string): Promise<Record<string, any>> {
    return lumeApiGet(
      name,
      storage || this.storage,
      this.host,
      this.port,
      this.verbose
    );
  }
  
  async listVMs(): Promise<Array<Record<string, any>>> {
    const response = await lumeApiGet(
      '',
      this.storage,
      this.host,
      this.port,
      this.verbose
    );
    
    // The response should be an array of VMs
    if (Array.isArray(response)) {
      return response;
    }
    
    // If it's an object with a vms property
    if (response.vms && Array.isArray(response.vms)) {
      return response.vms;
    }
    
    // Otherwise return empty array
    return [];
  }
  
  async runVM(
    image: string,
    name: string,
    runOpts: LumeRunOptions,
    storage?: string
  ): Promise<Record<string, any>> {
    // Ensure the image is available
    if (this.verbose) {
      console.log(`Pulling image ${image} if needed...`);
    }
    
    try {
      await lumeApiPull(image, this.host, this.port, this.verbose);
    } catch (error) {
      if (this.verbose) {
        console.log(`Failed to pull image: ${error}`);
      }
    }
    
    // Run the VM
    return lumeApiRun(
      image,
      name,
      runOpts,
      storage || this.storage,
      this.host,
      this.port,
      this.verbose
    );
  }
  
  async stopVM(name: string, storage?: string): Promise<void> {
    await lumeApiStop(
      name,
      storage || this.storage,
      this.host,
      this.port,
      this.verbose
    );
    
    // If ephemeral, the VM should be automatically deleted after stopping
    if (this.ephemeral && this.verbose) {
      console.log(`VM ${name} stopped and removed (ephemeral mode)`);
    }
  }
  
  async getIP(name: string, storage?: string, retryDelay: number = 1): Promise<string> {
    const maxRetries = 30;
    let retries = 0;
    
    while (retries < maxRetries) {
      try {
        const vmInfo = await this.getVM(name, storage);
        
        if (vmInfo.ip && vmInfo.ip !== '') {
          return vmInfo.ip;
        }
        
        if (vmInfo.status === 'stopped' || vmInfo.status === 'error') {
          throw new Error(`VM ${name} is in ${vmInfo.status} state`);
        }
      } catch (error) {
        if (retries === maxRetries - 1) {
          throw error;
        }
      }
      
      retries++;
      await new Promise(resolve => setTimeout(resolve, retryDelay * 1000));
    }
    
    throw new Error(`Failed to get IP for VM ${name} after ${maxRetries} retries`);
  }
  
  async updateVM(
    name: string,
    cpu?: number,
    memory?: string,
    storage?: string
  ): Promise<void> {
    // Validate memory format if provided
    if (memory) {
      parseMemory(memory); // This will throw if invalid
    }
    
    await lumeApiUpdate(
      name,
      cpu,
      memory,
      storage || this.storage,
      this.host,
      this.port,
      this.verbose
    );
  }
}
