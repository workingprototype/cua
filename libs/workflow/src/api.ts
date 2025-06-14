// Mock API for machines and chat
export type VM = {
  provider: 'Windows Sandbox' | 'C/ua Cloud';
  name: string;
  os: string;
  vnc_url?: string | null;
  status: 'running' | 'stopped';
};

const mockVMs: VM[] = [
  { provider: 'C/ua Cloud', name: 'm-linux-4l9zk7itlu', os: 'Ubuntu 22.04', vnc_url: 'https://m-linux-4l9zk7itlu.containers.cloud.trycua.com/vnc.html?autoconnect=true&password=f91c9a15f75a233b', status: 'running' },
  { provider: 'Windows Sandbox', name: 'Windows 11 VM', os: 'Windows 11', vnc_url: null, status: 'stopped' },
  { provider: 'C/ua Cloud', name: 'Cloud-Win', os: 'Windows 10', vnc_url: null, status: 'stopped' },
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
export type WorkflowNodeData = {
  prompt: string;
  gif: string;
  tool_calls?: string[];
};

export async function load_workflow(): Promise<WorkflowNodeData[]> {
  const res = await fetch('/src/assets/trajectory_nodes.json');
  return await res.json();
}
