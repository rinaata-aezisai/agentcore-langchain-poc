"use client";

import { useQuery } from "@tanstack/react-query";
import { agentApi } from "@/shared/api/client";

export default function ComparisonPage() {
  const { data: comparison } = useQuery({
    queryKey: ["comparison"],
    queryFn: agentApi.getComparison,
  });

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white mb-2">
          Strands Agents vs LangChain 総合比較
        </h1>
        <p className="text-slate-400">
          両実装の機能・特徴を詳細比較
        </p>
      </div>

      {/* Comparison Table */}
      <div className="bg-slate-800/50 border border-slate-700 rounded-xl overflow-hidden mb-8">
        <table className="w-full">
          <thead>
            <tr className="border-b border-slate-700">
              <th className="px-6 py-4 text-left text-sm font-semibold text-slate-300">観点</th>
              <th className="px-6 py-4 text-left text-sm font-semibold text-blue-400">Strands Agents</th>
              <th className="px-6 py-4 text-left text-sm font-semibold text-purple-400">LangChain</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-700">
            <ComparisonRow
              aspect="AWSネイティブ"
              strands="◎ 完全統合"
              langchain="○ langchain-aws"
            />
            <ComparisonRow
              aspect="エコシステム"
              strands="△ 新しい"
              langchain="◎ 成熟"
            />
            <ComparisonRow
              aspect="学習曲線"
              strands="○ シンプル"
              langchain="△ 複雑"
            />
            <ComparisonRow
              aspect="カスタマイズ"
              strands="○ 標準的"
              langchain="◎ 高度"
            />
            <ComparisonRow
              aspect="Observability"
              strands="○ CloudWatch"
              langchain="◎ LangSmith/LangFuse"
            />
            <ComparisonRow
              aspect="ワークフロー"
              strands="△ 限定的"
              langchain="◎ LangGraph"
            />
            <ComparisonRow
              aspect="マルチエージェント"
              strands="△ 基本対応"
              langchain="◎ 階層型対応"
            />
            <ComparisonRow
              aspect="ポリシー制御"
              strands="◎ Cedar統合"
              langchain="○ カスタム実装"
            />
            <ComparisonRow
              aspect="品質評価"
              strands="◎ 13評価器内蔵"
              langchain="○ LangSmith"
            />
            <ComparisonRow
              aspect="コード実行"
              strands="◎ 最大8時間"
              langchain="○ Deep Agents"
            />
          </tbody>
        </table>
      </div>

      {/* Detailed Comparison */}
      <div className="grid grid-cols-2 gap-6">
        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-blue-400 mb-4">
            Strands Agents の強み
          </h3>
          <ul className="space-y-3">
            <li className="flex items-start gap-2">
              <span className="text-green-400 mt-0.5">✓</span>
              <div>
                <span className="text-white font-medium">Policy (Preview)</span>
                <p className="text-sm text-slate-400">エンタープライズガバナンスで圧倒的優位</p>
              </div>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-green-400 mt-0.5">✓</span>
              <div>
                <span className="text-white font-medium">Evaluations (Preview)</span>
                <p className="text-sm text-slate-400">品質管理がネイティブ統合</p>
              </div>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-green-400 mt-0.5">✓</span>
              <div>
                <span className="text-white font-medium">双方向音声</span>
                <p className="text-sm text-slate-400">ボイスエージェントに最適</p>
              </div>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-green-400 mt-0.5">✓</span>
              <div>
                <span className="text-white font-medium">Code Interpreter</span>
                <p className="text-sm text-slate-400">最大8時間の連続実行</p>
              </div>
            </li>
          </ul>
        </div>

        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-purple-400 mb-4">
            LangChain の強み
          </h3>
          <ul className="space-y-3">
            <li className="flex items-start gap-2">
              <span className="text-green-400 mt-0.5">✓</span>
              <div>
                <span className="text-white font-medium">LangGraph 1.0 GA</span>
                <p className="text-sm text-slate-400">プロダクション環境での安心感</p>
              </div>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-green-400 mt-0.5">✓</span>
              <div>
                <span className="text-white font-medium">Agent Builder</span>
                <p className="text-sm text-slate-400">非開発者でもエージェント構築可能</p>
              </div>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-green-400 mt-0.5">✓</span>
              <div>
                <span className="text-white font-medium">Model Profiles</span>
                <p className="text-sm text-slate-400">信頼性大幅向上</p>
              </div>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-green-400 mt-0.5">✓</span>
              <div>
                <span className="text-white font-medium">エコシステム</span>
                <p className="text-sm text-slate-400">成熟したコミュニティとドキュメント</p>
              </div>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}

function ComparisonRow({
  aspect,
  strands,
  langchain,
}: {
  aspect: string;
  strands: string;
  langchain: string;
}) {
  return (
    <tr className="hover:bg-slate-800/30">
      <td className="px-6 py-3 text-sm text-slate-300">{aspect}</td>
      <td className="px-6 py-3 text-sm text-slate-400">{strands}</td>
      <td className="px-6 py-3 text-sm text-slate-400">{langchain}</td>
    </tr>
  );
}

