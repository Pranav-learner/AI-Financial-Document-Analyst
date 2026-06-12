import ReactECharts from "echarts-for-react";
import { memo } from "react";

interface RevenueTrendChartProps {
  labels: string[];
  values: number[];
  unit?: string;
}

function RevenueTrendChartInner({ labels, values, unit = "USD M" }: RevenueTrendChartProps) {
  const option = {
    tooltip: { trigger: "axis" as const, formatter: "{b}: {c} " + unit },
    grid: { top: 30, right: 20, bottom: 30, left: 60 },
    xAxis: { type: "category" as const, data: labels, axisLabel: { fontSize: 11, color: "#64748b" }, axisLine: { lineStyle: { color: "#e2e8f0" } } },
    yAxis: { type: "value" as const, axisLabel: { fontSize: 11, color: "#64748b", formatter: "{value}" }, splitLine: { lineStyle: { color: "#f1f5f9" } } },
    series: [
      {
        name: "Revenue",
        type: "bar" as const,
        data: values,
        itemStyle: { color: "#6366f1", borderRadius: [4, 4, 0, 0] },
        emphasis: { itemStyle: { color: "#4f46e5" } },
        barMaxWidth: 40,
      },
    ],
    animation: true,
  };

  return <ReactECharts option={option} style={{ height: 300 }} opts={{ renderer: "svg" }} />;
}

const RevenueTrendChart = memo(RevenueTrendChartInner);
export default RevenueTrendChart;
