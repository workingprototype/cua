<script lang="ts">
  import { Position, Handle, NodeToolbar, type NodeProps } from '@xyflow/svelte';
  import Icon from '@iconify/svelte';
  let { id, data, selected }: NodeProps = $props();
  // Type guard for data
  let label = '';
  let gif: string | undefined = undefined;
  let isStart = false;
  if (data && typeof data === 'object') {
    const d = data as { label?: unknown; gif?: unknown; isStart?: unknown };
    label = typeof d.label === 'string' ? d.label : '';
    gif = typeof d.gif === 'string' ? d.gif : undefined;
    isStart = !!d.isStart;
  }

  function handleDelete() {
    console.log('Delete node:', id);
    // TODO: Implement delete functionality
  }

  function handleOptions() {
    console.log('Options for node:', id);
    // TODO: Implement options functionality
  }
</script>

<NodeToolbar position={Position.Top} align="center">
  <div class="flex gap-1 bg-white rounded-lg shadow-lg border border-gray-200 p-1">
    <button 
      class="p-1.5 hover:bg-gray-100 rounded text-gray-600 hover:text-gray-800 transition-colors"
      onclick={handleOptions}
      title="Options"
    >
      <Icon icon="mdi:dots-horizontal" width="16" height="16" />
    </button>
    <button 
      class="p-1.5 hover:bg-red-100 rounded text-gray-600 hover:text-red-600 transition-colors"
      onclick={handleDelete}
      title="Delete"
    >
      <Icon icon="mdi:delete-outline" width="16" height="16" />
    </button>
  </div>
</NodeToolbar>

<div class="w-60 bg-white rounded-lg shadow flex flex-col overflow-hidden {selected ? 'ring-2 ring-blue-500 ring-offset-2' : ''}" data-id={id} tabindex="0" role="button" style="cursor:pointer;">
  <!-- First row: icon + type label -->
  <div class="flex flex-row items-center gap-2 px-3 pt-3 pb-1">
    <span class="flex items-center justify-center mt-0.5">
      {#if isStart}
        <Icon icon="mdi:play-circle-outline" width="22" height="22" class="text-green-500" />
        <span class="uppercase tracking-widest text-xs text-gray-400 ml-1">Start</span>
      {:else}
        <Icon icon="mdi:cursor-default-outline" width="20" height="20" class="text-gray-400" />
        <span class="uppercase tracking-widest text-xs text-gray-400 ml-1">Act</span>
      {/if}
    </span>
  </div>
  <!-- Second row: prompt as monospace text field -->
  <div class="font-mono text-sm bg-gray-50 px-3 py-2 rounded mb-2 mx-3 break-words border border-gray-100">{label}</div>
  <!-- Third row: gif -->
  {#if gif}
    <div class="w-full h-40 bg-gray-100 flex items-stretch justify-stretch">
      <img src={gif.startsWith('/') ? gif : '/src/' + gif} alt={label} class="w-full h-full object-cover" />
    </div>
  {/if}
  <Handle type="target" position={Position.Left} />
  <Handle type="source" position={Position.Right} />
</div>
