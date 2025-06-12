/**
 * Lume VM provider implementation.
 */

export let HAS_LUME = false;

try {
  // Check if curl is available
  const { execSync } = require('child_process');
  execSync('which curl', { stdio: 'ignore' });
  HAS_LUME = true;
} catch {
  HAS_LUME = false;
}

export { LumeProvider } from './provider';
