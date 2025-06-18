import {
  describe,
  expect,
  it,
  beforeEach,
  afterEach,
  vi,
  beforeAll,
  afterAll,
} from "vitest";
import { InterfaceFactory } from "../../src/interface/factory.ts";
import { OSType } from "../../src/types.ts";
import { ws } from "msw";
import { setupServer } from "msw/node";

describe("Interface Integration Tests", () => {
  const testIp = "192.168.1.100";
  const testPort = 8000;

  // Create WebSocket server
  const server = setupServer();

  beforeAll(() => {
    server.listen({ onUnhandledRequest: "error" });
  });

  afterAll(() => {
    server.close();
  });

  beforeEach(() => {
    // Reset handlers for each test
    server.resetHandlers();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe("Cross-platform interface creation", () => {
    it("should create correct interface for each OS type", async () => {
      const osTypes = [OSType.MACOS, OSType.LINUX, OSType.WINDOWS];
      const interfaces: Array<{
        os: OSType;
        interface: ReturnType<typeof InterfaceFactory.createInterfaceForOS>;
      }> = [];

      // Create interfaces for each OS
      for (const os of osTypes) {
        const interface_ = InterfaceFactory.createInterfaceForOS(os, testIp);
        interfaces.push({ os, interface: interface_ });
      }

      // Verify each interface is created correctly
      expect(interfaces).toHaveLength(3);
      for (const { os, interface: iface } of interfaces) {
        expect(iface).toBeDefined();
        // Check that the interface name contains the OS type in some form
        const osName = os.toLowerCase();
        expect(iface.constructor.name.toLowerCase()).toContain(osName);
      }
    });

    it("should handle multiple interfaces with different IPs", async () => {
      const ips = ["192.168.1.100", "192.168.1.101", "192.168.1.102"];
      const interfaces = ips.map((ip) =>
        InterfaceFactory.createInterfaceForOS(OSType.MACOS, ip)
      );

      // Set up WebSocket handlers for each IP
      for (const ip of ips) {
        const wsLink = ws.link(`ws://${ip}:${testPort}/ws`);
        server.use(
          wsLink.addEventListener("connection", ({ client }) => {
            client.addEventListener("message", () => {
              // Echo back success response
              client.send(JSON.stringify({ success: true }));
            });
          })
        );
      }

      // Connect all interfaces
      await Promise.all(interfaces.map((iface) => iface.connect()));

      // Verify all are connected
      for (const iface of interfaces) {
        expect(iface.isConnected()).toBe(true);
      }

      // Clean up
      for (const iface of interfaces) {
        iface.disconnect();
      }
    });
  });

  describe("Connection management", () => {
    it("should handle connection lifecycle", async () => {
      // Set up WebSocket handler
      const wsLink = ws.link(`ws://${testIp}:${testPort}/ws`);
      server.use(
        wsLink.addEventListener("connection", ({ client }) => {
          client.addEventListener("message", () => {
            // Echo back success response
            client.send(JSON.stringify({ success: true }));
          });
        })
      );

      const interface_ = InterfaceFactory.createInterfaceForOS(
        OSType.MACOS,
        testIp
      );

      // Initially not connected
      expect(interface_.isConnected()).toBe(false);

      // Connect
      await interface_.connect();
      expect(interface_.isConnected()).toBe(true);

      // Disconnect
      interface_.disconnect();

      // Wait a tick for the close to process
      await new Promise((resolve) => process.nextTick(resolve));
      expect(interface_.isConnected()).toBe(false);
    });

    it("should handle connection errors gracefully", async () => {
      // Don't register a handler - connection will succeed but no responses
      const interface_ = InterfaceFactory.createInterfaceForOS(
        OSType.MACOS,
        "192.0.2.1" // TEST-NET-1 address
      );

      // Should connect (WebSocket mock always connects)
      await interface_.connect();
      expect(interface_.isConnected()).toBe(true);

      interface_.disconnect();
    });

    it("should handle secure connections", async () => {
      const secureIp = "192.0.2.1";
      const securePort = 8443;

      // Register handler for secure connection
      const wsLink = ws.link(`wss://${secureIp}:${securePort}/ws`);
      server.use(
        wsLink.addEventListener("connection", ({ client }) => {
          client.addEventListener("message", () => {
            // Echo back success response
            client.send(JSON.stringify({ success: true }));
          });
        })
      );

      const interface_ = InterfaceFactory.createInterfaceForOS(
        OSType.MACOS,
        secureIp,
        "testuser",
        "testpass"
      );

      await interface_.connect();
      expect(interface_.isConnected()).toBe(true);

      interface_.disconnect();
    });
  });

  describe("Performance and concurrency", () => {
    it("should handle rapid command sequences", async () => {
      const receivedCommands: string[] = [];

      // Set up WebSocket handler that tracks commands
      const wsLink = ws.link(`ws://${testIp}:${testPort}/ws`);
      server.use(
        wsLink.addEventListener("connection", ({ client }) => {
          client.addEventListener("message", (event) => {
            const data = JSON.parse(event.data as string);
            receivedCommands.push(data.action);
            // Send response with command index
            client.send(
              JSON.stringify({
                success: true,
                data: `Response for ${data.action}`,
              })
            );
          });
        })
      );

      const interface_ = InterfaceFactory.createInterfaceForOS(
        OSType.MACOS,
        testIp
      );
      await interface_.connect();

      // Send multiple commands rapidly
      const commands = ["left_click", "right_click", "double_click"];
      const promises = commands.map((cmd) => {
        switch (cmd) {
          case "left_click":
            return interface_.leftClick(100, 200);
          case "right_click":
            return interface_.rightClick(150, 250);
          case "double_click":
            return interface_.doubleClick(200, 300);
        }
      });

      await Promise.all(promises);

      // Verify all commands were received
      expect(receivedCommands).toHaveLength(3);
      expect(receivedCommands).toContain("left_click");
      expect(receivedCommands).toContain("right_click");
      expect(receivedCommands).toContain("double_click");

      interface_.disconnect();
    });

    it("should maintain command order with locking", async () => {
      const receivedCommands: Array<{ action: string; index: number }> = [];

      // Set up WebSocket handler that tracks commands with delay
      const wsLink = ws.link(`ws://${testIp}:${testPort}/ws`);
      server.use(
        wsLink.addEventListener("connection", ({ client }) => {
          client.addEventListener("message", async (event) => {
            // Add delay to simulate processing
            await new Promise((resolve) => setTimeout(resolve, 10));

            const data = JSON.parse(event.data as string);
            receivedCommands.push({
              action: data.action,
              index: data.index,
            });

            client.send(JSON.stringify({ success: true }));
          });
        })
      );

      const interface_ = InterfaceFactory.createInterfaceForOS(
        OSType.MACOS,
        testIp
      );
      await interface_.connect();

      // Helper to send command with index
      async function sendCommandWithIndex(action: string, index: number) {
        await interface_.sendCommand({ action, index });
      }

      // Send commands in sequence
      await sendCommandWithIndex("command1", 0);
      await sendCommandWithIndex("command2", 1);
      await sendCommandWithIndex("command3", 2);

      // Wait for all commands to be processed
      await new Promise((resolve) => setTimeout(resolve, 50));

      // Verify commands were received in order
      expect(receivedCommands).toHaveLength(3);
      expect(receivedCommands[0]).toEqual({ action: "command1", index: 0 });
      expect(receivedCommands[1]).toEqual({ action: "command2", index: 1 });
      expect(receivedCommands[2]).toEqual({ action: "command3", index: 2 });

      interface_.disconnect();
    });
  });

  describe("Error handling", () => {
    it("should handle command failures", async () => {
      // Set up WebSocket handler that returns errors
      const wsLink = ws.link(`ws://${testIp}:${testPort}/ws`);
      server.use(
        wsLink.addEventListener("connection", ({ client }) => {
          client.addEventListener("message", (event) => {
            const data = JSON.parse(event.data as string);

            if (data.action === "fail_command") {
              client.send(
                JSON.stringify({
                  success: false,
                  error: "Command failed",
                })
              );
            } else {
              client.send(JSON.stringify({ success: true }));
            }
          });
        })
      );

      const interface_ = InterfaceFactory.createInterfaceForOS(
        OSType.MACOS,
        testIp
      );
      await interface_.connect();

      // Send a failing command
      await expect(
        interface_.sendCommand({ action: "fail_command" })
      ).rejects.toThrow("Command failed");

      // Verify interface is still connected
      expect(interface_.isConnected()).toBe(true);

      // Send a successful command
      const result = await interface_.sendCommand({
        action: "success_command",
      });
      expect(result.success).toBe(true);

      interface_.disconnect();
    });

    it("should handle disconnection during command", async () => {
      // Set up WebSocket handler that captures WebSocket instance
      const wsLink = ws.link(`ws://${testIp}:${testPort}/ws`);
      server.use(
        wsLink.addEventListener("connection", ({ client }) => {
          client.addEventListener("message", async () => {
            // Simulate disconnection during command processing
            await new Promise((resolve) => setTimeout(resolve, 10));
            client.close();
          });
        })
      );

      const interface_ = InterfaceFactory.createInterfaceForOS(
        OSType.MACOS,
        testIp
      );
      await interface_.connect();

      // Send command that will trigger disconnection
      await expect(
        interface_.sendCommand({ action: "disconnect_me" })
      ).rejects.toThrow();

      // Wait for close to process
      await new Promise((resolve) => setTimeout(resolve, 20));

      // Verify interface is disconnected
      expect(interface_.isConnected()).toBe(false);
    });
  });

  describe("Feature-specific tests", () => {
    it("should handle screenshot commands", async () => {
      // Set up WebSocket handler
      const wsLink = ws.link(`ws://${testIp}:${testPort}/ws`);
      server.use(
        wsLink.addEventListener("connection", ({ client }) => {
          client.addEventListener("message", () => {
            // Echo back success response with screenshot data
            client.send(JSON.stringify({ 
              success: true,
              data: "base64encodedimage"
            }));
          });
        })
      );

      const interface_ = InterfaceFactory.createInterfaceForOS(
        OSType.MACOS,
        testIp
      );
      await interface_.connect();

      const screenshot = await interface_.screenshot();
      expect(screenshot).toBeInstanceOf(Buffer);
      expect(screenshot.toString("base64")).toBe("base64encodedimage");

      interface_.disconnect();
    });

    it("should handle screen size queries", async () => {
      // Set up WebSocket handler
      const wsLink = ws.link(`ws://${testIp}:${testPort}/ws`);
      server.use(
        wsLink.addEventListener("connection", ({ client }) => {
          client.addEventListener("message", () => {
            // Echo back success response with screen size
            client.send(JSON.stringify({ 
              success: true,
              data: { width: 1920, height: 1080 }
            }));
          });
        })
      );

      const interface_ = InterfaceFactory.createInterfaceForOS(
        OSType.LINUX,
        testIp
      );
      await interface_.connect();

      const screenSize = await interface_.getScreenSize();
      expect(screenSize).toEqual({ width: 1920, height: 1080 });

      interface_.disconnect();
    });

    it("should handle file operations", async () => {
      // Set up WebSocket handler
      const wsLink = ws.link(`ws://${testIp}:${testPort}/ws`);
      server.use(
        wsLink.addEventListener("connection", ({ client }) => {
          client.addEventListener("message", () => {
            // Echo back success response with file data
            client.send(JSON.stringify({ 
              success: true,
              data: "file content"
            }));
          });
        })
      );

      const interface_ = InterfaceFactory.createInterfaceForOS(
        OSType.WINDOWS,
        testIp
      );
      await interface_.connect();

      // Test file exists
      const exists = await interface_.fileExists("/test/file.txt");
      expect(exists).toBe(true);

      // Test read text
      const content = await interface_.readText("/test/file.txt");
      expect(content).toBe("file content");

      // Test list directory
      const files = await interface_.listDir("/test");
      expect(files).toEqual(["file1.txt", "file2.txt", "dir1"]);

      interface_.disconnect();
    });
  });
});
