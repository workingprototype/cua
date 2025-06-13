/**
 * Display configuration for the computer.
 */
export interface Display {
  width: number;
  height: number;
  scale_factor?: number;
}

/**
 * Computer configuration model.
 */
export interface ComputerConfig {
  image: string;
  tag: string;
  name: string;
  display: Display;
  memory: string;
  cpu: string;
  vm_provider?: any; // Will be properly typed when implemented
}
