import { describe, expect, it } from "vitest";
import { Computer, OSType, VMProviderType } from "../src/index";

describe("Cloud Interface", () => {
  it("should create a cloud computer", () => {
    const computer = Computer.create({
      vmProvider: VMProviderType.CLOUD,
      name: "computer-name",
      size: "small",
      osType: OSType.LINUX,
      apiKey: "asdf",
    });
  });
});
