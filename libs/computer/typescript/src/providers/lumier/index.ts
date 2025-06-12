/**
 * Lumier VM provider implementation.
 */

export let HAS_LUMIER = false;

try {
  // Check if Docker is available
  const { execSync } = require("child_process");
  execSync("which docker", { stdio: "ignore" });
  HAS_LUMIER = true;
} catch {
  HAS_LUMIER = false;
}

export { LumierProvider } from "./provider";
