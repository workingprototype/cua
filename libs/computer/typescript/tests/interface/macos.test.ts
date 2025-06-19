import { describe, expect, it, beforeEach, afterEach } from "vitest";
import { MacOSComputerInterface } from "../../src/interface/macos.ts";
import { WebSocketServer, WebSocket } from "ws";

describe("MacOSComputerInterface", () => {
  // Define test parameters
  const testParams = {
    ipAddress: "localhost",
    username: "testuser",
    password: "testpass",
    apiKey: "test-api-key",
    vmName: "test-vm",
  };

  // WebSocket server mock
  let wss: WebSocketServer;
  let serverPort: number;
  let connectedClients: WebSocket[] = [];

  // Track received messages for verification
  interface ReceivedMessage {
    action: string;
    [key: string]: unknown;
  }
  let receivedMessages: ReceivedMessage[] = [];

  // Set up WebSocket server before all tests
  beforeEach(async () => {
    receivedMessages = [];
    connectedClients = [];

    // Create WebSocket server on a random available port
    wss = new WebSocketServer({ port: 0 });
    serverPort = (wss.address() as { port: number }).port;

    // Update test params with the actual server address
    testParams.ipAddress = `localhost:${serverPort}`;

    // Handle WebSocket connections
    wss.on("connection", (ws, req) => {
      connectedClients.push(ws);

      // Verify authentication headers
      const apiKey = req.headers["x-api-key"];
      const vmName = req.headers["x-vm-name"];

      if (apiKey !== testParams.apiKey || vmName !== testParams.vmName) {
        ws.close(1008, "Unauthorized");
        return;
      }

      // Handle incoming messages
      ws.on("message", (data) => {
        try {
          const message = JSON.parse(data.toString());
          receivedMessages.push(message);

          // Send appropriate responses based on action
          switch (message.action) {
            case "screenshot":
              ws.send(JSON.stringify({
                data: Buffer.from("fake-screenshot-data").toString("base64")
              }));
              break;
            case "get_screen_size":
              ws.send(JSON.stringify({ data: { width: 1920, height: 1080 } }));
              break;
            case "get_cursor_position":
              ws.send(JSON.stringify({ data: { x: 100, y: 200 } }));
              break;
            case "copy_to_clipboard":
              ws.send(JSON.stringify({ data: "clipboard content" }));
              break;
            case "file_exists":
              ws.send(JSON.stringify({ data: true }));
              break;
            case "directory_exists":
              ws.send(JSON.stringify({ data: true }));
              break;
            case "list_dir":
              ws.send(JSON.stringify({ data: ["file1.txt", "file2.txt"] }));
              break;
            case "read_text":
              ws.send(JSON.stringify({ data: "file content" }));
              break;
            case "read_bytes":
              ws.send(JSON.stringify({ 
                data: Buffer.from("binary content").toString("base64") 
              }));
              break;
            case "run_command":
              ws.send(JSON.stringify({ data: { stdout: "command output", stderr: "" } }));
              break;
            case "get_accessibility_tree":
              ws.send(JSON.stringify({
                data: {
                  role: "window",
                  title: "Test Window",
                  bounds: { x: 0, y: 0, width: 1920, height: 1080 },
                  children: []
                }
              }));
              break;
            case "to_screen_coordinates":
            case "to_screenshot_coordinates":
              ws.send(JSON.stringify({ data: [message.x || 0, message.y || 0] }));
              break;
            default:
              // For all other actions, just send success
              ws.send(JSON.stringify({ success: true }));
              break;
          }
        } catch (error) {
          ws.send(JSON.stringify({ error: (error as Error).message }));
        }
      });

      ws.on("error", (error) => {
        console.error("WebSocket error:", error);
      });
    });
  });

  // Clean up WebSocket server after each test
  afterEach(async () => {
    // Close all connected clients
    for (const client of connectedClients) {
      if (client.readyState === WebSocket.OPEN) {
        client.close();
      }
    }

    // Close the server
    await new Promise<void>((resolve) => {
      wss.close(() => resolve());
    });
  });

  describe("Connection Management", () => {
    it("should connect with proper authentication headers", async () => {
      const macosInterface = new MacOSComputerInterface(
        testParams.ipAddress,
        testParams.username,
        testParams.password,
        testParams.apiKey,
        testParams.vmName,
        false
      );

      await macosInterface.connect();

      // Verify the interface is connected
      expect(macosInterface.isConnected()).toBe(true);
      expect(connectedClients.length).toBe(1);

      await macosInterface.disconnect();
    });

    it("should handle connection without API key", async () => {
      // Create a separate server that doesn't check auth
      const noAuthWss = new WebSocketServer({ port: 0 });
      const noAuthPort = (noAuthWss.address() as { port: number }).port;

      noAuthWss.on("connection", (ws) => {
        ws.on("message", () => {
          ws.send(JSON.stringify({ success: true }));
        });
      });

      const macosInterface = new MacOSComputerInterface(
        `localhost:${noAuthPort}`,
        testParams.username,
        testParams.password,
        undefined,
        undefined,
        false
      );

      await macosInterface.connect();
      expect(macosInterface.isConnected()).toBe(true);

      await macosInterface.disconnect();
      await new Promise<void>((resolve) => {
        noAuthWss.close(() => resolve());
      });
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
        testParams.vmName,
        false
      );
      await macosInterface.connect();
    });

    afterEach(async () => {
      if (macosInterface) {
        await macosInterface.disconnect();
      }
    });

    it("should send mouse_down command", async () => {
      await macosInterface.mouseDown(100, 200, "left");
      
      const lastMessage = receivedMessages[receivedMessages.length - 1];
      expect(lastMessage).toEqual({
        action: "mouse_down",
        x: 100,
        y: 200,
        button: "left"
      });
    });

    it("should send mouse_up command", async () => {
      await macosInterface.mouseUp(100, 200, "right");
      
      const lastMessage = receivedMessages[receivedMessages.length - 1];
      expect(lastMessage).toEqual({
        action: "mouse_up",
        x: 100,
        y: 200,
        button: "right"
      });
    });

    it("should send left_click command", async () => {
      await macosInterface.leftClick(150, 250);
      
      const lastMessage = receivedMessages[receivedMessages.length - 1];
      expect(lastMessage).toEqual({
        action: "left_click",
        x: 150,
        y: 250
      });
    });

    it("should send right_click command", async () => {
      await macosInterface.rightClick(200, 300);
      
      const lastMessage = receivedMessages[receivedMessages.length - 1];
      expect(lastMessage).toEqual({
        action: "right_click",
        x: 200,
        y: 300
      });
    });

    it("should send double_click command", async () => {
      await macosInterface.doubleClick(250, 350);
      
      const lastMessage = receivedMessages[receivedMessages.length - 1];
      expect(lastMessage).toEqual({
        action: "double_click",
        x: 250,
        y: 350
      });
    });

    it("should send move_cursor command", async () => {
      await macosInterface.moveCursor(300, 400);
      
      const lastMessage = receivedMessages[receivedMessages.length - 1];
      expect(lastMessage).toEqual({
        action: "move_cursor",
        x: 300,
        y: 400
      });
    });

    it("should send drag_to command", async () => {
      await macosInterface.dragTo(400, 500, "left", 1.5);
      
      const lastMessage = receivedMessages[receivedMessages.length - 1];
      expect(lastMessage).toEqual({
        action: "drag_to",
        x: 400,
        y: 500,
        button: "left",
        duration: 1.5
      });
    });

    it("should send drag command with path", async () => {
      const path: Array<[number, number]> = [[100, 100], [200, 200], [300, 300]];
      await macosInterface.drag(path, "middle", 2.0);
      
      const lastMessage = receivedMessages[receivedMessages.length - 1];
      expect(lastMessage).toEqual({
        action: "drag",
        path: path,
        button: "middle",
        duration: 2.0
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
        testParams.vmName,
        false
      );
      await macosInterface.connect();
    });

    afterEach(async () => {
      if (macosInterface) {
        await macosInterface.disconnect();
      }
    });

    it("should send key_down command", async () => {
      await macosInterface.keyDown("a");
      
      const lastMessage = receivedMessages[receivedMessages.length - 1];
      expect(lastMessage).toEqual({
        action: "key_down",
        key: "a"
      });
    });

    it("should send key_up command", async () => {
      await macosInterface.keyUp("b");
      
      const lastMessage = receivedMessages[receivedMessages.length - 1];
      expect(lastMessage).toEqual({
        action: "key_up",
        key: "b"
      });
    });

    it("should send type_text command", async () => {
      await macosInterface.typeText("Hello, World!");
      
      const lastMessage = receivedMessages[receivedMessages.length - 1];
      expect(lastMessage).toEqual({
        action: "type_text",
        text: "Hello, World!"
      });
    });

    it("should send press_key command", async () => {
      await macosInterface.pressKey("enter");
      
      const lastMessage = receivedMessages[receivedMessages.length - 1];
      expect(lastMessage).toEqual({
        action: "press_key",
        key: "enter"
      });
    });

    it("should send hotkey command", async () => {
      await macosInterface.hotkey("cmd", "c");
      
      const lastMessage = receivedMessages[receivedMessages.length - 1];
      expect(lastMessage).toEqual({
        action: "hotkey",
        keys: ["cmd", "c"]
      });
    });
  });

  describe("Scrolling Actions", () => {
    let macosInterface: MacOSComputerInterface;

    beforeEach(async () => {
      macosInterface = new MacOSComputerInterface(
        testParams.ipAddress,
        testParams.username,
        testParams.password,
        testParams.apiKey,
        testParams.vmName,
        false
      );
      await macosInterface.connect();
    });

    afterEach(async () => {
      if (macosInterface) {
        await macosInterface.disconnect();
      }
    });

    it("should send scroll command", async () => {
      await macosInterface.scroll(10, -5);
      
      const lastMessage = receivedMessages[receivedMessages.length - 1];
      expect(lastMessage).toEqual({
        action: "scroll",
        x: 10,
        y: -5
      });
    });

    it("should send scroll_down command", async () => {
      await macosInterface.scrollDown(3);
      
      const lastMessage = receivedMessages[receivedMessages.length - 1];
      expect(lastMessage).toEqual({
        action: "scroll_down",
        clicks: 3
      });
    });

    it("should send scroll_up command", async () => {
      await macosInterface.scrollUp(2);
      
      const lastMessage = receivedMessages[receivedMessages.length - 1];
      expect(lastMessage).toEqual({
        action: "scroll_up",
        clicks: 2
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
        testParams.vmName,
        false
      );
      await macosInterface.connect();
    });

    afterEach(async () => {
      if (macosInterface) {
        await macosInterface.disconnect();
      }
    });

    it("should get screenshot", async () => {
      const screenshot = await macosInterface.screenshot();
      
      expect(screenshot).toBeInstanceOf(Buffer);
      expect(screenshot.toString()).toBe("fake-screenshot-data");
      
      const lastMessage = receivedMessages[receivedMessages.length - 1];
      expect(lastMessage).toEqual({
        action: "screenshot"
      });
    });

    it("should get screen size", async () => {
      const size = await macosInterface.getScreenSize();
      
      expect(size).toEqual({ width: 1920, height: 1080 });
      
      const lastMessage = receivedMessages[receivedMessages.length - 1];
      expect(lastMessage).toEqual({
        action: "get_screen_size"
      });
    });

    it("should get cursor position", async () => {
      const position = await macosInterface.getCursorPosition();
      
      expect(position).toEqual({ x: 100, y: 200 });
      
      const lastMessage = receivedMessages[receivedMessages.length - 1];
      expect(lastMessage).toEqual({
        action: "get_cursor_position"
      });
    });
  });

  describe("Clipboard Actions", () => {
    let macosInterface: MacOSComputerInterface;

    beforeEach(async () => {
      macosInterface = new MacOSComputerInterface(
        testParams.ipAddress,
        testParams.username,
        testParams.password,
        testParams.apiKey,
        testParams.vmName,
        false
      );
      await macosInterface.connect();
    });

    afterEach(async () => {
      if (macosInterface) {
        await macosInterface.disconnect();
      }
    });

    it("should copy to clipboard", async () => {
      const text = await macosInterface.copyToClipboard();
      
      expect(text).toBe("clipboard content");
      
      const lastMessage = receivedMessages[receivedMessages.length - 1];
      expect(lastMessage).toEqual({
        action: "copy_to_clipboard"
      });
    });

    it("should set clipboard", async () => {
      await macosInterface.setClipboard("new clipboard text");
      
      const lastMessage = receivedMessages[receivedMessages.length - 1];
      expect(lastMessage).toEqual({
        action: "set_clipboard",
        text: "new clipboard text"
      });
    });
  });

  describe("File System Actions", () => {
    let macosInterface: MacOSComputerInterface;

    beforeEach(async () => {
      macosInterface = new MacOSComputerInterface(
        testParams.ipAddress,
        testParams.username,
        testParams.password,
        testParams.apiKey,
        testParams.vmName,
        false
      );
      await macosInterface.connect();
    });

    afterEach(async () => {
      if (macosInterface) {
        await macosInterface.disconnect();
      }
    });

    it("should check file exists", async () => {
      const exists = await macosInterface.fileExists("/path/to/file");
      
      expect(exists).toBe(true);
      
      const lastMessage = receivedMessages[receivedMessages.length - 1];
      expect(lastMessage).toEqual({
        action: "file_exists",
        path: "/path/to/file"
      });
    });

    it("should check directory exists", async () => {
      const exists = await macosInterface.directoryExists("/path/to/dir");
      
      expect(exists).toBe(true);
      
      const lastMessage = receivedMessages[receivedMessages.length - 1];
      expect(lastMessage).toEqual({
        action: "directory_exists",
        path: "/path/to/dir"
      });
    });

    it("should list directory", async () => {
      const files = await macosInterface.listDir("/path/to/dir");
      
      expect(files).toEqual(["file1.txt", "file2.txt"]);
      
      const lastMessage = receivedMessages[receivedMessages.length - 1];
      expect(lastMessage).toEqual({
        action: "list_dir",
        path: "/path/to/dir"
      });
    });

    it("should read text file", async () => {
      const content = await macosInterface.readText("/path/to/file.txt");
      
      expect(content).toBe("file content");
      
      const lastMessage = receivedMessages[receivedMessages.length - 1];
      expect(lastMessage).toEqual({
        action: "read_text",
        path: "/path/to/file.txt"
      });
    });

    it("should write text file", async () => {
      await macosInterface.writeText("/path/to/file.txt", "new content");
      
      const lastMessage = receivedMessages[receivedMessages.length - 1];
      expect(lastMessage).toEqual({
        action: "write_text",
        path: "/path/to/file.txt",
        content: "new content"
      });
    });

    it("should read binary file", async () => {
      const content = await macosInterface.readBytes("/path/to/file.bin");
      
      expect(content).toBeInstanceOf(Buffer);
      expect(content.toString()).toBe("binary content");
      
      const lastMessage = receivedMessages[receivedMessages.length - 1];
      expect(lastMessage).toEqual({
        action: "read_bytes",
        path: "/path/to/file.bin"
      });
    });

    it("should write binary file", async () => {
      const buffer = Buffer.from("binary data");
      await macosInterface.writeBytes("/path/to/file.bin", buffer);
      
      const lastMessage = receivedMessages[receivedMessages.length - 1];
      expect(lastMessage).toEqual({
        action: "write_bytes",
        path: "/path/to/file.bin",
        content: buffer.toString("base64")
      });
    });

    it("should delete file", async () => {
      await macosInterface.deleteFile("/path/to/file");
      
      const lastMessage = receivedMessages[receivedMessages.length - 1];
      expect(lastMessage).toEqual({
        action: "delete_file",
        path: "/path/to/file"
      });
    });

    it("should create directory", async () => {
      await macosInterface.createDir("/path/to/new/dir");
      
      const lastMessage = receivedMessages[receivedMessages.length - 1];
      expect(lastMessage).toEqual({
        action: "create_dir",
        path: "/path/to/new/dir"
      });
    });

    it("should delete directory", async () => {
      await macosInterface.deleteDir("/path/to/dir");
      
      const lastMessage = receivedMessages[receivedMessages.length - 1];
      expect(lastMessage).toEqual({
        action: "delete_dir",
        path: "/path/to/dir"
      });
    });

    it("should run command", async () => {
      const [stdout, stderr] = await macosInterface.runCommand("ls -la");
      
      expect(stdout).toBe("command output");
      expect(stderr).toBe("");
      
      const lastMessage = receivedMessages[receivedMessages.length - 1];
      expect(lastMessage).toEqual({
        action: "run_command",
        command: "ls -la"
      });
    });
  });

  describe("Accessibility Actions", () => {
    let macosInterface: MacOSComputerInterface;

    beforeEach(async () => {
      macosInterface = new MacOSComputerInterface(
        testParams.ipAddress,
        testParams.username,
        testParams.password,
        testParams.apiKey,
        testParams.vmName,
        false
      );
      await macosInterface.connect();
    });

    afterEach(async () => {
      if (macosInterface) {
        await macosInterface.disconnect();
      }
    });

    it("should get accessibility tree", async () => {
      const tree = await macosInterface.getAccessibilityTree();
      
      expect(tree).toEqual({
        role: "window",
        title: "Test Window",
        bounds: { x: 0, y: 0, width: 1920, height: 1080 },
        children: []
      });
      
      const lastMessage = receivedMessages[receivedMessages.length - 1];
      expect(lastMessage).toEqual({
        action: "get_accessibility_tree"
      });
    });

    it("should convert to screen coordinates", async () => {
      const [x, y] = await macosInterface.toScreenCoordinates(100, 200);
      
      expect(x).toBe(100);
      expect(y).toBe(200);
      
      const lastMessage = receivedMessages[receivedMessages.length - 1];
      expect(lastMessage).toEqual({
        action: "to_screen_coordinates",
        x: 100,
        y: 200
      });
    });

    it("should convert to screenshot coordinates", async () => {
      const [x, y] = await macosInterface.toScreenshotCoordinates(300, 400);
      
      expect(x).toBe(300);
      expect(y).toBe(400);
      
      const lastMessage = receivedMessages[receivedMessages.length - 1];
      expect(lastMessage).toEqual({
        action: "to_screenshot_coordinates",
        x: 300,
        y: 400
      });
    });
  });

  describe("Error Handling", () => {
    it("should handle WebSocket connection errors", async () => {
      // Use a valid but unreachable IP to avoid DNS errors
      const macosInterface = new MacOSComputerInterface(
        "localhost:9999",
        testParams.username,
        testParams.password,
        testParams.apiKey,
        testParams.vmName,
        false
      );

      // Connection should fail
      await expect(macosInterface.connect()).rejects.toThrow();
    });

    it("should handle command errors", async () => {
      // Create a server that returns errors
      const errorWss = new WebSocketServer({ port: 0 });
      const errorPort = (errorWss.address() as { port: number }).port;

      errorWss.on("connection", (ws) => {
        ws.on("message", () => {
          ws.send(JSON.stringify({ error: "Command failed" }));
        });
      });

      const macosInterface = new MacOSComputerInterface(
        `localhost:${errorPort}`,
        testParams.username,
        testParams.password,
        testParams.apiKey,
        testParams.vmName,
        false
      );

      await macosInterface.connect();

      // Command should throw error
      await expect(macosInterface.leftClick(100, 100)).rejects.toThrow("Command failed");

      await macosInterface.disconnect();
      await new Promise<void>((resolve) => {
        errorWss.close(() => resolve());
      });
    });

    it("should handle disconnection gracefully", async () => {
      const macosInterface = new MacOSComputerInterface(
        testParams.ipAddress,
        testParams.username,
        testParams.password,
        testParams.apiKey,
        testParams.vmName,
        false
      );

      await macosInterface.connect();
      expect(macosInterface.isConnected()).toBe(true);

      // Disconnect
      macosInterface.disconnect();
      expect(macosInterface.isConnected()).toBe(false);

      // Should reconnect automatically on next command
      await macosInterface.leftClick(100, 100);
      expect(macosInterface.isConnected()).toBe(true);

      await macosInterface.disconnect();
    });

    it("should handle force close", async () => {
      const macosInterface = new MacOSComputerInterface(
        testParams.ipAddress,
        testParams.username,
        testParams.password,
        testParams.apiKey,
        testParams.vmName,
        false
      );

      await macosInterface.connect();
      expect(macosInterface.isConnected()).toBe(true);

      // Force close
      macosInterface.forceClose();
      expect(macosInterface.isConnected()).toBe(false);
    });
  });
});
