import { useState } from "react";
import { ru } from "../i18n/ru";

interface BodygraphImageProps {
  imageUrl: string;
}

export function BodygraphImage({ imageUrl }: BodygraphImageProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <>
      <button
        className="bodygraph-frame"
        type="button"
        onClick={() => setIsExpanded(true)}
        aria-label={ru.result.enlarge}
      >
        <span className="bodygraph-aura" aria-hidden="true" />
        <img src={imageUrl} alt={ru.result.imageAlt} />
      </button>

      {isExpanded ? (
        <div className="image-lightbox" role="dialog" aria-modal="true">
          <button
            className="image-lightbox__close"
            type="button"
            onClick={() => setIsExpanded(false)}
            aria-label="Закрыть"
          >
            ×
          </button>
          <img src={imageUrl} alt={ru.result.imageAlt} />
        </div>
      ) : null}
    </>
  );
}
