<script lang="ts">
import WorkflowSidebar from './WorkflowSidebar.svelte';
import WorkflowMain from './WorkflowMain.svelte';
    import { SvelteFlowProvider } from '@xyflow/svelte';
</script>

<div class="flex h-full w-full">
  <WorkflowSidebar />
  <SvelteFlowProvider>
    <WorkflowMain />
  </SvelteFlowProvider>
</div>
