import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronRight, ChevronLeft, HelpCircle, Play } from "lucide-react";
import Button from "../components/Button";

interface Step {
  title: string;
  route: string;
  tip: string;
  actionLabel: string;
}

const STEPS: Step[] = [
  {
    title: "1. Upload Filing",
    route: "/",
    tip: "Start by checking out the recent filings upload status on the dashboard. Pinned examples are ready to explore.",
    actionLabel: "Go to Dashboard",
  },
  {
    title: "2. Analyze Company",
    route: "/financial",
    tip: "Examine extracted metrics (Revenue, Gross Margin, Net Income) and check the interactive sparkline trend graphs.",
    actionLabel: "Analyze Financials",
  },
  {
    title: "3. Explore Risks",
    route: "/risks",
    tip: "Inspect identified risks categorized by severity. Click any row to slide out the detailed evidence citation context.",
    actionLabel: "Explore Risks",
  },
  {
    title: "4. Inspect Management Tone",
    route: "/management",
    tip: "Audit positive/negative management sentiments and confidence/hedging lines calculated across sections.",
    actionLabel: "Inspect Tone",
  },
  {
    title: "5. Compare Competitors",
    route: "/benchmark",
    tip: "Compare performance using multi-dimensional radar charts. Try entering a benchmarking cohort run ID.",
    actionLabel: "Benchmark Cohort",
  },
  {
    title: "6. Generate Investment Memo",
    route: "/memos",
    tip: "Generate structured memos utilizing LLM evidence integration. Review citations mapping generated facts directly back to PDF sections.",
    actionLabel: "Generate Memo",
  },
  {
    title: "7. Ask Analyst Agent",
    route: "/agent",
    tip: "Chat with the agent. Type a question about risks or financials, and watch it show citations of evidence.",
    actionLabel: "Start Analyst Chat",
  },
];

/**
 * Presentation guided demo walkthrough assistant widget to help reviewers.
 */
export default function DemoGuide() {
  const [active, setActive] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const navigate = useNavigate();

  const handleNext = () => {
    const nextIdx = Math.min(STEPS.length - 1, currentStep + 1);
    setCurrentStep(nextIdx);
    navigate(STEPS[nextIdx].route);
  };

  const handlePrev = () => {
    const prevIdx = Math.max(0, currentStep - 1);
    setCurrentStep(prevIdx);
    navigate(STEPS[prevIdx].route);
  };

  const startDemo = () => {
    setActive(true);
    setCurrentStep(0);
    navigate(STEPS[0].route);
  };

  if (!active) {
    return (
      <Button
        variant="outline"
        size="sm"
        onClick={startDemo}
        className="flex items-center gap-1.5 border-brand-300 text-brand-700 bg-brand-50/50 hover:bg-brand-50"
        aria-label="Start guided demo tour"
      >
        <Play className="w-3.5 h-3.5 text-brand-600 fill-brand-600" />
        Interactive Guide
      </Button>
    );
  }

  const step = STEPS[currentStep];

  return (
    <div
      className="glass-panel border-brand-300 shadow-xl bg-gradient-to-r from-brand-50/90 to-white/90 p-4 max-w-2xl flex flex-col md:flex-row items-center justify-between gap-4 animate-slide-up"
      role="region"
      aria-label="Guided Demo Assistant"
    >
      <div className="flex items-start gap-3 flex-1">
        <HelpCircle className="w-5 h-5 text-brand-600 shrink-0 mt-0.5" aria-hidden="true" />
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wider text-brand-800">
            Guided Tour: Step {currentStep + 1} of {STEPS.length}
          </h4>
          <span className="text-sm font-bold text-surface-900 block mt-0.5">{step.title}</span>
          <p className="text-xs text-surface-600 mt-1 leading-relaxed">{step.tip}</p>
        </div>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <Button
          variant="outline"
          size="sm"
          onClick={handlePrev}
          disabled={currentStep === 0}
          aria-label="Previous step"
        >
          <ChevronLeft className="w-4 h-4" />
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={handleNext}
          disabled={currentStep === STEPS.length - 1}
          aria-label="Next step"
        >
          <ChevronRight className="w-4 h-4" />
        </Button>
        <Button
          variant="primary"
          size="sm"
          onClick={() => setActive(false)}
          className="ml-1"
          aria-label="Exit guide"
        >
          Exit Guide
        </Button>
      </div>
    </div>
  );
}
