<script lang="ts">
  import TextContentPart from './TextContentPart.svelte';
  import ImageContentPart from './ImageContentPart.svelte';
  import ComputerCallContentPart from './ComputerCallContentPart.svelte';

  export let message: { from: string; value: string | Array<{ type: string }> };

  // Preprocess message.value for computer_call isFirstInTrajectory
  let processedParts: any[] = [];
  $: if (Array.isArray(message.value)) {
    const seen = new Set();
    processedParts = message.value.map(part => {
      if (part.type === 'computer_call' && part.trajectory_id) {
        if (seen.has(part.trajectory_id)) {
          return { ...part, _isFirstInTrajectory: false };
        } else {
          seen.add(part.trajectory_id);
          return { ...part, _isFirstInTrajectory: true };
        }
      }
      return part;
    });
  } else {
    processedParts = message.value;
  }

</script>

<div class="flex items-start gap-3 py-2">
  <div class="font-bold text-xs text-gray-500 min-w-[3.5rem] text-right pr-2 pt-1">{message.from}</div>
  <div class="flex-1">
    {#if typeof message.value === 'string'}
      <TextContentPart part={{ type: 'text', text: message.value }} />
    {:else}
      {#each processedParts as part, i (part)}
        {#if part.type === 'text'}
          <TextContentPart part={part} />
        {:else if part.type === 'image_url'}
          <ImageContentPart part={part} />
        {:else if part.type === 'computer_call'}
          <ComputerCallContentPart part={part} isFirstInTrajectory={part._isFirstInTrajectory} />
        {/if}
      {/each}
    {/if}
  </div>
</div>
