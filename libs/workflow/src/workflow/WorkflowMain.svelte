<script lang="ts">
import {
  SvelteFlow,
  Controls,
  Background,
  MiniMap,
  Panel,
  useOnSelectionChange,
  type Node,
  type Edge,
  Position
} from "@xyflow/svelte";
import TrajectoryNode from "./TrajectoryNode.svelte";
import Icon from '@iconify/svelte';
import '@xyflow/svelte/dist/style.css';
import { onMount } from 'svelte';
import { load_workflow, type WorkflowNodeData } from '../api';

const nodeTypes = { trajectory: TrajectoryNode };

let nodes = $state.raw<Node[]>([]);
let edges = $state.raw<Edge[]>([]);
let selectedNodes = $state.raw<string[]>([]);
let selectedEdges = $state.raw<string[]>([]);
let runHistory = $state<(string | { name: string; screenshot?: string })[]>([]);
let activeTab = $state<'run-history' | 'demonstration' | 'properties'>('run-history');
let nodeProperties = $state({
  agent: 'cascade',
  prompt: '',
  tools: ['computer:left_click'],
  enableCache: true,
  maxActions: 10
});
let showToolsEditor = $state(false);
const availableTools = [
  'cua:create_vm',
  'cua:load_vm',
  'computer:open_app',
  'computer:bash',
  'computer:left_click',
  'computer:wait',
  'computer:type_text'
];

// Mock data for run history UI (keep only if needed for placeholder)
const mockRunHistory = [
  {
    type: 'agent-run',
    steps: 15,
    cacheHits: 16,
    cacheMisses: 3,
    tokens: 12450,
    price: 0.24,
    timestamp: '2 minutes ago'
  },
  {
    type: 'agent-run',
    steps: 8,
    cacheHits: 12,
    cacheMisses: 1,
    tokens: 8230,
    price: 0.16,
    timestamp: '5 minutes ago'
  },
  {
    type: 'agent-run',
    steps: 23,
    cacheHits: 7,
    cacheMisses: 8,
    tokens: 18750,
    price: 0.38,
    timestamp: '12 minutes ago'
  }
];

onMount(async () => {
  const data: WorkflowNodeData[] = await load_workflow();
  nodes = data.map((item, idx) => ({
    id: String(idx + 1),
    type: "trajectory",
    data: {
      label: item.prompt,
      gif: item.gif,
      tool_calls: item.tool_calls ?? [],
      isStart: idx === 0,
    },
    position: { x: idx * 320, y: 0 },
    sourcePosition: Position.Right,
    targetPosition: Position.Left,
    selected: false,
  }));
  edges = data.slice(1).map((_, idx) => ({
    id: `${idx + 1}-${idx + 2}`,
    source: String(idx + 1),
    target: String(idx + 2),
  }));
  // No node selected by default
  // selectedNodes = [];
  // runHistory = [];
});

useOnSelectionChange(({ nodes, edges }) => {
  selectedNodes = nodes.map((node) => node.id);
  selectedEdges = edges.map((edge) => edge.id);
});

// Use the selection change hook instead of nodeClick, if needed
// (add your selection logic here if required)
</script>

<main class="flex-1 h-screen w-full overflow-y-auto">
  <div class="h-full">
    <SvelteFlow bind:nodes bind:edges {nodeTypes} fitView>
      <Controls />
      <Background bgColor="#f5f5f5" />
      <MiniMap />
      {#if selectedNodes.length > 0}
      <Panel position="top-right">
        <div class="w-80 max-h-[70vh] overflow-y-auto bg-white rounded-lg shadow-lg mt-4 mr-2 border border-gray-200">
            <div class="flex border-b border-gray-200">
              <button class="flex-1 px-3 py-2 text-xs font-medium {activeTab === 'run-history' ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50' : 'text-gray-500 hover:text-gray-700'}" on:click={() => activeTab = 'run-history'} title="Run History">
                <div class="flex items-center justify-center">
                  <Icon icon="mdi:history" width="16" height="16" />
                </div>
              </button>
              <button class="flex-1 px-3 py-2 text-xs font-medium {activeTab === 'properties' ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50' : 'text-gray-500 hover:text-gray-700'}" on:click={() => activeTab = 'properties'} title="Properties">
                <div class="flex items-center justify-center">
                  <Icon icon="mdi:cog-outline" width="16" height="16" />
                </div>
              </button>
              <button class="flex-1 px-3 py-2 text-xs font-medium {activeTab === 'demonstration' ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50' : 'text-gray-500 hover:text-gray-700'}" on:click={() => activeTab = 'demonstration'} title="Demonstrations">
                <div class="flex items-center justify-center">
                  <Icon icon="mdi:play-circle-outline" width="16" height="16" />
                </div>
              </button>
            </div>
            <div class="p-4">
              {#if activeTab === 'run-history'}
                <h3 class="text-sm font-semibold mb-3 flex items-center gap-2">
                  <Icon icon="mdi:history" width="16" height="16" />
                  Run History
                </h3>
                <div class="space-y-3">
                  {#each mockRunHistory as run, i}
                    <div class="bg-gray-50 rounded-lg p-3 border border-gray-100">
                      <div class="flex items-center justify-between mb-2">
                        <div class="flex items-center gap-2">
                          <div class="w-2 h-2 bg-green-500 rounded-full"></div>
                          <span class="text-xs font-medium text-gray-600 uppercase tracking-wide">Agent Run</span>
                        </div>
                        <span class="text-xs font-medium text-gray-900">{run.steps} steps</span>
                      </div>
                      <div class="text-xs text-gray-600 mb-2">
                        {run.cacheHits} cache hits (muscle-mem)
                      </div>
                      <div class="text-xs text-gray-500 mb-2">
                        {run.cacheMisses} cache misses • {run.tokens.toLocaleString()} tokens • ${run.price.toFixed(2)}
                      </div>
                      <button class="text-xs text-blue-600 hover:text-blue-800 font-medium">
                        see trajectory →
                      </button>
                    </div>
                  {/each}
                </div>
              {:else if activeTab === 'demonstration'}
                <h3 class="text-sm font-semibold mb-3 flex items-center gap-2">
                  <Icon icon="mdi:play-circle-outline" width="16" height="16" />
                  Demonstrations
                </h3>
                {#if runHistory.length > 0}
                  <div class="space-y-2">
                    {#each runHistory as call, i}
                      <div class="bg-gray-50 rounded px-3 py-2">
                        {#if typeof call === 'string'}
                          <div class="text-xs font-mono">{call}</div>
                        {:else if call && typeof call === 'object'}
                          <div class="text-xs font-mono mb-1">{call.name || call}</div>
                          {#if call.screenshot}
                            <img src={call.screenshot.startsWith('/') ? call.screenshot : '/src/' + call.screenshot} 
                                 alt="Screenshot for {call.name}" 
                                 class="w-full max-w-48 h-auto rounded border border-gray-200 mt-1" />
                          {/if}
                        {/if}
                      </div>
                    {/each}
                  </div>
                {:else}
                  <div class="text-gray-400 italic text-center py-8">No tool calls available</div>
                {/if}
              {:else if activeTab === 'properties'}
                <h3 class="text-sm font-semibold mb-3 flex items-center gap-2">
                  <Icon icon="mdi:cog-outline" width="16" height="16" />
                  Node Properties
                </h3>
                <form class="space-y-3">
                  <div>
                    <label for="agent-select" class="block text-xs font-medium text-gray-700 mb-1">Agent</label>
                    <select id="agent-select" bind:value={nodeProperties.agent} class="w-full px-2 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-transparent">
                      <option value="cascade">C/ua Orchestrator</option>
                      <option value="claude">Claude</option>
                      <option value="gpt-4">GPT-4</option>
                      <option value="gemini">Gemini</option>
                    </select>
                  </div>
                  <div>
                    <label for="prompt-textarea" class="block text-xs font-medium text-gray-700 mb-1">Prompt</label>
                    <textarea 
                      id="prompt-textarea"
                      bind:value={nodeProperties.prompt} 
                      class="w-full px-2 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-transparent resize-none"
                      rows="2"
                      placeholder="Enter your prompt here..."
                    ></textarea>
                  </div>
                  <div>
                    <label for={showToolsEditor ? "tools-select" : undefined} class="block text-xs font-medium text-gray-700 mb-1">Tools</label>
                    <div class="flex items-center justify-between mb-2">
                      <span class="text-xs font-medium text-gray-600">{nodeProperties.tools.length} tools selected</span>
                      <button 
                        type="button"
                        class="text-xs text-blue-600 hover:text-blue-800 font-medium"
                        on:click={() => showToolsEditor = !showToolsEditor}
                      >
                        {showToolsEditor ? 'Hide' : 'Edit'}
                      </button>
                    </div>
                    {#if showToolsEditor}
                      <select 
                        id="tools-select"
                        bind:value={nodeProperties.tools} 
                        multiple 
                        class="w-full px-2 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-transparent"
                        size="4"
                      >
                        {#each availableTools as tool}
                          <option value={tool}>{tool}</option>
                        {/each}
                      </select>
                    {/if}
                  </div>
                  <div>
                    <label for="max-actions-input" class="block text-xs font-medium text-gray-700 mb-1">Max Actions</label>
                    <input 
                      id="max-actions-input"
                      type="number" 
                      bind:value={nodeProperties.maxActions} 
                      min="1" 
                      max="100"
                      class="w-full px-2 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>
                  <div>
                    <label class="flex items-center">
                      <input type="checkbox" bind:checked={nodeProperties.enableCache} class="mr-2 scale-75" />
                      <span class="text-xs font-medium text-gray-700">Enable Cache</span>
                    </label>
                  </div>
                </form>
              {/if}
            </div>
          </div>
      </Panel>
      {/if}
    </SvelteFlow>
  </div>
</main>
