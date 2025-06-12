/**
 * Types of VM providers available.
 */
export enum VMProviderType {
  LUME = 'lume',
  LUMIER = 'lumier',
  CLOUD = 'cloud',
  UNKNOWN = 'unknown'
}

/**
 * Base interface for VM providers.
 * All VM provider implementations must implement this interface.
 */
export interface BaseVMProvider {
  /**
   * Get the provider type.
   */
  readonly providerType: VMProviderType;

  /**
   * Get VM information by name.
   * 
   * @param name Name of the VM to get information for
   * @param storage Optional storage path override
   * @returns Dictionary with VM information including status, IP address, etc.
   */
  getVM(name: string, storage?: string): Promise<Record<string, any>>;

  /**
   * List all available VMs.
   */
  listVMs(): Promise<Array<Record<string, any>>>;

  /**
   * Run a VM by name with the given options.
   * 
   * @param image VM image to run
   * @param name Name for the VM
   * @param runOpts Run options for the VM
   * @param storage Optional storage path
   * @returns VM run response
   */
  runVM(
    image: string,
    name: string,
    runOpts: Record<string, any>,
    storage?: string
  ): Promise<Record<string, any>>;

  /**
   * Stop a VM by name.
   * 
   * @param name Name of the VM to stop
   * @param storage Optional storage path
   */
  stopVM(name: string, storage?: string): Promise<void>;

  /**
   * Get the IP address of a VM.
   * 
   * @param name Name of the VM
   * @param storage Optional storage path
   * @param retryDelay Delay between retries in seconds
   * @returns IP address of the VM
   */
  getIP(name: string, storage?: string, retryDelay?: number): Promise<string>;

  /**
   * Update VM settings.
   * 
   * @param name Name of the VM
   * @param cpu New CPU allocation
   * @param memory New memory allocation
   * @param storage Optional storage path
   */
  updateVM(
    name: string,
    cpu?: number,
    memory?: string,
    storage?: string
  ): Promise<void>;

  /**
   * Context manager enter method
   */
  __aenter__(): Promise<this>;

  /**
   * Context manager exit method
   */
  __aexit__(
    excType: any,
    excVal: any,
    excTb: any
  ): Promise<void>;
}

/**
 * Abstract base class for VM providers that implements context manager
 */
export abstract class BaseVMProviderImpl implements BaseVMProvider {
  abstract readonly providerType: VMProviderType;
  
  abstract getVM(name: string, storage?: string): Promise<Record<string, any>>;
  abstract listVMs(): Promise<Array<Record<string, any>>>;
  abstract runVM(
    image: string,
    name: string,
    runOpts: Record<string, any>,
    storage?: string
  ): Promise<Record<string, any>>;
  abstract stopVM(name: string, storage?: string): Promise<void>;
  abstract getIP(name: string, storage?: string, retryDelay?: number): Promise<string>;
  abstract updateVM(
    name: string,
    cpu?: number,
    memory?: string,
    storage?: string
  ): Promise<void>;

  async __aenter__(): Promise<this> {
    // Default implementation - can be overridden
    return this;
  }

  /**
    * Async context manager exit.
    * 
    * This method is called when exiting an async context manager block.
    * It handles proper cleanup of resources, including stopping any running containers.
  */
  async __aexit__(
    _excType: any,
    _excVal: any,
    _excTb: any
  ): Promise<void> {
    // Default implementation - can be overridden
  }
}
