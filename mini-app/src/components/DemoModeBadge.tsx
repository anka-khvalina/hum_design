import { ru } from "../i18n/ru";

interface DemoModeBadgeProps {
  mode?: string;
}

export function DemoModeBadge({ mode }: DemoModeBadgeProps) {
  if (!mode) {
    return null;
  }

  return (
    <aside className="demo-badge" aria-label={`${ru.technical.demoMode}: ${mode}`}>
      <span>{ru.technical.demoMode}</span>
      <strong>{mode}</strong>
    </aside>
  );
}
