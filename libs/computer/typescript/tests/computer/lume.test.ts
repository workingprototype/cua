import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { LumeComputer } from "../../src/computer/providers/lume";
import { VMProviderType, OSType } from "../../src/computer/types";
import type { LumeComputerConfig, Display } from "../../src/computer/types";
import type { VMInfo } from "../../src/util/lume";
import * as lumeApi from "../../src/util/lume";

// Mock the lume API module
vi.mock("../../src/util/lume", () => ({
  lumeApiGet: vi.fn(),
  lumeApiRun: vi.fn(),
  lumeApiStop: vi.fn(),
  lumeApiUpdate: vi.fn(),
  lumeApiPull: vi.fn(),
  lumeApiDelete: vi.fn(),
}));

// Mock pino logger
vi.mock("pino", () => ({
  default: () => ({
    info: vi.fn(),
    error: vi.fn(),
    debug: vi.fn(),
    warn: vi.fn(),
  }),
}));

describe("LumeComputer", () => {
  const mockVMInfo: VMInfo = {
    name: "test-vm",
    status: "running",
    diskSize: { allocated: 1024, total: 10240 },
    memorySize: 2048,
    os: "macos",
    display: "1920x1080",
    locationName: "local",
    cpuCount: 4,
    ipAddress: "192.168.1.100",
    vncUrl: "vnc://localhost:5900",
    sharedDirectories: [],
  };

  const defaultConfig: LumeComputerConfig = {
    name: "test-vm",
    osType: OSType.MACOS,
    vmProvider: VMProviderType.LUME,
    display: "1920x1080",
    memory: "8GB",
    cpu: 4,
    image: "macos-sequoia-cua:latest",
    port: 7777,
    host: "localhost",
    ephemeral: false,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("constructor", () => {
    it("should initialize with default config", () => {
      const computer = new LumeComputer(defaultConfig);
      expect(computer.getName()).toBe("test-vm");
      expect(computer.getOSType()).toBe(OSType.MACOS);
      expect(computer.getVMProviderType()).toBe(VMProviderType.LUME);
    });

    it("should accept display as string", () => {
      const config = { ...defaultConfig, display: "1024x768" };
      const computer = new LumeComputer(config);
      expect(computer).toBeDefined();
    });

    it("should accept display as Display object", () => {
      const display: Display = { width: 1920, height: 1080, scale_factor: 2 };
      const config = { ...defaultConfig, display };
      const computer = new LumeComputer(config);
      expect(computer).toBeDefined();
    });
  });

  describe("getVm", () => {
    it("should get VM info successfully", async () => {
      vi.mocked(lumeApi.lumeApiGet).mockResolvedValue([mockVMInfo]);

      const computer = new LumeComputer(defaultConfig);
      const result = await computer.getVm("test-vm");

      expect(lumeApi.lumeApiGet).toHaveBeenCalledWith(
        "test-vm",
        "localhost",
        7777,
        undefined
      );
      expect(result).toEqual(mockVMInfo);
    });

    it("should handle VM not found error", async () => {
      vi.mocked(lumeApi.lumeApiGet).mockResolvedValue([]);

      const computer = new LumeComputer(defaultConfig);
      await expect(computer.getVm("test-vm")).rejects.toThrow("VM Not Found.");
    });

    it("should handle stopped VM state", async () => {
      const stoppedVM = {
        ...mockVMInfo,
        status: "stopped",
        ipAddress: undefined,
      };
      vi.mocked(lumeApi.lumeApiGet).mockResolvedValue([stoppedVM]);

      const computer = new LumeComputer(defaultConfig);
      const result = await computer.getVm("test-vm");

      expect(result.status).toBe("stopped");
      expect(result.name).toBe("test-vm");
    });

    it("should handle VM without IP address", async () => {
      const noIpVM = { ...mockVMInfo, ipAddress: undefined };
      vi.mocked(lumeApi.lumeApiGet).mockResolvedValue([noIpVM]);

      const computer = new LumeComputer(defaultConfig);
      const result = await computer.getVm("test-vm");

      expect(result).toEqual(noIpVM);
    });

    it("should pass storage parameter", async () => {
      vi.mocked(lumeApi.lumeApiGet).mockResolvedValue([mockVMInfo]);

      const computer = new LumeComputer(defaultConfig);
      await computer.getVm("test-vm", "/custom/storage");

      expect(lumeApi.lumeApiGet).toHaveBeenCalledWith(
        "test-vm",
        "localhost",
        7777,
        "/custom/storage"
      );
    });
  });

  describe("listVm", () => {
    it("should list all VMs", async () => {
      const vmList = [mockVMInfo, { ...mockVMInfo, name: "another-vm" }];
      vi.mocked(lumeApi.lumeApiGet).mockResolvedValue(vmList);

      const computer = new LumeComputer(defaultConfig);
      const result = await computer.listVm();

      expect(lumeApi.lumeApiGet).toHaveBeenCalledWith("", "localhost", 7777);
      expect(result).toEqual(vmList);
    });
  });

  describe("runVm", () => {
    it("should run VM when it already exists", async () => {
      vi.mocked(lumeApi.lumeApiGet).mockResolvedValue([mockVMInfo]);
      vi.mocked(lumeApi.lumeApiRun).mockResolvedValue(mockVMInfo);

      const computer = new LumeComputer(defaultConfig);
      const runOpts = { memory: "4GB" };
      const result = await computer.runVm(
        "macos-sequoia-cua:latest",
        "test-vm",
        runOpts
      );

      expect(lumeApi.lumeApiGet).toHaveBeenCalledWith(
        "test-vm",
        "localhost",
        7777,
        undefined
      );
      expect(lumeApi.lumeApiRun).toHaveBeenCalledWith(
        "test-vm",
        "localhost",
        7777,
        runOpts,
        undefined
      );
      expect(result).toEqual(mockVMInfo);
    });

    it("should pull and run VM when it doesn't exist", async () => {
      vi.mocked(lumeApi.lumeApiGet).mockRejectedValueOnce(
        new Error("VM not found")
      );
      vi.mocked(lumeApi.lumeApiPull).mockResolvedValue(mockVMInfo);
      vi.mocked(lumeApi.lumeApiRun).mockResolvedValue(mockVMInfo);

      const computer = new LumeComputer(defaultConfig);
      const result = await computer.runVm(
        "macos-sequoia-cua:latest",
        "test-vm"
      );

      expect(lumeApi.lumeApiGet).toHaveBeenCalled();
      expect(lumeApi.lumeApiPull).toHaveBeenCalledWith(
        "macos-sequoia-cua:latest",
        "test-vm",
        "localhost",
        7777,
        undefined,
        "ghcr.io",
        "trycua"
      );
      expect(lumeApi.lumeApiRun).toHaveBeenCalled();
      expect(result).toEqual(mockVMInfo);
    });

    it("should handle pull failure", async () => {
      vi.mocked(lumeApi.lumeApiGet).mockRejectedValueOnce(
        new Error("VM not found")
      );
      vi.mocked(lumeApi.lumeApiPull).mockRejectedValue(
        new Error("Pull failed")
      );

      const computer = new LumeComputer(defaultConfig);
      await expect(
        computer.runVm("macos-sequoia-cua:latest", "test-vm")
      ).rejects.toThrow("Pull failed");
    });

    it("should pass storage parameter", async () => {
      vi.mocked(lumeApi.lumeApiGet).mockResolvedValue([mockVMInfo]);
      vi.mocked(lumeApi.lumeApiRun).mockResolvedValue(mockVMInfo);

      const computer = new LumeComputer(defaultConfig);
      await computer.runVm(
        "macos-sequoia-cua:latest",
        "test-vm",
        {},
        "/storage"
      );

      expect(lumeApi.lumeApiGet).toHaveBeenCalledWith(
        "test-vm",
        "localhost",
        7777,
        "/storage"
      );
      expect(lumeApi.lumeApiRun).toHaveBeenCalledWith(
        "test-vm",
        "localhost",
        7777,
        {},
        "/storage"
      );
    });
  });

  describe("stopVm", () => {
    it("should stop VM normally", async () => {
      vi.mocked(lumeApi.lumeApiStop).mockResolvedValue(mockVMInfo);

      const computer = new LumeComputer(defaultConfig);
      const result = await computer.stopVm("test-vm");

      expect(lumeApi.lumeApiStop).toHaveBeenCalledWith(
        "test-vm",
        "localhost",
        7777,
        undefined
      );
      expect(result).toEqual(mockVMInfo);
    });

    it("should delete VM after stopping in ephemeral mode", async () => {
      const stoppedVM = { ...mockVMInfo, status: "stopped" };
      vi.mocked(lumeApi.lumeApiStop).mockResolvedValue(stoppedVM);
      vi.mocked(lumeApi.lumeApiDelete).mockResolvedValue(null);

      const ephemeralConfig = { ...defaultConfig, ephemeral: true };
      const computer = new LumeComputer(ephemeralConfig);
      const result = await computer.stopVm("test-vm");

      expect(lumeApi.lumeApiStop).toHaveBeenCalled();
      expect(lumeApi.lumeApiDelete).toHaveBeenCalledWith(
        "test-vm",
        "localhost",
        7777,
        undefined,
        false,
        false
      );
      expect(result).toMatchObject({
        ...stoppedVM,
        deleted: true,
        deleteResult: null,
      });
    });

    it("should handle delete failure in ephemeral mode", async () => {
      vi.mocked(lumeApi.lumeApiStop).mockResolvedValue(mockVMInfo);
      vi.mocked(lumeApi.lumeApiDelete).mockRejectedValue(
        new Error("Delete failed")
      );

      const ephemeralConfig = { ...defaultConfig, ephemeral: true };
      const computer = new LumeComputer(ephemeralConfig);

      await expect(computer.stopVm("test-vm")).rejects.toThrow(
        "Failed to delete ephemeral VM test-vm: Error: Failed to delete VM: Error: Delete failed"
      );
    });
  });

  describe("pullVm", () => {
    it("should pull VM image successfully", async () => {
      vi.mocked(lumeApi.lumeApiPull).mockResolvedValue(mockVMInfo);

      const computer = new LumeComputer(defaultConfig);
      const result = await computer.pullVm("test-vm", "ubuntu:latest");

      expect(lumeApi.lumeApiPull).toHaveBeenCalledWith(
        "ubuntu:latest",
        "test-vm",
        "localhost",
        7777,
        undefined,
        "ghcr.io",
        "trycua"
      );
      expect(result).toEqual(mockVMInfo);
    });

    it("should throw error if image parameter is missing", async () => {
      const computer = new LumeComputer(defaultConfig);
      await expect(computer.pullVm("test-vm", "")).rejects.toThrow(
        "Image parameter is required for pullVm"
      );
    });

    it("should use custom registry and organization", async () => {
      vi.mocked(lumeApi.lumeApiPull).mockResolvedValue(mockVMInfo);

      const computer = new LumeComputer(defaultConfig);
      await computer.pullVm(
        "test-vm",
        "custom:tag",
        "/storage",
        "docker.io",
        "myorg"
      );

      expect(lumeApi.lumeApiPull).toHaveBeenCalledWith(
        "custom:tag",
        "test-vm",
        "localhost",
        7777,
        "/storage",
        "docker.io",
        "myorg"
      );
    });

    it("should handle pull failure", async () => {
      vi.mocked(lumeApi.lumeApiPull).mockRejectedValue(
        new Error("Network error")
      );

      const computer = new LumeComputer(defaultConfig);
      await expect(computer.pullVm("test-vm", "ubuntu:latest")).rejects.toThrow(
        "Failed to pull VM: Error: Network error"
      );
    });
  });

  describe("deleteVm", () => {
    it("should delete VM successfully", async () => {
      vi.mocked(lumeApi.lumeApiDelete).mockResolvedValue(null);

      const computer = new LumeComputer(defaultConfig);
      const result = await computer.deleteVm("test-vm");

      expect(lumeApi.lumeApiDelete).toHaveBeenCalledWith(
        "test-vm",
        "localhost",
        7777,
        undefined,
        false,
        false
      );
      expect(result).toBeNull();
    });

    it("should handle delete failure", async () => {
      vi.mocked(lumeApi.lumeApiDelete).mockRejectedValue(
        new Error("Permission denied")
      );

      const computer = new LumeComputer(defaultConfig);
      await expect(computer.deleteVm("test-vm")).rejects.toThrow(
        "Failed to delete VM: Error: Permission denied"
      );
    });

    it("should pass storage parameter", async () => {
      vi.mocked(lumeApi.lumeApiDelete).mockResolvedValue(null);

      const computer = new LumeComputer(defaultConfig);
      await computer.deleteVm("test-vm", "/storage");

      expect(lumeApi.lumeApiDelete).toHaveBeenCalledWith(
        "test-vm",
        "localhost",
        7777,
        "/storage",
        false,
        false
      );
    });
  });

  describe("updateVm", () => {
    it("should update VM configuration", async () => {
      const updatedVM = { ...mockVMInfo, memorySize: 4096 };
      vi.mocked(lumeApi.lumeApiUpdate).mockResolvedValue(updatedVM);

      const computer = new LumeComputer(defaultConfig);
      const updateOpts = { memory: "4GB" };
      const result = await computer.updateVm("test-vm", updateOpts);

      expect(lumeApi.lumeApiUpdate).toHaveBeenCalledWith(
        "test-vm",
        "localhost",
        7777,
        updateOpts,
        undefined,
        false,
        false
      );
      expect(result).toEqual(updatedVM);
    });

    it("should pass storage parameter", async () => {
      vi.mocked(lumeApi.lumeApiUpdate).mockResolvedValue(mockVMInfo);

      const computer = new LumeComputer(defaultConfig);
      await computer.updateVm("test-vm", {}, "/storage");

      expect(lumeApi.lumeApiUpdate).toHaveBeenCalledWith(
        "test-vm",
        "localhost",
        7777,
        {},
        "/storage",
        false,
        false
      );
    });
  });

  describe("getIp", () => {
    it("should return IP address immediately if available", async () => {
      vi.mocked(lumeApi.lumeApiGet).mockResolvedValue([mockVMInfo]);

      const computer = new LumeComputer(defaultConfig);
      const ip = await computer.getIp("test-vm");

      expect(ip).toBe("192.168.1.100");
      expect(lumeApi.lumeApiGet).toHaveBeenCalledTimes(1);
    });

    it("should retry until IP address is available", async () => {
      const noIpVM = { ...mockVMInfo, ipAddress: undefined };
      vi.mocked(lumeApi.lumeApiGet)
        .mockResolvedValueOnce([noIpVM])
        .mockResolvedValueOnce([noIpVM])
        .mockResolvedValueOnce([mockVMInfo]);

      const computer = new LumeComputer(defaultConfig);
      const ip = await computer.getIp("test-vm", undefined, 0.1); // Short retry delay for testing

      expect(ip).toBe("192.168.1.100");
      expect(lumeApi.lumeApiGet).toHaveBeenCalledTimes(3);
    });

    it("should throw error if VM is stopped", async () => {
      const stoppedVM = {
        ...mockVMInfo,
        status: "stopped",
        ipAddress: undefined,
      };
      vi.mocked(lumeApi.lumeApiGet).mockResolvedValue([stoppedVM]);

      const computer = new LumeComputer(defaultConfig);
      await expect(computer.getIp("test-vm")).rejects.toThrow(
        "VM test-vm is in 'stopped' state and will not get an IP address"
      );
    });

    it("should throw error if VM is in error state", async () => {
      const errorVM = { ...mockVMInfo, status: "error", ipAddress: undefined };
      vi.mocked(lumeApi.lumeApiGet).mockResolvedValue([errorVM]);

      const computer = new LumeComputer(defaultConfig);
      await expect(computer.getIp("test-vm")).rejects.toThrow(
        "VM test-vm is in 'error' state and will not get an IP address"
      );
    });

    it("should handle getVm errors", async () => {
      vi.mocked(lumeApi.lumeApiGet).mockRejectedValue(
        new Error("Network error")
      );

      const computer = new LumeComputer(defaultConfig);
      await expect(computer.getIp("test-vm")).rejects.toThrow("Network error");
    });

    it("should pass storage parameter", async () => {
      vi.mocked(lumeApi.lumeApiGet).mockResolvedValue([mockVMInfo]);

      const computer = new LumeComputer(defaultConfig);
      await computer.getIp("test-vm", "/storage");

      expect(lumeApi.lumeApiGet).toHaveBeenCalledWith(
        "test-vm",
        "localhost",
        7777,
        "/storage"
      );
    });
  });

  describe("integration scenarios", () => {
    it("should handle full VM lifecycle", async () => {
      // Simulate VM not existing initially
      vi.mocked(lumeApi.lumeApiGet).mockRejectedValueOnce(
        new Error("VM not found")
      );
      vi.mocked(lumeApi.lumeApiPull).mockResolvedValue(mockVMInfo);

      // Simulate VM starting without IP, then getting IP
      const startingVM = {
        ...mockVMInfo,
        ipAddress: undefined,
        status: "starting",
      };
      vi.mocked(lumeApi.lumeApiRun).mockResolvedValue(startingVM);
      vi.mocked(lumeApi.lumeApiGet)
        .mockResolvedValueOnce([startingVM])
        .mockResolvedValueOnce([mockVMInfo]);

      // Simulate stop
      const stoppedVM = { ...mockVMInfo, status: "stopped" };
      vi.mocked(lumeApi.lumeApiStop).mockResolvedValue(stoppedVM);

      const computer = new LumeComputer(defaultConfig);

      // Run VM (should pull first)
      await computer.runVm("macos-sequoia-cua:latest", "test-vm");

      // Get IP (should retry once)
      const ip = await computer.getIp("test-vm", undefined, 0.1);
      expect(ip).toBe("192.168.1.100");

      // Stop VM
      const stopResult = await computer.stopVm("test-vm");
      expect(stopResult.status).toBe("stopped");
    });

    it("should handle ephemeral VM lifecycle", async () => {
      const ephemeralConfig = { ...defaultConfig, ephemeral: true };
      const computer = new LumeComputer(ephemeralConfig);

      // Setup mocks
      vi.mocked(lumeApi.lumeApiGet).mockResolvedValue([mockVMInfo]);
      vi.mocked(lumeApi.lumeApiRun).mockResolvedValue(mockVMInfo);
      vi.mocked(lumeApi.lumeApiStop).mockResolvedValue({
        ...mockVMInfo,
        status: "stopped",
      });
      vi.mocked(lumeApi.lumeApiDelete).mockResolvedValue(null);

      // Run and stop ephemeral VM
      await computer.runVm("macos-sequoia-cua:latest", "test-vm");
      const result = await computer.stopVm("test-vm");

      // Verify VM was deleted
      expect(lumeApi.lumeApiDelete).toHaveBeenCalled();
      expect(result).toBe(null);
    });
  });
});
