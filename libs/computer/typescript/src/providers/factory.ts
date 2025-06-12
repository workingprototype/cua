/**
 * Factory for creating VM providers.
 */

import type { BaseVMProvider } from './base';
import { VMProviderType } from './base';

export interface VMProviderOptions {
  port?: number;
  host?: string;
  binPath?: string;
  storage?: string;
  sharedPath?: string;
  image?: string;
  verbose?: boolean;
  ephemeral?: boolean;
  noVNCPort?: number;
  [key: string]: any; // Allow additional provider-specific options
}

export class VMProviderFactory {
  /**
   * Create a VM provider instance based on the provider type.
   * 
   * @param providerType The type of provider to create
   * @param options Provider-specific options
   * @returns The created VM provider instance
   * @throws Error if the provider type is not supported or dependencies are missing
   */
  static async createProvider(
    providerType: VMProviderType | string,
    options: VMProviderOptions = {}
  ): Promise<BaseVMProvider> {
    // Convert string to enum if needed
    let type: VMProviderType;
    if (typeof providerType === 'string') {
      const normalizedType = providerType.toLowerCase();
      if (Object.values(VMProviderType).includes(normalizedType as VMProviderType)) {
        type = normalizedType as VMProviderType;
      } else {
        type = VMProviderType.UNKNOWN;
      }
    } else {
      type = providerType;
    }

    // Extract common options with defaults
    const {
      port = 7777,
      host = 'localhost',
      binPath,
      storage,
      sharedPath,
      image,
      verbose = false,
      ephemeral = false,
      noVNCPort,
      ...additionalOptions
    } = options;

    switch (type) {
      case VMProviderType.LUME: {
        try {
          // Dynamic import for Lume provider
          const { LumeProvider, HAS_LUME } = await import('./lume');
          
          if (!HAS_LUME) {
            throw new Error(
              'The required dependencies for LumeProvider are not available. ' +
              'Please ensure curl is installed and in your PATH.'
            );
          }
          
          return new LumeProvider({
            port,
            host,
            storage,
            verbose,
            ephemeral
          });
        } catch (error) {
          if (error instanceof Error && error.message.includes('Cannot find module')) {
            throw new Error(
              'The LumeProvider module is not available. ' +
              'Please install it with: npm install @cua/computer-lume'
            );
          }
          throw error;
        }
      }

      case VMProviderType.LUMIER: {
        try {
          // Dynamic import for Lumier provider
          const { LumierProvider, HAS_LUMIER } = await import('./lumier');
          
          if (!HAS_LUMIER) {
            throw new Error(
              'Docker is required for LumierProvider. ' +
              'Please install Docker for Apple Silicon and Lume CLI before using this provider.'
            );
          }
          
          return new LumierProvider({
            port,
            host,
            storage,
            sharedPath,
            image: image || 'macos-sequoia-cua:latest',
            verbose,
            ephemeral,
            noVNCPort
          });
        } catch (error) {
          if (error instanceof Error && error.message.includes('Cannot find module')) {
            throw new Error(
              'The LumierProvider module is not available. ' +
              'Docker and Lume CLI are required for LumierProvider. ' +
              'Please install Docker for Apple Silicon and run the Lume installer script.'
            );
          }
          throw error;
        }
      }

      case VMProviderType.CLOUD: {
        try {
          // Dynamic import for Cloud provider
          const { CloudProvider } = await import('./cloud');
          
          return new CloudProvider({
            verbose,
            ...additionalOptions
          });
        } catch (error) {
          if (error instanceof Error && error.message.includes('Cannot find module')) {
            throw new Error(
              'The CloudProvider is not fully implemented yet. ' +
              'Please use LUME or LUMIER provider instead.'
            );
          }
          throw error;
        }
      }

      default:
        throw new Error(`Unsupported provider type: ${providerType}`);
    }
  }
}
