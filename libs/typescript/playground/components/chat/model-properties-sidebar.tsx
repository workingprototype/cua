"use client";

import React, { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Separator } from "../ui/separator";
import { ScrollArea } from "../ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Settings, Cpu, Zap, Brain, Bot, Images, SlidersHorizontal } from "lucide-react";
import { ChatOptions } from "./chat-layout";
import { AGENT_LOOPS, MODELS_BY_LOOP } from "@/lib/chat-client";

export interface AgentLoopConfig {
  loop: string;
  model: string;
  provider: string;
  temperature?: number;
  maxTokens?: number;
  systemPrompt?: string;
  saveTrajectory?: boolean;
  verbosity?: number;
  useOaicompat?: boolean;
  providerBaseUrl?: string;
  imageRetention?: number;
}

interface ModelPropertiesSidebarProps {
  isCollapsed: boolean;
  onToggle?: () => void;
  chatOptions?: ChatOptions;
  onChatOptionsChange?: (options: ChatOptions) => void;
}



export default function ModelPropertiesSidebar({
  isCollapsed,
  onToggle,
  chatOptions,
  onChatOptionsChange
}: ModelPropertiesSidebarProps) {
  const handleLoopChange = (loop: string) => {
    if (!chatOptions || !onChatOptionsChange) return;
    
    const availableModels = MODELS_BY_LOOP[loop] || [];
    const defaultModel = availableModels[0] || "";
    
    onChatOptionsChange({
      ...chatOptions,
      agent: {
        ...chatOptions.agent,
        loop,
        model: defaultModel,
      },
    });
  };

  const handleModelChange = (model: string) => {
    if (!chatOptions || !onChatOptionsChange) return;
    
    onChatOptionsChange({
      ...chatOptions,
      agent: {
        ...chatOptions.agent,
        model,
      },
    });
  };

  const handleAgentConfigChange = (updates: Partial<ChatOptions['agent']>) => {
    if (!chatOptions || !onChatOptionsChange) return;
    
    onChatOptionsChange({
      ...chatOptions,
      agent: {
        ...chatOptions.agent,
        ...updates,
      },
    });
  };

  const currentLoop = chatOptions?.agent.loop || "ANTHROPIC";
  const currentModel = chatOptions?.agent.model || "claude-3-5-sonnet-20240620";
  const availableModels = MODELS_BY_LOOP[currentLoop] || [];

  if (isCollapsed) {
    return (
      <div className="flex flex-col items-center p-2 space-y-4">
        <Settings className="h-6 w-6" />
      </div>
    );
  }

  return (
    <ScrollArea className="h-full">
      <div className="flex flex-col space-y-4 p-4">
        <div className="flex items-center space-x-2">
          <SlidersHorizontal className="h-5 w-5" />
          <h2 className="text-lg font-semibold">Agent Properties</h2>
        </div>

        <Separator />

        {/* Agent Loop Selection */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center space-x-2">
              <Bot className="h-4 w-4" />
              <span>Agent Loop</span>
            </CardTitle>
            <CardDescription>
              Select the computer-use implementation
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Select
              value={currentLoop}
              onValueChange={handleLoopChange}
            >
              <SelectTrigger className="text-left py-6">
                <SelectValue placeholder="Select agent loop" />
              </SelectTrigger>
              <SelectContent>
                {AGENT_LOOPS.map((loop) => (
                  <SelectItem key={loop.value} value={loop.value}>
                    <div className="flex flex-col">
                      <span className="font-medium">{loop.label}</span>
                      <span className="text-xs text-muted-foreground">
                        {loop.description}
                      </span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </CardContent>
        </Card>

        {/* Model Selection */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center space-x-2">
              <Brain className="h-4 w-4" />
              <span>LLM Model</span>
            </CardTitle>
            <CardDescription>
              Select the language model for this agent loop
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Select
              value={currentModel}
              onValueChange={handleModelChange}
              disabled={!currentLoop}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select model" />
              </SelectTrigger>
              <SelectContent>
                {availableModels.map((model) => (
                  <SelectItem key={model} value={model}>
                    {model}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            
            {availableModels.length === 0 && currentLoop && (
              <p className="text-xs text-muted-foreground">
                No models available for selected agent loop
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </ScrollArea>
  );
}
