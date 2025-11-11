import {
  ActionBarPrimitive,
  BranchPickerPrimitive,
  ComposerPrimitive,
  MessagePrimitive,
  ThreadPrimitive,
} from '@assistant-ui/react';
import {
  ArrowDownIcon,
  ArrowUpIcon,
  CheckIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  CopyIcon,
  RefreshCwIcon,
} from 'lucide-react';
import type { FC } from 'react';
import { NewChatButton } from './NewChatButton';
import { MarkdownText } from '@/components/assistant-ui/markdown-text';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

export const Thread: FC = () => {
  return (
    <ThreadPrimitive.Root className="relative flex h-full flex-col overflow-hidden bg-background text-foreground">
      <NewChatButton />
      <ThreadPrimitive.Viewport className="flex h-full flex-col items-center overflow-y-scroll scroll-smooth bg-inherit px-4 pt-8">
        <ThreadWelcome />

        <ThreadPrimitive.Messages
          components={{
            UserMessage: UserMessage,
            AssistantMessage: AssistantMessage,
          }}
        />

        <ThreadPrimitive.If empty={false}>
          <div className="min-h-8 flex-grow" />
        </ThreadPrimitive.If>

        <div className="sticky bottom-0 mt-3 flex w-full max-w-2xl flex-col items-center justify-end rounded-t-lg bg-inherit pb-4">
          <ThreadScrollToBottom />
          <Composer />
        </div>
      </ThreadPrimitive.Viewport>
    </ThreadPrimitive.Root>
  );
};

const ThreadScrollToBottom: FC = () => {
  return (
    <ThreadPrimitive.ScrollToBottom asChild>
      <Button
        variant="outline"
        size="icon"
        className="absolute -top-8 rounded-full disabled:invisible"
      >
        <ArrowDownIcon className="h-4 w-4" />
      </Button>
    </ThreadPrimitive.ScrollToBottom>
  );
};

const ThreadWelcome: FC = () => {
  return (
    <ThreadPrimitive.Empty>
      <div className="flex w-full max-w-2xl flex-grow flex-col">
        <div className="flex w-full flex-grow flex-col items-center justify-center">
          <h1 className="text-2xl font-bold">RoofGPT</h1>
          <p className="mt-4 text-muted-foreground">
            Ask me anything about roofing codes, warranties, and systems
          </p>
        </div>
      </div>
    </ThreadPrimitive.Empty>
  );
};

const Composer: FC = () => {
  return (
    <ComposerPrimitive.Root className="flex w-full flex-wrap items-end rounded-lg border bg-inherit px-2.5 shadow-sm transition-colors ease-in focus-within:border-ring/20">
      <ComposerPrimitive.Input
        rows={1}
        autoFocus
        placeholder="Ask about roofing..."
        className="max-h-40 flex-grow resize-none border-none bg-transparent px-2 py-4 text-sm outline-none placeholder:text-muted-foreground focus:ring-0 disabled:cursor-not-allowed"
      />
      <ComposerAction />
    </ComposerPrimitive.Root>
  );
};

const ComposerAction: FC = () => {
  return (
    <>
      <ThreadPrimitive.If running={false}>
        <ComposerPrimitive.Send asChild>
          <Button
            size="icon"
            className="my-2.5 h-8 w-8 rounded-full p-2 transition-opacity ease-in"
          >
            <ArrowUpIcon className="h-4 w-4" />
          </Button>
        </ComposerPrimitive.Send>
      </ThreadPrimitive.If>
      <ThreadPrimitive.If running>
        <ComposerPrimitive.Cancel asChild>
          <Button
            size="icon"
            variant="outline"
            className="my-2.5 h-8 w-8 rounded-full p-2 transition-opacity ease-in"
          >
            <CircleStopIcon />
          </Button>
        </ComposerPrimitive.Cancel>
      </ThreadPrimitive.If>
    </>
  );
};

const UserMessage: FC = () => {
  return (
    <MessagePrimitive.Root className="grid w-full max-w-2xl auto-rows-auto grid-cols-[minmax(72px,1fr)_auto] gap-y-2 py-4 [&:where(>*)]:col-start-2">
      <div className="col-start-2 row-start-2 max-w-xl break-words rounded-3xl bg-muted px-5 py-2.5 text-foreground">
        <MessagePrimitive.Content />
      </div>

      <BranchPicker className="col-span-full col-start-1 row-start-3 -mr-1 justify-end" />
    </MessagePrimitive.Root>
  );
};

const AssistantMessage: FC = () => {
  return (
    <MessagePrimitive.Root className="relative grid w-full max-w-2xl grid-cols-[auto_auto_1fr] grid-rows-[auto_1fr] py-4">
      <div className="col-span-2 col-start-2 row-start-1 my-1.5 max-w-xl break-words leading-7 text-foreground">
        <MessagePrimitive.Parts components={{ Text: MarkdownText }} />
      </div>

      <AssistantActionBar />

      <BranchPicker className="col-start-2 row-start-2 -ml-2 mr-2" />
    </MessagePrimitive.Root>
  );
};

const AssistantActionBar: FC = () => {
  return (
    <ActionBarPrimitive.Root
      hideWhenRunning
      autohide="not-last"
      autohideFloat="single-branch"
      className="col-start-3 row-start-2 -ml-1 flex gap-1 text-muted-foreground data-[floating]:absolute data-[floating]:rounded-md data-[floating]:border data-[floating]:bg-background data-[floating]:p-1 data-[floating]:shadow-sm"
    >
      <ActionBarPrimitive.Copy asChild>
        <Button variant="ghost" size="icon" className="h-6 w-6 p-1">
          <MessagePrimitive.If copied>
            <CheckIcon className="h-4 w-4" />
          </MessagePrimitive.If>
          <MessagePrimitive.If copied={false}>
            <CopyIcon className="h-4 w-4" />
          </MessagePrimitive.If>
        </Button>
      </ActionBarPrimitive.Copy>
      <ActionBarPrimitive.Reload asChild>
        <Button variant="ghost" size="icon" className="h-6 w-6 p-1">
          <RefreshCwIcon className="h-4 w-4" />
        </Button>
      </ActionBarPrimitive.Reload>
    </ActionBarPrimitive.Root>
  );
};

const BranchPicker: FC<BranchPickerPrimitive.Root.Props> = ({
  className,
  ...rest
}) => {
  return (
    <BranchPickerPrimitive.Root
      hideWhenSingleBranch
      className={cn(
        'inline-flex items-center text-xs text-muted-foreground',
        className,
      )}
      {...rest}
    >
      <BranchPickerPrimitive.Previous asChild>
        <Button variant="ghost" size="icon" className="h-6 w-6 p-1">
          <ChevronLeftIcon className="h-4 w-4" />
        </Button>
      </BranchPickerPrimitive.Previous>
      <span className="font-medium">
        <BranchPickerPrimitive.Number /> / <BranchPickerPrimitive.Count />
      </span>
      <BranchPickerPrimitive.Next asChild>
        <Button variant="ghost" size="icon" className="h-6 w-6 p-1">
          <ChevronRightIcon className="h-4 w-4" />
        </Button>
      </BranchPickerPrimitive.Next>
    </BranchPickerPrimitive.Root>
  );
};

const CircleStopIcon = () => {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 16 16"
      fill="currentColor"
      width="16"
      height="16"
    >
      <rect width="10" height="10" x="3" y="3" rx="2" />
    </svg>
  );
};
