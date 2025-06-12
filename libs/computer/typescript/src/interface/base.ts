import type { KeyType, MouseButton, AccessibilityTree } from './models';

/**
 * Base interface for computer control implementations.
 */
export interface BaseComputerInterface {
  /**
   * Wait for the interface to be ready.
   */
  waitForReady(): Promise<void>;
  
  /**
   * Get a screenshot of the current screen.
   */
  getScreenshot(): Promise<Buffer>;
  
  /**
   * Move the mouse to the specified coordinates.
   */
  moveMouse(x: number, y: number): Promise<void>;
  
  /**
   * Click the mouse at the current position.
   */
  click(button?: MouseButton): Promise<void>;
  
  /**
   * Type text at the current cursor position.
   */
  typeText(text: string): Promise<void>;
  
  /**
   * Press a key.
   */
  pressKey(key: KeyType): Promise<void>;
  
  /**
   * Get the accessibility tree.
   */
  getAccessibilityTree(): Promise<AccessibilityTree>;
}
