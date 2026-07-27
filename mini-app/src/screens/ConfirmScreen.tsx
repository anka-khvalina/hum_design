import { ru } from "../i18n/ru";
import type { BirthFormData } from "../types";

interface ConfirmScreenProps {
  data: BirthFormData;
  onEdit: () => void;
  onBuild: () => void;
  isSubmitting: boolean;
}

export function ConfirmScreen({ data, onEdit, onBuild, isSubmitting }: ConfirmScreenProps) {
  const rows = [
    [ru.confirm.name, data.name],
    [ru.confirm.date, formatDate(data.birthDate)],
    [ru.confirm.time, data.birthTime],
    [ru.confirm.place, data.location?.label ?? ""],
    [ru.confirm.timezone, data.location?.timezone ?? "Определим автоматически"]
  ];

  return (
    <section className="screen">
      <p className="eyebrow">{ru.brand}</p>
      <h1>{ru.confirm.title}</h1>
      <p className="muted">{ru.confirm.subtitle}</p>

      <div className="panel confirm-card">
        {rows.map(([label, value]) => (
          <div className="confirm-row" key={label}>
            <span>{label}</span>
            <strong>{value}</strong>
          </div>
        ))}
      </div>

      <div className="bottom-cta button-stack">
        <button className="button button--secondary" type="button" onClick={onEdit}>
          {ru.confirm.edit}
        </button>
        <button
          className="button button--primary"
          type="button"
          disabled={isSubmitting}
          onClick={onBuild}
        >
          {isSubmitting ? "Строим..." : ru.confirm.build}
        </button>
      </div>
    </section>
  );
}

function formatDate(value: string): string {
  if (!value) {
    return "";
  }

  return new Intl.DateTimeFormat("ru-RU", {
    day: "numeric",
    month: "long",
    year: "numeric"
  }).format(new Date(`${value}T00:00:00`));
}
