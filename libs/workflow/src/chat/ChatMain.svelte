<script lang="ts">
import Icon from '@iconify/svelte';
import { onMount } from 'svelte';

import { list_vms } from '../api';
let machines: { id: string; name: string }[] = [];

onMount(async () => {
  const vms = await list_vms();
  machines = vms.map(vm => ({ id: vm.name, name: vm.name }));
  selectedMachine = machines[0]?.id;
});
let agents = [
  { id: 'ui-tars', name: 'UI-Tars' },
  { id: 'anthropic', name: 'Claude' },
  { id: 'gpt', name: 'GPT-4' }
];

let selectedMachine: string | undefined = undefined;
let selectedAgent = agents[0]?.id;
let chatInput = '';
import ChatMessage from './ChatMessage.svelte';

let messages = [
  {
    from: 'user',
    value: [
      { type: 'text', text: 'Can you open the Wikipedia homepage and click the search box?' }
    ]
  },
  {
    from: 'assistant',
    value: [
      {
        type: 'computer_call',
        computer_name: 'm-linux-4l9zk7itlu',
        image_url: 'https://placehold.co/400x200/png',
        action: { type: 'navigate', url: 'https://wikipedia.org' },
        trajectory_id: 'traj_1234'
      },
      {
        type: 'computer_call',
        action: { type: 'click', x: 200, y: 70 },
        trajectory_id: 'traj_1234',
        computer_name: 'm-linux-4l9zk7itlu'
      },
      {
        type: 'computer_call',
        action: { type: 'type', text: 'Athens' },
        trajectory_id: 'traj_1234',
        computer_name: 'm-linux-4l9zk7itlu'
      }
    ]
  }
];

function sendMessage() {
  if (chatInput.trim()) {
    messages = [
      ...messages,
      {
        from: 'user',
        value: [ { type: 'text', text: chatInput } ]
      }
    ];
    chatInput = '';
  }
}
</script>

<main class="flex-1 flex flex-col">
  <div class="flex items-center justify-center py-6 bg-gray-100">
    <div class="flex gap-8 p-3 rounded-xl border border-gray-200 bg-white/80 shadow-lg">
      <div class="flex-1 flex-col items-center gap-1 min-w-[200px]">
        <span class="text-xs text-gray-500 font-semibold mb-1 flex items-center gap-1">
          <Icon icon="mdi:desktop-classic" width="16" height="16" class="text-gray-400" />
          Machine
        </span>
        <select
          class="bg-gray-100 rounded-lg px-3 py-1 focus:outline-none focus:ring-2 focus:ring-blue-400 w-full"
          bind:value={selectedMachine}
        >
          {#each machines as machine}
            <option value={machine.id}>{machine.name}</option>
          {/each}
        </select>
      </div>
      <div class="flex-1 flex-col items-center gap-1 min-w-[200px]">
        <span class="text-xs text-gray-500 font-semibold mb-1 flex items-center gap-1">
          <Icon icon="mdi:robot" width="16" height="16" class="text-gray-400" />
          Computer-use agent
        </span>
        <select
          class="bg-gray-100 rounded-lg px-3 py-1 focus:outline-none focus:ring-2 focus:ring-blue-400 w-full"
          bind:value={selectedAgent}
        >
          {#each agents as agent}
            <option value={agent.id}>{agent.name}</option>
          {/each}
        </select>
      </div>
    </div>
  </div>

  <div class="flex-1 flex flex-col justify-end bg-gray-100 overflow-y-auto px-4 py-6">
    <div class="flex flex-col gap-2 max-w-2xl w-full mx-auto">
      {#each messages as message}
        <ChatMessage {message} />
      {/each}
    </div>
    <form class="w-full max-w-2xl mx-auto mt-4 flex gap-2" on:submit|preventDefault={sendMessage}>
      <input
        class="flex-1 rounded-lg border border-gray-300 px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400 shadow"
        type="text"
        placeholder="Type a message..."
        bind:value={chatInput}
        autocomplete="off"
      />
      <button
        type="submit"
        class="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition flex items-center justify-center shadow"
        title="Send"
      >
        <Icon icon="mdi:send" width="22" height="22" />
      </button>
    </form>
  </div>
</main>
