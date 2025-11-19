import { PencilIcon } from 'lucide-react';
import { STORAGE_KEY } from './chatHistoryAdapter';
import { Button } from '@/components/ui/button';

export function NewChatButton() {
  const handleNewChat = () => {
    // Clear localStorage
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch (error) {
      console.warn('[New Chat] Failed to clear localStorage:', error);
    }

    // Reload page to trigger history adapter to load empty messages
    window.location.reload();
  };

  return (
    <Button
      variant="default"
      size="sm"
      onClick={handleNewChat}
      aria-label="New Chat"
      className="absolute top-4 left-4 z-10"
    >
      <PencilIcon className="h-4 w-4" />
      <span>New Chat</span>
    </Button>
  );
}
