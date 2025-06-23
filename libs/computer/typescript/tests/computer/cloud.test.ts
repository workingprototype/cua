import { describe, expect, it } from "vitest";
import { OSType } from "../../src/types";
import { Computer } from "../../src";

describe("Computer Cloud", () => {
  it("Should create computer instance", () => {
    const cloud = new Computer({
      apiKey: "asdf",
      name: "s-linux-1234",
      osType: OSType.LINUX,
    });
    expect(cloud).toBeInstanceOf(Computer);
  });
});
