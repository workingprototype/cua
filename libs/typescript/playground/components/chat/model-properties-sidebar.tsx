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

        {/* Advanced Settings */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center space-x-2">
              <Cpu className="h-4 w-4" />
              <span>Advanced Settings</span>
            </CardTitle>
            <CardDescription>
              Configure advanced model parameters
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Temperature */}
            <div className="space-y-2">
              <Label htmlFor="temperature" className="text-sm">
                Temperature
              </Label>
              <Input
                id="temperature"
                type="number"
                min="0"
                max="2"
                step="0.1"
                value={chatOptions?.agent.temperature || 0.7}
                onChange={(e) => 
                  handleAgentConfigChange({ temperature: parseFloat(e.target.value) })
                }
                className="text-sm"
              />
              <p className="text-xs text-muted-foreground">
                Controls randomness (0.0 = deterministic, 2.0 = very random)
              </p>
            </div>

            {/* Max Tokens */}
            <div className="space-y-2">
              <Label htmlFor="maxTokens" className="text-sm">
                Max Tokens
              </Label>
              <Input
                id="maxTokens"
                type="number"
                min="1"
                max="8192"
                value={chatOptions?.agent.max_tokens || 4096}
                onChange={(e) => 
                  handleAgentConfigChange({ max_tokens: parseInt(e.target.value) })
                }
                className="text-sm"
              />
              <p className="text-xs text-muted-foreground">
                Maximum number of tokens to generate
              </p>
            </div>

            {/* System Prompt */}
            {/* <div className="space-y-2">
              <Label htmlFor="systemPrompt" className="text-sm">
                System Prompt
              </Label>
              <Textarea
                id="systemPrompt"
                placeholder="Enter custom system prompt..."
                value={localConfig.systemPrompt || ""}
                onChange={(e) => 
                  handleConfigUpdate({ systemPrompt: e.target.value })
                }
                className="text-sm min-h-[80px]"
              />
              <p className="text-xs text-muted-foreground">
                Custom instructions for the agent
              </p>
            </div> */}

            {/* Save Trajectory */}
            {/* <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label className="text-sm">Save Trajectory</Label>
                <p className="text-xs text-muted-foreground">
                  Save conversation history
                </p>
              </div>
              <Switch
                checked={localConfig.saveTrajectory ?? true}
                onCheckedChange={(checked: boolean) => 
                  handleConfigUpdate({ saveTrajectory: checked })
                }
              />
            </div> */}

            {/* Verbosity */}
            {/* <div className="space-y-2">
              <Label htmlFor="verbosity" className="text-sm">
                Verbosity Level
              </Label>
              <Select
                value={localConfig.verbosity?.toString() || "20"}
                onValueChange={(value) => 
                  handleConfigUpdate({ verbosity: parseInt(value) })
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="10">Debug (10)</SelectItem>
                  <SelectItem value="20">Info (20)</SelectItem>
                  <SelectItem value="30">Warning (30)</SelectItem>
                  <SelectItem value="40">Error (40)</SelectItem>
                </SelectContent>
              </Select>
            </div> */}

            {/* Image Retention - Not part of chat options, commented out */}
            {/* <div className="space-y-2">
              <Label htmlFor="imageRetention" className="text-sm">
                Image Retention
              </Label>
              <Input
                id="imageRetention"
                type="number"
                min="0"
                max="100"
                value={3}
                className="text-sm"
              />
              <p className="text-xs text-muted-foreground">
                Number of images to retain in memory
              </p>
            </div> */}

            {/* OpenAI Compatible API */}
            {/* <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label className="text-sm">Use OpenAI Compatible API</Label>
                <p className="text-xs text-muted-foreground">
                  Enable for custom API endpoints
                </p>
              </div>
              <Switch
                checked={localConfig.useOaicompat ?? false}
                onCheckedChange={(checked: boolean) => 
                  handleConfigUpdate({ useOaicompat: checked })
                }
              />
            </div> */}

            {/* Provider Base URL */}
            {chatOptions?.agent.use_oaicompat && (
              <div className="space-y-2">
                <Label htmlFor="providerBaseUrl" className="text-sm">
                  Provider Base URL
                </Label>
                <Input
                  id="providerBaseUrl"
                  type="url"
                  placeholder="https://api.example.com/v1"
                  value={chatOptions?.agent.provider_base_url || ""}
                  onChange={(e) => 
                    handleAgentConfigChange({ provider_base_url: e.target.value })
                  }
                  className="text-sm"
                />
                <p className="text-xs text-muted-foreground">
                  Custom API endpoint URL
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </ScrollArea>
  );
}
