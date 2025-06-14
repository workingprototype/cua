<script lang="ts">
  export let part: { type: 'image_url'; image_url: string };
</script>

<div class="my-2">
  <img src={part.image_url} alt="Chat image" class="max-w-full rounded-md shadow-md" />
</div>
