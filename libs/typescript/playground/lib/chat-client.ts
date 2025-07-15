import { Message } from 'ai';

// Agent loop options
export const AGENT_LOOPS = [
  { value: "OPENAI", label: "OpenAI", description: "Uses OpenAI Operator CUA model" },
  { value: "ANTHROPIC", label: "Anthropic", description: "Uses Anthropic Computer-Use models" },
  { value: "OMNI", label: "Omni", description: "Uses OmniParser for element pixel-detection" },
  { value: "UITARS", label: "UI-TARS", description: "UI-TARS implementation" },
];

// Model options for each agent loop
export const MODELS_BY_LOOP: Record<string, string[]> = {
  OPENAI: ["computer-use-preview"],
  ANTHROPIC: ["claude-3-5-sonnet-20240620", "claude-3-7-sonnet-20250219"],
  OMNI: [
    "claude-3-5-sonnet-20240620",
    "claude-3-7-sonnet-20250219", 
    "gpt-4.5-preview",
    "gpt-4o",
    "gpt-4"
  ],
  UITARS: [
    "ByteDance-Seed/UI-TARS-1.5-7B",
    "huggingface/ByteDance-Seed/UI-TARS-1.5-7B"
  ],
};

export interface ChatClientOptions {
  baseUrl?: string;
  headers?: Record<string, string>;
}

export class ChatClient {
  private baseUrl: string;
  private headers: Record<string, string>;

  constructor(options: ChatClientOptions = {}) {
    this.baseUrl = options.baseUrl || 'http://localhost:8001';
    this.headers = {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    };
  }

  async *stream(
    messages: Message[],
    options: {
      computer?: {
        provider: string;
        name: string;
        os: string;
        api_key?: string;
      };
      agent?: {
        loop: string;
        model: string;
        temperature?: number;
        max_tokens?: number;
        system_prompt?: string;
        save_trajectory?: boolean;
        verbosity?: number;
        use_oaicompat?: boolean;
        provider_base_url?: string;
      };
      signal?: AbortSignal;
    } = {}
  ) {
    // Ensure required fields are present
    if (!options.computer) {
      throw new Error('Computer configuration is required');
    }
    if (!options.agent) {
      throw new Error('Agent configuration is required');
    }

    // Convert messages to the expected format
    const formattedMessages = messages.map(msg => ({
      role: msg.role,
      content: msg.content
    }));

    // Helper function to get agent API key based on loop
    const getAgentApiKey = (loop: string): string => {
      if (typeof window === 'undefined') return "";
      
      switch (loop) {
        case "ANTHROPIC":
        case "OMNI":
          return localStorage.getItem("anthropic_api_key") || process.env.NEXT_PUBLIC_ANTHROPIC_API_KEY || "";
        case "OPENAI":
          return localStorage.getItem("openai_api_key") || process.env.NEXT_PUBLIC_OPENAI_API_KEY || "";
        case "UITARS":
          // UI-TARS might use different API key or none
          return localStorage.getItem("uitars_api_key") || "";
        default:
          return "";
      }
    };

    // Build computer config - only include api_key for cua-cloud provider
    const computerConfig: any = {
      provider: options.computer.provider,
      name: options.computer.name,
      os: options.computer.os
    };
    
    // Only add api_key if provider is cua-cloud
    if (options.computer.provider === "cua-cloud") {
      computerConfig.api_key = options.computer.api_key || '';
    }

    const requestBody = {
      messages: formattedMessages,
      computer: computerConfig,
      agent: {
        loop: options.agent.loop,
        model: options.agent.model,
        temperature: options.agent.temperature,
        max_tokens: options.agent.max_tokens,
        system_prompt: options.agent.system_prompt,
        save_trajectory: options.agent.save_trajectory ?? true,
        verbosity: options.agent.verbosity,
        use_oaicompat: options.agent.use_oaicompat ?? false,
        provider_base_url: options.agent.provider_base_url,
        provider_api_key: getAgentApiKey(options.agent.loop)
      }
    };

    console.log("Request body:", JSON.stringify(requestBody, null, 2));

    const response = await this.fetch('/chat', {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify(requestBody),
      signal: options.signal,
    });

    if (!response.body) {
      throw new Error('Response body is null');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        
        // Keep the last incomplete line in the buffer
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.trim()) continue;
          
          try {
            const type = line[0];
            const data = JSON.parse(line.slice(2));
            
            if (type === '0') {
              // Text part - yield content directly
              yield data;
            } else if (type === 'g') {
              // Reasoning part - yield as dictionary
              yield { type: 'reasoning', content: data };
            } else if (type === '2') {
              // Data part - yield as dictionary
              yield { type: 'data', content: data };
            } else if (type === '3') {
              // Error part
              yield `Error: ${data}`;
            } else if (type === 'e') {
              // End of stream
              return;
            }
          } catch (err) {
            console.error('Error parsing chunk:', err, 'Line:', line);
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  }

  private async fetch(input: string, init?: RequestInit) {
    const url = `${this.baseUrl}${input}`;
    const response = await fetch(url, {
      ...init,
      headers: {
        ...this.headers,
        ...(init?.headers || {}),
      },
    });

    if (!response.ok) {
      const error = await response.text().catch(() => response.statusText);
      throw new Error(`HTTP error! status: ${response.status}, message: ${error}`);
    }

    return response;
  }
}

// Default instance
export const chatClient = new ChatClient();
