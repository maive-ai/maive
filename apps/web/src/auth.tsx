import {
  Configuration as AuthConfiguration,
  AuthenticationApi,
} from '@maive/api/client';
import * as React from 'react';
import { useCallback, useContext, useEffect } from 'react';
import type { User } from '@maive/api/client';
import { signOut as apiSignOut, getCurrentUser } from './clients/auth';
import { COGNITO_SIGN_IN_URL, env } from './env';

export interface AuthContext {
  isAuthenticated: boolean;
  isLoading: boolean;
  signIn: () => void;
  signOut: () => Promise<void>;
  user: User | null;
}

const AuthContext = React.createContext<AuthContext | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = React.useState<User | null>(null);
  const [isLoading, setIsLoading] = React.useState(true);

  useEffect(() => {
    getCurrentUser()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setIsLoading(false));
  }, []);

  const signIn = useCallback(() => {
    window.location.href = COGNITO_SIGN_IN_URL;
  }, []);

  const signOut = useCallback(async () => {
    await apiSignOut();
    setUser(null);
    window.location.href = '/';
  }, []);

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated: user ? true : false,
        isLoading,
        user,
        signIn,
        signOut,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within an AuthProvider');
  return context;
}
