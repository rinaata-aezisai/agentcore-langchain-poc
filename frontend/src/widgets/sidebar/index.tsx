"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/shared/lib/utils";

interface NavItem {
  href: string;
  label: string;
  icon: React.ReactNode;
  badge?: string;
  description?: string;
}

const AGENTCORE_SERVICES: NavItem[] = [
  {
    href: "/services/runtime",
    label: "Runtime",
    icon: <ServerIcon />,
    description: "サーバーレス実行環境",
  },
  {
    href: "/services/memory",
    label: "Memory",
    icon: <DatabaseIcon />,
    description: "短期・長期メモリ管理",
  },
  {
    href: "/services/gateway",
    label: "Gateway",
    icon: <GatewayIcon />,
    description: "MCP対応ツール変換",
  },
  {
    href: "/services/identity",
    label: "Identity",
    icon: <ShieldIcon />,
    description: "アイデンティティ管理",
  },
  {
    href: "/services/code-interpreter",
    label: "Code Interpreter",
    icon: <CodeIcon />,
    description: "コード実行サンドボックス",
  },
  {
    href: "/services/browser",
    label: "Browser",
    icon: <GlobeIcon />,
    description: "クラウドブラウザ環境",
  },
  {
    href: "/services/observability",
    label: "Observability",
    icon: <ChartIcon />,
    description: "トレース・監視",
  },
  {
    href: "/services/evaluations",
    label: "Evaluations",
    icon: <CheckIcon />,
    badge: "Preview",
    description: "品質評価システム",
  },
  {
    href: "/services/policy",
    label: "Policy",
    icon: <LockIcon />,
    badge: "Preview",
    description: "ガバナンス制御",
  },
];

const COMPARISON_LINKS: NavItem[] = [
  {
    href: "/comparison",
    label: "総合比較",
    icon: <CompareIcon />,
    description: "Strands vs LangChain",
  },
  {
    href: "/benchmark",
    label: "ベンチマーク",
    icon: <SpeedIcon />,
    description: "パフォーマンス測定",
  },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 h-screen w-64 bg-slate-800 border-r border-slate-700 overflow-y-auto">
      {/* Logo */}
      <div className="p-4 border-b border-slate-700">
        <Link href="/" className="flex items-center gap-2">
          <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-sm">AC</span>
          </div>
          <div>
            <h1 className="text-white font-semibold text-sm">AgentCore PoC</h1>
            <p className="text-slate-400 text-xs">vs LangChain</p>
          </div>
        </Link>
      </div>

      {/* Quick Chat */}
      <div className="p-4 border-b border-slate-700">
        <Link
          href="/chat"
          className={cn(
            "flex items-center gap-3 px-3 py-2 rounded-lg transition-colors",
            pathname === "/chat"
              ? "bg-blue-600 text-white"
              : "text-slate-300 hover:bg-slate-700"
          )}
        >
          <ChatIcon />
          <span className="font-medium">Chat テスト</span>
        </Link>
      </div>

      {/* AgentCore Services */}
      <div className="p-4">
        <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
          AgentCore Services
        </h2>
        <nav className="space-y-1">
          {AGENTCORE_SERVICES.map((item) => (
            <NavLink key={item.href} item={item} isActive={pathname === item.href} />
          ))}
        </nav>
      </div>

      {/* Comparison */}
      <div className="p-4 border-t border-slate-700">
        <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
          比較・分析
        </h2>
        <nav className="space-y-1">
          {COMPARISON_LINKS.map((item) => (
            <NavLink key={item.href} item={item} isActive={pathname === item.href} />
          ))}
        </nav>
      </div>

      {/* Agent Type Indicator */}
      <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-slate-700 bg-slate-800">
        <div className="text-xs text-slate-400">
          <span className="block mb-1">Current Agent:</span>
          <span className="text-white font-medium">
            {typeof window !== "undefined" && process.env.NEXT_PUBLIC_AGENT_TYPE === "langchain"
              ? "LangChain + LangGraph"
              : "Strands Agents"}
          </span>
        </div>
      </div>
    </aside>
  );
}

function NavLink({ item, isActive }: { item: NavItem; isActive: boolean }) {
  return (
    <Link
      href={item.href}
      className={cn(
        "flex items-center gap-3 px-3 py-2 rounded-lg transition-colors group",
        isActive
          ? "bg-slate-700 text-white"
          : "text-slate-400 hover:bg-slate-700/50 hover:text-slate-200"
      )}
    >
      <span className="w-5 h-5 shrink-0">{item.icon}</span>
      <span className="flex-1 text-sm">{item.label}</span>
      {item.badge && (
        <span className="px-1.5 py-0.5 text-[10px] font-medium bg-amber-500/20 text-amber-400 rounded">
          {item.badge}
        </span>
      )}
    </Link>
  );
}

// Icons
function ChatIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
    </svg>
  );
}

function ServerIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" />
    </svg>
  );
}

function DatabaseIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
    </svg>
  );
}

function GatewayIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
    </svg>
  );
}

function ShieldIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
    </svg>
  );
}

function CodeIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
    </svg>
  );
}

function GlobeIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
    </svg>
  );
}

function ChartIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  );
}

function LockIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
    </svg>
  );
}

function CompareIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
    </svg>
  );
}

function SpeedIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
    </svg>
  );
}

