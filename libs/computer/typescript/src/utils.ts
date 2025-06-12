/**
 * Utility functions for the Computer module.
 */

/**
 * Sleep for a specified number of milliseconds
 * @param ms Number of milliseconds to sleep
 */
export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Parse a display string in format "WIDTHxHEIGHT"
 * @param display Display string to parse
 * @returns Object with width and height
 */
export function parseDisplayString(display: string): {
  width: number;
  height: number;
} {
  const match = display.match(/^(\d+)x(\d+)$/);
  if (!match || !match[1] || !match[2]) {
    throw new Error(
      "Display string must be in format 'WIDTHxHEIGHT' (e.g. '1024x768')"
    );
  }
  return {
    width: parseInt(match[1], 10),
    height: parseInt(match[2], 10),
  };
}

/**
 * Validate image format (should be in format "image:tag")
 * @param image Image string to validate
 * @returns Object with image name and tag
 */
export function parseImageString(image: string): { name: string; tag: string } {
  const parts = image.split(":");
  if (parts.length !== 2 || !parts[0] || !parts[1]) {
    throw new Error("Image must be in the format <image_name>:<tag>");
  }
  return {
    name: parts[0],
    tag: parts[1],
  };
}

/**
 * Convert bytes to human-readable format
 * @param bytes Number of bytes
 * @returns Human-readable string
 */
export function formatBytes(bytes: number): string {
  const units = ["B", "KB", "MB", "GB", "TB"];
  let size = bytes;
  let unitIndex = 0;

  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex++;
  }

  return `${size.toFixed(2)} ${units[unitIndex]}`;
}

/**
 * Parse memory string (e.g., "8GB") to bytes
 * @param memory Memory string
 * @returns Number of bytes
 */
export function parseMemoryString(memory: string): number {
  const match = memory.match(/^(\d+)(B|KB|MB|GB|TB)?$/i);
  if (!match || !match[1] || !match[2]) {
    throw new Error("Invalid memory format. Use format like '8GB' or '1024MB'");
  }

  const value = parseInt(match[1], 10);
  const unit = match[2].toUpperCase();

  const multipliers: Record<string, number> = {
    B: 1,
    KB: 1024,
    MB: 1024 * 1024,
    GB: 1024 * 1024 * 1024,
    TB: 1024 * 1024 * 1024 * 1024,
  };

  return value * (multipliers[unit] || 1);
}

/**
 * Create a timeout promise that rejects after specified milliseconds
 * @param ms Timeout in milliseconds
 * @param message Optional error message
 */
export function timeout<T>(ms: number, message?: string): Promise<T> {
  return new Promise((_, reject) => {
    setTimeout(() => {
      reject(new Error(message || `Timeout after ${ms}ms`));
    }, ms);
  });
}

/**
 * Race a promise against a timeout
 * @param promise The promise to race
 * @param ms Timeout in milliseconds
 * @param message Optional timeout error message
 */
export async function withTimeout<T>(
  promise: Promise<T>,
  ms: number,
  message?: string
): Promise<T> {
  return Promise.race([promise, timeout<T>(ms, message)]);
}
