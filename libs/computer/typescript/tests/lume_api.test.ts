import { describe, expect, it, vi } from "vitest";
import {
  lumeApiGet,
  lumeApiRun,
  lumeApiStop,
  lumeApiUpdate,
  lumeApiPull,
  lumeApiDelete,
  type VMInfo,
  type RunOptions,
  type UpdateOptions,
} from "../src/util/lume";

const PORT = 1213;
const HOST = "localhost";

describe("Lume API", () => {
  describe("lumeApiGet", () => {
    it("should fetch VM information successfully", async () => {
      // Mock fetch for this test - API returns a single VMDetails object
      const mockVMInfo: VMInfo = {
        name: "test-vm",
        status: "stopped",
        diskSize: { allocated: 1024, total: 10240 },
        memorySize: 2048,
        os: "ubuntu",
        display: "1920x1080",
        locationName: "local",
        cpuCount: 2,
        sharedDirectories: [
          {
            hostPath: "/home/user/shared",
            tag: "shared",
            readOnly: false,
          },
        ],
      };

      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => mockVMInfo,
        headers: new Headers({ "content-type": "application/json" }),
      } as Response);

      const result = await lumeApiGet("test-vm", HOST, PORT);

      expect(result).toEqual([mockVMInfo]);
      expect(fetch).toHaveBeenCalledWith(
        `http://${HOST}:${PORT}/lume/vms/test-vm`,
        expect.objectContaining({
          method: "GET",
          signal: expect.any(AbortSignal),
        })
      );
    });

    it("should list all VMs when name is empty", async () => {
      // Mock fetch for list VMs - API returns an array
      const mockVMList: VMInfo[] = [
        {
          name: "vm1",
          status: "running",
          diskSize: { allocated: 1024, total: 10240 },
          memorySize: 2048,
          os: "ubuntu",
          display: "1920x1080",
          locationName: "local",
          cpuCount: 2,
        },
        {
          name: "vm2",
          status: "stopped",
          diskSize: { allocated: 2048, total: 10240 },
          memorySize: 4096,
          os: "debian",
          display: "1920x1080",
          locationName: "local",
          cpuCount: 4,
        },
      ];

      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => mockVMList,
        headers: new Headers({ "content-type": "application/json" }),
      } as Response);

      const result = await lumeApiGet("", HOST, PORT);

      expect(result).toEqual(mockVMList);
      expect(fetch).toHaveBeenCalledWith(
        `http://${HOST}:${PORT}/lume/vms`,
        expect.objectContaining({
          method: "GET",
          signal: expect.any(AbortSignal),
        })
      );
    });

    it("should handle storage parameter encoding correctly", async () => {
      const mockVMInfo: VMInfo = {
        name: "test-vm",
        status: "stopped",
        diskSize: { allocated: 1024, total: 10240 },
        memorySize: 2048,
        os: "ubuntu",
        display: "1920x1080",
        locationName: "local",
        cpuCount: 2,
      };

      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => mockVMInfo,
        headers: new Headers({ "content-type": "application/json" }),
      } as Response);

      const storage = "/path/with spaces/and#special?chars";
      await lumeApiGet("test-vm", HOST, PORT, storage);

      const expectedUrl = `http://${HOST}:${PORT}/lume/vms/test-vm?storage=${encodeURIComponent(
        storage
      )}`;
      expect(fetch).toHaveBeenCalledWith(
        expectedUrl,
        expect.objectContaining({
          method: "GET",
        })
      );
    });

    it("should handle HTTP errors", async () => {
      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: false,
        status: 404,
        headers: new Headers(),
      } as Response);

      await expect(lumeApiGet("test-vm", HOST, PORT)).rejects.toThrow(
        "API request failed: HTTP error returned from API server (status: 404)"
      );
    });

    it("should handle connection refused errors", async () => {
      const error = new Error("Connection refused");
      (error as Error).message = "ECONNREFUSED";
      global.fetch = vi.fn().mockRejectedValueOnce(error);

      await expect(lumeApiGet("test-vm", HOST, PORT)).rejects.toThrow(
        "API request failed: Failed to connect to the API server - it might still be starting up"
      );
    });

    it("should handle timeout errors", async () => {
      const error = new Error("Request aborted");
      error.name = "AbortError";
      global.fetch = vi.fn().mockRejectedValueOnce(error);

      await expect(lumeApiGet("test-vm", HOST, PORT)).rejects.toThrow(
        "API request failed: Operation timeout - the API server is taking too long to respond"
      );
    });

    it("should handle host not found errors", async () => {
      const error = new Error("Host not found");
      (error as Error).message = "ENOTFOUND";
      global.fetch = vi.fn().mockRejectedValueOnce(error);

      await expect(lumeApiGet("test-vm", HOST, PORT)).rejects.toThrow(
        "API request failed: Failed to resolve host - check the API server address"
      );
    });
  });

  describe("lumeApiRun", () => {
    it("should run a VM successfully", async () => {
      const mockVMInfo: VMInfo = {
        name: "test-vm",
        status: "running",
        diskSize: { allocated: 1024, total: 10240 },
        memorySize: 2048,
        os: "ubuntu",
        display: "1920x1080",
        locationName: "local",
        cpuCount: 2,
        vncUrl: "vnc://localhost:5900",
        ipAddress: "192.168.1.100",
      };

      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => mockVMInfo,
        headers: new Headers({ "content-type": "application/json" }),
      } as Response);

      const runOpts: RunOptions = {
        memory: "2G",
        cpus: 2,
        display: "1920x1080",
      };

      const result = await lumeApiRun("test-vm", HOST, PORT, runOpts);

      expect(result).toEqual(mockVMInfo);
      expect(fetch).toHaveBeenCalledWith(
        `http://${HOST}:${PORT}/lume/vms/test-vm/run`,
        expect.objectContaining({
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(runOpts),
          signal: expect.any(AbortSignal),
        })
      );
    });

    it("should handle storage parameter in run request", async () => {
      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => ({ name: "test-vm" }),
        headers: new Headers({ "content-type": "application/json" }),
      } as Response);

      const storage = "/custom/storage/path";
      const runOpts: RunOptions = { memory: "1G" };

      await lumeApiRun("test-vm", HOST, PORT, runOpts, storage);

      const expectedUrl = `http://${HOST}:${PORT}/lume/vms/test-vm/run?storage=${encodeURIComponent(
        storage
      )}`;
      expect(fetch).toHaveBeenCalledWith(
        expectedUrl,
        expect.objectContaining({
          method: "POST",
        })
      );
    });

    it("should handle run errors", async () => {
      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: false,
        status: 500,
        headers: new Headers(),
      } as Response);

      await expect(lumeApiRun("test-vm", HOST, PORT, {})).rejects.toThrow(
        "API request failed: HTTP error returned from API server (status: 500)"
      );
    });
  });

  describe("lumeApiStop", () => {
    it("should stop a VM successfully", async () => {
      const mockVMInfo: VMInfo = {
        name: "test-vm",
        status: "stopped",
        diskSize: { allocated: 1024, total: 10240 },
        memorySize: 2048,
        os: "ubuntu",
        display: "1920x1080",
        locationName: "local",
        cpuCount: 2,
      };

      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => mockVMInfo,
        headers: new Headers({ "content-type": "application/json" }),
      } as Response);

      const result = await lumeApiStop("test-vm", HOST, PORT);

      expect(result).toEqual(mockVMInfo);
      expect(fetch).toHaveBeenCalledWith(
        `http://${HOST}:${PORT}/lume/vms/test-vm/stop`,
        expect.objectContaining({
          method: "POST",
          signal: expect.any(AbortSignal),
          headers: {
            "Content-Type": "application/json",
          },
          body: "{}",
        })
      );
    });

    it("should handle storage parameter in stop request", async () => {
      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => ({ name: "test-vm" }),
        headers: new Headers({ "content-type": "application/json" }),
      } as Response);

      const storage = "/storage/path";
      await lumeApiStop("test-vm", HOST, PORT, storage);

      const expectedUrl = `http://${HOST}:${PORT}/lume/vms/test-vm/stop?storage=${encodeURIComponent(
        storage
      )}`;
      expect(fetch).toHaveBeenCalledWith(
        expectedUrl,
        expect.objectContaining({
          method: "POST",
        })
      );
    });
  });

  describe("lumeApiUpdate", () => {
    it("should update VM settings successfully", async () => {
      const mockVMInfo: VMInfo = {
        name: "test-vm",
        status: "stopped",
        diskSize: { allocated: 1024, total: 10240 },
        memorySize: 4096,
        os: "ubuntu",
        display: "2560x1440",
        locationName: "local",
        cpuCount: 2,
      };

      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => mockVMInfo,
        headers: new Headers({ "content-type": "application/json" }),
      } as Response);

      const updateOpts: UpdateOptions = {
        memory: "4G",
        display: "2560x1440",
      };

      const result = await lumeApiUpdate("test-vm", HOST, PORT, updateOpts);

      expect(result).toEqual(mockVMInfo);
      expect(fetch).toHaveBeenCalledWith(
        `http://${HOST}:${PORT}/lume/vms/test-vm/update`,
        expect.objectContaining({
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(updateOpts),
          signal: expect.any(AbortSignal),
        })
      );
    });

    it("should handle empty update options", async () => {
      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => ({ name: "test-vm" }),
        headers: new Headers({ "content-type": "application/json" }),
      } as Response);

      await lumeApiUpdate("test-vm", HOST, PORT, {});

      expect(fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          body: "{}",
        })
      );
    });
  });

  describe("lumeApiPull", () => {
    it("should pull a VM image successfully", async () => {
      const mockVMInfo: VMInfo = {
        name: "pulled-vm",
        status: "stopped",
        diskSize: { allocated: 2048, total: 10240 },
        memorySize: 2048,
        os: "ubuntu",
        display: "1920x1080",
        locationName: "local",
        cpuCount: 2,
      };

      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => mockVMInfo,
        headers: new Headers({ "content-type": "application/json" }),
      } as Response);

      const result = await lumeApiPull(
        "ubuntu:latest",
        "pulled-vm",
        HOST,
        PORT
      );

      expect(result).toEqual(mockVMInfo);
      expect(fetch).toHaveBeenCalledWith(
        `http://${HOST}:${PORT}/lume/pull`,
        expect.objectContaining({
          method: "POST",
          signal: expect.any(AbortSignal),
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            image: "ubuntu:latest",
            name: "pulled-vm",
            registry: "ghcr.io",
            organization: "trycua",
          }),
        })
      );
    });

    it("should use custom registry and organization", async () => {
      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => ({ name: "custom-vm" }),
        headers: new Headers({ "content-type": "application/json" }),
      } as Response);

      await lumeApiPull(
        "custom:tag",
        "custom-vm",
        HOST,
        PORT,
        undefined,
        "docker.io",
        "myorg"
      );

      expect(fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          body: JSON.stringify({
            image: "custom:tag",
            name: "custom-vm",
            registry: "docker.io",
            organization: "myorg",
          }),
        })
      );
    });

    it("should handle storage parameter in pull request", async () => {
      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => ({ name: "test-vm" }),
        headers: new Headers({ "content-type": "application/json" }),
      } as Response);

      const storage = "/custom/storage";
      await lumeApiPull("image:tag", "test-vm", HOST, PORT, storage);

      const expectedUrl = `http://${HOST}:${PORT}/lume/pull?storage=${encodeURIComponent(
        storage
      )}`;
      expect(fetch).toHaveBeenCalledWith(
        expectedUrl,
        expect.objectContaining({
          method: "POST",
        })
      );
    });
  });

  describe("lumeApiDelete", () => {
    it("should delete a VM successfully", async () => {
      const mockVMInfo: VMInfo = {
        name: "test-vm",
        status: "deleted",
        diskSize: { allocated: 0, total: 0 },
        memorySize: 0,
        os: "ubuntu",
        display: "",
        locationName: "local",
        cpuCount: 0,
      };

      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => mockVMInfo,
        headers: new Headers({ "content-type": "application/json" }),
      } as Response);

      const result = await lumeApiDelete("test-vm", HOST, PORT);

      expect(result).toEqual(mockVMInfo);
      expect(fetch).toHaveBeenCalledWith(
        `http://${HOST}:${PORT}/lume/vms/test-vm`,
        expect.objectContaining({
          method: "DELETE",
          signal: expect.any(AbortSignal),
        })
      );
    });

    it("should handle storage parameter in delete request", async () => {
      const storage = "/custom/storage";
      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => null,
        headers: new Headers(),
      } as Response);

      await lumeApiDelete("test-vm", HOST, PORT, storage);

      const expectedUrl = `http://${HOST}:${PORT}/lume/vms/test-vm?storage=${encodeURIComponent(
        storage
      )}`;
      expect(fetch).toHaveBeenCalledWith(
        expectedUrl,
        expect.objectContaining({
          method: "DELETE",
        })
      );
    });

    it("should handle 404 as successful deletion", async () => {
      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: false,
        status: 404,
        headers: new Headers(),
      } as Response);

      const result = await lumeApiDelete("non-existent-vm", HOST, PORT);

      expect(result).toBeNull();
    });

    it("should throw error for non-404 HTTP errors", async () => {
      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: false,
        status: 500,
        headers: new Headers(),
      } as Response);

      await expect(lumeApiDelete("test-vm", HOST, PORT)).rejects.toThrow(
        "API request failed: HTTP error returned from API server (status: 500)"
      );
    });
  });

  describe("Debug and Verbose Logging", () => {
    it("should log debug information when debug is true", async () => {
      const consoleSpy = vi.spyOn(console, "log").mockImplementation(() => {});

      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => [{ name: "test-vm", cpuCount: 2 }],
        headers: new Headers({ "content-type": "application/json" }),
      } as Response);

      await lumeApiGet("", HOST, PORT, undefined, true); // Empty name for list

      expect(consoleSpy).toHaveBeenCalledWith(
        expect.stringContaining("DEBUG: API response:")
      );

      consoleSpy.mockRestore();
    });

    it("should log verbose information when verbose is true", async () => {
      const consoleSpy = vi.spyOn(console, "log").mockImplementation(() => {});

      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => ({ name: "test-vm", cpuCount: 2 }),
        headers: new Headers({ "content-type": "application/json" }),
      } as Response);

      await lumeApiRun(
        "test-vm",
        HOST,
        PORT,
        { memory: "1G" },
        undefined,
        false,
        true
      );

      expect(consoleSpy).toHaveBeenCalled();

      consoleSpy.mockRestore();
    });
  });

  describe("Error Message Handling", () => {
    it("should handle generic errors with message", async () => {
      const error = new Error("Custom error message");
      global.fetch = vi.fn().mockRejectedValueOnce(error);

      await expect(lumeApiGet("test-vm", HOST, PORT)).rejects.toThrow(
        "API request failed: Custom error message"
      );
    });
  });
});
