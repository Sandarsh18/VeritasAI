import { useMemo } from "react";

function SkeletonCard({ className = "", lines = 3, showActions = true }) {
  const lineWidths = useMemo(() => {
    const presets = ["long", "medium", "short", "long"];
    return Array.from({ length: lines }, (_, index) => presets[index % presets.length]);
  }, [lines]);

  const rootClassName = ["skeleton-card", "card", "skeleton-card-shell", className]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={rootClassName} aria-busy="true" aria-live="polite" aria-label="Loading content">
      <div className="skeleton-section">
        <div className="skeleton-block skeleton-title" />
        <div className="skeleton-row">
          <div className="skeleton-block skeleton-pill" />
          <div className="skeleton-block skeleton-pill" style={{ width: "88px" }} />
        </div>
      </div>

      <div className="skeleton-section skeleton-stack">
        {lineWidths.map((widthClass, index) => (
          <div key={`skeleton-line-${index}`} className={`skeleton-block skeleton-line ${widthClass}`} />
        ))}
      </div>

      <div className="skeleton-section">
        <div className="skeleton-row">
          <div className="skeleton-block skeleton-button" />
          <div className="skeleton-block skeleton-button secondary" />
        </div>
      </div>

      {showActions && (
        <div className="skeleton-section">
          <div className="skeleton-block skeleton-line short" />
          <div className="skeleton-block skeleton-line medium" />
        </div>
      )}
    </div>
  );
}

export default SkeletonCard;