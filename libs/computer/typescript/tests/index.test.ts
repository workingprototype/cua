import { describe, expect, it } from "vitest";
import { Computer, OSType, VMProviderType } from "../src/index";

describe("Create Computer Instances", () => {
  it("should create a cloud computer", () => {
    const computer = Computer.create({
      vmProvider: VMProviderType.CLOUD,
      name: "computer-name",
      size: "small",
      osType: OSType.LINUX,
      apiKey: "asdf",
    });
  });
  it("should create a lume computer", () => {
    const computer = Computer.create({
      vmProvider: VMProviderType.LUME,
      display: { width: 1000, height: 1000, scale_factor: 1 },
      image: "computer-image",
      memory: "5GB",
      cpu: 2,
      name: "computer-name",
      osType: OSType.MACOS,
    });
  });
  it("should create a lumier computer", () => {
    const computer = Computer.create({
      vmProvider: VMProviderType.LUMIER,
      display: { width: 1000, height: 1000, scale_factor: 1 },
      image: "computer-image",
      memory: "5GB",
      cpu: 2,
      name: "computer-name",
      osType: OSType.MACOS,
    });
  });
});
