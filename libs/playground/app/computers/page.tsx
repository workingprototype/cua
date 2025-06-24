"use client";

import React, { useState } from "react";
import { ReusableSidebar } from "../../components/reusable-sidebar";
import { AddInstanceDialog } from "../../components/add-instance-dialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import Image from "next/image";
import { Plus, Monitor, Cpu, HardDrive, Wifi, ExternalLink, BookOpen } from "lucide-react";
import { useComputerStore, ComputerInstance } from "../hooks/useComputerStore";

export default function ComputersPage() {
  const { 
    instances, 
    selectedInstance, 
    setSelectedInstance, 
    addInstance 
  } = useComputerStore();
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [showGettingStarted, setShowGettingStarted] = useState(false);

  const handleAddInstance = () => {
    setShowAddDialog(true);
  };

  const handleCreateInstance = (instanceData: {
    provider: string;
    name: string;
    os: string;
    type: "small" | "medium" | "large";
  }) => {
    const newInstance: ComputerInstance = {
      id: Date.now().toString(),
      name: instanceData.name,
      status: "starting",
      type: instanceData.type,
      provider: instanceData.provider,
      os: instanceData.os
    };
    addInstance(newInstance);
    setSelectedInstance(newInstance.id);
    setShowAddDialog(false);
  };

  const handleShowGettingStarted = () => {
    setShowGettingStarted(true);
    setSelectedInstance(null); // Clear selected instance to show onboarding
  };

  const sidebarButtons = [
    {
      id: "add-instance",
      label: "Add Instance",
      icon: <Plus className="h-4 w-4" />,
      onClick: handleAddInstance
    },
    {
      id: "getting-started",
      label: "Getting Started",
      icon: <BookOpen className="h-4 w-4" />,
      onClick: handleShowGettingStarted
    }
  ];

  const getStatusColor = (status: string) => {
    switch (status) {
      case "running": return "bg-green-500";
      case "stopped": return "bg-red-500";
      case "starting": return "bg-yellow-500";
      default: return "bg-gray-500";
    }
  };

  const getOSIcon = (os: string) => {
    switch (os) {
      case "ubuntu":
        return <Image src="/os-icons/ubuntu.svg" alt="Ubuntu" width={16} height={16} className="flex-shrink-0 dark:invert" />;
      case "debian":
      case "centos":
        return <Image src="/os-icons/linux.svg" alt="Linux" width={16} height={16} className="flex-shrink-0 dark:invert" />;
      case "macos-sequoia":
        return <Image src="/os-icons/apple.svg" alt="macOS" width={16} height={16} className="flex-shrink-0 dark:invert" />;
      case "windows":
      case "windows-server":
        return <Image src="/os-icons/windows.svg" alt="Windows" width={16} height={16} className="flex-shrink-0 dark:invert" />;
      default:
        return <Monitor className="h-4 w-4 text-gray-500" />;
    }
  };

  const getTypeSpecs = (type: string) => {
    switch (type) {
      case "small": return { cpu: "1 vCPU", ram: "4GB RAM", description: "Perfect for simple automation tasks and testing" };
      case "medium": return { cpu: "2 vCPU", ram: "8GB RAM", description: "Ideal for most production workloads" };
      case "large": return { cpu: "8 vCPU", ram: "32GB RAM", description: "Built for complex, resource-intensive operations" };
      default: return { cpu: "Unknown", ram: "Unknown", description: "" };
    }
  };

  const instanceLinks = instances.map(instance => ({
    id: instance.id,
    label: instance.name,
    isActive: selectedInstance === instance.id,
    onClick: () => {
      setSelectedInstance(instance.id);
      setShowGettingStarted(false); // Hide getting started when instance is selected
    },
    icon: getOSIcon(instance.os)
  }));

  const OnboardingContent = () => (
    <div className="flex items-center justify-center h-full p-12">
      <div className="max-w-2xl text-center space-y-12 opacity-75">
        <div className="space-y-4">
          <Monitor className="h-16 w-16 mx-auto text-muted-foreground" />
          <h1 className="text-3xl font-bold">Get Started with C/ua Cloud Containers</h1>
          <p className="text-lg text-muted-foreground">
            Create powerful cloud containers for your automation tasks and workflows.
          </p>
        </div>

        <div className="space-y-6 text-left">
          <div className="space-y-4">
            <h2 className="text-xl font-semibold">Quick Setup Guide</h2>
            
            <div className="space-y-4">
              <div className="flex items-start gap-3 p-4 border rounded-lg">
                <div className="flex-shrink-0 w-6 h-6 bg-primary text-primary-foreground rounded-full flex items-center justify-center text-sm font-medium">
                  1
                </div>
                <div>
                  <h3 className="font-medium">Get Your API Key</h3>
                  <p className="text-sm text-muted-foreground mt-1">
                    Visit{" "}
                    <a 
                      href="https://trycua.com" 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="text-primary hover:underline inline-flex items-center gap-1"
                    >
                      trycua.com <ExternalLink className="h-3 w-3" />
                    </a>{" "}
                    to get your API key and access the dashboard.
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3 p-4 border rounded-lg">
                <div className="flex-shrink-0 w-6 h-6 bg-primary text-primary-foreground rounded-full flex items-center justify-center text-sm font-medium">
                  2
                </div>
                <div>
                  <h3 className="font-medium">Pick Your Operating System</h3>
                  <p className="text-sm text-muted-foreground mt-1 mb-3">
                    Choose from our supported operating systems for your containers.
                  </p>
                  <div className="flex items-center gap-4">
                    <div className="flex flex-col items-center gap-1">
                      <Image src="/os-icons/windows.svg" alt="Windows" width={24} height={24} className="dark:invert" />
                      <span className="text-xs text-muted-foreground">Windows</span>
                    </div>
                    <div className="flex flex-col items-center gap-1">
                      <Image src="/os-icons/ubuntu.svg" alt="Ubuntu" width={24} height={24} className="dark:invert" />
                      <span className="text-xs text-muted-foreground">Ubuntu</span>
                    </div>
                    <div className="flex flex-col items-center gap-1">
                      <Image src="/os-icons/apple.svg" alt="macOS" width={24} height={24} className="dark:invert" />
                      <span className="text-xs text-muted-foreground">macOS</span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="flex items-start gap-3 p-4 border rounded-lg">
                <div className="flex-shrink-0 w-6 h-6 bg-primary text-primary-foreground rounded-full flex items-center justify-center text-sm font-medium">
                  3
                </div>
                <div>
                  <h3 className="font-medium">Pick Your Computer Size</h3>
                  <p className="text-sm text-muted-foreground mt-1 mb-3">
                    Choose the right size for your workload.
                  </p>
                  <div className="space-y-2">
                    <div className="p-3 bg-muted rounded border-l-4 border-l-green-500">
                      <div className="font-medium text-sm">Small (1 vCPU, 4GB RAM)</div>
                      <div className="text-xs text-muted-foreground">Perfect for simple automation tasks and testing</div>
                    </div>
                    <div className="p-3 bg-muted rounded border-l-4 border-l-blue-500">
                      <div className="font-medium text-sm">Medium (2 vCPU, 8GB RAM)</div>
                      <div className="text-xs text-muted-foreground">Ideal for most production workloads</div>
                    </div>
                    <div className="p-3 bg-muted rounded border-l-4 border-l-purple-500">
                      <div className="font-medium text-sm">Large (8 vCPU, 32GB RAM)</div>
                      <div className="text-xs text-muted-foreground">Built for complex, resource-intensive operations</div>
                    </div>
                  </div>
                </div>
              </div>

              <div className="flex items-start gap-3 p-4 border rounded-lg">
                <div className="flex-shrink-0 w-6 h-6 bg-primary text-primary-foreground rounded-full flex items-center justify-center text-sm font-medium">
                  4
                </div>
                <div>
                  <h3 className="font-medium">Add the Instance to the Playground!</h3>
                  <p className="text-sm text-muted-foreground mt-1">
                    Click the "Add Instance" button to configure and launch your container in this interface.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <Button 
          onClick={handleAddInstance}
          size="lg" 
          className="mt-8"
        >
          <Plus className="h-4 w-4 mr-2" />
          Add Your First Instance
        </Button>
      </div>
    </div>
  );

  const InstanceDetails = ({ instance }: { instance: ComputerInstance }) => {
    const specs = getTypeSpecs(instance.type);
    
    return (
      <div className="p-8 space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">{instance.name}</h1>
            <div className="flex items-center gap-2 mt-2">
              <div className={`w-2 h-2 rounded-full ${getStatusColor(instance.status)}`} />
              <span className="text-sm text-muted-foreground capitalize">{instance.status}</span>
            </div>
          </div>
          <Badge variant="outline" className="capitalize">
            {instance.type}
          </Badge>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Cpu className="h-4 w-4" />
                CPU & Memory
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-1">
                <div className="text-lg font-semibold">{specs.cpu}</div>
                <div className="text-sm text-muted-foreground">{specs.ram}</div>
              </div>
            </CardContent>
          </Card>

          {instance.ip && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <Wifi className="h-4 w-4" />
                  Network
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-lg font-semibold">{instance.ip}</div>
                <div className="text-sm text-muted-foreground">Internal IP</div>
              </CardContent>
            </Card>
          )}

          {instance.uptime && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <HardDrive className="h-4 w-4" />
                  Uptime
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-lg font-semibold">{instance.uptime}</div>
                <div className="text-sm text-muted-foreground">Running time</div>
              </CardContent>
            </Card>
          )}
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Instance Configuration</CardTitle>
            <CardDescription>{specs.description}</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-sm font-medium">Status</span>
                <Badge 
                  variant={instance.status === "running" ? "default" : "secondary"}
                  className="capitalize"
                >
                  {instance.status}
                </Badge>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm font-medium">Type</span>
                <span className="text-sm capitalize">{instance.type}</span>
              </div>
              {instance.ip && (
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium">IP Address</span>
                  <span className="text-sm font-mono">{instance.ip}</span>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        <div className="flex gap-2">
          <Button 
            type="button"
            variant={instance.status === "running" ? "destructive" : "default"}
            onClick={() => {
              // Update instance status
            }}
          >
            {instance.status === "running" ? "Stop" : "Start"} Instance
          </Button>
          <Button type="button" variant="outline">
            Connect
          </Button>
          <Button type="button" variant="outline">
            Settings
          </Button>
        </div>
      </div>
    );
  };

  const selectedInstanceData = instances.find(i => i.id === selectedInstance);

  return (
    <div className="h-screen bg-background">
      <AddInstanceDialog 
        open={showAddDialog} 
        onOpenChange={setShowAddDialog} 
        onAddInstance={handleCreateInstance} 
      />
      <div className="flex h-full">
        <div className="w-64">
          <ReusableSidebar
            buttons={sidebarButtons}
            links={instanceLinks}
            linksTitle="Instances"
          />
        </div>
        <div className="flex-1 overflow-auto">
          {showGettingStarted ? (
            <OnboardingContent />
          ) : selectedInstanceData ? (
            <InstanceDetails instance={selectedInstanceData} />
          ) : (
            <OnboardingContent />
          )}
        </div>
      </div>
    </div>
  );
}
