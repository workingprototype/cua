import {
  describe,
  expect,
  it,
  beforeEach,
  afterEach,
} from "vitest";
import { MacOSComputerInterface } from "../../src/interface/macos.ts";
// Import the setup.ts which already has MSW configured
import "../setup.ts";

describe("MacOSComputerInterface", () => {
  // Define test parameters
  const testParams = {
    ipAddress: "192.0.2.1", // TEST-NET-1 address (RFC 5737) - guaranteed not to be routable
    username: "testuser",
    password: "testpass",
    apiKey: "test-api-key",
    vmName: "test-vm",
  };

  // Track received messages for verification
  // biome-ignore lint/suspicious/noExplicitAny: <explanation>
  let receivedMessages: any[] = [];

  beforeEach(() => {
    // Clear received messages before each test
    receivedMessages = [];
  });

  afterEach(() => {
    // Clear any state after each test
    receivedMessages = [];
  });

  describe("Connection Management", () => {
    it("should connect with proper authentication headers", async () => {
      const macosInterface = new MacOSComputerInterface(
        testParams.ipAddress,
        testParams.username,
        testParams.password,
        testParams.apiKey,
        testParams.vmName
      );

      await macosInterface.connect();

      // Verify the interface is connected
      expect(macosInterface.isConnected()).toBe(true);

      await macosInterface.disconnect();
    });
  });

  describe("Mouse Actions", () => {
    let macosInterface: MacOSComputerInterface;

    beforeEach(async () => {
      macosInterface = new MacOSComputerInterface(
        testParams.ipAddress,
        testParams.username,
        testParams.password,
        testParams.apiKey,
        testParams.vmName
      );
      // Remove initialize() call - connection happens on first command
      await new Promise((resolve) => setTimeout(resolve, 100));
    });

    afterEach(async () => {
      await macosInterface.disconnect();
    });

    it("should send mouse_down command", async () => {
      await macosInterface.mouseDown(100, 200, "left");

      expect(receivedMessages).toHaveLength(1);
      expect(receivedMessages[0]).toEqual({
        action: "mouse_down",
        x: 100,
        y: 200,
        button: "left",
      });
    });

    it("should send mouse_up command", async () => {
      await macosInterface.mouseUp(100, 200, "right");

      expect(receivedMessages).toHaveLength(1);
      expect(receivedMessages[0]).toEqual({
        action: "mouse_up",
        x: 100,
        y: 200,
        button: "right",
      });
    });

    it("should send left_click command", async () => {
      await macosInterface.leftClick(150, 250);

      expect(receivedMessages).toHaveLength(1);
      expect(receivedMessages[0]).toEqual({
        action: "left_click",
        x: 150,
        y: 250,
      });
    });

    it("should send right_click command", async () => {
      await macosInterface.rightClick(150, 250);

      expect(receivedMessages).toHaveLength(1);
      expect(receivedMessages[0]).toEqual({
        action: "right_click",
        x: 150,
        y: 250,
      });
    });

    it("should send double_click command", async () => {
      await macosInterface.doubleClick(150, 250);

      expect(receivedMessages).toHaveLength(1);
      expect(receivedMessages[0]).toEqual({
        action: "double_click",
        x: 150,
        y: 250,
      });
    });

    it("should send move_cursor command", async () => {
      await macosInterface.moveCursor(300, 400);

      expect(receivedMessages).toHaveLength(1);
      expect(receivedMessages[0]).toEqual({
        action: "move_cursor",
        x: 300,
        y: 400,
      });
    });

    it("should send drag_to command", async () => {
      await macosInterface.dragTo(500, 600, "left", 1.5);

      expect(receivedMessages).toHaveLength(1);
      expect(receivedMessages[0]).toEqual({
        action: "drag_to",
        x: 500,
        y: 600,
        button: "left",
        duration: 1.5,
      });
    });

    it("should send scroll command", async () => {
      await macosInterface.scroll(0, 10);

      expect(receivedMessages).toHaveLength(1);
      expect(receivedMessages[0]).toEqual({
        action: "scroll",
        x: 0,
        y: 10,
        clicks: 5,
      });
    });
  });

  describe("Keyboard Actions", () => {
    let macosInterface: MacOSComputerInterface;

    beforeEach(async () => {
      macosInterface = new MacOSComputerInterface(
        testParams.ipAddress,
        testParams.username,
        testParams.password,
        testParams.apiKey,
        testParams.vmName
      );
      // Remove initialize() call
      await new Promise((resolve) => setTimeout(resolve, 100));
    });

    afterEach(async () => {
      await macosInterface.disconnect();
    });

    it("should send key_down command", async () => {
      await macosInterface.keyDown("a");

      expect(receivedMessages).toHaveLength(1);
      expect(receivedMessages[0]).toEqual({
        action: "key_down",
        key: "a",
      });
    });

    it("should send key_up command", async () => {
      await macosInterface.keyUp("a");

      expect(receivedMessages).toHaveLength(1);
      expect(receivedMessages[0]).toEqual({
        action: "key_up",
        key: "a",
      });
    });

    it("should send key_press command", async () => {
      await macosInterface.keyDown("enter");

      expect(receivedMessages).toHaveLength(1);
      expect(receivedMessages[0]).toEqual({
        action: "key_press",
        key: "enter",
      });
    });

    it("should send type_text command", async () => {
      await macosInterface.typeText("Hello, World!");

      expect(receivedMessages).toHaveLength(1);
      expect(receivedMessages[0]).toEqual({
        action: "type_text",
        text: "Hello, World!",
      });
    });

    it("should send hotkey command", async () => {
      await macosInterface.hotkey("cmd", "c");

      expect(receivedMessages).toHaveLength(1);
      expect(receivedMessages[0]).toEqual({
        action: "hotkey",
        keys: ["cmd", "c"],
      });
    });
  });

  describe("Screen Actions", () => {
    let macosInterface: MacOSComputerInterface;

    beforeEach(async () => {
      macosInterface = new MacOSComputerInterface(
        testParams.ipAddress,
        testParams.username,
        testParams.password,
        testParams.apiKey,
        testParams.vmName
      );
      // Remove initialize() call
      await new Promise((resolve) => setTimeout(resolve, 100));
    });

    afterEach(async () => {
      await macosInterface.disconnect();
    });

    it("should get screenshot", async () => {
      const screenshot = await macosInterface.screenshot();

      expect(receivedMessages).toHaveLength(1);
      expect(receivedMessages[0]).toEqual({
        action: "screenshot",
      });
      expect(screenshot).toBe("base64encodedimage");
    });

    it("should get screen size", async () => {
      const screenSize = await macosInterface.getScreenSize();

      expect(receivedMessages).toHaveLength(1);
      expect(receivedMessages[0]).toEqual({
        action: "get_screen_size",
      });
      expect(screenSize).toEqual({ width: 1920, height: 1080 });
    });

    it("should get cursor position", async () => {
      const position = await macosInterface.getCursorPosition();

      expect(receivedMessages).toHaveLength(1);
      expect(receivedMessages[0]).toEqual({
        action: "get_cursor_position",
      });
      expect(position).toEqual({ x: 100, y: 200 });
    });

    it("should get accessibility tree", async () => {
      const tree = await macosInterface.getAccessibilityTree();

      expect(receivedMessages).toHaveLength(1);
      expect(receivedMessages[0]).toEqual({
        action: "get_accessibility_tree",
      });
      expect(tree).toEqual({
        role: "window",
        title: "Test Window",
        children: [],
      });
    });
  });

  describe("System Actions", () => {
    let macosInterface: MacOSComputerInterface;

    beforeEach(async () => {
      macosInterface = new MacOSComputerInterface(
        testParams.ipAddress,
        testParams.username,
        testParams.password,
        testParams.apiKey,
        testParams.vmName
      );
      // Remove initialize() call
      await new Promise((resolve) => setTimeout(resolve, 100));
    });

    afterEach(async () => {
      await macosInterface.disconnect();
    });

    it("should run command", async () => {
      const result = await macosInterface.runCommand("ls -la");

      expect(receivedMessages).toHaveLength(1);
      expect(receivedMessages[0]).toEqual({
        action: "run_command",
        command: "ls -la",
      });
      expect(result).toEqual({
        stdout: "command output",
        stderr: "",
        returncode: 0,
      });
    });
  });

  describe("Error Handling", () => {
    it("should handle WebSocket connection errors", async () => {
      // Use a valid but unreachable IP to avoid DNS errors
      const macosInterface = new MacOSComputerInterface(
        testParams.ipAddress,
        testParams.username,
        testParams.password,
        testParams.apiKey,
        testParams.vmName
      );

      // Try to send a command - should fail with connection error
      await expect(macosInterface.screenshot()).rejects.toThrow();

      await macosInterface.disconnect();
    });

    it("should handle server error responses", async () => {
      // Override the handler to send error response
      // server.use(
      //   chat.addEventListener("connection", ({ client, server }) => {
      //     client.addEventListener("message", () => {
      //       server.send(
      //         JSON.stringify({
      //           success: false,
      //           error: "Command failed",
      //         })
      //       );
      //     });
      //   })
      // );

      const macosInterface = new MacOSComputerInterface(
        testParams.ipAddress,
        testParams.username,
        testParams.password,
        testParams.apiKey,
        testParams.vmName
      );
      // Remove initialize() call
      await new Promise((resolve) => setTimeout(resolve, 100));

      await expect(macosInterface.screenshot()).rejects.toThrow(
        "Command failed"
      );

      await macosInterface.disconnect();
    });

    it("should handle closed connection", async () => {
      const macosInterface = new MacOSComputerInterface(
        testParams.ipAddress,
        testParams.username,
        testParams.password,
        testParams.apiKey,
        testParams.vmName
      );

      // Send a command to trigger connection
      await macosInterface.screenshot();

      // Close the interface
      await macosInterface.disconnect();

      // Try to use after closing
      await expect(macosInterface.screenshot()).rejects.toThrow(
        "Interface is closed"
      );
    });
  });

  describe("Command Locking", () => {
    let macosInterface: MacOSComputerInterface;

    beforeEach(async () => {
      macosInterface = new MacOSComputerInterface(
        testParams.ipAddress,
        testParams.username,
        testParams.password,
        testParams.apiKey,
        testParams.vmName
      );
      // Remove initialize() call
      await new Promise((resolve) => setTimeout(resolve, 100));
    });

    afterEach(async () => {
      await macosInterface.disconnect();
    });

    it("should serialize commands", async () => {
      // Send multiple commands simultaneously
      const promises = [
        macosInterface.leftClick(100, 100),
        macosInterface.rightClick(200, 200),
        macosInterface.typeText("test"),
      ];

      await Promise.all(promises);

      // Commands should be sent in order
      expect(receivedMessages).toHaveLength(3);
      expect(receivedMessages[0].action).toBe("left_click");
      expect(receivedMessages[1].action).toBe("right_click");
      expect(receivedMessages[2].action).toBe("type_text");
    });
  });
});
