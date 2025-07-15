"use client";

import React from "react";
import { ScrollArea } from "../ui/scroll-area";
import { Separator } from "../ui/separator";
import { Button } from "../ui/button";
import { Monitor, Terminal, Power } from "lucide-react";

interface NoVNCProps {
  isCollapsed: boolean;
  onToggle?: () => void;
  containerName?: string;
  containerPassword?: string;
}

export default function NoVNCSidebar({
  isCollapsed,
  onToggle,
  containerName,
  containerPassword
}: NoVNCProps) {
  if (isCollapsed) {
    return (
      <div className="flex flex-col items-center p-2 space-y-4">
        <Monitor className="h-6 w-6" />
      </div>
    );
  }

  // Construct the NoVNC URL
  const vncUrl = containerName && containerPassword 
    ? `https://${containerName}.containers.cloud.trycua.com/vnc.html?autoconnect=true&resize=scale&password=${containerPassword}`
    : null;

  return (
    <ScrollArea className="h-full">
      <div className="flex flex-col space-y-4 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Monitor className="h-5 w-5" />
            <h2 className="text-lg font-semibold">Remote Desktop</h2>
          </div>
          
          {vncUrl && (
            <div className="flex items-center space-x-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  // Open terminal/shell - this could be implemented to open a terminal in the remote desktop
                  console.log('Opening terminal for:', containerName);
                }}
                className="h-8 px-2"
              >
                <Terminal className="h-4 w-4" />
              </Button>
              
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  // Power actions - this could be implemented to restart/shutdown the container
                  console.log('Power action for:', containerName);
                }}
                className="h-8 px-2"
              >
                <Power className="h-4 w-4" />
              </Button>
            </div>
          )}
        </div>

        <Separator />

        <div className="flex-1">
          {vncUrl ? (
            <iframe
              src={vncUrl}
              className="w-full h-[calc(100vh-120px)] border-0 rounded-md"
              title="NoVNC Remote Desktop"
            />
          ) : (
            <div className="flex items-center justify-center h-64 text-muted-foreground">
              <div className="text-center">
                <Monitor className="h-12 w-12 mx-auto mb-2 opacity-50" />
                <p className="text-sm">No container selected</p>
                <p className="text-xs">Select a computer to view remote desktop</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </ScrollArea>
  );
}
