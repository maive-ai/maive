import type { ThreadHistoryAdapter, ThreadMessage } from '@assistant-ui/react';

export const STORAGE_KEY = 'maive-chat-history';

interface StoredMessage {
  message: ThreadMessage;
  parentId: string | null;
}

export const chatHistoryAdapter: ThreadHistoryAdapter = {
  async load() {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (!stored) {
        return { messages: [] };
      }

      const storedMessages = JSON.parse(stored) as StoredMessage[];
      return { messages: storedMessages };
    } catch (error) {
      console.warn('[Chat History] Failed to load messages from localStorage:', error);
      return { messages: [] };
    }
  },

  async append(item: { message: ThreadMessage; parentId: string | null }): Promise<void> {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      const existingMessages = stored
        ? (JSON.parse(stored) as StoredMessage[])
        : [];

      const newMessage: StoredMessage = {
        message: item.message,
        parentId: item.parentId,
      };

      const updatedMessages = [...existingMessages, newMessage];
      localStorage.setItem(STORAGE_KEY, JSON.stringify(updatedMessages));
    } catch (error) {
      console.warn('[Chat History] Failed to save message to localStorage:', error);
    }
  },
};

