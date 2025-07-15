"use client";

import React, { useEffect, useState, useRef } from "react";
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
  type ImperativePanelHandle,
} from "@/components/ui/resizable";
import { cn } from "@/lib/utils";
import { Sidebar } from "../sidebar";
import { Message, useChat } from "ai/react";
import Chat, { ChatProps } from "./chat";
import ChatList from "./chat-list";
import { HamburgerMenuIcon } from "@radix-ui/react-icons";
import ModelPropertiesSidebar, { AgentLoopConfig } from "./model-properties-sidebar";
import NoVNCSidebar from "./novnc-sidebar";
import { ComputerInstance } from "../../app/hooks/useComputerStore";

// Chat options interface
export interface ChatOptions {
  computer: {
    provider: string;
    name: string;
    os: string;
    api_key?: string; // Optional - only required for cua-cloud provider
    password?: string; // Optional - password for NoVNC access
  };
  agent: {
    loop: string;
    model: string;
    temperature: number;
    max_tokens: number;
    system_prompt: string;
    save_trajectory: boolean;
    verbosity: number;
    use_oaicompat: boolean;
    provider_base_url: string;
  };
}

interface ChatLayoutProps {
  defaultLayout: number[] | undefined;
  defaultCollapsed?: boolean;
  navCollapsedSize: number;
  chatId: string;
  setMessages: (messages: Message[]) => void;
  sidebarVisible?: boolean;
  setSidebarVisible?: (visible: boolean) => void;
  chatOptions?: ChatOptions;
  onChatOptionsChange?: (options: ChatOptions) => void;
  availableInstances?: ComputerInstance[];
  onComputerChange?: (computerId: string) => void;
}

type MergedProps = ChatLayoutProps & ChatProps;

export function ChatLayout({
  defaultLayout = [15, 120, 20, 20],
  defaultCollapsed = false,
  navCollapsedSize,
  messages,
  input,
  handleInputChange,
  handleSubmit,
  isLoading,
  error,
  stop,
  chatId,
  setSelectedModel,
  loadingSubmit,
  formRef,
  setMessages,
  setInput,
  sidebarVisible,
  setSidebarVisible,
  chatOptions,
  onChatOptionsChange,
  availableInstances,
  onComputerChange,
}: MergedProps) {
  const [isCollapsed, setIsCollapsed] = React.useState(defaultCollapsed);
  const [isRightSidebarCollapsed, setIsRightSidebarCollapsed] = React.useState(false);
  const [isNoVNCSidebarCollapsed, setIsNoVNCSidebarCollapsed] = React.useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const rightPanelRef = useRef<ImperativePanelHandle>(null);
  const noVNCPanelRef = useRef<ImperativePanelHandle>(null);

  // Agent configuration state
  const [agentConfig, setAgentConfig] = useState<AgentLoopConfig>({
    loop: "ANTHROPIC",
    model: "claude-3-5-sonnet-20240620",
    provider: "anthropic",
    temperature: 0.7,
    maxTokens: 4096,
    saveTrajectory: true,
    verbosity: 20,
    useOaicompat: false,
  });

  useEffect(() => {
    const checkScreenWidth = () => {
      setIsMobile(window.innerWidth <= 1023);
    };

    // Initial check
    checkScreenWidth();

    // Event listener for screen width changes
    window.addEventListener("resize", checkScreenWidth);

    // Cleanup the event listener on component unmount
    return () => {
      window.removeEventListener("resize", checkScreenWidth);
    };
  }, []);

  useEffect(() => {
    const collapsed = localStorage.getItem("react-resizable-panels:right-collapsed");
    if (collapsed) {
      setIsRightSidebarCollapsed(JSON.parse(collapsed));
    }
    
    const noVNCCollapsed = localStorage.getItem("react-resizable-panels:novnc-collapsed");
    if (noVNCCollapsed) {
      setIsNoVNCSidebarCollapsed(JSON.parse(noVNCCollapsed));
    }
  }, []);

  const handleAgentConfigChange = (config: AgentLoopConfig) => {
    setAgentConfig(config);
    // You can add logic here to update the selected model based on agent config
    setSelectedModel(config.model);
  };

  const handleToggleRightSidebar = () => {
    const panel = rightPanelRef.current;
    if (panel) {
      if (isRightSidebarCollapsed) {
        panel.expand(25);
      } else {
        panel.collapse();
      }
    }
  };

  const handleToggleNoVNCSidebar = () => {
    const panel = noVNCPanelRef.current;
    if (panel) {
      if (isNoVNCSidebarCollapsed) {
        panel.expand(25);
      } else {
        panel.collapse();
      }
    }
  };

  return (
    <ResizablePanelGroup
      direction="horizontal"
      onLayout={(sizes: number[]) => {
        document.cookie = `react-resizable-panels:layout=${JSON.stringify(
          sizes
        )}`;
      }}
      className="h-screen items-stretch"
    >
      {/* Left Sidebar */}
      <ResizablePanel
        defaultSize={defaultLayout[0]}
        collapsedSize={navCollapsedSize}
        collapsible={true}
        // minSize={isMobile ? 0 : 12}
        maxSize={isMobile ? 0 : 16}
        onCollapse={() => {
          setIsCollapsed(true);
          document.cookie = `react-resizable-panels:collapsed=${JSON.stringify(
            true
          )}`;
        }}
        onExpand={() => {
          setIsCollapsed(false);
          document.cookie = `react-resizable-panels:collapsed=${JSON.stringify(
            false
          )}`;
        }}
        className={cn(
          isCollapsed
            ? "min-w-[50px] md:min-w-[70px] transition-all duration-300 ease-in-out"
            : "hidden md:block"
        )}
      >
        <Sidebar
          isCollapsed={isCollapsed || isMobile}
          messages={messages}
          isMobile={isMobile}
          chatId={chatId}
          setMessages={setMessages}
          visible={sidebarVisible}
          setVisible={setSidebarVisible}
        />
      </ResizablePanel>
      
      <ResizableHandle className={cn("hidden md:flex")} withHandle />
      
      {/* Main Chat Area */}
      <ResizablePanel
        className="h-full w-full flex justify-center"
        defaultSize={defaultLayout[1]}
        // minSize={30}
      >
        <Chat
          chatId={chatId}
          setSelectedModel={setSelectedModel}
          messages={messages}
          input={input}
          handleInputChange={handleInputChange}
          handleSubmit={handleSubmit}
          isLoading={isLoading}
          loadingSubmit={loadingSubmit}
          error={error}
          stop={stop}
          formRef={formRef}
          isMobile={isMobile}
          setInput={setInput}
          setMessages={setMessages}
          agentConfig={agentConfig}
          onAgentConfigChange={handleAgentConfigChange}
          onToggleRightSidebar={handleToggleRightSidebar}
          onToggleNoVNCSidebar={handleToggleNoVNCSidebar}
          chatOptions={chatOptions}
          onChatOptionsChange={onChatOptionsChange}
          availableInstances={availableInstances}
          onComputerChange={onComputerChange}
        />
      </ResizablePanel>
      
      <ResizableHandle className={cn("hidden md:flex")} withHandle />
      
      {/* NoVNC Sidebar */}
      <ResizablePanel
        ref={noVNCPanelRef}
        defaultSize={defaultLayout[2]}
        collapsedSize={0}
        collapsible={true}
        // minSize={isMobile ? 0 : 15}
        onCollapse={() => {
          setIsNoVNCSidebarCollapsed(true);
          document.cookie = `react-resizable-panels:novnc-collapsed=${JSON.stringify(
            true
          )}`;
        }}
        onExpand={() => {
          setIsNoVNCSidebarCollapsed(false);
          document.cookie = `react-resizable-panels:novnc-collapsed=${JSON.stringify(
            false
          )}`;
        }}
      >
        <NoVNCSidebar
          isCollapsed={isNoVNCSidebarCollapsed || isMobile}
          onToggle={handleToggleNoVNCSidebar}
          containerName={chatOptions?.computer?.name}
          containerPassword={chatOptions?.computer?.password}
        />
      </ResizablePanel>
      
      <ResizableHandle className={cn("hidden md:flex")} withHandle />
      
      {/* Right Sidebar - Model Properties */}
      <ResizablePanel
        ref={rightPanelRef}
        defaultSize={defaultLayout[3]}
        collapsedSize={0}
        collapsible={true}
        // minSize={isMobile ? 0 : 15}
        // maxSize={isMobile ? 0 : 25}
        onCollapse={() => {
          setIsRightSidebarCollapsed(true);
          document.cookie = `react-resizable-panels:right-collapsed=${JSON.stringify(
            true
          )}`;
        }}
        onExpand={() => {
          setIsRightSidebarCollapsed(false);
          document.cookie = `react-resizable-panels:right-collapsed=${JSON.stringify(
            false
          )}`;
        }}
      >
        <ModelPropertiesSidebar
          isCollapsed={isRightSidebarCollapsed || isMobile}
          onToggle={handleToggleRightSidebar}
          chatOptions={chatOptions}
          onChatOptionsChange={onChatOptionsChange}
        />
      </ResizablePanel>
    </ResizablePanelGroup>
  );
}
