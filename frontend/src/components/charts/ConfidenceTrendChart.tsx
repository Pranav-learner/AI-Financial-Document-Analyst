import ReactECharts from "echarts-for-react";
import { memo } from "react";

interface ConfidenceTrendChartProps {
  labels: string[];
  confidence: number[];
  hedging: number[];
}

function ConfidenceTrendChartInner({ labels, confidence, hedging }: ConfidenceTrendChartProps) {
  const option = {
    tooltip: { trigger: "axis" as const },
    legend: { bottom: 0, textStyle: { fontSize: 11, color: "#64748b" } },
    grid: { top: 20, right: 20, bottom: 40, left: 50 },
    xAxis: { type: "category" as const, data: labels, axisLabel: { fontSize: 11, color: "#64748b" }, axisLine: { lineStyle: { color: "#e2e8f0" } } },
    yAxis: { type: "value" as const, min: 0, max: 1, axisLabel: { fontSize: 11, color: "#64748b", formatter: (v: number) => `${(v * 100).toFixed(0)}%` }, splitLine: { lineStyle: { color: "#f1f5f9" } } },
    series: [
      {
        name: "Confidence",
        type: "line" as const,
        data: confidence,
        smooth: true,
        symbol: "circle",
        symbolSize: 6,
        lineStyle: { width: 2.5, color: "#22c55e" },
        itemStyle: { color: "#22c55e" },
        areaStyle: { color: "rgba(34,197,94,0.08)" },
      },
      {
        name: "Hedging",
        type: "line" as const,
        data: hedging,
        smooth: true,
        symbol: "diamond",
        symbolSize: 6,
        lineStyle: { width: 2.5, color: "#f59e0b" },
        itemStyle: { color: "#f59e0b" },
        areaStyle: { color: "rgba(245,158,11,0.08)" },
      },
    ],
    animation: true,
  };

  return <ReactECharts option={option} style={{ height: 300 }} opts={{ renderer: "svg" }} />;
}

const ConfidenceTrendChart = memo(ConfidenceTrendChartInner);
export default ConfidenceTrendChart;
