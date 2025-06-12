<script lang="ts">
  import {
    SvelteFlow,
    Controls,
    Background,
    MiniMap,
    type Node,
    type Edge,
    Position,
    Panel,
    useOnSelectionChange
  } from "@xyflow/svelte";
  import TrajectoryNode from "./TrajectoryNode.svelte";
  import "@xyflow/svelte/dist/style.css";
  import "./app.css";
  import { onMount } from "svelte";
  import Icon from '@iconify/svelte';

  const nodeTypes = { trajectory: TrajectoryNode };

  let nodes = $state.raw<Node[]>([]);
  let edges = $state.raw<Edge[]>([]);
  let selectedNodeId = $state<string | null>(null);
  let runHistory = $state<(string | { name: string; screenshot?: string })[]>([]);
  let activeTab = $state<'run-history' | 'demonstration'>('run-history');

  // Mock data for run history
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
    const res = await fetch("/src/assets/trajectory_nodes.json");
    const data: Array<{ prompt: string; gif: string; tool_calls?: string[] }> = await res.json();
    
    // Pick a random index for default selection
    const randomIndex = Math.floor(Math.random() * data.length);
    
    // Map the loaded JSON to Node[] shape for SvelteFlow
    nodes = data.map((item: { prompt: string; gif: string; tool_calls?: string[] }, idx: number) => ({
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
      selected: idx === randomIndex, // Select the random node by default
    }));
    // Generate edges: connect each node to the next
    edges = data.slice(1).map((_, idx) => ({
      id: `${idx + 1}-${idx + 2}`,
      source: String(idx + 1),
      target: String(idx + 2),
    }));
    
    // Set a random node as selected by default
    if (nodes.length > 0) {
      selectedNodeId = nodes[randomIndex].id;
      runHistory = (nodes[randomIndex].data?.tool_calls ?? []) as (string | { name: string; screenshot?: string })[];
    }
  });

  // Use the selection change hook instead of nodeClick
  useOnSelectionChange(({ nodes: selectedNodes }) => {
    if (selectedNodes.length > 0) {
      const nodeId = selectedNodes[0].id;
      selectedNodeId = nodeId;
      const node = nodes.find((n) => n.id === nodeId);
      runHistory = (node?.data?.tool_calls ?? []) as (string | { name: string; screenshot?: string })[];
    } else {
      selectedNodeId = null;
      runHistory = [];
    }
  });
</script>


<div style:height="100vh">
  <SvelteFlow bind:nodes bind:edges {nodeTypes} fitView>
    <Controls />
    <Background />
    <MiniMap />
    <Panel position="center-right">
  {#if selectedNodeId}
    <div class="w-80 max-h-[70vh] overflow-y-auto bg-white rounded-lg shadow-lg mt-4 mr-2 border border-gray-200">
      <!-- Tab Headers -->
      <div class="flex border-b border-gray-200">
        <button 
          class="flex-1 px-4 py-3 text-sm font-medium {activeTab === 'run-history' ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50' : 'text-gray-500 hover:text-gray-700'}"
          onclick={() => activeTab = 'run-history'}
        >
          <div class="flex items-center justify-center gap-2">
            <Icon icon="mdi:history" width="16" height="16" />
            Run History
          </div>
        </button>
        <button 
          class="flex-1 px-4 py-3 text-sm font-medium {activeTab === 'demonstration' ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50' : 'text-gray-500 hover:text-gray-700'}"
          onclick={() => activeTab = 'demonstration'}
        >
          <div class="flex items-center justify-center gap-2">
            <Icon icon="mdi:play-circle-outline" width="16" height="16" />
            Demonstration
          </div>
        </button>
      </div>
      
      <!-- Tab Content -->
      <div class="p-4">
        {#if activeTab === 'run-history'}
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
        {/if}
      </div>
    </div>
  {/if}
</Panel>
  </SvelteFlow>
</div>
