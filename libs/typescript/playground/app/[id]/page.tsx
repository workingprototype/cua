"use client";

import { ChatLayout } from "@/components/chat/chat-layout";
import { getSelectedModel } from "@/lib/model-helper";
import { chatClient } from "@/lib/chat-client";
import { Message, useChat } from "ai/react";
import React, { useEffect, useState, useCallback } from "react";
import { toast } from "sonner";
import { v4 as uuidv4 } from "uuid";
import useChatStore from "../hooks/useChatStore";
import { useComputerStore, ComputerInstance } from "../hooks/useComputerStore";

export default function Page({ params }: { params: { id: string } }) {
  const {
    messages,
    input,
    handleInputChange,
    handleSubmit,
    isLoading,
    error,
    stop,
    setMessages,
    setInput,
  } = useChat({
    onResponse: (response) => {
      if (response) {
        setLoadingSubmit(false);
      }
    },
    onError: (error) => {
      setLoadingSubmit(false);
      toast.error("An error occurred. Please try again.");
    },
  });
  const [chatId, setChatId] = React.useState<string>("");
  const [selectedModel, setSelectedModel] = React.useState<string>(
    getSelectedModel()
  );
  const [loadingSubmit, setLoadingSubmit] = React.useState(false);
  const formRef = React.useRef<HTMLFormElement>(null);
  const base64Images = useChatStore((state) => state.base64Images);
  const setBase64Images = useChatStore((state) => state.setBase64Images);

  // Computer store
  const { getAvailableInstances } = useComputerStore();
  const availableInstances = getAvailableInstances();
  
  // Helper function to get API key based on provider
  const getApiKeyForProvider = useCallback((provider: string): string => {
    if (typeof window === 'undefined') return "";
    
    if (provider === "cua-cloud") {
      return localStorage.getItem("cua_api_key") || "";
    } else if (provider === "anthropic") {
      return localStorage.getItem("anthropic_api_key") || process.env.NEXT_PUBLIC_ANTHROPIC_API_KEY || "";
    }
    return "";
  }, []);
  
  // Get default computer configuration (stable function)
  const getDefaultComputerConfig = useCallback(() => {
    // Try to get saved computer selection
    if (typeof window !== 'undefined') {
      const savedComputer = localStorage.getItem("selectedComputer");
      if (savedComputer) {
        const selectedInstance = availableInstances.find(instance => instance.id === savedComputer);
        if (selectedInstance) {
          const config: any = {
            provider: selectedInstance.provider,
            name: selectedInstance.name,
            os: selectedInstance.os
          };
          
          // Only add api_key for cua-cloud provider
          if (selectedInstance.provider === "cua-cloud") {
            config.api_key = localStorage.getItem("cua_api_key") || "";
          }
          
          return config;
        }
      }
    }
    
    // Default fallback (no API key for local VMs)
    return {
      provider: "anthropic",
      name: "default",
      os: "ubuntu"
    };
  }, [availableInstances]);
  
  // Chat options state with simple initialization
  const [chatOptions, setChatOptions] = useState(() => ({
    computer: {
      provider: "anthropic",
      name: "default",
      os: "ubuntu"
      // No api_key for local VMs
    },
    agent: {
      loop: "ANTHROPIC",
      model: selectedModel,
      temperature: 0.7,
      max_tokens: 4096,
      system_prompt: "",
      save_trajectory: true,
      verbosity: 20,
      use_oaicompat: false,
      provider_base_url: "",
    },
  }));
  
  // Initialize computer config once on mount
  const [isInitialized, setIsInitialized] = useState(false);
  
  // Handle computer selection changes
  const handleComputerChange = useCallback((computerId: string) => {
    const selectedInstance = availableInstances.find(instance => instance.id === computerId);
    if (selectedInstance) {
      const computerConfig: any = {
        provider: selectedInstance.provider,
        name: selectedInstance.name,
        os: selectedInstance.os
      };
      
      // Only add api_key for cua-cloud provider
      if (selectedInstance.provider === "cua-cloud") {
        computerConfig.api_key = getApiKeyForProvider(selectedInstance.provider);
      }
      
      setChatOptions(prev => ({
        ...prev,
        computer: computerConfig
      }));
      
      // Save selection to localStorage
      localStorage.setItem("selectedComputer", computerId);
    }
  }, [availableInstances, getApiKeyForProvider]);
  
  // Handle chat options changes
  const handleChatOptionsChange = useCallback((options: typeof chatOptions) => {
    setChatOptions(options);
  }, []);

  // Update chat options when selected model changes
  useEffect(() => {
    setChatOptions(prev => ({
      ...prev,
      agent: {
        ...prev.agent,
        model: selectedModel,
      },
    }));
  }, [selectedModel]);
  
  // Initialize computer config once on mount
  useEffect(() => {
    if (!isInitialized) {
      const defaultConfig = getDefaultComputerConfig();
      setChatOptions(prev => ({
        ...prev,
        computer: defaultConfig
      }));
      setIsInitialized(true);
    }
  }, [isInitialized, getDefaultComputerConfig]);

  React.useEffect(() => {
    if (params.id) {
      const item = localStorage.getItem(`chat_${params.id}`);
      if (item) {
        setMessages(JSON.parse(item));
      }
    }
  }, []);

  const addMessage = (Message: any) => {
    messages.push(Message);
    window.dispatchEvent(new Event("storage"));
    setMessages([...messages]);
  };

  // Function to handle chatting with chat client in production (client side)
  const handleSubmitProduction = async (
    e: React.FormEvent<HTMLFormElement>
  ) => {
    e.preventDefault();

    addMessage({ role: "user", content: input, id: chatId });
    setInput("");

    try {
      const stream = chatClient.stream(messages as Message[], {
        computer: chatOptions.computer,
        agent: chatOptions.agent,
      });

      let responseMessage = "";
      let toolInvocations: any[] = [];
      let annotations: any[] = [];
      
      for await (const chunk of stream) {
        if (typeof chunk === 'string') {
          // Regular text content
          responseMessage += chunk;
        } else if (typeof chunk === 'object' && chunk.type) {
          // Handle dictionary responses
          if (chunk.type === 'reasoning') {
            // Add reasoning content as annotation
            annotations.push({
              type: 'reasoning',
              content: chunk.content,
              timestamp: Date.now()
            });
          } else if (chunk.type === 'data') {
            // Handle computer actions as tool invocations and screenshots as annotations
            if (Array.isArray(chunk.content)) {
              for (const item of chunk.content) {
                if (item.type === 'computer_action') {
                  toolInvocations.push({
                    toolCallId: `tool_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
                    toolName: 'computer_action',
                    args: item.action,
                    state: 'result',
                    result: {
                      title: item.title,
                      action: item.action
                    }
                  });
                } else if (item.type === 'screenshot') {
                  // Add screenshot as annotation
                  annotations.push({
                    type: 'screenshot',
                    screenshot_base64: item.screenshot_base64,
                    action_type: item.action_type,
                    timestamp: item.timestamp
                  });
                }
              }
            }
          }
        }
        
        setLoadingSubmit(false);
        setMessages([
          ...messages,
          { 
            role: "assistant", 
            content: responseMessage, 
            id: chatId,
            toolInvocations: toolInvocations.length > 0 ? toolInvocations : undefined,
            annotations: annotations.length > 0 ? annotations : undefined
          },
        ]);
      }
      addMessage({ 
        role: "assistant", 
        content: responseMessage, 
        id: chatId,
        toolInvocations: toolInvocations.length > 0 ? toolInvocations : undefined,
        annotations: annotations.length > 0 ? annotations : undefined
      });
      // Update messages with final state
      setMessages([
        ...messages,
        { 
          role: "assistant", 
          content: responseMessage, 
          id: chatId,
          toolInvocations: toolInvocations.length > 0 ? toolInvocations : undefined,
          annotations: annotations.length > 0 ? annotations : undefined
        },
      ]);

      localStorage.setItem(`chat_${params.id}`, JSON.stringify(messages));
      // Trigger the storage event to update the sidebar component
      window.dispatchEvent(new Event("storage"));
    } catch (error) {
      toast.error("An error occurred. Please try again.");
      setLoadingSubmit(false);
    }
  };

  const onSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setLoadingSubmit(true);

    setMessages([...messages]);

    // Always use production handler (chat client)
    handleSubmitProduction(e);
    setBase64Images(null);
  };

  // When starting a new chat, append the messages to the local storage
  React.useEffect(() => {
    if (!isLoading && !error && messages.length > 0) {
      localStorage.setItem(`chat_${params.id}`, JSON.stringify(messages));
      // Trigger the storage event to update the sidebar component
      window.dispatchEvent(new Event("storage"));
    }
  }, [messages, chatId, isLoading, error]);

  return (
    <main className="flex h-[calc(100dvh)] flex-col items-center">
      <ChatLayout
        chatId={params.id}
        setSelectedModel={setSelectedModel}
        messages={messages}
        input={input}
        handleInputChange={handleInputChange}
        handleSubmit={onSubmit}
        isLoading={isLoading}
        loadingSubmit={loadingSubmit}
        error={error}
        stop={stop}
        navCollapsedSize={10}
        defaultLayout={[30, 160]}
        formRef={formRef}
        setMessages={setMessages}
        setInput={setInput}
        chatOptions={chatOptions}
        onChatOptionsChange={handleChatOptionsChange}
        availableInstances={availableInstances}
        onComputerChange={handleComputerChange}
      />
    </main>
  );
}
