/**
 * Logger implementation for the Computer library.
 */

export enum LogLevel {
  DEBUG = 10,
  VERBOSE = 15,
  INFO = 20,
  NORMAL = 20,
  WARNING = 30,
  ERROR = 40,
}

export class Logger {
  private name: string;
  private verbosity: number;

  constructor(name: string, verbosity: number | LogLevel = LogLevel.NORMAL) {
    this.name = name;
    this.verbosity = typeof verbosity === 'number' ? verbosity : verbosity;
  }

  private log(level: LogLevel, message: string, ...args: any[]): void {
    if (level >= this.verbosity) {
      const timestamp = new Date().toISOString();
      const levelName = LogLevel[level];
      console.log(`[${timestamp}] [${this.name}] [${levelName}] ${message}`, ...args);
    }
  }

  debug(message: string, ...args: any[]): void {
    this.log(LogLevel.DEBUG, message, ...args);
  }

  info(message: string, ...args: any[]): void {
    this.log(LogLevel.INFO, message, ...args);
  }

  verbose(message: string, ...args: any[]): void {
    this.log(LogLevel.VERBOSE, message, ...args);
  }

  warning(message: string, ...args: any[]): void {
    this.log(LogLevel.WARNING, message, ...args);
  }

  error(message: string, ...args: any[]): void {
    this.log(LogLevel.ERROR, message, ...args);
  }
}
