/**
 * macOS computer interface implementation.
 */

import { BaseComputerInterface } from "./base";
import type { MouseButton, CursorPosition, AccessibilityNode } from "./base";
import type { ScreenSize } from "../types";

export class MacOSComputerInterface extends BaseComputerInterface {
  // Mouse Actions
  async mouseDown(
    x?: number,
    y?: number,
    button: MouseButton = "left"
  ): Promise<void> {
    await this.sendCommand({ action: "mouse_down", x, y, button });
  }

  async mouseUp(
    x?: number,
    y?: number,
    button: MouseButton = "left"
  ): Promise<void> {
    await this.sendCommand({ action: "mouse_up", x, y, button });
  }

  async leftClick(x?: number, y?: number): Promise<void> {
    await this.sendCommand({ action: "left_click", x, y });
  }

  async rightClick(x?: number, y?: number): Promise<void> {
    await this.sendCommand({ action: "right_click", x, y });
  }

  async doubleClick(x?: number, y?: number): Promise<void> {
    await this.sendCommand({ action: "double_click", x, y });
  }

  async moveCursor(x: number, y: number): Promise<void> {
    await this.sendCommand({ action: "move_cursor", x, y });
  }

  async dragTo(
    x: number,
    y: number,
    button: MouseButton = "left",
    duration = 0.5
  ): Promise<void> {
    await this.sendCommand({ action: "drag_to", x, y, button, duration });
  }

  async drag(
    path: Array<[number, number]>,
    button: MouseButton = "left",
    duration = 0.5
  ): Promise<void> {
    await this.sendCommand({ action: "drag", path, button, duration });
  }

  // Keyboard Actions
  async keyDown(key: string): Promise<void> {
    await this.sendCommand({ action: "key_down", key });
  }

  async keyUp(key: string): Promise<void> {
    await this.sendCommand({ action: "key_up", key });
  }

  async typeText(text: string): Promise<void> {
    await this.sendCommand({ action: "type_text", text });
  }

  async pressKey(key: string): Promise<void> {
    await this.sendCommand({ action: "press_key", key });
  }

  async hotkey(...keys: string[]): Promise<void> {
    await this.sendCommand({ action: "hotkey", keys });
  }

  // Scrolling Actions
  async scroll(x: number, y: number): Promise<void> {
    await this.sendCommand({ action: "scroll", x, y });
  }

  async scrollDown(clicks = 1): Promise<void> {
    await this.sendCommand({ action: "scroll_down", clicks });
  }

  async scrollUp(clicks = 1): Promise<void> {
    await this.sendCommand({ action: "scroll_up", clicks });
  }

  // Screen Actions
  async screenshot(): Promise<Buffer> {
    const response = await this.sendCommand({ action: "screenshot" });
    return Buffer.from(response.data as string, "base64");
  }

  async getScreenSize(): Promise<ScreenSize> {
    const response = await this.sendCommand({ action: "get_screen_size" });
    return response.data as ScreenSize;
  }

  async getCursorPosition(): Promise<CursorPosition> {
    const response = await this.sendCommand({ action: "get_cursor_position" });
    return response.data as CursorPosition;
  }

  // Clipboard Actions
  async copyToClipboard(): Promise<string> {
    const response = await this.sendCommand({ action: "copy_to_clipboard" });
    return response.data as string;
  }

  async setClipboard(text: string): Promise<void> {
    await this.sendCommand({ action: "set_clipboard", text });
  }

  // File System Actions
  async fileExists(path: string): Promise<boolean> {
    const response = await this.sendCommand({ action: "file_exists", path });
    return response.data as boolean;
  }

  async directoryExists(path: string): Promise<boolean> {
    const response = await this.sendCommand({
      action: "directory_exists",
      path,
    });
    return response.data as boolean;
  }

  async listDir(path: string): Promise<string[]> {
    const response = await this.sendCommand({ action: "list_dir", path });
    return response.data as string[];
  }

  async readText(path: string): Promise<string> {
    const response = await this.sendCommand({ action: "read_text", path });
    return response.data as string;
  }

  async writeText(path: string, content: string): Promise<void> {
    await this.sendCommand({ action: "write_text", path, content });
  }

  async readBytes(path: string): Promise<Buffer> {
    const response = await this.sendCommand({ action: "read_bytes", path });
    return Buffer.from(response.data as string, "base64");
  }

  async writeBytes(path: string, content: Buffer): Promise<void> {
    await this.sendCommand({
      action: "write_bytes",
      path,
      content: content.toString("base64"),
    });
  }

  async deleteFile(path: string): Promise<void> {
    await this.sendCommand({ action: "delete_file", path });
  }

  async createDir(path: string): Promise<void> {
    await this.sendCommand({ action: "create_dir", path });
  }

  async deleteDir(path: string): Promise<void> {
    await this.sendCommand({ action: "delete_dir", path });
  }

  async runCommand(command: string): Promise<[string, string]> {
    const response = await this.sendCommand({ action: "run_command", command });
    const data = response.data as { stdout: string; stderr: string };
    return [data.stdout, data.stderr];
  }

  // Accessibility Actions
  async getAccessibilityTree(): Promise<AccessibilityNode> {
    const response = await this.sendCommand({
      action: "get_accessibility_tree",
    });
    return response.data as AccessibilityNode;
  }

  async toScreenCoordinates(x: number, y: number): Promise<[number, number]> {
    const response = await this.sendCommand({
      action: "to_screen_coordinates",
      x,
      y,
    });
    return response.data as [number, number];
  }

  async toScreenshotCoordinates(
    x: number,
    y: number
  ): Promise<[number, number]> {
    const response = await this.sendCommand({
      action: "to_screenshot_coordinates",
      x,
      y,
    });
    return response.data as [number, number];
  }
}
