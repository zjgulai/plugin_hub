export const CONTENT_COMMAND_BAR_CSS = `
:host {
  display: block;
  color-scheme: light;
  font-family: Aptos, "IBM Plex Sans", "Segoe UI", Arial, sans-serif;
  letter-spacing: 0;
}

* {
  box-sizing: border-box;
}

button,
input {
  font: inherit;
}

.ph-shell {
  width: min(100%, 1540px);
  margin: 14px auto;
  border: 1px solid #247a82;
  background: #fbfcf7;
  color: #20231f;
  box-shadow: 0 14px 28px rgba(32, 35, 31, 0.11);
  overflow: hidden;
}

.ph-command {
  display: grid;
  grid-template-columns: minmax(170px, 0.7fr) minmax(130px, 0.54fr) minmax(360px, 1.9fr) auto;
  gap: 14px;
  align-items: center;
  padding: 12px 14px;
  border-bottom: 1px solid #d7decf;
}

.ph-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  padding-right: 12px;
  border-right: 1px solid #d7decf;
}

.ph-brand-mark {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border: 2px solid #247a82;
  color: #247a82;
  font-size: 12px;
  font-weight: 900;
}

.ph-brand strong {
  display: block;
  font-size: 16px;
  line-height: 1.1;
}

.ph-brand span {
  display: block;
  margin-top: 2px;
  color: #697168;
  font-size: 12px;
  font-weight: 700;
}

.ph-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.ph-badge {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 5px 9px;
  border: 1px solid #aebba6;
  background: #ffffff;
  color: #20231f;
  font-size: 12px;
  font-weight: 800;
  white-space: nowrap;
}

.ph-badge--amazon {
  border-color: #996f12;
  background: #f6edcf;
}

.ph-badge--reddit {
  border-color: #a45636;
  background: #f5e6dc;
}

.ph-object {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 10px;
  min-width: 0;
  margin: 0;
  padding: 8px 10px;
  border: 1px solid #d7decf;
  background: #ffffff;
}

.ph-object div {
  min-width: 0;
}

.ph-object dt,
.ph-confidence span,
.ph-footer label span {
  color: #697168;
  font-size: 10px;
  font-weight: 900;
  text-transform: uppercase;
}

.ph-object dd {
  overflow: hidden;
  margin: 3px 0 0;
  font-size: 13px;
  font-weight: 900;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ph-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  min-width: max-content;
}

.ph-button,
.ph-icon-button {
  min-height: 36px;
  border: 1px solid #247a82;
  background: #ffffff;
  color: #1f5f65;
  cursor: pointer;
  font-size: 13px;
  font-weight: 900;
}

.ph-button {
  padding: 0 14px;
}

.ph-button--primary {
  border-color: #0f665f;
  background: #0f665f;
  color: #ffffff;
}

.ph-button:disabled {
  cursor: wait;
  opacity: 0.64;
}

.ph-icon-button {
  padding: 0 10px;
}

.ph-button:hover:not(:disabled),
.ph-icon-button:hover {
  border-color: #151816;
}

.ph-pipeline {
  display: grid;
  grid-template-columns: minmax(170px, 0.7fr) minmax(0, 1fr) minmax(118px, 0.28fr);
  gap: 16px;
  align-items: center;
  padding: 12px 14px;
  border-bottom: 1px solid #d7decf;
  background: #f7f8f4;
}

.ph-pipeline-title {
  min-width: 0;
}

.ph-pipeline-title strong {
  display: block;
  font-size: 14px;
}

.ph-pipeline-title span {
  display: block;
  margin-top: 4px;
  color: #697168;
  font-size: 12px;
}

.ph-pipeline ol {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 10px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.ph-step {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  padding: 8px;
  border: 1px solid transparent;
}

.ph-step-index {
  display: grid;
  flex: 0 0 auto;
  place-items: center;
  width: 20px;
  height: 20px;
  border: 1px solid #aebba6;
  background: #ffffff;
  color: #697168;
  font-size: 11px;
  font-weight: 900;
}

.ph-step strong,
.ph-step span {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ph-step strong {
  font-size: 13px;
}

.ph-step div span {
  margin-top: 2px;
  color: #697168;
  font-size: 12px;
}

.ph-step--done .ph-step-index {
  border-color: #2f7d56;
  background: #e3f2e8;
  color: #2f7d56;
}

.ph-step--active {
  border-color: #247a82;
  background: #dff0f2;
}

.ph-step--error {
  border-color: #b13f37;
  background: #f8e1de;
}

.ph-confidence {
  min-width: 0;
  padding-left: 14px;
  border-left: 1px solid #d7decf;
  text-align: right;
}

.ph-confidence strong {
  display: block;
  margin-top: 2px;
  color: #247a82;
  font-size: 26px;
  line-height: 1;
}

.ph-footer {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 14px;
  align-items: center;
  padding: 11px 14px;
  color: #3c4339;
  font-size: 13px;
}

.ph-footer p {
  flex: 1 1 360px;
  margin: 0;
  min-width: 260px;
}

.ph-footer label {
  display: flex;
  align-items: center;
  gap: 7px;
  min-width: min(100%, 300px);
}

.ph-footer input {
  width: 220px;
  min-height: 30px;
  border: 1px solid #aebba6;
  background: #ffffff;
  color: #20231f;
  padding: 4px 8px;
}

.ph-export-actions {
  display: flex;
  gap: 6px;
}

.ph-mini-button {
  min-height: 30px;
  padding: 0 9px;
  border: 1px solid #aebba6;
  background: #ffffff;
  color: #1f5f65;
  cursor: pointer;
  font-size: 12px;
  font-weight: 900;
}

.ph-mini-button:hover {
  border-color: #151816;
}

.ph-mini-button:disabled {
  cursor: wait;
  opacity: 0.64;
}

.ph-run-state,
.ph-notice,
.ph-error {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 4px 8px;
  border: 1px solid #d7decf;
  background: #ffffff;
  font-size: 12px;
  font-weight: 800;
}

.ph-notice {
  border-color: #247a82;
  background: #dff0f2;
}

.ph-error {
  border-color: #b13f37;
  background: #f8e1de;
  color: #8f2821;
}

@media (max-width: 980px) {
  .ph-command,
  .ph-pipeline {
    grid-template-columns: 1fr;
  }

  .ph-brand {
    border-right: 0;
    padding-right: 0;
  }

  .ph-object,
  .ph-pipeline ol {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .ph-actions {
    justify-content: flex-start;
    flex-wrap: wrap;
    min-width: 0;
  }

  .ph-confidence {
    border-left: 0;
    padding-left: 0;
    text-align: left;
  }
}
`;
