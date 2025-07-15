export function getSelectedModel(): string {
    if (typeof window !== 'undefined') {
      const storedModel = localStorage.getItem('selectedModel');
      return storedModel || 'claude-3-7-sonnet-20250219';
    } else {
      // Default model
      return 'claude-3-7-sonnet-20250219';
    }
  }