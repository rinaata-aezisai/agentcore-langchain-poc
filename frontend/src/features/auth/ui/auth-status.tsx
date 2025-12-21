'use client';

import { useState, useEffect } from 'react';
import { getCurrentUser, signOut } from 'aws-amplify/auth';
import { cn } from '@/shared/lib/utils';

interface AuthUser {
  userId: string;
  username: string;
}

export function AuthStatus() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkUser();
  }, []);

  async function checkUser() {
    try {
      const currentUser = await getCurrentUser();
      setUser({
        userId: currentUser.userId,
        username: currentUser.username,
      });
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }

  async function handleSignOut() {
    try {
      await signOut();
      setUser(null);
      window.location.href = '/auth/signin';
    } catch (error) {
      console.error('Sign out error:', error);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center gap-2 px-3 py-2">
        <div className="w-4 h-4 border-2 border-slate-400 border-t-transparent rounded-full animate-spin" />
        <span className="text-sm text-slate-400">Loading...</span>
      </div>
    );
  }

  if (!user) {
    return (
      <a
        href="/auth/signin"
        className={cn(
          'flex items-center gap-2 px-4 py-2 rounded-lg',
          'bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium',
          'transition-colors'
        )}
      >
        サインイン
      </a>
    );
  }

  return (
    <div className="flex items-center gap-3">
      <div className="flex items-center gap-2">
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
          <span className="text-white text-sm font-medium">
            {user.username.charAt(0).toUpperCase()}
          </span>
        </div>
        <span className="text-sm text-slate-300">{user.username}</span>
      </div>
      <button
        onClick={handleSignOut}
        className={cn(
          'px-3 py-1.5 rounded-lg text-sm',
          'bg-slate-700 hover:bg-slate-600 text-slate-300',
          'transition-colors'
        )}
      >
        サインアウト
      </button>
    </div>
  );
}


