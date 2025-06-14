<script lang="ts">
  import Icon from '@iconify/svelte';
  export let part: {
    type: 'computer_call',
    computer_name: string,
    image_url?: string,
    action?: { type: string; [key: string]: any },
    trajectory_id: string
  };
  export let isFirstInTrajectory: boolean = true;

  function actionDescription(action?: { type: string; [key: string]: any }) {
    if (!action) return '';
    if (action.type === 'click') {
      return `Click at (${action.x}, ${action.y})`;
    }
    if (action.type === 'type') {
      return `Type: ${action.text || ''}`;
    }
    return action.type ? `Action: ${action.type}` : '';
  }
</script>

<div class="my-2">
  <div class="flex flex-col w-full">
    <!-- Only show name, screenshot, play for the first in trajectory -->
    {#if isFirstInTrajectory}
      <span class="text-xs text-blue-500 font-semibold mb-1 flex items-center gap-1">
        <Icon icon="mdi:desktop-classic" width="16" height="16" class="text-blue-400 mr-1" />
        Controlling: <span class="font-bold">{part.computer_name}</span>
      </span>
      {#if part.image_url}
  <div class="w-3/4 aspect-video bg-gradient-to-br from-gray-300 to-gray-200 rounded-xl flex items-center justify-center text-gray-400 text-3xl shadow-inner relative overflow-hidden mb-2 group">
    <img src={part.image_url} alt="Computer call screenshot" class="object-contain w-full h-full" />
    <button
      class="absolute inset-0 flex items-center justify-center z-10 transition-all duration-150 group bg-black/25 opacity-0 group-hover:opacity-100"
      title="Play"
      aria-label="Play computer call video or animation"
      style="outline: none;"
    >
      <span class="rounded-full bg-black/25 p-5 flex items-center justify-center shadow-lg border border-white/10 backdrop-blur-xs transition-all duration-150 group-hover:scale-110 group-hover:shadow-black/30 group-hover:shadow-lg group-active:scale-95 group-active:shadow-black/50">
        <svg class="w-12 h-12 text-white drop-shadow" fill="currentColor" viewBox="0 0 24 24">
          <path d="M8 5v14l11-7z" />
        </svg>
      </span>
    </button>
  </div>
{/if}
    {/if}
    <!-- Always show action info if present -->
    {#if part.action}
      <div class="text-[10px] text-gray-400 font-mono mb-1">{actionDescription(part.action)}</div>
    {/if}
  </div>
</div>
