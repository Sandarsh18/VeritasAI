import { useMemo } from "react";

import SkeletonCard from "./SkeletonCard";

function SkeletonLoader({ loading = true, children, fallback, className = "" }) {
  const rootClassName = useMemo(() => ["skeleton-loader", className].filter(Boolean).join(" "), [className]);

  if (!loading) {
    return children;
  }

  return <div className={rootClassName}>{fallback || <SkeletonCard />}</div>;
}

export default SkeletonLoader;