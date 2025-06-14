<script lang="ts">
import Sidebar from './Sidebar.svelte';

export let activePage: 'machines' | 'chat' | 'workflow';
export let setActivePage: (page: 'machines' | 'chat' | 'workflow') => void;
</script>

<div class="flex h-screen w-screen">
  <Sidebar active={activePage} on:select={e => setActivePage(e.detail.key)} />
  <slot />
</div>
