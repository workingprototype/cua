<script lang="ts">
import Icon from '@iconify/svelte';
import { onMount } from 'svelte';

let menuOpen = false;

function openMenu() {
  menuOpen = true;
}
function closeMenu() {
  menuOpen = false;
}

function handleNewWorkflow() {
  // TODO: Implement new workflow creation logic
  closeMenu();
}

function handleImportFromChat() {
  // TODO: Implement import from chat logic
  closeMenu();
}

// Close menu on outside click
function handleClickOutside(event: MouseEvent) {
  const menu = document.getElementById('workflow-menu-dropdown');
  const btn = document.getElementById('workflow-menu-btn');
  if (menu && btn && !menu.contains(event.target as Node) && !btn.contains(event.target as Node)) {
    closeMenu();
  }
}

onMount(() => {
  window.addEventListener('mousedown', handleClickOutside);
  return () => window.removeEventListener('mousedown', handleClickOutside);
});
</script>

<aside class="w-64 bg-white border-r border-gray-100 flex flex-col p-4 shadow-sm">
  <div class="flex items-center justify-between mb-3">
    <h2 class="text-xs font-bold px-2 py-1 uppercase tracking-wider text-gray-500">Workflows</h2>
    <div class="relative">
      <button id="workflow-menu-btn" class="p-1 rounded-lg hover:bg-blue-50 transition flex items-center justify-center" title="Workflow Menu" on:click={() => menuOpen = !menuOpen} aria-haspopup="true" aria-expanded={menuOpen}>
        <Icon icon="material-symbols:add-circle-outline-rounded" width="22" height="22" class="text-blue-600" />
      </button>
      {#if menuOpen}
        <div id="workflow-menu-dropdown" class="absolute right-0 mt-2 w-56 bg-white border border-gray-200 rounded-lg shadow-lg z-20">
          <button class="w-full text-left px-4 py-2 hover:bg-blue-50 transition font-semibold text-blue-700" on:click={handleNewWorkflow}>
            New Workflow
          </button>
          <button class="w-full text-left px-4 py-2 hover:bg-blue-50 transition" on:click={handleImportFromChat}>
            Import from Chat
          </button>
          <button class="w-full text-left px-4 py-2 hover:bg-blue-50 transition" on:click={handleImportFromChat}>
            Import demonstration
          </button>
        </div>
      {/if}
    </div>
  </div>
  <div class="flex-1 text-gray-400 flex items-center justify-center">No workflows yet</div>
</aside>
