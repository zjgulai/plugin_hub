type ReviewState = "clear" | "review";

type QualityBadgeProps = {
  confidence: number;
  flags: string[];
};

export function QualityBadge({ confidence, flags }: QualityBadgeProps) {
  const state = flags.length > 0 ? "review" : "clear";
  const percent = Math.round(confidence * 100);
  const label = reviewLabels[state];

  return (
    <div className={`qualityBadge qualityBadge--${state}`} aria-label={`证据状态${label}`}>
      <span className="qualityBadge__dot" />
      <span className="qualityBadge__label">{label}</span>
      <span className="qualityBadge__meta">覆盖 {percent}%</span>
      <span className="qualityBadge__flags">{flags.length} 个质量标记</span>
    </div>
  );
}

const reviewLabels: Record<ReviewState, string> = {
  clear: "已校验",
  review: "需复核"
};
