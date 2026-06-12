import ReactECharts from "echarts-for-react";
import { memo } from "react";

interface BenchmarkRadarChartProps {
  indicators: string[];
  series: { name: string; values: number[]; color?: string }[];
}

const COLORS = ["#6366f1", "#22c55e", "#f59e0b", "#ef4444", "#3b82f6"];

function BenchmarkRadarChartInner({ indicators, series }: BenchmarkRadarChartProps) {
  const option = {
    tooltip: {},
    legend: { bottom: 0, textStyle: { fontSize: 11, color: "#64748b" } },
    radar: {
      indicator: indicators.map((name) => ({ name, max: 100 })),
      shape: "polygon" as const,
      splitArea: { areaStyle: { color: ["#fafbfc", "#f1f5f9"] } },
      axisLine: { lineStyle: { color: "#e2e8f0" } },
      splitLine: { lineStyle: { color: "#e2e8f0" } },
      axisName: { fontSize: 11, color: "#64748b" },
    },
    series: [
      {
        type: "radar" as const,
        data: series.map((s, i) => ({
          name: s.name,
          value: s.values,
          lineStyle: { color: s.color ?? COLORS[i % COLORS.length], width: 2 },
          itemStyle: { color: s.color ?? COLORS[i % COLORS.length] },
          areaStyle: { color: `${s.color ?? COLORS[i % COLORS.length]}18` },
        })),
      },
    ],
    animation: true,
  };

  return <ReactECharts option={option} style={{ height: 350 }} opts={{ renderer: "svg" }} />;
}

const BenchmarkRadarChart = memo(BenchmarkRadarChartInner);
export default BenchmarkRadarChart;
