"use client";

import React, { useState } from "react";
import { ReusableSidebar } from "../../components/reusable-sidebar";
import { AddInstanceDialog } from "../../components/add-instance-dialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import Image from "next/image";
import { Plus, Monitor, Cpu, HardDrive, Wifi, ExternalLink, BookOpen, RefreshCw } from "lucide-react";
import { useComputerStore, ComputerInstance } from "../hooks/useComputerStore";

export default function ComputersPage() {
  const { 
    instances, 
    selectedInstance, 
    setSelectedInstance, 
    addInstance, 
    updateInstanceScreenshot 
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
    const { updateInstanceScreenshot } = useComputerStore();
    const [isRefreshing, setIsRefreshing] = React.useState(false);
    
    const handleRefreshScreenshot = async () => {
      setIsRefreshing(true);
      try {
        // Get CUA API key from localStorage
        const cuaApiKey = localStorage.getItem('cua_api_key') || '';
        
        const response = await fetch('/api/screenshot', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            provider: instance.provider,
            name: instance.name,
            os: instance.os,
            api_key: cuaApiKey
          })
        });
        
        if (response.ok) {
          const data = await response.json();
          if (data.success && data.screenshot) {
            updateInstanceScreenshot(instance.id, data.screenshot);
          }
        } else {
          console.error('Failed to take screenshot:', response.statusText);
        }
      } catch (error) {
        console.error('Error taking screenshot:', error);
      } finally {
        setIsRefreshing(false);
      }
    };
    
    return (
      <div className="p-8 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">{instance.name}</h1>
            <div className="flex items-center gap-2 mt-2">
              <div className={`w-2 h-2 rounded-full ${getStatusColor(instance.status)}`} />
              <span className="text-sm text-muted-foreground capitalize">{instance.status}</span>
              <span className="text-sm text-muted-foreground">•</span>
              <span className="text-sm text-muted-foreground capitalize">{instance.provider}</span>
            </div>
          </div>
          <Button 
            variant="outline" 
            onClick={handleRefreshScreenshot}
            disabled={isRefreshing}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
            {isRefreshing ? 'Taking Screenshot...' : 'Refresh Screenshot'}
          </Button>
        </div>

        {/* Screenshot Display */}
        <div className="w-full">
          {instance.lastScreenshot ? (
            <div className="space-y-4">
              <img 
                src={`data:image/png;base64,${instance.lastScreenshot}`}
                alt={`Screenshot of ${instance.name}`}
                className="w-full max-w-5xl mx-auto border rounded-lg shadow-lg"
              />
              {instance.lastScreenshotTime && (
                <p className="text-sm text-muted-foreground text-center">
                  Last updated: {new Date(instance.lastScreenshotTime).toLocaleString()}
                </p>
              )}
            </div>
          ) : (
            <div className="flex items-center justify-center h-96 bg-muted rounded-lg border-2 border-dashed border-muted-foreground/25">
              <div className="text-center">
                <Monitor className="h-16 w-16 mx-auto mb-4 text-muted-foreground/50" />
                <h3 className="text-lg font-medium mb-2">No Screenshot Available</h3>
                <p className="text-sm text-muted-foreground mb-4">
                  Take a screenshot to see the current state of {instance.name}
                </p>
                <Button 
                  onClick={handleRefreshScreenshot}
                  disabled={isRefreshing}
                >
                  <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
                  Take Screenshot
                </Button>
              </div>
            </div>
          )}
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
