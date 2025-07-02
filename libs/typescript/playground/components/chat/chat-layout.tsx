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

interface ChatLayoutProps {
  defaultLayout: number[] | undefined;
  defaultCollapsed?: boolean;
  navCollapsedSize: number;
  chatId: string;
  setMessages: (messages: Message[]) => void;
  sidebarVisible?: boolean;
  setSidebarVisible?: (visible: boolean) => void;
}

type MergedProps = ChatLayoutProps & ChatProps;

export function ChatLayout({
  defaultLayout = [20, 160, 20],
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
}: MergedProps) {
  const [isCollapsed, setIsCollapsed] = React.useState(defaultCollapsed);
  const [isRightSidebarCollapsed, setIsRightSidebarCollapsed] = React.useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const rightPanelRef = useRef<ImperativePanelHandle>(null);

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
        minSize={isMobile ? 0 : 12}
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
        minSize={30}
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
        />
      </ResizablePanel>
      
      <ResizableHandle className={cn("hidden md:flex")} withHandle />
      
      {/* Right Sidebar - Model Properties */}
      <ResizablePanel
        ref={rightPanelRef}
        defaultSize={defaultLayout[2]}
        collapsedSize={0}
        collapsible={true}
        minSize={isMobile ? 0 : 15}
        maxSize={isMobile ? 0 : 25}
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
          agentConfig={agentConfig}
          onConfigChange={handleAgentConfigChange}
          onToggle={handleToggleRightSidebar}
        />
      </ResizablePanel>
    </ResizablePanelGroup>
  );
}
