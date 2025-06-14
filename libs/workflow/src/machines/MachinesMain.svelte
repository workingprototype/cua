<script lang="ts">
import Icon from '@iconify/svelte';
export let selectedVM: any = null;
import screenshot from '../assets/screenshot.png';

let playing = false;

function handlePlay() {
  playing = !playing;
}
</script>

<main class="flex-1 flex flex-col">
  {#if selectedVM}
    <div class="flex items-center justify-between px-6 py-3 bg-white/90 backdrop-blur supports-[backdrop-filter]:bg-white/60 shadow-sm">
      <span class="font-bold text-lg text-gray-900">{selectedVM.name}</span>
      <div class="flex gap-2">
        <!-- Play/Stop toggle -->
        <button class="bg-blue-600 text-white px-3 py-1 rounded-lg hover:bg-blue-700 transition flex items-center justify-center" title={playing ? 'Stop' : 'Play'} on:click={() => selectedVM.status = 'starting'}>
          <Icon icon={playing ? 'mdi:stop' : 'mdi:play'} width="22" height="22" />
        </button>
        {#if selectedVM.status === 'running'}
        <button class="bg-red-500 text-white px-3 py-1 rounded-lg hover:bg-red-600 transition flex items-center justify-center" title="Stop">
          <Icon icon="mdi:stop" width="22" height="22" />
        </button>
        {/if}
        <!-- Restart -->
        <button class="bg-gray-100 text-blue-600 px-3 py-1 rounded-lg hover:bg-blue-200 transition flex items-center justify-center" title="Restart">
          <Icon icon="mdi:restart" width="22" height="22" />
        </button>
        <!-- Trash -->
        <button class="bg-gray-100 text-red-500 px-3 py-1 rounded-lg hover:bg-red-100 transition flex items-center justify-center" title="Delete">
          <Icon icon="mdi:trash-can-outline" width="22" height="22" />
        </button>
      </div>
    </div>
    <div class="flex-1 flex flex-col items-center justify-center bg-gray-100">
      {#if playing && selectedVM.vnc_url}
        <iframe src={selectedVM.vnc_url} title="VNC Console" class="w-3/4 aspect-video rounded-xl border-2 border-blue-400 shadow-lg" allowfullscreen></iframe>
      {:else}
        <div class="w-3/4 aspect-video bg-gradient-to-br from-gray-300 to-gray-200 rounded-xl flex items-center justify-center text-gray-400 text-3xl shadow-inner relative overflow-hidden">
          <img src={screenshot} alt="Default Screenshot" class="object-contain w-full h-full {selectedVM.status === 'stopped' ? 'blur-md' : ''}" />
          <button
            class="absolute inset-0 flex items-center justify-center z-10 transition-all duration-150 group"
            title="Play"
            on:click={() => {
              if (selectedVM.vnc_url) {
                window.open(selectedVM.vnc_url, '_blank', 'noopener');
              } else {
                selectedVM.status = 'starting';
              }
            }}
            style="outline: none;"
          >
            <span class="rounded-full bg-black/25 p-5 flex items-center justify-center shadow-lg border border-white/10 backdrop-blur-xs transition-all duration-150 group-hover:scale-110 group-hover:shadow-gray-400/30 group-hover:shadow-lg group-active:scale-95 group-active:shadow-gray-600/50">
              <Icon icon={selectedVM.status === 'stopped' ? 'mdi:power' : 'mdi:play'} width="48" height="48" class="text-white drop-shadow" />
            </span>
          </button>
        </div>
      {/if}
      <div class="mt-6 w-3/4 bg-white rounded-xl shadow-lg p-6">
        <div class="grid grid-cols-2 gap-4 text-sm text-gray-700">
          <div><span class="font-semibold">Provider:</span> {selectedVM.provider}</div>
          <div><span class="font-semibold">OS:</span> {selectedVM.os}</div>
          <div><span class="font-semibold">Status:</span> <span class="text-yellow-600">{selectedVM.status}</span></div>
          <div><span class="font-semibold">Memory:</span> 8 GB</div>
          <div><span class="font-semibold">Size:</span> 11.7 GB</div>
        </div>
      </div>
    </div>
  {:else}
    <div class="flex-1 flex items-center justify-center text-gray-400">No VM selected</div>
  {/if}
</main>
