"use client";

import React, { useState } from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { MessageCircle, Monitor, Settings } from "lucide-react";
import Image from "next/image";

interface PlaygroundLayoutProps {
  children: React.ReactNode;
}

export function PlaygroundLayout({ children }: PlaygroundLayoutProps) {
  const [activeTab, setActiveTab] = useState("chat");

  const sidebarItems = [
    {
      id: "chat",
      icon: MessageCircle,
      label: "Chat",
      href: "/",
    },
    {
      id: "vm-instances",
      icon: Monitor,
      label: "VM Instances",
      href: "/vm-instances",
    },
  ];

  const bottomItems = [
    {
      id: "settings",
      icon: Settings,
      label: "Settings",
      href: "/settings",
    },
  ];

  return (
    <div className="flex h-screen bg-background">
      {/* Icon-based Sidebar */}
      <div className="flex flex-col w-16 bg-muted/30 border-r border-border">
        {/* Logo Section */}
        <div className="flex items-center justify-center h-16 border-b border-border">
          <div className="w-8 h-8 relative">
            <Image
              src="https://www.trycua.com/logo-white.svg"
              alt="CUA Logo"
              width={32}
              height={32}
              className="dark:block hidden"
            />
            <Image
              src="https://www.trycua.com/logo-black.svg"
              alt="CUA Logo"
              width={32}
              height={32}
              className="dark:hidden block"
            />
          </div>
        </div>

        {/* Main Navigation */}
        <div className="flex-1 flex flex-col items-center py-4 space-y-2">
          <TooltipProvider>
            {sidebarItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              
              return (
                <Tooltip key={item.id}>
                  <TooltipTrigger asChild>
                    <Button
                      variant={isActive ? "default" : "ghost"}
                      size="icon"
                      className={cn(
                        "w-10 h-10 rounded-lg",
                        isActive && "bg-primary text-primary-foreground"
                      )}
                      onClick={() => setActiveTab(item.id)}
                    >
                      <Icon className="h-5 w-5" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent side="right">
                    <p>{item.label}</p>
                  </TooltipContent>
                </Tooltip>
              );
            })}
          </TooltipProvider>
        </div>

        {/* Bottom Navigation */}
        <div className="flex flex-col items-center pb-4 space-y-2">
          <TooltipProvider>
            {bottomItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              
              return (
                <Tooltip key={item.id}>
                  <TooltipTrigger asChild>
                    <Button
                      variant={isActive ? "default" : "ghost"}
                      size="icon"
                      className={cn(
                        "w-10 h-10 rounded-lg",
                        isActive && "bg-primary text-primary-foreground"
                      )}
                      onClick={() => setActiveTab(item.id)}
                    >
                      <Icon className="h-5 w-5" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent side="right">
                    <p>{item.label}</p>
                  </TooltipContent>
                </Tooltip>
              );
            })}
          </TooltipProvider>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col">
        {children}
      </div>
    </div>
  );
}
