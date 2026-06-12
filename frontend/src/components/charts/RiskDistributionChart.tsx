import ReactECharts from "echarts-for-react";
import { memo } from "react";

interface RiskDistributionChartProps {
  data: { name: string; value: number }[];
  title?: string;
}

const COLORS = ["#ef4444", "#f59e0b", "#22c55e", "#3b82f6", "#8b5cf6", "#ec4899", "#14b8a6"];

function RiskDistributionChartInner({ data, title }: RiskDistributionChartProps) {
  const option = {
    tooltip: { trigger: "item" as const, formatter: "{b}: {c} ({d}%)" },
    legend: { bottom: 0, textStyle: { fontSize: 11, color: "#64748b" } },
    series: [
      {
        name: title ?? "Distribution",
        type: "pie" as const,
        radius: ["45%", "70%"],
        center: ["50%", "45%"],
        avoidLabelOverlap: true,
        label: { show: false },
        emphasis: { label: { show: true, fontSize: 13, fontWeight: "bold" as const } },
        data: data.map((d, i) => ({
          ...d,
          itemStyle: { color: COLORS[i % COLORS.length] },
        })),
      },
    ],
    animation: true,
  };

  return <ReactECharts option={option} style={{ height: 300 }} opts={{ renderer: "svg" }} />;
}

const RiskDistributionChart = memo(RiskDistributionChartInner);
export default RiskDistributionChart;
