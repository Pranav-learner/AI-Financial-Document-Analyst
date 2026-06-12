import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import RiskBadge from "../RiskBadge";
import ConfidenceBadge from "../ConfidenceBadge";

describe("Badges Components", () => {
  describe("RiskBadge", () => {
    it("renders risk severity correctly", () => {
      render(<RiskBadge severity="HIGH" />);
      const badge = screen.getByRole("status");
      expect(badge).toHaveTextContent("HIGH");
      expect(badge).toHaveClass("badge-danger");
    });

    it("uses default styling for unknown severity", () => {
      render(<RiskBadge severity="UNKNOWN_VALUE" />);
      const badge = screen.getByRole("status");
      expect(badge).toHaveTextContent("UNKNOWN_VALUE");
      expect(badge).toHaveClass("badge-neutral");
    });
  });

  describe("ConfidenceBadge", () => {
    it("renders percentage and correct color for high score", () => {
      render(<ConfidenceBadge score={0.85} />);
      const badge = screen.getByRole("status");
      expect(badge).toHaveTextContent("85%");
      expect(badge).toHaveClass("badge-success");
    });

    it("renders warning color for medium score", () => {
      render(<ConfidenceBadge score={0.6} />);
      const badge = screen.getByRole("status");
      expect(badge).toHaveTextContent("60%");
      expect(badge).toHaveClass("badge-warning");
    });
  });
});
