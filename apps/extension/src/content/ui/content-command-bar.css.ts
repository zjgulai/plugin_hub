export const CONTENT_COMMAND_BAR_CSS = `
:host {
  display: block;
  color-scheme: light;
  font-family: "SF Pro Text", "Helvetica Neue", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
  letter-spacing: 0;
  pointer-events: none;
}

* {
  box-sizing: border-box;
}

button,
input {
  font: inherit;
}

button {
  border-radius: 0;
  touch-action: manipulation;
}

.ph-shell {
  --ph-accent: #3e78d6;
  --ph-accent-strong: #245fb8;
  --ph-accent-soft: #e7f0ff;
  --ph-border: #d9dee8;
  --ph-border-strong: #b9c1cf;
  --ph-muted: #747d8c;
  --ph-text: #20242c;
  --ph-panel: #ffffff;
  --ph-panel-soft: #f7f9fc;
  --ph-radius: 8px;
  --ph-shadow: 0 20px 48px rgba(35, 45, 62, 0.2), 0 1px 0 rgba(255, 255, 255, 0.8) inset;
  --ph-shadow-soft: 0 10px 26px rgba(35, 45, 62, 0.12);
  position: fixed;
  top: 16px;
  right: 16px;
  bottom: 16px;
  z-index: 2147483640;
  width: min(420px, calc(100vw - 32px));
  color: var(--ph-text);
  pointer-events: none;
}

.ph-shell--amazon {
  --ph-platform: #c28a2c;
  --ph-platform-soft: #fbf1de;
}

.ph-shell--reddit {
  --ph-platform: #c94d48;
  --ph-platform-soft: #fae7e5;
}

.ph-shell--instagram {
  --ph-platform: #bb4f93;
  --ph-platform-soft: #f8e7f2;
}

.ph-shell--collapsed {
  top: 50%;
  bottom: auto;
  width: 68px;
  transform: translateY(-50%);
}

.ph-drawer,
.ph-rail {
  pointer-events: auto;
  border: 1px solid rgba(185, 193, 207, 0.88);
  border-radius: var(--ph-radius);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(247, 249, 252, 0.97)),
    var(--ph-panel);
  box-shadow: var(--ph-shadow);
}

.ph-drawer {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 420px;
  scrollbar-color: #b9c1cf transparent;
  overflow-x: hidden;
  overflow-y: auto;
  overscroll-behavior: contain;
}

.ph-button:focus-visible,
.ph-ghost-button:focus-visible,
.ph-mini-button:focus-visible,
.ph-loop-tab:focus-visible,
.ph-rail:focus-visible,
.ph-settings summary:focus-visible,
.ph-settings input:focus-visible {
  outline: 3px solid color-mix(in srgb, var(--ph-accent) 38%, transparent);
  outline-offset: 2px;
}

.ph-drawer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px;
  border-bottom: 1px solid rgba(217, 222, 232, 0.92);
  background: linear-gradient(180deg, #ffffff, #f7f9fc);
}

.ph-brand {
  display: flex;
  align-items: center;
  min-width: 0;
  gap: 10px;
}

.ph-brand-mark,
.ph-rail-mark {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border: 1px solid color-mix(in srgb, var(--ph-platform, var(--ph-accent)) 60%, var(--ph-border));
  border-radius: 7px;
  background: linear-gradient(180deg, #ffffff, var(--ph-platform-soft, var(--ph-accent-soft)));
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8);
  color: var(--ph-platform, var(--ph-accent));
  font-size: 12px;
  font-weight: 900;
}

.ph-brand strong,
.ph-rail-copy strong {
  display: block;
  font-size: 16px;
  line-height: 1.1;
}

.ph-brand span,
.ph-rail-copy span,
.ph-section-heading span,
.ph-source h2 + span {
  color: var(--ph-muted);
  font-size: 12px;
  font-weight: 700;
}

.ph-header-actions,
.ph-primary-actions,
.ph-button-row {
  display: flex;
  gap: 8px;
}

.ph-header-actions {
  flex: 0 0 auto;
}

.ph-section {
  padding: 14px;
  border-bottom: 1px solid var(--ph-border);
  background: #fbfcf7;
}

.ph-loop-tabs {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 6px;
  padding: 10px 12px 0;
  background: #ffffff;
}

.ph-loop-tab {
  min-width: 0;
  min-height: 34px;
  border: 1px solid var(--ph-border);
  background: #f7f9fc;
  color: var(--ph-muted);
  cursor: pointer;
  font-size: 12px;
  font-weight: 900;
}

.ph-loop-tab[aria-selected="true"] {
  border-color: var(--ph-accent-strong);
  background: var(--ph-accent-soft);
  color: var(--ph-accent-strong);
}

.ph-loop-tab--done {
  border-color: #9dccb1;
}

.ph-loop-tab--active {
  border-color: var(--ph-accent);
}

.ph-loop-tab--error {
  border-color: #b13f37;
  color: #8f2821;
}

.ph-stage-panel {
  display: grid;
  gap: 5px;
  padding-top: 10px;
  background: #ffffff;
}

.ph-stage-panel span {
  color: var(--ph-muted);
  font-size: 10px;
  font-weight: 900;
  text-transform: uppercase;
}

.ph-stage-panel strong {
  font-size: 15px;
}

.ph-stage-panel p,
.ph-recovery p {
  margin: 0;
  color: var(--ph-muted);
  font-size: 12px;
  font-weight: 760;
  line-height: 1.45;
  overflow-wrap: anywhere;
}

.ph-stage-panel--done {
  border-left: 3px solid #2f7d56;
}

.ph-stage-panel--active {
  border-left: 3px solid var(--ph-accent);
}

.ph-stage-panel--error {
  border-left: 3px solid #b13f37;
}

.ph-source {
  background: #ffffff;
}

.ph-section-kicker {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 10px;
}

.ph-badge {
  display: inline-flex;
  align-items: center;
  min-height: 26px;
  padding: 4px 8px;
  border: 1px solid var(--ph-border);
  background: #ffffff;
  color: var(--ph-text);
  font-size: 12px;
  font-weight: 800;
  white-space: nowrap;
}

.ph-badge--amazon,
.ph-badge--reddit,
.ph-badge--instagram {
  border-color: var(--ph-accent);
  background: var(--ph-accent-soft);
}

.ph-source h2 {
  display: -webkit-box;
  overflow: hidden;
  margin: 0 0 12px;
  color: var(--ph-text);
  font-size: 18px;
  line-height: 1.25;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
}

.ph-meta-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin: 0;
}

.ph-meta-grid div {
  min-width: 0;
  padding: 8px;
  border: 1px solid #e1e6dc;
  background: #fbfcf7;
}

.ph-meta-grid dt,
.ph-metrics span,
.ph-settings label span {
  color: var(--ph-muted);
  font-size: 10px;
  font-weight: 900;
  text-transform: uppercase;
}

.ph-meta-grid dd {
  overflow: hidden;
  margin: 4px 0 0;
  font-size: 13px;
  font-weight: 900;
  line-height: 1.25;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ph-action-panel {
  display: grid;
  gap: 10px;
  background: #f7f8f4;
}

.ph-next-action {
  display: grid;
  gap: 5px;
  padding: 10px;
  border: 1px solid #dfe6d9;
  background: #ffffff;
}

.ph-next-action span {
  color: var(--ph-muted);
  font-size: 10px;
  font-weight: 900;
  text-transform: uppercase;
}

.ph-next-action strong {
  font-size: 15px;
}

.ph-next-action p {
  margin: 0;
  color: var(--ph-muted);
  font-size: 12px;
  font-weight: 750;
  line-height: 1.45;
}

.ph-secondary-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.ph-recovery {
  display: grid;
  gap: 5px;
}

.ph-recovery strong {
  font-size: 14px;
}

.ph-recovery--info {
  border-left: 3px solid var(--ph-accent);
}

.ph-recovery--warning {
  border-left: 3px solid #b78321;
}

.ph-recovery--error {
  border-left: 3px solid #b13f37;
}

.ph-button,
.ph-ghost-button,
.ph-mini-button {
  min-height: 36px;
  border: 1px solid var(--ph-accent);
  background: #ffffff;
  color: var(--ph-accent-strong);
  cursor: pointer;
  font-size: 13px;
  font-weight: 900;
}

.ph-button {
  padding: 0 12px;
}

.ph-button--primary {
  width: 100%;
  min-height: 42px;
  border-color: var(--ph-accent-strong);
  background: var(--ph-accent-strong);
  color: #ffffff;
}

.ph-button--tertiary {
  width: 100%;
  border-color: #c6d0bf;
  color: var(--ph-text);
}

.ph-ghost-button {
  min-height: 30px;
  padding: 0 8px;
  border-color: #c6d0bf;
  font-size: 12px;
}

.ph-button:hover:not(:disabled),
.ph-ghost-button:hover,
.ph-mini-button:hover,
.ph-rail:hover {
  border-color: #151816;
}

.ph-button:disabled,
.ph-mini-button:disabled {
  cursor: wait;
  opacity: 0.64;
}

.ph-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  background: #ffffff;
}

.ph-metrics div {
  min-width: 0;
  padding: 10px;
  border: 1px solid #e1e6dc;
  background: #fbfcf7;
}

.ph-metrics strong {
  display: block;
  overflow: hidden;
  margin-top: 4px;
  color: var(--ph-accent);
  font-size: 22px;
  line-height: 1;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ph-pipeline {
  background: #fbfcf7;
}

.ph-section-heading {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.ph-section-heading strong {
  font-size: 14px;
}

.ph-section-heading span {
  overflow: hidden;
  text-align: right;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ph-pipeline-list {
  display: grid;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.ph-step {
  display: grid;
  grid-template-columns: 24px minmax(0, 1fr);
  gap: 9px;
  align-items: start;
  min-width: 0;
  padding: 9px;
  border: 1px solid #e1e6dc;
  background: #ffffff;
}

.ph-step-index {
  display: grid;
  place-items: center;
  width: 22px;
  height: 22px;
  border: 1px solid #aebba6;
  background: #ffffff;
  color: var(--ph-muted);
  font-size: 11px;
  font-weight: 900;
}

.ph-step strong {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ph-step strong {
  font-size: 13px;
}

.ph-step div span {
  display: block;
  margin-top: 2px;
  color: var(--ph-muted);
  font-size: 12px;
  line-height: 1.35;
  overflow-wrap: anywhere;
}

.ph-step--done .ph-step-index {
  border-color: #2f7d56;
  background: #e3f2e8;
  color: #2f7d56;
}

.ph-step--active {
  border-color: var(--ph-accent);
  background: var(--ph-accent-soft);
}

.ph-step--error {
  border-color: #b13f37;
  background: #f8e1de;
}

.ph-evidence {
  background: #ffffff;
}

.ph-button-row {
  flex-wrap: wrap;
}

.ph-mini-button {
  min-height: 32px;
  padding: 0 10px;
  border-color: #c6d0bf;
  font-size: 12px;
}

.ph-status-stack {
  display: grid;
  gap: 7px;
  margin-top: 10px;
}

.ph-run-state,
.ph-notice,
.ph-error {
  display: block;
  min-height: 28px;
  padding: 6px 8px;
  border: 1px solid var(--ph-border);
  background: #ffffff;
  font-size: 12px;
  font-weight: 800;
  line-height: 1.35;
  overflow-wrap: anywhere;
}

.ph-notice {
  border-color: var(--ph-accent);
  background: var(--ph-accent-soft);
}

.ph-error {
  border-color: #b13f37;
  background: #f8e1de;
  color: #8f2821;
}

.ph-settings {
  margin-top: auto;
  background: #f7f8f4;
}

.ph-settings summary {
  cursor: pointer;
  color: var(--ph-text);
  font-size: 13px;
  font-weight: 900;
}

.ph-settings label {
  display: grid;
  gap: 6px;
  margin-top: 10px;
}

.ph-settings input {
  width: 100%;
  min-height: 34px;
  border: 1px solid #aebba6;
  background: #ffffff;
  color: var(--ph-text);
  padding: 5px 8px;
}

.ph-rail {
  display: grid;
  gap: 8px;
  justify-items: center;
  width: 68px;
  min-height: 168px;
  padding: 10px 8px;
  color: var(--ph-text);
  cursor: pointer;
}

.ph-rail-copy {
  display: grid;
  gap: 4px;
  min-width: 0;
  writing-mode: vertical-rl;
}

.ph-rail-copy strong,
.ph-rail-copy span {
  overflow: hidden;
  max-height: 84px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ph-rail-state {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  max-width: 52px;
  padding: 3px 6px;
  border: 1px solid var(--ph-border);
  background: #ffffff;
  color: var(--ph-accent-strong);
  font-size: 11px;
  font-weight: 900;
}

@media (max-width: 720px) {
  .ph-shell {
    top: auto;
    right: max(8px, env(safe-area-inset-right));
    bottom: max(8px, env(safe-area-inset-bottom));
    left: max(8px, env(safe-area-inset-left));
    width: auto;
  }

  .ph-shell--collapsed {
    right: max(10px, env(safe-area-inset-right));
    left: auto;
    bottom: max(10px, env(safe-area-inset-bottom));
    width: 64px;
    transform: none;
  }

  .ph-drawer {
    max-height: min(82vh, 680px);
    min-height: 0;
  }

  .ph-loop-tabs {
    grid-template-columns: repeat(5, minmax(56px, 1fr));
    overflow-x: auto;
  }

  .ph-source h2 {
    font-size: 16px;
    -webkit-line-clamp: 2;
  }

  .ph-meta-grid,
  .ph-primary-actions,
  .ph-metrics {
    grid-template-columns: 1fr;
  }

  .ph-section-heading {
    align-items: flex-start;
    flex-direction: column;
    gap: 4px;
  }

  .ph-section-heading span {
    text-align: left;
    white-space: normal;
  }
}

@media (max-height: 720px) and (min-width: 721px) {
  .ph-shell {
    top: 8px;
    right: 8px;
    bottom: 8px;
  }

  .ph-section,
  .ph-drawer-header {
    padding: 10px;
  }

  .ph-source h2 {
    -webkit-line-clamp: 2;
  }
}

/* Smartisan-inspired extension surface. */
.ph-drawer::before {
  display: block;
  height: 1px;
  margin: 0 10px;
  background: rgba(255, 255, 255, 0.9);
  content: "";
}

.ph-brand strong,
.ph-source h2,
.ph-section-heading strong {
  font-family: "SF Pro Display", "Helvetica Neue", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
  font-weight: 760;
}

.ph-section {
  border-bottom-color: rgba(217, 222, 232, 0.92);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.74), rgba(247, 249, 252, 0.72));
}

.ph-source,
.ph-evidence {
  background: linear-gradient(180deg, #ffffff, #f9fbfe);
}

.ph-badge,
.ph-meta-grid div,
.ph-next-action,
.ph-metrics div,
.ph-step,
.ph-run-state,
.ph-notice,
.ph-error,
.ph-settings input,
.ph-rail-state {
  border-color: rgba(217, 222, 232, 0.96);
  border-radius: 7px;
  background: linear-gradient(180deg, #ffffff, #f7f9fc);
  box-shadow: inset 0 1px 2px rgba(35, 45, 62, 0.08), 0 1px 0 rgba(255, 255, 255, 0.78);
}

.ph-badge--amazon,
.ph-badge--reddit,
.ph-badge--instagram {
  border-color: color-mix(in srgb, var(--ph-platform, var(--ph-accent)) 42%, var(--ph-border));
  background: linear-gradient(180deg, #ffffff, var(--ph-platform-soft, var(--ph-accent-soft)));
  color: var(--ph-text);
}

.ph-meta-grid dt,
.ph-metrics span,
.ph-settings label span,
.ph-next-action span {
  letter-spacing: 0.04em;
}

.ph-meta-grid dd,
.ph-metrics strong {
  font-weight: 760;
}

.ph-action-panel,
.ph-pipeline,
.ph-settings {
  background: linear-gradient(180deg, #f8fafd, #eef2f7);
}

.ph-next-action {
  padding: 12px;
}

.ph-button,
.ph-ghost-button,
.ph-mini-button,
.ph-loop-tab {
  border-radius: 7px;
  transition: background 140ms ease, border-color 140ms ease, box-shadow 140ms ease, transform 140ms ease;
}

.ph-button {
  border-color: rgba(36, 95, 184, 0.78);
  background: linear-gradient(180deg, #ffffff, #f1f5fb);
  color: var(--ph-accent-strong);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.78), 0 5px 12px rgba(35, 45, 62, 0.08);
}

.ph-button--primary {
  border-color: rgba(36, 95, 184, 0.88);
  background: linear-gradient(180deg, #5f94e5, var(--ph-accent));
  color: #ffffff;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.36), 0 8px 18px rgba(36, 95, 184, 0.22);
}

.ph-button--tertiary,
.ph-ghost-button,
.ph-mini-button {
  border-color: rgba(185, 193, 207, 0.9);
  background: linear-gradient(180deg, #ffffff, #f5f7fb);
  color: var(--ph-text);
}

.ph-button:hover:not(:disabled),
.ph-ghost-button:hover,
.ph-mini-button:hover,
.ph-rail:hover {
  border-color: rgba(36, 95, 184, 0.86);
  box-shadow: 0 8px 18px rgba(35, 45, 62, 0.13);
  transform: translateY(-1px);
}

.ph-button:disabled,
.ph-mini-button:disabled {
  cursor: not-allowed;
  opacity: 0.58;
}

.ph-step-index {
  border-color: rgba(185, 193, 207, 0.92);
  border-radius: 999px;
  background: linear-gradient(180deg, #ffffff, #f2f5fa);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.82);
}

.ph-step--done .ph-step-index {
  border-color: rgba(61, 141, 100, 0.42);
  background: linear-gradient(180deg, #ffffff, #e8f5ee);
  color: #2f7d56;
}

.ph-step--active {
  border-color: rgba(62, 120, 214, 0.42);
  background: linear-gradient(180deg, #ffffff, var(--ph-accent-soft));
}

.ph-step--error,
.ph-error {
  border-color: rgba(201, 77, 72, 0.46);
  background: linear-gradient(180deg, #ffffff, #fae7e5);
}

.ph-notice {
  border-color: rgba(62, 120, 214, 0.42);
  background: linear-gradient(180deg, #ffffff, var(--ph-accent-soft));
}

.ph-rail {
  background: linear-gradient(180deg, #ffffff, #f5f7fb);
}

.ph-rail-mark {
  border-radius: 50%;
}
`;
