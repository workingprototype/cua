import type { BaseComputerInterface } from './base';
import type { OSType } from '../computer';

export interface InterfaceOptions {
  ipAddress: string;
  apiKey?: string;
  vmName?: string;
}

/**
 * Factory for creating OS-specific computer interfaces.
 */
export class InterfaceFactory {
  /**
   * Create an interface for the specified OS.
   * 
   * @param os The operating system type ('macos', 'linux', 'windows')
   * @param ipAddress The IP address to connect to
   * @param apiKey Optional API key for cloud providers
   * @param vmName Optional VM name for cloud providers
   * @returns An instance of the appropriate computer interface
   */
  static createInterfaceForOS(
    os: OSType,
    ipAddress: string,
    apiKey?: string,
    vmName?: string
  ): BaseComputerInterface {
    const options: InterfaceOptions = {
      ipAddress,
      apiKey,
      vmName
    };

    switch (os) {
      case 'macos':
        // Dynamic import would be used in real implementation
        // TODO: Implement macOS interface
        throw new Error('macOS interface not yet implemented');
        
      case 'linux':
        // Dynamic import would be used in real implementation
        // TODO: Implement Linux interface
        throw new Error('Linux interface not yet implemented');
        
      case 'windows':
        // Dynamic import would be used in real implementation
        // TODO: Implement Windows interface
        throw new Error('Windows interface not yet implemented');
        
      default:
        // TODO: Implement interface for this OS
        throw new Error(`Interface for OS ${os} not implemented`);
    }
  }
}
