<script lang="ts">
import Icon from '@iconify/svelte';
import { createEventDispatcher } from 'svelte';

const items = [
  { key: 'machines', icon: 'mdi:monitor-multiple', label: 'Machines' },
  { key: 'chat', icon: 'mdi:chat-outline', label: 'Chat' },
  { key: 'workflow', icon: 'mdi:chart-sankey-variant', label: 'Workflow' }
];

export let active: string;
const dispatch = createEventDispatcher();

function select(key: string) {
  dispatch('select', { key });
}
</script>

<aside class="h-full w-16 bg-white flex flex-col items-center py-4 shadow-lg border-r border-gray-200">
  <img src="https://www.trycua.com/logo-black.svg" alt="CUA Logo" class="h-8 mb-6" style="max-width: 32px;" />
  {#each items as item}
    <button
      class="group relative mb-4 p-2 rounded-lg flex items-center justify-center transition-colors duration-150 focus:outline-none"
      class:bg-blue-100={active === item.key}
      class:border-blue-500={active === item.key}
      class:text-blue-600={active === item.key}
      class:text-gray-500={active !== item.key}
      class:border-l-4={active === item.key}
      aria-label={item.label}
      aria-current={active === item.key ? 'page' : undefined}
      tabindex="0"
      on:click={() => select(item.key)}
    >
      <Icon icon={item.icon} class="text-2xl" />
      <span class="absolute left-16 top-1/2 -translate-y-1/2 scale-0 group-hover:scale-100 bg-gray-800 text-white text-xs rounded px-2 py-1 transition-transform duration-100 origin-left whitespace-nowrap shadow-lg pointer-events-none">
        {item.label}
      </span>
    </button>
  {/each}
</aside>

