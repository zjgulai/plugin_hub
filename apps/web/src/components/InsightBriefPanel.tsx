import React from "react";

import type { InsightBrief } from "../lib/api";

type InsightBriefPanelProps = {
  briefs: InsightBrief[];
  error: string | null;
};

export function InsightBriefPanel({ briefs, error }: InsightBriefPanelProps) {
  const primaryBrief = selectPrimaryBrief(briefs);

  return (
    <section className="opsPanel insightBriefPanel" aria-label="VOC 经营诊断">
      <div className="sectionMiniHeading">
        <p className="panelKicker">VOC Strategy Brief</p>
        <h2>VOC 经营诊断</h2>
      </div>
      {error ? <p className="mutedText">{error}</p> : null}
      {!primaryBrief && !error ? <p className="mutedText">暂无经营诊断。</p> : null}
      {primaryBrief ? <InsightBriefContent brief={primaryBrief} /> : null}
    </section>
  );
}

function InsightBriefContent({ brief }: { brief: InsightBrief }) {
  const primaryAction = brief.action_plan[0];
  const primaryGap = brief.data_gaps[0];
  const primaryEvidence = brief.evidence_refs[0];

  return (
    <div className="insightBrief">
      <div className="insightBrief__header">
        <div>
          <span className={`platformTag platformTag--${brief.scope.platform}`}>
            {brief.scope.platform}
          </span>
          <h3>{brief.headline}</h3>
        </div>
        <dl className="insightBrief__confidence">
          <div>
            <dt>confidence</dt>
            <dd>{brief.confidence.level}</dd>
          </div>
          <div>
            <dt>evidence</dt>
            <dd>{brief.confidence.evidence_count}</dd>
          </div>
        </dl>
      </div>

      <p className="insightBrief__reason">{brief.confidence.reason}</p>

      <div className="insightBrief__grid">
        <section aria-label="关键信号">
          <h4>关键信号</h4>
          <ul className="briefSignalList">
            {brief.business_signals.slice(0, 3).map((signal) => (
              <li key={signal.signal_id}>
                <div>
                  <span>{signal.signal_type}</span>
                  <strong>{signal.priority}</strong>
                </div>
                <p>{signal.business_impact}</p>
              </li>
            ))}
          </ul>
        </section>

        <section aria-label="行动计划">
          <h4>行动计划</h4>
          {primaryAction ? (
            <div className="briefAction">
              <div>
                <span>{primaryAction.action_type}</span>
                <strong>{primaryAction.expected_metric}</strong>
              </div>
              <h5>{primaryAction.title}</h5>
              <p>{primaryAction.recommendation}</p>
            </div>
          ) : (
            <p className="mutedText">暂无行动建议。</p>
          )}
        </section>
      </div>

      <div className="insightBrief__footer">
        {primaryGap ? (
          <p>
            <strong>证据缺口</strong>
            <span>{primaryGap.description}</span>
          </p>
        ) : null}
        {primaryEvidence ? (
          <blockquote>
            <span>Evidence</span>
            <p>{primaryEvidence.quote}</p>
          </blockquote>
        ) : null}
      </div>
    </div>
  );
}

function selectPrimaryBrief(briefs: InsightBrief[]): InsightBrief | null {
  return briefs
    .slice()
    .sort((left, right) => priorityScore(right) - priorityScore(left))[0] ?? null;
}

function priorityScore(brief: InsightBrief): number {
  const confidenceScore = {
    high: 4,
    medium: 3,
    low: 2,
    hypothesis: 1
  }[brief.confidence.level] ?? 0;
  return confidenceScore * 10 + brief.confidence.evidence_count;
}
