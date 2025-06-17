/**
 * Shared logger module for the computer library
 */
import pino from "pino";

// Create and export default loggers for common components
export const computerLogger = pino({ name: "computer" });
