<script lang="ts">
import MainLayout from './MainLayout.svelte';
import MachinesPage from './machines/MachinesPage.svelte';
import WorkflowPage from './workflow/WorkflowPage.svelte';
import ChatPage from './chat/ChatPage.svelte';

let activePage = $state<'machines' | 'chat' | 'workflow'>('machines');
</script>

<MainLayout {activePage} setActivePage={page => activePage = page}>
  {#if activePage === 'machines'}
    <MachinesPage />
  {:else if activePage === 'workflow'}
    <WorkflowPage />
  {:else if activePage === 'chat'}
    <ChatPage />
  {/if}
</MainLayout>
