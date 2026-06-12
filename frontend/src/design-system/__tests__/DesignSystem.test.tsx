import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import Skeleton from "../components/Skeleton";
import DemoGuide from "../patterns/DemoGuide";
import { useObservability } from "@/hooks/useObservability";
import { MemoryRouter } from "react-router-dom";

// Simple test component to verify useObservability
function ObservabilityTestComponent() {
  const { trackInteraction, logs } = useObservability();
  return (
    <div>
      <button onClick={() => trackInteraction("click", "test-btn")}>
        Click Me
      </button>
      <div data-testid="log-count">{logs.length}</div>
    </div>
  );
}

describe("Design System Primitives & Patterns", () => {
  describe("Skeleton Component", () => {
    it("renders with correct variant classes", () => {
      const { container: textContainer } = render(<Skeleton variant="text" />);
      expect(textContainer.firstChild).toHaveClass("h-4");
      expect(textContainer.firstChild).toHaveClass("bg-surface-200/80");
      expect(textContainer.firstChild).toHaveClass("animate-shimmer");

      const { container: circleContainer } = render(<Skeleton variant="circular" className="w-12 h-12" />);
      expect(circleContainer.firstChild).toHaveClass("rounded-full");
      expect(circleContainer.firstChild).toHaveClass("w-12");

      const { container: cardContainer } = render(<Skeleton variant="card" />);
      expect(cardContainer.firstChild).toHaveClass("glass-panel");
      expect(cardContainer.firstChild).toHaveClass("animate-pulse");
    });
  });

  describe("DemoGuide Pattern", () => {
    it("renders guides list and displays details on click", () => {
      render(
        <MemoryRouter>
          <DemoGuide />
        </MemoryRouter>
      );
      
      // Initially active is false, so we should see the "Interactive Guide" button
      const startBtn = screen.getByRole("button", { name: /Start guided demo tour/i });
      expect(startBtn).toBeInTheDocument();
      
      // Click start to activate the guide
      fireEvent.click(startBtn);
      
      // Now the step title and details should show up
      expect(screen.getByText(/Guided Tour: Step 1 of/i)).toBeInTheDocument();
      expect(screen.getByText(/1. Upload Filing/i)).toBeInTheDocument();
      expect(screen.getByText(/Start by checking out the recent filings upload status/i)).toBeInTheDocument();
    });
  });

  describe("useObservability Hook", () => {
    it("tracks interaction events correctly", () => {
      render(<ObservabilityTestComponent />);
      
      const button = screen.getByRole("button", { name: /Click Me/i });
      const logs = screen.getByTestId("log-count");
      
      expect(logs).toHaveTextContent("0");
      
      fireEvent.click(button);
      
      // The log count should update to 1
      expect(logs).toHaveTextContent("1");
    });
  });
});
