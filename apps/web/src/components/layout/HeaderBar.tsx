import { useAuth } from '@/auth';
import { Button } from '@/components/ui/button';
import type { User } from '@maive/api/client';
import { User2 } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

export type HeaderBarProps = {
  user: User | null;
};

export default function HeaderBar({ user }: HeaderBarProps) {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const modalRef = useRef<HTMLDivElement>(null);
  const { signOut } = useAuth();

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        modalRef.current &&
        !modalRef.current.contains(event.target as Node)
      ) {
        setIsModalOpen(false);
      }
    }

    if (isModalOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isModalOpen]);

  const handleSignOut = async () => {
    await signOut();
    setIsModalOpen(false);
  };

  return (
    <header className="flex h-16 items-center justify-end bg-neutral-50 px-6">
      <div className="relative">
        <Button
          variant="outline"
          size="icon"
          onClick={() => setIsModalOpen(!isModalOpen)}
          aria-label="User menu"
          className="rounded-full border border-primary-900 bg-neutral-50 hover:bg-neutral-100 transition-colors"
        >
          <User2 className="h-5 w-5 text-primary-900" />
        </Button>

        {isModalOpen && (
          <div
            ref={modalRef}
            className="absolute right-0 top-10 w-72 bg-white border border-gray-200 rounded-lg shadow-lg z-50"
          >
            <div className="p-4">
              <div className="flex items-center gap-3 mb-4">
                <div className="h-12 w-12 rounded-full bg-gray-300 flex items-center justify-center">
                  <User2 className="h-8 w-8 text-gray-700" />
                </div>
                <div className="flex-1">
                  <p className="text-sm text-gray-600">{user?.email}</p>
                </div>
              </div>

              <Button
                variant="outline"
                onClick={handleSignOut}
                className="w-full text-left border-primary-900 text-primary-900 bg-primary-50 hover:bg-neutral-100"
              >
                Sign out
              </Button>
            </div>
          </div>
        )}
      </div>
    </header>
  );
}
