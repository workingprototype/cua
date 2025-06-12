/**
 * Helper functions and decorators for the Computer module.
 */

import type { Computer } from './computer';

// Global reference to the default computer instance
let _defaultComputer: Computer | null = null;

/**
 * Set the default computer instance to be used by the remote decorator.
 * 
 * @param computer The computer instance to use as default
 */
export function setDefaultComputer(computer: Computer): void {
  _defaultComputer = computer;
}

/**
 * Get the default computer instance.
 * 
 * @returns The default computer instance or null
 */
export function getDefaultComputer(): Computer | null {
  return _defaultComputer;
}

/**
 * Decorator that wraps a function to be executed remotely via computer.venvExec
 * 
 * @param venvName Name of the virtual environment to execute in
 * @param computer The computer instance to use, or "default" to use the globally set default
 * @param maxRetries Maximum number of retries for the remote execution
 */
export function sandboxed(
  venvName: string = 'default',
  computer: Computer | 'default' = 'default',
  maxRetries: number = 3
) {
  return function <T extends (...args: any[]) => any>(
    target: any,
    propertyKey: string,
    descriptor: PropertyDescriptor
  ) {
    const originalMethod = descriptor.value;

    descriptor.value = async function (...args: Parameters<T>): Promise<ReturnType<T>> {
      // Determine which computer instance to use
      const comp = computer === 'default' ? _defaultComputer : computer;

      if (!comp) {
        throw new Error(
          'No computer instance available. Either specify a computer instance or call setDefaultComputer() first.'
        );
      }

      for (let i = 0; i < maxRetries; i++) {
        try {
          return await comp.venvExec(venvName, originalMethod, ...args);
        } catch (error) {
          console.error(`Attempt ${i + 1} failed:`, error);
          if (i < maxRetries - 1) {
            await new Promise(resolve => setTimeout(resolve, 1000));
          } else {
            throw error;
          }
        }
      }
      
      // This should never be reached, but satisfies TypeScript's control flow analysis
      throw new Error('Unexpected: maxRetries loop completed without returning or throwing');
    };

    return descriptor;
  };
}
