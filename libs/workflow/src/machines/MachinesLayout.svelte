<script lang="ts">
import MachinesSidebar from './MachinesSidebar.svelte';
import MachinesMain from './MachinesMain.svelte';
import { onMount } from 'svelte';
import { list_vms, type VM } from '../api';

let vms: VM[] = [];
let selectedVM: VM | null = null;
let loading = true;

onMount(async () => {
  vms = await list_vms();
  selectedVM = vms[0] || null;
  loading = false;
});

function handleSelect(vm: VM) {
  selectedVM = vm;
}
</script>

<div class="flex h-full w-full">
  <MachinesSidebar {vms} {selectedVM} onSelect={handleSelect} />
  <MachinesMain {selectedVM} />
</div>
