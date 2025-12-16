'use client';

import { useState } from 'react';
import { signIn, signUp, confirmSignUp, resetPassword, confirmResetPassword } from 'aws-amplify/auth';
import { useRouter } from 'next/navigation';
import { cn } from '@/shared/lib/utils';

type AuthMode = 'signin' | 'signup' | 'confirm' | 'forgot' | 'reset';

export default function SignInPage() {
  const router = useRouter();
  const [mode, setMode] = useState<AuthMode>('signin');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  
  // フォーム状態
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [confirmationCode, setConfirmationCode] = useState('');

  async function handleSignIn(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const result = await signIn({ username: email, password });
      
      if (result.isSignedIn) {
        router.push('/chat');
      } else if (result.nextStep.signInStep === 'CONFIRM_SIGN_UP') {
        setMode('confirm');
      }
    } catch (err: unknown) {
      const authError = err as { message?: string };
      setError(authError.message || 'サインインに失敗しました');
    } finally {
      setLoading(false);
    }
  }

  async function handleSignUp(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    if (password !== confirmPassword) {
      setError('パスワードが一致しません');
      setLoading(false);
      return;
    }

    try {
      const result = await signUp({
        username: email,
        password,
        options: {
          userAttributes: { email },
        },
      });

      if (result.nextStep.signUpStep === 'CONFIRM_SIGN_UP') {
        setMode('confirm');
        setSuccessMessage('確認コードをメールで送信しました');
      }
    } catch (err: unknown) {
      const authError = err as { message?: string };
      setError(authError.message || 'サインアップに失敗しました');
    } finally {
      setLoading(false);
    }
  }

  async function handleConfirmSignUp(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      await confirmSignUp({ username: email, confirmationCode });
      
      // 確認後に自動サインイン
      await signIn({ username: email, password });
      router.push('/chat');
    } catch (err: unknown) {
      const authError = err as { message?: string };
      setError(authError.message || '確認に失敗しました');
    } finally {
      setLoading(false);
    }
  }

  async function handleForgotPassword(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      await resetPassword({ username: email });
      setMode('reset');
      setSuccessMessage('パスワードリセットコードをメールで送信しました');
    } catch (err: unknown) {
      const authError = err as { message?: string };
      setError(authError.message || 'パスワードリセットに失敗しました');
    } finally {
      setLoading(false);
    }
  }

  async function handleResetPassword(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    if (password !== confirmPassword) {
      setError('パスワードが一致しません');
      setLoading(false);
      return;
    }

    try {
      await confirmResetPassword({
        username: email,
        confirmationCode,
        newPassword: password,
      });
      
      setSuccessMessage('パスワードをリセットしました。サインインしてください。');
      setMode('signin');
      setPassword('');
      setConfirmPassword('');
      setConfirmationCode('');
    } catch (err: unknown) {
      const authError = err as { message?: string };
      setError(authError.message || 'パスワードリセットに失敗しました');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-4">
      <div className="w-full max-w-md">
        {/* ロゴ */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">
            AI Agent PoC
          </h1>
          <p className="text-slate-400">
            AgentCore vs LangChain 比較検証
          </p>
        </div>

        {/* カード */}
        <div className="bg-slate-800/50 border border-slate-700 rounded-2xl p-8 backdrop-blur-sm">
          {/* タブ */}
          {(mode === 'signin' || mode === 'signup') && (
            <div className="flex gap-2 mb-6">
              <button
                onClick={() => { setMode('signin'); setError(null); }}
                className={cn(
                  'flex-1 py-2 rounded-lg text-sm font-medium transition-colors',
                  mode === 'signin'
                    ? 'bg-blue-600 text-white'
                    : 'bg-slate-700 text-slate-400 hover:bg-slate-600'
                )}
              >
                サインイン
              </button>
              <button
                onClick={() => { setMode('signup'); setError(null); }}
                className={cn(
                  'flex-1 py-2 rounded-lg text-sm font-medium transition-colors',
                  mode === 'signup'
                    ? 'bg-blue-600 text-white'
                    : 'bg-slate-700 text-slate-400 hover:bg-slate-600'
                )}
              >
                アカウント作成
              </button>
            </div>
          )}

          {/* エラー/成功メッセージ */}
          {error && (
            <div className="mb-4 p-3 bg-red-900/30 border border-red-700 rounded-lg text-red-400 text-sm">
              {error}
            </div>
          )}
          {successMessage && (
            <div className="mb-4 p-3 bg-green-900/30 border border-green-700 rounded-lg text-green-400 text-sm">
              {successMessage}
            </div>
          )}

          {/* サインインフォーム */}
          {mode === 'signin' && (
            <form onSubmit={handleSignIn} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">
                  メールアドレス
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className={cn(
                    'w-full px-4 py-2.5 rounded-lg',
                    'bg-slate-900 border border-slate-600 text-white',
                    'focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500',
                    'placeholder:text-slate-500'
                  )}
                  placeholder="you@example.com"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">
                  パスワード
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className={cn(
                    'w-full px-4 py-2.5 rounded-lg',
                    'bg-slate-900 border border-slate-600 text-white',
                    'focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500'
                  )}
                />
              </div>
              <button
                type="submit"
                disabled={loading}
                className={cn(
                  'w-full py-3 rounded-lg font-medium',
                  'bg-blue-600 hover:bg-blue-700 text-white',
                  'transition-colors',
                  loading && 'opacity-50 cursor-not-allowed'
                )}
              >
                {loading ? 'サインイン中...' : 'サインイン'}
              </button>
              <button
                type="button"
                onClick={() => setMode('forgot')}
                className="w-full text-sm text-slate-400 hover:text-slate-300"
              >
                パスワードをお忘れですか？
              </button>
            </form>
          )}

          {/* サインアップフォーム */}
          {mode === 'signup' && (
            <form onSubmit={handleSignUp} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">
                  メールアドレス
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className={cn(
                    'w-full px-4 py-2.5 rounded-lg',
                    'bg-slate-900 border border-slate-600 text-white',
                    'focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500',
                    'placeholder:text-slate-500'
                  )}
                  placeholder="you@example.com"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">
                  パスワード
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  minLength={8}
                  className={cn(
                    'w-full px-4 py-2.5 rounded-lg',
                    'bg-slate-900 border border-slate-600 text-white',
                    'focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500'
                  )}
                />
                <p className="text-xs text-slate-500 mt-1">
                  8文字以上、大文字・小文字・数字を含む
                </p>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">
                  パスワード確認
                </label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                  className={cn(
                    'w-full px-4 py-2.5 rounded-lg',
                    'bg-slate-900 border border-slate-600 text-white',
                    'focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500'
                  )}
                />
              </div>
              <button
                type="submit"
                disabled={loading}
                className={cn(
                  'w-full py-3 rounded-lg font-medium',
                  'bg-blue-600 hover:bg-blue-700 text-white',
                  'transition-colors',
                  loading && 'opacity-50 cursor-not-allowed'
                )}
              >
                {loading ? 'アカウント作成中...' : 'アカウント作成'}
              </button>
            </form>
          )}

          {/* 確認コードフォーム */}
          {mode === 'confirm' && (
            <form onSubmit={handleConfirmSignUp} className="space-y-4">
              <div className="text-center mb-4">
                <h2 className="text-lg font-semibold text-white">メール確認</h2>
                <p className="text-sm text-slate-400">
                  {email} に送信された確認コードを入力してください
                </p>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">
                  確認コード
                </label>
                <input
                  type="text"
                  value={confirmationCode}
                  onChange={(e) => setConfirmationCode(e.target.value)}
                  required
                  className={cn(
                    'w-full px-4 py-2.5 rounded-lg text-center text-2xl tracking-widest',
                    'bg-slate-900 border border-slate-600 text-white',
                    'focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500'
                  )}
                  placeholder="123456"
                  maxLength={6}
                />
              </div>
              <button
                type="submit"
                disabled={loading}
                className={cn(
                  'w-full py-3 rounded-lg font-medium',
                  'bg-blue-600 hover:bg-blue-700 text-white',
                  'transition-colors',
                  loading && 'opacity-50 cursor-not-allowed'
                )}
              >
                {loading ? '確認中...' : '確認'}
              </button>
              <button
                type="button"
                onClick={() => setMode('signup')}
                className="w-full text-sm text-slate-400 hover:text-slate-300"
              >
                戻る
              </button>
            </form>
          )}

          {/* パスワードリセット（メール入力） */}
          {mode === 'forgot' && (
            <form onSubmit={handleForgotPassword} className="space-y-4">
              <div className="text-center mb-4">
                <h2 className="text-lg font-semibold text-white">パスワードリセット</h2>
                <p className="text-sm text-slate-400">
                  登録したメールアドレスを入力してください
                </p>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">
                  メールアドレス
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className={cn(
                    'w-full px-4 py-2.5 rounded-lg',
                    'bg-slate-900 border border-slate-600 text-white',
                    'focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500'
                  )}
                />
              </div>
              <button
                type="submit"
                disabled={loading}
                className={cn(
                  'w-full py-3 rounded-lg font-medium',
                  'bg-blue-600 hover:bg-blue-700 text-white',
                  'transition-colors',
                  loading && 'opacity-50 cursor-not-allowed'
                )}
              >
                {loading ? '送信中...' : 'リセットコード送信'}
              </button>
              <button
                type="button"
                onClick={() => setMode('signin')}
                className="w-full text-sm text-slate-400 hover:text-slate-300"
              >
                サインインに戻る
              </button>
            </form>
          )}

          {/* パスワードリセット（新パスワード入力） */}
          {mode === 'reset' && (
            <form onSubmit={handleResetPassword} className="space-y-4">
              <div className="text-center mb-4">
                <h2 className="text-lg font-semibold text-white">新しいパスワード設定</h2>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">
                  リセットコード
                </label>
                <input
                  type="text"
                  value={confirmationCode}
                  onChange={(e) => setConfirmationCode(e.target.value)}
                  required
                  className={cn(
                    'w-full px-4 py-2.5 rounded-lg',
                    'bg-slate-900 border border-slate-600 text-white',
                    'focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500'
                  )}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">
                  新しいパスワード
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  minLength={8}
                  className={cn(
                    'w-full px-4 py-2.5 rounded-lg',
                    'bg-slate-900 border border-slate-600 text-white',
                    'focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500'
                  )}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">
                  パスワード確認
                </label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                  className={cn(
                    'w-full px-4 py-2.5 rounded-lg',
                    'bg-slate-900 border border-slate-600 text-white',
                    'focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500'
                  )}
                />
              </div>
              <button
                type="submit"
                disabled={loading}
                className={cn(
                  'w-full py-3 rounded-lg font-medium',
                  'bg-blue-600 hover:bg-blue-700 text-white',
                  'transition-colors',
                  loading && 'opacity-50 cursor-not-allowed'
                )}
              >
                {loading ? 'リセット中...' : 'パスワードをリセット'}
              </button>
            </form>
          )}
        </div>

        {/* フッター */}
        <p className="text-center text-sm text-slate-500 mt-6">
          AgentCore vs LangChain PoC © 2024
        </p>
      </div>
    </div>
  );
}

