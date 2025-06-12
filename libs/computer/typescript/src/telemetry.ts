/**
 * Telemetry tracking for Computer usage.
 */

interface TelemetryEvent {
  event: string;
  timestamp: Date;
  properties?: Record<string, any>;
}

export class TelemetryManager {
  private enabled: boolean = true;
  private events: TelemetryEvent[] = [];

  setEnabled(enabled: boolean): void {
    this.enabled = enabled;
  }

  isEnabled(): boolean {
    return this.enabled;
  }

  track(event: string, properties?: Record<string, any>): void {
    if (!this.enabled) {
      return;
    }

    const telemetryEvent: TelemetryEvent = {
      event,
      timestamp: new Date(),
      properties,
    };

    this.events.push(telemetryEvent);

    // In a real implementation, this would send to a telemetry service
    // For now, just log to debug
    if (process.env.NODE_ENV === "development") {
      console.debug("[Telemetry]", event, properties);
    }
  }

  getEvents(): TelemetryEvent[] {
    return [...this.events];
  }

  clear(): void {
    this.events = [];
  }
}

// Singleton instance
const telemetryManager = new TelemetryManager();

/**
 * Record computer initialization event
 */
export function recordComputerInitialization(): void {
  telemetryManager.track("computer_initialized", {
    timestamp: new Date().toISOString(),
    version: process.env.npm_package_version || "unknown",
  });
}

/**
 * Record VM start event
 */
export function recordVMStart(vmName: string, provider: string): void {
  telemetryManager.track("vm_started", {
    vm_name: vmName,
    provider,
    timestamp: new Date().toISOString(),
  });
}

/**
 * Record VM stop event
 */
export function recordVMStop(vmName: string, duration: number): void {
  telemetryManager.track("vm_stopped", {
    vm_name: vmName,
    duration_ms: duration,
    timestamp: new Date().toISOString(),
  });
}

/**
 * Record interface action
 */
export function recordInterfaceAction(
  action: string,
  details?: Record<string, any>
): void {
  telemetryManager.track("interface_action", {
    action,
    ...details,
    timestamp: new Date().toISOString(),
  });
}

/**
 * Set telemetry enabled/disabled
 */
export function setTelemetryEnabled(enabled: boolean): void {
  telemetryManager.setEnabled(enabled);
}

/**
 * Check if telemetry is enabled
 */
export function isTelemetryEnabled(): boolean {
  return telemetryManager.isEnabled();
}

export { telemetryManager };
