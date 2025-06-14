// Mock API for machines and chat
export type VM = {
  provider: 'Windows Sandbox' | 'C/ua Cloud' | 'Lume';
  name: string;
  os: string;
  vnc_url?: string | null;
  status: 'running' | 'stopped';
};

const mockVMs: VM[] = [
  { provider: 'C/ua Cloud', name: 'm-linux-4l9zk7itlu', os: 'Ubuntu 22.04', vnc_url: 'https://m-linux-4l9zk7itlu.containers.cloud.trycua.com/vnc.html?autoconnect=true&password=f91c9a15f75a233b', status: 'running' },
  { provider: 'Windows Sandbox', name: 'Windows 11 VM', os: 'Windows 11', vnc_url: null, status: 'stopped' },
  { provider: 'Lume', name: 'macos-sequoia-cua_latest', os: 'macOS 15.5', vnc_url: null, status: 'stopped' },
];

export async function list_vms(): Promise<VM[]> {
  // Simulate API latency
  await new Promise((r) => setTimeout(r, 250));
  return [...mockVMs];
}

export async function add_vm(vm: VM): Promise<void> {
  // No-op for now
  await new Promise((r) => setTimeout(r, 100));
}

export async function remove_vm(name: string): Promise<void> {
  // No-op for now
  await new Promise((r) => setTimeout(r, 100));
}

// Simple chat API stub (OpenAI wrapper)
export async function chat(prompt: string): Promise<string> {
  // Replace with real OpenAI call
  await new Promise((r) => setTimeout(r, 400));
  return `Echo: ${prompt}`;
}

// ----------- Workflow/Trajectory Loader -----------
export type ToolCall = {
  name: string;
  screenshot?: string;
};

export type WorkflowNodeData = {
  prompt: string;
  gif: string;
  tool_calls?: ToolCall[];
};

export async function load_workflow(): Promise<WorkflowNodeData[]> {
  const res = await fetch('/src/assets/trajectory_nodes.json');
  return await res.json();
}

// ----------- Mock Chat Loader -----------
export type ChatMessageData = {
  from: 'user' | 'assistant';
  value: any;
};

export async function load_mock_chat(): Promise<ChatMessageData[]> {
  const res = await fetch('/src/assets/trajectory_nodes.json');
  const data: WorkflowNodeData[] = await res.json();
  // Use the first VM for all computer_calls
  const firstVM = mockVMs[0]?.name || 'vm-1';
  const chat: ChatMessageData[] = [];
  for (const node of data) {
    // User message
    chat.push({ from: 'user', value: [ { type: 'text', text: node.prompt } ] });
    // Assistant tool calls
    if (node.tool_calls && node.tool_calls.length > 0) {
      chat.push({
        from: 'assistant',
        value: node.tool_calls.map(tc => {
          let image_url: string | undefined;
          if (tc.screenshot) {
            image_url = tc.screenshot.startsWith('/') ? tc.screenshot : '/src/' + tc.screenshot;
          } else if (node.gif) {
            image_url = node.gif.startsWith('/') ? node.gif : '/src/' + node.gif;
          } else {
            image_url = undefined;
          }
          return {
            type: 'computer_call',
            computer_name: firstVM,
            image_url,
            action: { type: tc.name },
            trajectory_id: 'traj_mock',
          };
        })
      });
    }
  }
  return chat;
}
