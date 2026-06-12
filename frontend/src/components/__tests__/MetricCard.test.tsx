import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import MetricCard from "../MetricCard";

describe("MetricCard Component", () => {
  it("renders metric label and value correctly", () => {
    render(<MetricCard label="Total Revenue" value="$1,234M" />);
    expect(screen.getByText("Total Revenue")).toBeInTheDocument();
    expect(screen.getByText("$1,234M")).toBeInTheDocument();
  });

  it("renders trend details when trendValue is provided", () => {
    render(
      <MetricCard
        label="Gross Profit"
        value="$500M"
        change={15.4}
        changeLabel="YoY"
      />,
    );
    expect(screen.getByText("+15.4%")).toBeInTheDocument();
    expect(screen.getByText("YoY")).toBeInTheDocument();
  });
});
