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
        <div class="relative group mb-2">
          <img src={part.image_url} alt="Computer call screenshot" class="max-w-xs rounded-md shadow-md" />
          <button class="absolute inset-0 flex items-center justify-center bg-black/30 rounded-md opacity-0 group-hover:opacity-100 transition" title="Play" aria-label="Play computer call video or animation">
            <svg class="w-12 h-12 text-white" fill="currentColor" viewBox="0 0 24 24">
              <path d="M8 5v14l11-7z" />
            </svg>
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
