"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface ComputerInstance {
  id: string;
  name: string;
  status: "running" | "stopped" | "starting";
  type: "small" | "medium" | "large";
  provider: string;
  password?: string; // Password for the noVNC
  os: string;
  ip?: string;
  uptime?: string;
  lastScreenshot?: string; // Base64 encoded screenshot
  lastScreenshotTime?: string; // ISO timestamp
}

interface ComputerStore {
  instances: ComputerInstance[];
  selectedInstance: string | null;
  setInstances: (instances: ComputerInstance[]) => void;
  addInstance: (instance: ComputerInstance) => void;
  setSelectedInstance: (instanceId: string | null) => void;
  getRunningInstances: () => ComputerInstance[];
  getAvailableInstances: () => ComputerInstance[];
  updateInstanceScreenshot: (instanceId: string, screenshot: string) => void;
  resetToDefault: () => void;
}

export const useComputerStore = create<ComputerStore>()(
  persist(
    (set, get) => ({
      instances: [
        {
          id: "1",
          name: "macos-sequoia-cua:latest",
          status: "running",
          type: "medium",
          provider: "lume",
          os: "macos-sequoia"
        },
        {
          id: "2",
          name: "Windows Sandbox",
          status: "running",
          type: "small",
          provider: "windows-sandbox",
          os: "windows"
        }
      ],
      selectedInstance: null,
      setInstances: (instances) => set({ instances }),
      addInstance: (instance) => set((state) => ({ 
        instances: [...state.instances, instance] 
      })),
      setSelectedInstance: (instanceId) => set({ selectedInstance: instanceId }),
      getRunningInstances: () => {
        const { instances } = get();
        return instances.filter(instance => instance.status === "running");
      },
      getAvailableInstances: () => {
        const { instances } = get();
        return instances.filter(instance => instance.status === "running" || instance.provider == "cua-cloud");
      },
      updateInstanceScreenshot: (instanceId, screenshot) => {
        const { instances } = get();
        const updatedInstances = instances.map(instance => {
          if (instance.id === instanceId) {
            return { ...instance, lastScreenshot: screenshot, lastScreenshotTime: new Date().toISOString() };
          }
          return instance;
        });
        set({ instances: updatedInstances });
      },
      resetToDefault: () => set({
        instances: [
          {
            id: "1",
            name: "macos-sequoia-cua:latest",
            status: "running",
            type: "medium",
            provider: "lume",
            os: "macos-sequoia"
          },
          {
            id: "2",
            name: "Windows Sandbox",
            status: "running",
            type: "small",
            provider: "windows-sandbox",
            os: "windows"
          }
        ],
        selectedInstance: null
      })
    }),
    {
      name: "computer-store",
    }
  )
);
