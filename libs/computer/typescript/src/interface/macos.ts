import type { BaseComputerInterface } from "./base";
import type { KeyType, MouseButton, AccessibilityTree } from "./types";

/**
 * macOS-specific implementation of the computer interface.
 */
export class MacOSComputerInterface implements BaseComputerInterface {
  private ip_address: string;

  constructor(ip_address: string) {
    this.ip_address = ip_address;
  }

  async waitForReady(): Promise<void> {
    // Implementation will go here
  }

  async getScreenshot(): Promise<Buffer> {
    // Implementation will go here
    return Buffer.from([]);
  }

  async moveMouse(x: number, y: number): Promise<void> {
    // Implementation will go here
  }

  async click(button: MouseButton = "left"): Promise<void> {
    // Implementation will go here
  }

  async typeText(text: string): Promise<void> {
    // Implementation will go here
  }

  async pressKey(key: KeyType): Promise<void> {
    // Implementation will go here
  }

  async getAccessibilityTree(): Promise<AccessibilityTree> {
    // Implementation will go here
    return {
      success: false,
      frontmost_application: "",
      windows: [],
    };
  }
}
