<script lang="ts">
import Icon from '@iconify/svelte';
import { onMount } from 'svelte';

let chats: { id: number; title: string }[] = [];
let nextId = 1;
let menuOpenId: number | null = null;
let renamingId: number | null = null;
let renameTitle = '';

function addChat() {
  chats = [
    ...chats,
    { id: nextId++, title: 'New chat' }
  ];
}

function openMenu(id: number) {
  menuOpenId = id;
}
function closeMenu() {
  menuOpenId = null;
}
function startRename(id: number, current: string) {
  renamingId = id;
  renameTitle = current;
  closeMenu();
}
function confirmRename(id: number) {
  chats = chats.map(c => c.id === id ? { ...c, title: renameTitle } : c);
  renamingId = null;
  renameTitle = '';
}
function deleteChat(id: number) {
  chats = chats.filter(c => c.id !== id);
  closeMenu();
}
</script>

<aside class="w-64 bg-white border-r border-gray-100 flex flex-col p-4 shadow-sm">
  <div class="flex items-center justify-between mb-3">
    <h2 class="text-xs font-bold px-2 py-1 uppercase tracking-wider text-gray-500">Chat History</h2>
    <button class="p-1 rounded-lg hover:bg-blue-50 transition flex items-center justify-center" title="New Chat" on:click={addChat}>
      <Icon icon="material-symbols:add-circle-outline-rounded" width="22" height="22" class="text-blue-600" />
    </button>
  </div>
  {#if chats.length === 0}
    <div class="flex-1 text-gray-400 flex items-center justify-center">No chats yet</div>
  {:else}
    <ul class="flex-1 flex flex-col gap-1">
      {#each chats as chat}
        <li class="group flex items-center justify-between px-2 py-1 rounded hover:bg-blue-50 relative">
          {#if renamingId === chat.id}
            <input
              class="flex-1 rounded bg-gray-100 px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 shadow-sm"
              bind:value={renameTitle}
              on:blur={() => confirmRename(chat.id)}
              on:keydown={(e) => (e.key === 'Enter' && confirmRename(chat.id))}
              autofocus
            />
          {:else}
            <span class="truncate text-sm">{chat.title}</span>
            <button class="ml-2 opacity-0 group-hover:opacity-100 transition p-1 rounded hover:bg-gray-200" on:click={() => openMenu(chat.id)}>
              <Icon icon="mdi:dots-horizontal" width="20" height="20" />
            </button>
            {#if menuOpenId === chat.id}
              <div class="absolute right-8 top-1 z-10 bg-white rounded shadow-xl w-32 py-1">
                <button class="flex items-center gap-2 w-full text-left px-3 py-2 text-sm hover:bg-gray-100" on:click={() => startRename(chat.id, chat.title)}>
                  <Icon icon="mdi:pencil" width="18" height="18" class="text-gray-500" />
                  Rename
                </button>
                <button class="flex items-center gap-2 w-full text-left px-3 py-2 text-sm hover:bg-gray-100 text-red-600" on:click={() => deleteChat(chat.id)}>
                  <Icon icon="mdi:trash-can-outline" width="18" height="18" class="text-red-500" />
                  Delete
                </button>
              </div>
              <div class="fixed inset-0 z-0" on:click={closeMenu} />
            {/if}
          {/if}
        </li>
      {/each}
    </ul>
  {/if}
</aside>
