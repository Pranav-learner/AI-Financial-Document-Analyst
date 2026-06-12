import ReactECharts from "echarts-for-react";
import { memo } from "react";

interface MarginTrendChartProps {
  labels: string[];
  series: { name: string; data: number[]; color?: string }[];
}

function MarginTrendChartInner({ labels, series }: MarginTrendChartProps) {
  const colors = ["#6366f1", "#22c55e", "#f59e0b", "#ef4444", "#3b82f6"];

  const option = {
    tooltip: { trigger: "axis" as const },
    legend: { bottom: 0, textStyle: { fontSize: 11, color: "#64748b" } },
    grid: { top: 20, right: 20, bottom: 40, left: 50 },
    xAxis: { type: "category" as const, data: labels, axisLabel: { fontSize: 11, color: "#64748b" }, axisLine: { lineStyle: { color: "#e2e8f0" } } },
    yAxis: { type: "value" as const, axisLabel: { fontSize: 11, color: "#64748b", formatter: "{value}%" }, splitLine: { lineStyle: { color: "#f1f5f9" } } },
    series: series.map((s, i) => ({
      name: s.name,
      type: "line" as const,
      data: s.data,
      smooth: true,
      symbol: "circle",
      symbolSize: 6,
      lineStyle: { width: 2.5, color: s.color ?? colors[i % colors.length] },
      itemStyle: { color: s.color ?? colors[i % colors.length] },
    })),
    animation: true,
  };

  return <ReactECharts option={option} style={{ height: 300 }} opts={{ renderer: "svg" }} />;
}

const MarginTrendChart = memo(MarginTrendChartInner);
export default MarginTrendChart;
