import ReactECharts from "echarts-for-react";
import { memo } from "react";

interface BenchmarkBarChartProps {
  companies: string[];
  scores: number[];
  label?: string;
}

function BenchmarkBarChartInner({ companies, scores, label = "Score" }: BenchmarkBarChartProps) {
  // Sort by score descending for leaderboard effect
  const pairs = companies.map((c, i) => ({ name: c, score: scores[i] })).sort((a, b) => b.score - a.score);

  const option = {
    tooltip: { trigger: "axis" as const, formatter: "{b}: {c}" },
    grid: { top: 10, right: 20, bottom: 20, left: 100 },
    xAxis: { type: "value" as const, axisLabel: { fontSize: 11, color: "#64748b" }, splitLine: { lineStyle: { color: "#f1f5f9" } } },
    yAxis: { type: "category" as const, data: pairs.map((p) => p.name), axisLabel: { fontSize: 11, color: "#334155", fontWeight: 500 as number }, axisLine: { lineStyle: { color: "#e2e8f0" } }, inverse: true },
    series: [
      {
        name: label,
        type: "bar" as const,
        data: pairs.map((p, i) => ({
          value: p.score,
          itemStyle: {
            color: i === 0 ? "#6366f1" : i === 1 ? "#818cf8" : i === 2 ? "#a5b4fc" : "#cbd5e1",
            borderRadius: [0, 4, 4, 0],
          },
        })),
        barMaxWidth: 28,
      },
    ],
    animation: true,
  };

  return <ReactECharts option={option} style={{ height: Math.max(200, pairs.length * 45) }} opts={{ renderer: "svg" }} />;
}

const BenchmarkBarChart = memo(BenchmarkBarChartInner);
export default BenchmarkBarChart;
