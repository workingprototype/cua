import React from "react";
import ChatTopbar from "./chat-topbar";
import ChatList from "./chat-list";
import ChatBottombar from "./chat-bottombar";
import { Message, useChat } from "ai/react";
import { ChatRequestOptions } from "ai";
import { v4 as uuidv4 } from "uuid";
import { AgentLoopConfig } from "./model-properties-sidebar";
import { ChatOptions } from "./chat-layout";
import { ComputerInstance } from "../../app/hooks/useComputerStore";

export interface ChatProps {
  chatId?: string;
  setSelectedModel: React.Dispatch<React.SetStateAction<string>>;
  messages: Message[];
  input: string;
  handleInputChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
  handleSubmit: (
    e: React.FormEvent<HTMLFormElement>,
    chatRequestOptions?: ChatRequestOptions
  ) => void;
  isLoading: boolean;
  loadingSubmit?: boolean;
  error: undefined | Error;
  stop: () => void;
  formRef: React.RefObject<HTMLFormElement>;
  isMobile?: boolean;
  setInput?: React.Dispatch<React.SetStateAction<string>>;
  setMessages: (messages: Message[]) => void;
  agentConfig?: AgentLoopConfig;
  onAgentConfigChange?: (config: AgentLoopConfig) => void;
  onToggleRightSidebar?: () => void;
  onToggleNoVNCSidebar?: () => void;
  chatOptions?: ChatOptions;
  onChatOptionsChange?: (options: ChatOptions) => void;
  availableInstances?: ComputerInstance[];
  onComputerChange?: (computerId: string) => void;
}

export default function Chat({
  messages,
  input,
  handleInputChange,
  handleSubmit,
  isLoading,
  error,
  stop,
  setSelectedModel,
  chatId,
  loadingSubmit,
  formRef,
  isMobile,
  setInput,
  setMessages,
  agentConfig,
  onAgentConfigChange,
  onToggleRightSidebar,
  onToggleNoVNCSidebar,
  chatOptions,
  onChatOptionsChange,
  availableInstances,
  onComputerChange
}: ChatProps) {
  return (
    <div className="flex flex-col justify-between w-full max-w-3xl h-full ">
      <ChatTopbar
        setSelectedModel={setSelectedModel}
        isLoading={isLoading}
        chatId={chatId}
        messages={messages}
        setMessages={setMessages}
        onToggleRightSidebar={onToggleRightSidebar}
        onToggleNoVNCSidebar={onToggleNoVNCSidebar}
        chatOptions={chatOptions}
        onChatOptionsChange={onChatOptionsChange}
        availableInstances={availableInstances}
        onComputerChange={onComputerChange}
      />

      <ChatList
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
        setMessages={setMessages}
      />

      <ChatBottombar
        setSelectedModel={setSelectedModel}
        messages={messages}
        input={input}
        handleInputChange={handleInputChange}
        handleSubmit={handleSubmit}
        isLoading={isLoading}
        error={error}
        stop={stop}
        formRef={formRef}
        setInput={setInput}
        setMessages={setMessages}
      />
    </div>
  );
}
