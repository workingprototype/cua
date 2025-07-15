"use client";

import { ChatLayout } from "@/components/chat/chat-layout";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogContent,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import UsernameForm from "@/components/username-form";
import { getSelectedModel } from "@/lib/model-helper";
import { chatClient } from "@/lib/chat-client";
import { Message, useChat } from "ai/react";
import React, { useEffect, useRef, useState, useCallback } from "react";
import { toast } from "sonner";
import { v4 as uuidv4 } from "uuid";
import useChatStore from "./hooks/useChatStore";
import { useComputerStore, ComputerInstance } from "./hooks/useComputerStore";

export default function Home() {
  const {
    messages,
    input,
    handleInputChange,
    handleSubmit,
    isLoading,
    error,
    data,
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
  const [open, setOpen] = React.useState(false);
  const [loadingSubmit, setLoadingSubmit] = React.useState(false);
  const formRef = useRef<HTMLFormElement>(null);
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
      provider: "lume",
      name: "macos-sequoia-cua:latest",
      os: "macos"
    };
  }, [availableInstances]);
  
  // Chat options state with simple initialization
  const [chatOptions, setChatOptions] = useState(() => ({
    computer: {
      provider: "lume",
      name: "macos-sequoia-cua:latest",
      os: "macos",
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
        os: selectedInstance.os,
        password: selectedInstance.password,
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

  useEffect(() => {
    if (messages.length < 1) {
      // Generate a random id for the chat
      console.log("Generating chat id");
      const id = uuidv4();
      setChatId(id);
    }
  }, [messages]);

  React.useEffect(() => {
    if (!isLoading && !error && chatId && messages.length > 0) {
      // Save messages to local storage
      localStorage.setItem(`chat_${chatId}`, JSON.stringify(messages));
      // Trigger the storage event to update the sidebar component
      window.dispatchEvent(new Event("storage"));
    }
  }, [chatId, isLoading, error]);

  useEffect(() => {
    if (!localStorage.getItem("ollama_user")) {
      setOpen(true);
    }
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
      // Try to get saved computer selection first
      if (typeof window !== 'undefined') {
        const savedComputer = localStorage.getItem("selectedComputer");
        if (savedComputer && availableInstances.length > 0) {
          const selectedInstance = availableInstances.find(instance => instance.id === savedComputer);
          if (selectedInstance) {
            // Use handleComputerChange to properly initialize the selected computer
            handleComputerChange(savedComputer);
            setIsInitialized(true);
            return;
          }
        }
      }
      
      // Fallback to default config if no saved computer or not found
      const defaultConfig = getDefaultComputerConfig();
      setChatOptions(prev => ({
        ...prev,
        computer: defaultConfig
      }));
      setIsInitialized(true);
    }
  }, [isInitialized, getDefaultComputerConfig, availableInstances, handleComputerChange]);

  const addMessage = (Message: Message) => {
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
      setMessages([...messages]);

      localStorage.setItem(`chat_${chatId}`, JSON.stringify(messages));
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

  const onOpenChange = (isOpen: boolean) => { 
    const username = localStorage.getItem("ollama_user")
    if (username) return setOpen(isOpen)

    localStorage.setItem("ollama_user", "Anonymous")
    window.dispatchEvent(new Event("storage"))
    setOpen(isOpen)
  }
  
  return (
    <main className="flex h-[calc(100dvh)] flex-col items-center ">
      <Dialog open={open} onOpenChange={onOpenChange}>
        <ChatLayout
          chatId=""
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
          defaultLayout={[20, 120, 20, 20]}
          formRef={formRef}
          setMessages={setMessages}
          setInput={setInput}
          chatOptions={chatOptions}
          onChatOptionsChange={handleChatOptionsChange}
          availableInstances={availableInstances}
          onComputerChange={handleComputerChange}
        />
        <DialogContent className="flex flex-col space-y-4">
          <DialogHeader className="space-y-2">
            <DialogTitle>Welcome to C/ua!</DialogTitle>
            <DialogDescription>
              Enter your name to get started. This is just to personalize your
              experience.
            </DialogDescription>
            <UsernameForm setOpen={setOpen} />
          </DialogHeader>
        </DialogContent>
      </Dialog>
    </main>
  );
}
