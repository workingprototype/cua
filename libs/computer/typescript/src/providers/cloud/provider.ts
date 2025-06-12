/**
 * Cloud VM provider implementation.
 * 
 * This provider is a placeholder for cloud-based VM provisioning.
 * It will be implemented to support cloud VM services in the future.
 */

import { BaseVMProviderImpl, VMProviderType } from '../base';

export interface CloudProviderOptions {
  verbose?: boolean;
  apiKey?: string;
  region?: string;
  [key: string]: any;
}

export class CloudProvider extends BaseVMProviderImpl {
  readonly providerType = VMProviderType.CLOUD;
  
  private verbose: boolean;
  private options: CloudProviderOptions;
  
  constructor(options: CloudProviderOptions = {}) {
    super();
    this.verbose = options.verbose || false;
    this.options = options;
  }
  
  // TODO: Implement getVM for cloud provider
  async getVM(name: string, storage?: string): Promise<Record<string, any>> {
    throw new Error('CloudProvider is not fully implemented yet. Please use LUME or LUMIER provider instead.');
  }
  
  // TODO: Implement listVMs for cloud provider
  async listVMs(): Promise<Array<Record<string, any>>> {
    throw new Error('CloudProvider is not fully implemented yet. Please use LUME or LUMIER provider instead.');
  }
  
  // TODO: Implement runVM for cloud provider
  async runVM(
    image: string,
    name: string,
    runOpts: Record<string, any>,
    storage?: string
  ): Promise<Record<string, any>> {
    throw new Error('CloudProvider is not fully implemented yet. Please use LUME or LUMIER provider instead.');
  }
  
  // TODO: Implement stopVM for cloud provider
  async stopVM(name: string, storage?: string): Promise<void> {
    throw new Error('CloudProvider is not fully implemented yet. Please use LUME or LUMIER provider instead.');
  }
  
  // TODO: Implement getIP for cloud provider
  async getIP(name: string, storage?: string, retryDelay?: number): Promise<string> {
    throw new Error('CloudProvider is not fully implemented yet. Please use LUME or LUMIER provider instead.');
  }
  
  // TODO: Implement updateVM for cloud provider
  async updateVM(
    name: string,
    cpu?: number,
    memory?: string,
    storage?: string
  ): Promise<void> {
    throw new Error('CloudProvider is not fully implemented yet. Please use LUME or LUMIER provider instead.');
  }
}
