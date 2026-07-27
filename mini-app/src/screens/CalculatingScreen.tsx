import { useEffect, useState } from "react";
import { ProgressSteps } from "../components/ProgressSteps";
import { ru } from "../i18n/ru";

export function CalculatingScreen() {
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    const interval = window.setInterval(() => {
      setActiveIndex((current) => Math.min(current + 1, ru.calculating.statuses.length - 1));
    }, 900);

    return () => window.clearInterval(interval);
  }, []);

  return (
    <section className="screen calculating-screen">
      <p className="eyebrow">{ru.brand}</p>
      <h1>{ru.calculating.title}</h1>
      <p className="muted">{ru.calculating.subtitle}</p>
      <ProgressSteps steps={ru.calculating.statuses} activeIndex={activeIndex} />
    </section>
  );
}
