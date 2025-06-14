<script lang="ts">
import Icon from '@iconify/svelte';
import type { VM } from '../api';
import { onMount } from 'svelte';
export let vms: VM[] = [];
export let selectedVM: VM | null = null;
export let onSelect: (vm: VM) => void = () => {};

let showDropdown = false;
let showCloudExistingModal = false;
let cloudVmName = '';
let cloudApiKey = '';

function handleAdd(type: string) {
  showDropdown = false;
  if (type === 'cloud_existing') {
    showCloudExistingModal = true;
    cloudVmName = '';
    cloudApiKey = '';
  }
}

function closeCloudExistingModal() {
  showCloudExistingModal = false;
}

function addCloudExistingVm() {
  // TODO: Replace with actual logic to add the VM
  console.log('Adding existing cloud VM:', cloudVmName, cloudApiKey);
  showCloudExistingModal = false;
}

// Close dropdown on outside click
function handleClickOutside(event: MouseEvent) {
  const dropdown = document.getElementById('machines-add-dropdown');
  const btn = document.getElementById('machines-menu-btn');
  if (dropdown && btn && !dropdown.contains(event.target as Node) && !btn.contains(event.target as Node)) {
    showDropdown = false;
  }
}

onMount(() => {
  document.addEventListener('mousedown', handleClickOutside);
  return () => document.removeEventListener('mousedown', handleClickOutside);
});
</script>

<aside class="w-64 bg-white border-r border-gray-100 flex flex-col p-4 shadow-sm">
  <div class="flex items-center justify-between mb-3">
    <h2 class="text-xs font-bold px-2 py-1 uppercase tracking-wider text-gray-500">Machines</h2>
    <div class="relative">
      <button
        id="machines-menu-btn"
        class="p-1 rounded-lg hover:bg-blue-50 transition flex items-center justify-center"
        title="New Machine"
        on:click={() => showDropdown = !showDropdown}
        aria-haspopup="true"
        aria-expanded={showDropdown}
      >
        <Icon icon="material-symbols:add-circle-outline-rounded" width="22" height="22" class="text-blue-600" />
      </button>
      {#if showDropdown}
        <div id="machines-add-dropdown" class="absolute right-0 mt-2 w-56 bg-white border border-gray-200 rounded-lg shadow-lg z-20">
          <button class="w-full text-left px-4 py-2 hover:bg-blue-50 transition font-semibold text-blue-700" on:click={() => handleAdd('cloud_existing')}>
            Add existing cloud VM...
          </button>
          <button class="w-full text-left px-4 py-2 text-gray-300 cursor-not-allowed transition" disabled>
            Create a cloud VM...
          </button>
          <button class="w-full text-left px-4 py-2 text-gray-300 cursor-not-allowed transition" disabled>
            Create a local VM...
          </button>
          <button class="w-full text-left px-4 py-2 text-gray-300 cursor-not-allowed transition" disabled>
            Add existing RDP/VNC VM...
          </button>
        </div>
      {/if}

      <!-- Modal for Add existing cloud VM -->
      {#if showCloudExistingModal}
      <div class="fixed inset-0 z-30 flex items-center justify-center bg-black/40">
        <div class="bg-white rounded-xl shadow-xl p-8 w-full max-w-sm">
          <h3 class="text-lg font-semibold mb-4">Add Existing Cloud VM</h3>
          <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700 mb-1">VM Name</label>
            <input type="text" bind:value={cloudVmName} class="w-full border rounded px-3 py-2 focus:outline-none focus:ring focus:ring-blue-200" placeholder="Enter VM name" />
          </div>
          <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700 mb-1">c/ua API Key</label>
            <input type="password" bind:value={cloudApiKey} class="w-full border rounded px-3 py-2 focus:outline-none focus:ring focus:ring-blue-200" placeholder="Enter API key" />
          </div>
          <div class="flex justify-end gap-2 mt-6">
            <button class="px-4 py-2 rounded bg-gray-200 text-gray-700 hover:bg-gray-300" on:click={closeCloudExistingModal}>Cancel</button>
            <button class="px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-700 font-semibold" on:click={addCloudExistingVm}>Add</button>
          </div>
        </div>
      </div>
      {/if}


    </div>
  </div>
  <ul class="flex-1 overflow-y-auto space-y-1">
    {#each vms as vm}
      <li>
        <button
          type="button"
          class="w-full flex items-center gap-3 px-2 py-2 rounded-lg transition focus:outline-none focus:ring-0 focus:ring-blue-500 hover:bg-blue-50"
          class:bg-blue-100={selectedVM && selectedVM.name === vm.name}
          aria-current={selectedVM && selectedVM.name === vm.name ? 'page' : undefined}
          on:click={() => onSelect(vm)}
        >
          <span class="text-2xl">
            <Icon icon="material-symbols:monitor-outline" width="28" height="28" class="text-blue-400" />
          </span>
          <span class="flex flex-col text-left">
            <span class="font-semibold text-gray-800 text-sm">{vm.name}</span>
            <span class="text-xs text-gray-500">{vm.provider} &bull; {vm.os}</span>
          </span>
        </button>
      </li>
    {/each}
  </ul>
</aside>
