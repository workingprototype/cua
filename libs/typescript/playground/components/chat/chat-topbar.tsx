"use client";

import React, { useEffect } from "react";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";

import { Button } from "../ui/button";
import { CaretSortIcon, HamburgerMenuIcon, MixerHorizontalIcon, LaptopIcon, PersonIcon, DesktopIcon, LightningBoltIcon } from "@radix-ui/react-icons";
import { Monitor } from "lucide-react";
import { Sidebar } from "../sidebar";
import { Message } from "ai/react";
import { getSelectedModel } from "@/lib/model-helper";
import Image from "next/image";
import { ChatOptions } from "./chat-layout";
import { Bot } from "lucide-react";
import { AGENT_LOOPS, MODELS_BY_LOOP } from "@/lib/chat-client";
import { ComputerInstance } from "../../app/hooks/useComputerStore";

interface ChatTopbarProps {
  setSelectedModel: React.Dispatch<React.SetStateAction<string>>;
  isLoading: boolean;
  chatId?: string;
  messages: Message[];
  setMessages: (messages: Message[]) => void;
  onToggleRightSidebar?: () => void;
  onToggleNoVNCSidebar?: () => void;
  chatOptions?: ChatOptions;
  onChatOptionsChange?: (options: ChatOptions) => void;
  availableInstances?: ComputerInstance[];
  onComputerChange?: (computerId: string) => void;
}

export default function ChatTopbar({
  setSelectedModel,
  isLoading,
  chatId,
  messages,
  setMessages,
  onToggleRightSidebar,
  onToggleNoVNCSidebar,
  chatOptions,
  onChatOptionsChange,
  availableInstances = [],
  onComputerChange
}: ChatTopbarProps) {
  const [models, setModels] = React.useState<string[]>([]);
  const [open, setOpen] = React.useState(false);
  const [agentLoopOpen, setAgentLoopOpen] = React.useState(false);
  const [computerOpen, setComputerOpen] = React.useState(false);
  const [sheetOpen, setSheetOpen] = React.useState(false);
  const [currentModel, setCurrentModel] = React.useState<string | null>(null);
  const [selectedComputer, setSelectedComputer] = React.useState<string | null>(null);



  // Initialize component state (runs once)
  useEffect(() => {
    setCurrentModel(getSelectedModel());
    
    // Load saved computer selection
    if (typeof window !== 'undefined') {
      const savedComputer = localStorage.getItem("selectedComputer");
      if (savedComputer) {
        setSelectedComputer(savedComputer);
      }
    }

    const env = process.env.NODE_ENV;

    const fetchModels = async () => {
      try {
        if (env === "production") {
          const response = await fetch(process.env.NEXT_PUBLIC_OLLAMA_URL + "/api/tags");
          const json = await response.json();
          
          // Check if json.models exists and is an array
          if (json && Array.isArray(json.models)) {
            const apiModels = json.models.map((model: any) => model.name);
            setModels([...apiModels]);
          } else {
            console.error("Invalid API response format:", json);
            setModels([]);
          }
        } else {
          const response = await fetch("/api/tags");
          const json = await response.json();
          
          // Check if json.models exists and is an array
          if (json && Array.isArray(json.models)) {
            const apiModels = json.models.map((model: any) => model.name);
            setModels([...apiModels]);
          } else {
            console.error("Invalid API response format:", json);
            setModels([]);
          }
        }
      } catch (error) {
        console.error("Error fetching models:", error);
        setModels([]);
      }
    };
    fetchModels();
  }, []); // Only run once on mount



  const handleModelChange = (model: string) => {
    setCurrentModel(model);
    setSelectedModel(model);
    if (typeof window !== 'undefined') {
      localStorage.setItem("selectedModel", model);
    }
    setOpen(false);
  };

  const handleAgentLoopChange = (loop: string) => {
    if (onChatOptionsChange && chatOptions) {
      const availableModels = MODELS_BY_LOOP[loop] || [];
      const firstModel = availableModels[0] || "";
      
      onChatOptionsChange({
        ...chatOptions,
        agent: {
          ...chatOptions.agent,
          loop: loop,
          model: firstModel
        }
      });
    }
    setAgentLoopOpen(false);
  };

  const handleComputerChange = (computerId: string) => {
    setSelectedComputer(computerId);
    setComputerOpen(false);

    // Call the parent handler to update chat options
    if (onComputerChange) {
      onComputerChange(computerId);
    }
  };

  const handleCloseSidebar = () => {
    setSheetOpen(false);  // Close the sidebar
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
        return null;
    }
  };

  return (
    <div className="w-full flex flex-col lg:flex-row px-4 py-6 items-center justify-between lg:justify-center gap-4">
      <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
        <SheetTrigger>
          <HamburgerMenuIcon className="lg:hidden w-5 h-5" />
        </SheetTrigger>
        <SheetContent side="left">
          <Sidebar
            isCollapsed={false}
            messages={messages}
            isMobile={true}
            chatId={chatId || ""}
            setMessages={setMessages}
            closeSidebar={handleCloseSidebar} 
          />
        </SheetContent>
      </Sheet>

      <div className="flex flex-wrap gap-4 items-center justify-center lg:justify-start">
        <div className="flex items-center gap-2 min-w-0">
          <Bot className="h-4 w-4 text-muted-foreground flex-shrink-0" />
          <Popover open={agentLoopOpen} onOpenChange={setAgentLoopOpen}>
          <PopoverTrigger asChild>
            <Button
              disabled={isLoading}
              variant="outline"
              role="combobox"
              aria-expanded={agentLoopOpen}
              className="w-[200px] sm:w-[160px] md:w-[200px] justify-between"
            >
              <span className="truncate">
                {AGENT_LOOPS.find(loop => loop.value === (chatOptions?.agent.loop || "ANTHROPIC"))?.label || "Select agent loop"}
              </span>
              <CaretSortIcon className="ml-2 h-4 w-4 shrink-0 opacity-50" />
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-[200px] p-1">
            {AGENT_LOOPS.map((loop) => (
              <Button
                key={loop.value}
                variant="ghost"
                className="w-full justify-start"
                onClick={() => {
                  handleAgentLoopChange(loop.value);
                }}
              >
                {loop.label}
              </Button>
            ))}
          </PopoverContent>
        </Popover>
        </div>

        {/* Model Dropdown */}
        {/* <Popover open={open} onOpenChange={setOpen}>
          <PopoverTrigger asChild>
            <Button
              disabled={isLoading}
              variant="outline"
              role="combobox"
              aria-expanded={open}
              className="w-[250px] justify-between"
            >
              {currentModel || "Select model"}
              <CaretSortIcon className="ml-2 h-4 w-4 shrink-0 opacity-50" />
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-[250px] p-1">
            {models.length > 0 ? (
              models.map((model) => (
                <Button
                  key={model}
                  variant="ghost"
                  className="w-full"
                  onClick={() => {
                    handleModelChange(model);
                  }}
                >
                  {model}
                </Button>
              ))
            ) : (
              <Button variant="ghost" disabled className="w-full">
                No models available
              </Button>
            )}
          </PopoverContent>
        </Popover>
        </div> */}

        <div className="flex items-center gap-2 min-w-0">
          <DesktopIcon className="h-4 w-4 text-muted-foreground flex-shrink-0" />
          <Popover open={computerOpen} onOpenChange={setComputerOpen}>
          <PopoverTrigger asChild>
            <Button
              disabled={isLoading}
              variant="outline"
              role="combobox"
              aria-expanded={computerOpen}
              className="w-[250px] sm:w-[200px] md:w-[250px] justify-between"
            >
              <div className="flex items-center gap-2 overflow-hidden min-w-0">
                {selectedComputer ? (
                  <>
                    {getOSIcon(availableInstances.find(c => c.id === selectedComputer)?.os || '')}
                    <span className="truncate">
                      {availableInstances.find(c => c.id === selectedComputer)?.name || "Select computer"}
                    </span>
                  </>
                ) : "Select computer"}
              </div>
              <CaretSortIcon className="ml-2 h-4 w-4 shrink-0 opacity-50" />
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-[250px] p-1">
            {availableInstances.length > 0 ? (
              availableInstances.map((computer) => (
                <Button
                  key={computer.id}
                  variant="ghost"
                  className="w-full justify-start"
                  onClick={() => {
                    handleComputerChange(computer.id);
                  }}
                >
                  <div className="flex items-center gap-2">
                    {getOSIcon(computer.os)}
                    <span className="truncate">{computer.name}</span>
                  </div>
                </Button>
              ))
            ) : (
              <Button variant="ghost" disabled className="w-full">
                No available computers
              </Button>
            )}
          </PopoverContent>
        </Popover>
        </div>

        <div className="flex items-center justify-center lg:justify-start gap-2">
          {/* NoVNC Icon */}
          <Button
            variant="outline"
            size="icon"
            onClick={onToggleNoVNCSidebar}
            className="h-10 w-10"
          >
            <Monitor className="h-4 w-4" />
          </Button>

          {/* Settings Icon */}
          <Button
            variant="outline"
            size="icon"
            onClick={onToggleRightSidebar}
            className="h-10 w-10"
          >
            <MixerHorizontalIcon className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
