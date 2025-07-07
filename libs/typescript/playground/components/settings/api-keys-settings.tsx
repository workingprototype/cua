"use client";

import React, { useEffect, useState } from "react";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
  FormDescription,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Eye, EyeOff, Key, Trash2 } from "lucide-react";

const apiKeySchema = z.object({
  cuaKey: z.string().optional(),
  openaiKey: z.string().optional(),
  anthropicKey: z.string().optional(),
  ollamaUrl: z.string().url().optional().or(z.literal("")),
});

export function ApiKeysSettings() {
  const [showOpenAI, setShowOpenAI] = useState(false);
  const [showAnthropic, setShowAnthropic] = useState(false);

  const form = useForm<z.infer<typeof apiKeySchema>>({
    resolver: zodResolver(apiKeySchema),
    defaultValues: {
      cuaKey: "",
      openaiKey: "",
      anthropicKey: "",
      ollamaUrl: "",
    },
  });

  useEffect(() => {
    // Load saved API keys from localStorage
    const cuaKey = localStorage.getItem("cua_api_key") || "";
    const openaiKey = localStorage.getItem("openai_api_key") || "";
    const anthropicKey = localStorage.getItem("anthropic_api_key") || "";
    const ollamaUrl = localStorage.getItem("ollama_url") || "";

    form.reset({
      cuaKey,
      openaiKey,
      anthropicKey,
      ollamaUrl,
    });
  }, []); // Empty dependency array - only run once on mount

  function onSubmit(values: z.infer<typeof apiKeySchema>) {
    // Save API keys to localStorage
    if (values.cuaKey) {
      localStorage.setItem("cua_api_key", values.cuaKey);
    }
    if (values.openaiKey) {
      localStorage.setItem("openai_api_key", values.openaiKey);
    }
    if (values.anthropicKey) {
      localStorage.setItem("anthropic_api_key", values.anthropicKey);
    }
    if (values.ollamaUrl) {
      localStorage.setItem("ollama_url", values.ollamaUrl);
    }

    toast.success("API keys updated successfully");
  }

  const clearApiKey = (keyType: "cua" | "openai" | "anthropic" | "ollama") => {
    switch (keyType) {
      case "cua":
        localStorage.removeItem("cua_api_key");
        form.setValue("cuaKey", "");
        break;
      case "openai":
        localStorage.removeItem("openai_api_key");
        form.setValue("openaiKey", "");
        break;
      case "anthropic":
        localStorage.removeItem("anthropic_api_key");
        form.setValue("anthropicKey", "");
        break;
      case "ollama":
        localStorage.removeItem("ollama_url");
        form.setValue("ollamaUrl", "");
        break;
    }
    toast.success("API key cleared");
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h2 className="text-xl font-semibold mb-2">API Keys</h2>
        <p className="text-muted-foreground">
          Configure your API keys for different AI and VM providers
        </p>
      </div>

      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
          {/* C/ua API Key */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Key className="h-5 w-5" />
                C/ua API Key
              </CardTitle>
              <CardDescription>
                Required for C/ua Cloud Containers. Get your key from{" "}
                <a
                  href="https://www.trycua.com/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary hover:underline"
                >
                  C/ua Dashboard
                </a>
              </CardDescription>
            </CardHeader>
            <CardContent>
              <FormField
                control={form.control}
                name="cuaKey"
                render={({ field }) => (
                  <FormItem>
                    <FormControl>
                      <div className="flex gap-2">
                        <div className="relative flex-1">
                          <Input
                            {...field}
                            type={showOpenAI ? "text" : "password"}
                            placeholder="sk-..."
                          />
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            className="absolute right-2 top-1/2 -translate-y-1/2 h-8 w-8"
                            onClick={() => setShowOpenAI(!showOpenAI)}
                          >
                            {showOpenAI ? (
                              <EyeOff className="h-4 w-4" />
                            ) : (
                              <Eye className="h-4 w-4" />
                            )}
                          </Button>
                        </div>
                        <Button
                          type="button"
                          variant="outline"
                          size="icon"
                          onClick={() => clearApiKey("cua")}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </CardContent>
          </Card>

          {/* OpenAI API Key */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Key className="h-5 w-5" />
                OpenAI API Key
              </CardTitle>
              <CardDescription>
                Required for GPT models. Get your key from{" "}
                <a
                  href="https://platform.openai.com/api-keys"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary hover:underline"
                >
                  OpenAI Platform
                </a>
              </CardDescription>
            </CardHeader>
            <CardContent>
              <FormField
                control={form.control}
                name="openaiKey"
                render={({ field }) => (
                  <FormItem>
                    <FormControl>
                      <div className="flex gap-2">
                        <div className="relative flex-1">
                          <Input
                            {...field}
                            type={showOpenAI ? "text" : "password"}
                            placeholder="sk-..."
                          />
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            className="absolute right-2 top-1/2 -translate-y-1/2 h-8 w-8"
                            onClick={() => setShowOpenAI(!showOpenAI)}
                          >
                            {showOpenAI ? (
                              <EyeOff className="h-4 w-4" />
                            ) : (
                              <Eye className="h-4 w-4" />
                            )}
                          </Button>
                        </div>
                        <Button
                          type="button"
                          variant="outline"
                          size="icon"
                          onClick={() => clearApiKey("openai")}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </CardContent>
          </Card>

          {/* Anthropic API Key */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Key className="h-5 w-5" />
                Anthropic API Key
              </CardTitle>
              <CardDescription>
                Required for Claude models. Get your key from{" "}
                <a
                  href="https://console.anthropic.com/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary hover:underline"
                >
                  Anthropic Console
                </a>
              </CardDescription>
            </CardHeader>
            <CardContent>
              <FormField
                control={form.control}
                name="anthropicKey"
                render={({ field }) => (
                  <FormItem>
                    <FormControl>
                      <div className="flex gap-2">
                        <div className="relative flex-1">
                          <Input
                            {...field}
                            type={showAnthropic ? "text" : "password"}
                            placeholder="sk-ant-..."
                          />
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            className="absolute right-2 top-1/2 -translate-y-1/2 h-8 w-8"
                            onClick={() => setShowAnthropic(!showAnthropic)}
                          >
                            {showAnthropic ? (
                              <EyeOff className="h-4 w-4" />
                            ) : (
                              <Eye className="h-4 w-4" />
                            )}
                          </Button>
                        </div>
                        <Button
                          type="button"
                          variant="outline"
                          size="icon"
                          onClick={() => clearApiKey("anthropic")}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </CardContent>
          </Card>

          {/* Ollama URL */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Key className="h-5 w-5" />
                Ollama URL
              </CardTitle>
              <CardDescription>
                URL for your local Ollama instance (e.g., http://localhost:11434)
              </CardDescription>
            </CardHeader>
            <CardContent>
              <FormField
                control={form.control}
                name="ollamaUrl"
                render={({ field }) => (
                  <FormItem>
                    <FormControl>
                      <div className="flex gap-2">
                        <Input
                          {...field}
                          type="url"
                          placeholder="http://localhost:11434"
                          className="flex-1"
                        />
                        <Button
                          type="button"
                          variant="outline"
                          size="icon"
                          onClick={() => clearApiKey("ollama")}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </CardContent>
          </Card>

          <div className="flex justify-end">
            <Button type="submit">Save API Keys</Button>
          </div>
        </form>
      </Form>
    </div>
  );
}
