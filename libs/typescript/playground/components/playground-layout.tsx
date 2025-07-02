"use client";

import React, { useState, useEffect } from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { MessageCircle, Monitor, Settings } from "lucide-react";
import Image from "next/image";
import { useRouter } from "next/navigation";

interface PlaygroundLayoutProps {
  children: React.ReactNode;
}

export function PlaygroundLayout({ children }: PlaygroundLayoutProps) {
  const router = useRouter();
  const [pathname, setPathname] = useState("");
  const [sidebarVisible, setSidebarVisible] = useState(true);

  // Get current pathname
  useEffect(() => {
    if (typeof window !== "undefined") {
      setPathname(window.location.pathname);
    }
  }, []);

  // Determine active tab based on current path
  const getActiveTab = () => {
    if (pathname === "/" || pathname.startsWith("/chat")) return "chat";
    if (pathname.startsWith("/computers")) return "computers";
    if (pathname.startsWith("/settings")) return "settings";
    return "chat";
  };

  const [activeTab, setActiveTab] = useState(getActiveTab());

  // Update active tab when pathname changes
  useEffect(() => {
    setActiveTab(getActiveTab());
  }, [pathname]);

  const sidebarItems = [
    {
      id: "chat",
      icon: MessageCircle,
      label: "Chat",
      href: "/",
    },
    {
      id: "computers",
      icon: Monitor,
      label: "Computers",
      href: "/computers",
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

  const handleNavigation = (item: { id: string; href: string }) => {
    // Navigate to new page
    setActiveTab(item.id);
    router.push(item.href);
    setPathname(item.href);
  };

  return (
    <div className="flex h-screen bg-background">
      {/* Icon-based Sidebar */}
      <div className="flex flex-col w-16 bg-muted/30 border-r border-border">
        {/* Logo Section */}
        <div className="flex items-center justify-center h-16 border-b border-border">
          <div className="w-8 h-8 relative">
            <Image
              src="/logo-white.svg"
              alt="CUA Logo"
              width={32}
              height={32}
              className="dark:block hidden"
            />
            <Image
              src="/logo-black.svg"
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
                      onClick={() => handleNavigation(item)}
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
                      onClick={() => handleNavigation(item)}
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
      <div className="flex-1 overflow-hidden">
        {React.cloneElement(children as React.ReactElement, { 
          sidebarVisible,
          setSidebarVisible 
        })}
      </div>
    </div>
  );
}
