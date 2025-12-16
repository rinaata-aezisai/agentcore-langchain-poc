"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, useEffect } from "react";
import { configureAmplify } from "@/lib/amplify-config";

// Amplify設定の初期化
let amplifyConfigured = false;

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 1000 * 60 * 5, // 5分
        retry: 1,
      },
    },
  }));

  useEffect(() => {
    if (!amplifyConfigured) {
      configureAmplify();
      amplifyConfigured = true;
    }
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
}


