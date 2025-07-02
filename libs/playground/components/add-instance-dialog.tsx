"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

interface AddInstanceDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onAddInstance: (instance: {
    provider: string;
    name: string;
    os: string;
    type: "small" | "medium" | "large";
  }) => void;
}

const osOptions = {
  "cua-cloud": [
    { value: "ubuntu", label: "Ubuntu 22.04 LTS" }
  ],
  "lume": [
    { value: "macos", label: "macOS Sequoia" }
  ],
  "windows-sandbox": [
    { value: "windows", label: "Windows 11" }
  ],
  "host-computer": [
    { value: "linux", label: "Linux" },
    { value: "windows", label: "Windows" },
    { value: "macos", label: "macOS" }
  ]
};

const CuaCloudOptions = ({ 
  vmName, 
  setVmName, 
  os, 
  setOs 
}: {
  vmName: string;
  setVmName: (name: string) => void;
  os: string;
  setOs: (os: string) => void;
}) => (
  <div className="space-y-4">
    <div className="space-y-2">
      <Label htmlFor="cua-container-name">Container Name</Label>
      <Input
        id="cua-container-name"
        placeholder="Enter container name"
        value={vmName}
        onChange={(e) => setVmName(e.target.value)}
      />
    </div>
    <div className="space-y-2">
      <Label htmlFor="cua-os">Operating System</Label>
      <Select value={os} onValueChange={setOs}>
        <SelectTrigger>
          <SelectValue placeholder="Select OS" />
        </SelectTrigger>
        <SelectContent>
          {osOptions["cua-cloud"].map((option) => (
            <SelectItem key={option.value} value={option.value}>
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  </div>
);

const LumeOptions = ({ 
  vmName, 
  setVmName, 
  os, 
  setOs 
}: {
  vmName: string;
  setVmName: (name: string) => void;
  os: string;
  setOs: (os: string) => void;
}) => (
  <div className="space-y-4">
    <div className="space-y-2">
      <Label htmlFor="lume-container-name">Container Name</Label>
      <Input
        id="lume-container-name"
        placeholder="Enter container name"
        value={vmName}
        onChange={(e) => setVmName(e.target.value)}
      />
    </div>
    <div className="space-y-2">
      <Label htmlFor="lume-os">Operating System</Label>
      <Select value={os} onValueChange={setOs}>
        <SelectTrigger>
          <SelectValue placeholder="Select OS" />
        </SelectTrigger>
        <SelectContent>
          {osOptions["lume"].map((option) => (
            <SelectItem key={option.value} value={option.value}>
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  </div>
);

const WindowsSandboxOptions = ({ 
  vmName, 
  setVmName 
}: {
  vmName: string;
  setVmName: (name: string) => void;
}) => (
  <div className="space-y-4">
    <div className="space-y-2">
      <Label htmlFor="sandbox-name">Name</Label>
      <Input
        id="sandbox-name"
        placeholder="Enter name"
        value={vmName}
        onChange={(e) => setVmName(e.target.value)}
      />
    </div>
    <div className="space-y-2">
      <Label>Operating System</Label>
      <div className="p-3 bg-muted rounded-md">
        <span className="text-sm text-muted-foreground">Windows 11</span>
      </div>
    </div>
  </div>
);

const HostComputerOptions = ({ 
  vmName, 
  setVmName, 
  os, 
  setOs, 
  host, 
  setHost 
}: {
  vmName: string;
  setVmName: (name: string) => void;
  os: string;
  setOs: (os: string) => void;
  host: string;
  setHost: (host: string) => void;
}) => (
  <div className="space-y-4">
    <div className="space-y-2">
      <Label htmlFor="host-name">Name</Label>
      <Input
        id="host-name"
        placeholder="Enter name"
        value={vmName}
        onChange={(e) => setVmName(e.target.value)}
      />
    </div>
    <div className="space-y-2">
      <Label htmlFor="host-os">Operating System</Label>
      <Select value={os} onValueChange={setOs}>
        <SelectTrigger>
          <SelectValue placeholder="Select OS" />
        </SelectTrigger>
        <SelectContent>
          {osOptions["host-computer"].map((option) => (
            <SelectItem key={option.value} value={option.value}>
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
    <div className="space-y-2">
      <Label htmlFor="host-host">Host</Label>
      <Input
        id="host-host"
        value="localhost"
        disabled
        className="bg-muted"
      />
    </div>
  </div>
);

export function AddInstanceDialog({ open, onOpenChange, onAddInstance }: AddInstanceDialogProps) {
  const [provider, setProvider] = useState<string>("");
  const [vmName, setVmName] = useState<string>("");
  const [os, setOs] = useState<string>("");
  const [host, setHost] = useState<string>("localhost");

  const providers = [
    {
      value: "cua-cloud",
      label: "C/ua Cloud Containers",
      description: "Scalable cloud containers with flexible sizing options"
    },
    {
      value: "lume",
      label: "Lume",
      description: "Local virtual machines using Apple Virtualization"
    },
    {
      value: "windows-sandbox",
      label: "Windows Sandbox",
      description: "Isolated Windows environment for testing"
    },
    {
      value: "host-computer",
      label: "Host Computer",
      description: "Use the host computer as a provider"
    }
  ];

  const handleSubmit = () => {
    if (!provider || !vmName) return;
    
    const finalOs = provider === "windows-sandbox" ? "windows" : os;
    if (!finalOs && provider !== "windows-sandbox") return;

    onAddInstance({
      provider,
      name: vmName,
      os: finalOs,
      type: "small" // Default to small, can be expanded later
    });

    // Reset form
    setProvider("");
    setVmName("");
    setOs("");
    setHost("localhost");
    onOpenChange(false);
  };

  const renderProviderOptions = () => {
    switch (provider) {
      case "cua-cloud":
        return <CuaCloudOptions vmName={vmName} setVmName={setVmName} os={os} setOs={setOs} />;
      case "lume":
        return <LumeOptions vmName={vmName} setVmName={setVmName} os={os} setOs={setOs} />;
      case "windows-sandbox":
        return <WindowsSandboxOptions vmName={vmName} setVmName={setVmName} />;
      case "host-computer":
        return <HostComputerOptions vmName={vmName} setVmName={setVmName} os={os} setOs={setOs} host={host} setHost={setHost} />;
      default:
        return null;
    }
  };

  const isFormValid = () => {
    if (!provider || !vmName) return false;
    if (provider === "windows-sandbox") return true;
    if (provider === "host-computer") return !!os;
    return !!os;
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Add New Instance</DialogTitle>
          <DialogDescription>
            Choose a provider and configure your new virtual machine instance.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          {/* Provider Selection */}
          <div className="space-y-3">
            <Label>Provider</Label>
            <Select value={provider} onValueChange={setProvider}>
              <SelectTrigger className="py-6">
                <SelectValue placeholder="Select a provider" />
              </SelectTrigger>
              <SelectContent align="start">
                {providers.map((prov) => (
                  <SelectItem key={prov.value} value={prov.value} className="py-3">
                    <div className="flex flex-col items-start">
                      <span>{prov.label}</span>
                      <span className="text-xs text-muted-foreground">{prov.description}</span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Provider-specific Options */}
          {provider && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">
                  {providers.find(p => p.value === provider)?.label} Configuration
                </CardTitle>
                <CardDescription>
                  Configure the settings for your new instance.
                </CardDescription>
              </CardHeader>
              <CardContent>
                {renderProviderOptions()}
              </CardContent>
            </Card>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={!isFormValid()}>
            Create Instance
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
