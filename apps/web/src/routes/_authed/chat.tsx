import { createFileRoute } from '@tanstack/react-router';
import { ChatRuntimeProvider } from '@/components/chat/ChatRuntimeProvider';

export const Route = createFileRoute('/_authed/chat')({
  component: ChatPage,
});

function ChatPage() {
  return <ChatRuntimeProvider />;
}
