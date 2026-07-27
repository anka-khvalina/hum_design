interface ProgressStepsProps {
  steps: readonly string[];
  activeIndex: number;
}

export function ProgressSteps({ steps, activeIndex }: ProgressStepsProps) {
  const progress = Math.min(100, Math.round(((activeIndex + 1) / steps.length) * 100));

  return (
    <div className="progress-card" aria-live="polite">
      <div className="progress-orbit" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
      <div className="progress-track">
        <div className="progress-track__fill" style={{ width: `${progress}%` }} />
      </div>
      <ol className="progress-steps">
        {steps.map((step, index) => (
          <li
            className={
              index < activeIndex
                ? "progress-step progress-step--done"
                : index === activeIndex
                  ? "progress-step progress-step--active"
                  : "progress-step"
            }
            key={step}
          >
            <span className="progress-step__dot" />
            {step}
          </li>
        ))}
      </ol>
    </div>
  );
}
