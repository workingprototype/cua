<script lang="ts">
import MainLayout from './MainLayout.svelte';
import MachinesPage from './machines/MachinesPage.svelte';
import WorkflowPage from './workflow/WorkflowPage.svelte';
import ChatPage from './chat/ChatPage.svelte';
import { onMount } from 'svelte';

let activePage = $state<'machines' | 'chat' | 'workflow'>('machines');

function getPageFromUrl(): 'machines' | 'chat' | 'workflow' {
  const path = window.location.pathname;
  if (path.includes('/workflow')) return 'workflow';
  if (path.includes('/chat')) return 'chat';
  return 'machines';
}

function setActivePage(page: 'machines' | 'chat' | 'workflow') {
  activePage = page;
  const url = page === 'machines' ? '/' : `/${page}`;
  window.history.pushState({}, '', url);
}

onMount(() => {
  activePage = getPageFromUrl();
  
  // Listen for browser back/forward navigation
  window.addEventListener('popstate', () => {
    activePage = getPageFromUrl();
  });
});
</script>

<MainLayout {activePage} setActivePage={page => setActivePage(page)}>
  {#if activePage === 'machines'}
    <MachinesPage />
  {:else if activePage === 'workflow'}
    <WorkflowPage />
  {:else if activePage === 'chat'}
    <ChatPage />
  {/if}
</MainLayout>
