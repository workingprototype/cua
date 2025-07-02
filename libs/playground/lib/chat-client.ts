import { Message } from 'ai';

export interface ChatClientOptions {
  baseUrl?: string;
  headers?: Record<string, string>;
}

export class ChatClient {
  private baseUrl: string;
  private headers: Record<string, string>;

  constructor(options: ChatClientOptions = {}) {
    this.baseUrl = options.baseUrl || '';
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
    const response = await this.fetch('/api/chat/stream', {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify({
        messages,
        computer: options.computer,
        agent: options.agent,
      }),
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
            
            if (type === '0' && data.content) {
              // Yield content chunks
              yield data.content;
            } else if (type === 'e') {
              // End of stream
              return;
            }
          } catch (err) {
            console.error('Error parsing chunk:', err);
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
