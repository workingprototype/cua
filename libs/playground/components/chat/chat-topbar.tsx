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
import { Sidebar } from "../sidebar";
import { Message } from "ai/react";
import { getSelectedModel } from "@/lib/model-helper";
import { useComputerStore } from "../../app/hooks/useComputerStore";
import Image from "next/image";
import { AgentLoopConfig } from "./model-properties-sidebar";
import { Bot } from "lucide-react";

interface ChatTopbarProps {
  setSelectedModel: React.Dispatch<React.SetStateAction<string>>;
  isLoading: boolean;
  chatId?: string;
  messages: Message[];
  setMessages: (messages: Message[]) => void;
  agentConfig?: AgentLoopConfig;
  onAgentConfigChange?: (config: AgentLoopConfig) => void;
  onToggleRightSidebar?: () => void;
}

// Agent loop options
const AGENT_LOOPS = [
  { value: "OPENAI", label: "OpenAI" },
  { value: "ANTHROPIC", label: "Anthropic" },
  { value: "OMNI", label: "Omni" },
  { value: "UITARS", label: "UI-TARS" },
];

export default function ChatTopbar({
  setSelectedModel,
  isLoading,
  chatId,
  messages,
  setMessages,
  agentConfig,
  onAgentConfigChange,
  onToggleRightSidebar
}: ChatTopbarProps) {
  const [models, setModels] = React.useState<string[]>([]);
  const [open, setOpen] = React.useState(false);
  const [agentLoopOpen, setAgentLoopOpen] = React.useState(false);
  const [computerOpen, setComputerOpen] = React.useState(false);
  const [sheetOpen, setSheetOpen] = React.useState(false);
  const [currentModel, setCurrentModel] = React.useState<string | null>(null);
  const [selectedComputer, setSelectedComputer] = React.useState<string | null>(null);
  
  const { getAvailableInstances } = useComputerStore();
  const availableInstances = getAvailableInstances();

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
  }, []);

  const handleModelChange = (model: string) => {
    setCurrentModel(model);
    setSelectedModel(model);
    if (typeof window !== 'undefined') {
      localStorage.setItem("selectedModel", model);
    }
    setOpen(false);
  };

  const handleAgentLoopChange = (loop: string) => {
    if (onAgentConfigChange && agentConfig) {
      onAgentConfigChange({
        ...agentConfig,
        loop,
        provider: loop.toLowerCase(),
      });
    }
    setAgentLoopOpen(false);
  };

  const handleComputerChange = (computerId: string) => {
    setSelectedComputer(computerId);
    if (typeof window !== 'undefined') {
      localStorage.setItem("selectedComputer", computerId);
    }
    setComputerOpen(false);
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
    <div className="w-full flex px-4 py-6 items-center justify-between lg:justify-center gap-4">
      <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
        <SheetTrigger>
          <HamburgerMenuIcon className="lg:hidden w-5 h-5" />
        </SheetTrigger>
        <SheetContent side="left">
          <Sidebar
            chatId={chatId || ""}
            isCollapsed={false}
            isMobile={false}
            messages={messages}
            setMessages={setMessages}
            closeSidebar={handleCloseSidebar} 
          />
        </SheetContent>
      </Sheet>

      <div className="flex gap-4 items-center">
        <div className="flex items-center gap-2">
          <Bot className="h-4 w-4 text-muted-foreground" />
          <Popover open={agentLoopOpen} onOpenChange={setAgentLoopOpen}>
          <PopoverTrigger asChild>
            <Button
              disabled={isLoading}
              variant="outline"
              role="combobox"
              aria-expanded={agentLoopOpen}
              className="w-[200px] justify-between"
            >
              {agentConfig?.loop 
                ? AGENT_LOOPS.find(l => l.value === agentConfig.loop)?.label || "Select agent"
                : "Select agent"
              }
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

        <div className="flex items-center gap-2">
          <DesktopIcon className="h-4 w-4 text-muted-foreground" />
          <Popover open={computerOpen} onOpenChange={setComputerOpen}>
          <PopoverTrigger asChild>
            <Button
              disabled={isLoading}
              variant="outline"
              role="combobox"
              aria-expanded={computerOpen}
              className="w-[250px] justify-between"
            >
              <div className="flex items-center gap-2 overflow-hidden">
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
  );
}
