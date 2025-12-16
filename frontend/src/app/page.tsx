import Link from "next/link";

const SERVICES = [
  {
    id: "runtime",
    name: "Runtime",
    description: "AIエージェントとツールをホストするサーバーレス実行環境",
    status: "GA",
    langchainEquivalent: "LangServe / LangGraph Cloud",
  },
  {
    id: "memory",
    name: "Memory",
    description: "短期・長期メモリ管理による文脈認識機能",
    status: "GA",
    langchainEquivalent: "LangGraph Checkpointer",
  },
  {
    id: "gateway",
    name: "Gateway",
    description: "API、Lambda関数をMCP対応ツールに変換",
    status: "GA",
    langchainEquivalent: "LangChain Tools",
  },
  {
    id: "identity",
    name: "Identity",
    description: "エージェント用のアイデンティティ・アクセス管理",
    status: "GA",
    langchainEquivalent: "Custom Implementation",
  },
  {
    id: "code-interpreter",
    name: "Code Interpreter",
    description: "コード実行用の隔離されたサンドボックス環境（最大8時間）",
    status: "GA",
    langchainEquivalent: "Deep Agents Sandboxes",
  },
  {
    id: "browser",
    name: "Browser",
    description: "Webアプリケーション操作用のクラウドブラウザ環境",
    status: "GA",
    langchainEquivalent: "Playwright / Browser Use",
  },
  {
    id: "observability",
    name: "Observability",
    description: "統合されたトレース、デバッグ、監視機能",
    status: "GA",
    langchainEquivalent: "LangSmith / LangFuse",
  },
  {
    id: "evaluations",
    name: "Evaluations",
    description: "リアルワールド性能に基づくエージェント品質評価",
    status: "Preview",
    langchainEquivalent: "LangSmith Evaluations",
  },
  {
    id: "policy",
    name: "Policy",
    description: "ビジネスルールとガバナンスによる制御機能",
    status: "Preview",
    langchainEquivalent: "LangGraph Interrupt",
  },
];

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <div className="p-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">
            AgentCore vs LangChain 比較検証
          </h1>
          <p className="text-slate-400">
            AWS Bedrock AgentCore 9サービスとLangChainエコシステムの機能比較
          </p>
        </div>

        {/* Quick Actions */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          <Link
            href="/chat"
            className="p-6 bg-gradient-to-br from-blue-600 to-blue-700 rounded-xl hover:from-blue-500 hover:to-blue-600 transition-all group"
          >
            <h3 className="text-lg font-semibold text-white mb-1">Chat テスト</h3>
            <p className="text-blue-200 text-sm">基本的なチャット機能を検証</p>
          </Link>
          <Link
            href="/comparison"
            className="p-6 bg-gradient-to-br from-purple-600 to-purple-700 rounded-xl hover:from-purple-500 hover:to-purple-600 transition-all"
          >
            <h3 className="text-lg font-semibold text-white mb-1">総合比較</h3>
            <p className="text-purple-200 text-sm">Strands vs LangChain 比較表</p>
          </Link>
          <Link
            href="/benchmark"
            className="p-6 bg-gradient-to-br from-emerald-600 to-emerald-700 rounded-xl hover:from-emerald-500 hover:to-emerald-600 transition-all"
          >
            <h3 className="text-lg font-semibold text-white mb-1">ベンチマーク</h3>
            <p className="text-emerald-200 text-sm">パフォーマンス測定結果</p>
          </Link>
        </div>

        {/* Services Grid */}
        <h2 className="text-xl font-semibold text-white mb-4">
          AgentCore 9サービス検証
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {SERVICES.map((service) => (
            <Link
              key={service.id}
              href={`/services/${service.id}`}
              className="p-5 bg-slate-800/50 border border-slate-700 rounded-xl hover:border-slate-600 hover:bg-slate-800 transition-all group"
            >
              <div className="flex items-start justify-between mb-3">
                <h3 className="text-lg font-medium text-white group-hover:text-blue-400 transition-colors">
                  {service.name}
                </h3>
                <span
                  className={`px-2 py-0.5 text-xs font-medium rounded ${
                    service.status === "Preview"
                      ? "bg-amber-500/20 text-amber-400"
                      : "bg-green-500/20 text-green-400"
                  }`}
                >
                  {service.status}
                </span>
              </div>
              <p className="text-slate-400 text-sm mb-3">{service.description}</p>
              <div className="text-xs text-slate-500">
                <span className="text-slate-600">LangChain相当: </span>
                {service.langchainEquivalent}
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
