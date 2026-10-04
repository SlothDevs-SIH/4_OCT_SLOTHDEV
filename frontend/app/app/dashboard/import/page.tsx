"use client";
/**
 * Frontend 1A · Import & data quality.
 * Backend: POST /businesses/{id}/imports, POST /imports/{id}/confirm, GET /imports/{id}/report, GET /imports/{id}/quarantine,
 *          GET /businesses/{id}/data-quality, POST /demo/import-sample, GET /demo/sample-import/orders.csv
 */
import { useState } from "react";
import { backend1A } from "@/lib/services/backend1/backend1A";
import { errorMessage } from "@/lib/http";
import { useAsync } from "@/lib/useAsync";
import { duplicateColumns, missingRequired, validateCsvFile } from "@/lib/validation";
import type { ImportKind, ImportReport, ImportUpload } from "@/lib/types";
import { Banner, DemoBadge, EmptyState, ErrorState, Loading, PageHeader, QualityBadge, RequireBusiness } from "@/components/ui";

export default function ImportPage() {
  return (
    <>
      <PageHeader title="Import & data quality" sub="Upload a CSV, review the suggested column mapping, confirm, and see exactly what was repaired and quarantined."
        right={<span className="badge info">Frontend 1A</span>} />
      <RequireBusiness>{(id) => <ImportFlow businessId={id} />}</RequireBusiness>
    </>
  );
}

function ImportFlow({ businessId }: { businessId: string }) {
  const [kind, setKind] = useState<ImportKind>("orders");
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [upload, setUpload] = useState<ImportUpload | null>(null);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [report, setReport] = useState<ImportReport | null>(null);
  const [busy, setBusy] = useState<"upload" | "confirm" | "sample" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showQuarantine, setShowQuarantine] = useState(false);

  const quality = useAsync(() => backend1A.dataQuality(businessId), `dq:${businessId}:${report?.import_id ?? ""}`);
  const quarantine = useAsync(showQuarantine && report ? () => backend1A.quarantine(report.import_id, 50) : null, `q:${report?.import_id}:${showQuarantine}`);

  function adopt(u: ImportUpload) {
    setUpload(u);
    setMapping(Object.fromEntries(Object.entries(u.suggested_mapping).filter(([, m]) => m.column).map(([f, m]) => [f, m.column as string])));
    setReport(u.report ?? null); setShowQuarantine(false);
  }

  async function doUpload() {
    const msg = validateCsvFile(file); setFileError(msg);
    if (msg || !file) return;
    setBusy("upload"); setError(null); setReport(null);
    try { adopt(await backend1A.uploadImport(businessId, kind, file)); }
    catch (e) { setError(errorMessage(e)); } finally { setBusy(null); }
  }
  async function doSample() {
    setBusy("sample"); setError(null);
    try { adopt(await backend1A.importSample()); quality.reload(); }
    catch (e) { setError(errorMessage(e)); } finally { setBusy(null); }
  }
  async function doConfirm() {
    if (!upload) return;
    setBusy("confirm"); setError(null);
    try { setReport(await backend1A.confirmImport(upload.import_id, mapping)); quality.reload(); }
    catch (e) { setError(errorMessage(e)); } finally { setBusy(null); }
  }

  const missing = upload ? missingRequired(upload, mapping) : [];
  const dupes = duplicateColumns(mapping);

  return (
    <div className="stack">
      {error && <Banner tone="bad">{error}</Banner>}

      <div className="grid cols-2">
        <section className="card" aria-labelledby="up-h">
          <h2 id="up-h">1 · Upload a CSV</h2>
          <div className="stack">
            <label className="field">File type
              <select id="import-kind" value={kind} onChange={(e) => setKind(e.target.value as ImportKind)}>
                <option value="orders">Orders</option><option value="campaigns">Campaigns</option><option value="leads">Leads</option>
              </select></label>
            <label className="field">CSV file
              <input id="import-file" type="file" accept=".csv,text/csv" aria-invalid={!!fileError}
                onChange={(e) => { setFile(e.target.files?.[0] ?? null); setFileError(null); }} />
              {fileError && <span className="field-error" role="alert">{fileError}</span>}</label>
            <div className="row">
              <button id="import-upload" className="btn primary" disabled={busy !== null} onClick={doUpload}>{busy === "upload" ? "Uploading…" : "Upload and suggest mapping"}</button>
            </div>
            <p className="small muted">Try the built-in messy sample: <a href={backend1A.sampleCsvUrl} download>download the CSV</a> or run it through the real pipeline.</p>
            <div><button id="import-sample" className="btn" disabled={busy !== null} onClick={doSample}>{busy === "sample" ? "Running…" : "Run messy sample (demo business)"}</button></div>
          </div>
        </section>

        <section className="card" aria-labelledby="dq-h">
          <h2 id="dq-h">Overall data confidence</h2>
          {quality.loading && <Loading rows={1} />}
          {quality.error && <ErrorState error={quality.error} onRetry={quality.reload} />}
          {quality.data && (
            <div className="stack">
              <div className="row"><QualityBadge flag={quality.data.overall.badge} />
                <strong>{Math.round(quality.data.overall.confidence * 100)}%</strong><DemoBadge synthetic={quality.data.synthetic} /></div>
              <div className="bar"><span style={{ width: `${quality.data.overall.confidence * 100}%` }} /></div>
              <p className="muted">{quality.data.overall.summary}</p>
              <div className="row small">
                <span className="badge">Unattributed revenue {quality.data.overall.unattributed_revenue_pct}%</span>
                {quality.data.kpi_quality && Object.entries(quality.data.kpi_quality).map(([k, v]) => <span key={k} className="muted">{k.replace(/_/g, " ")}: <QualityBadge flag={v as any} /></span>)}
              </div>
            </div>
          )}
        </section>
      </div>

      {upload && (
        <section className="card" aria-labelledby="map-h">
          <div className="row between"><h2 id="map-h">2 · Column mapping</h2>
            <span className="muted small">{upload.filename} · {upload.rows_total} rows · {upload.kind}</span></div>
          <div className="table-wrap"><table>
            <thead><tr><th>Canonical field</th><th>Your column</th><th>Confidence</th></tr></thead>
            <tbody>{Object.entries(upload.suggested_mapping).map(([field, s]) => (
              <tr key={field}>
                <td><span className="mono">{field}</span> {s.required && <span className="badge warn">required</span>}</td>
                <td><select aria-label={`Column for ${field}`} value={mapping[field] ?? ""}
                  onChange={(e) => setMapping((m) => ({ ...m, [field]: e.target.value }))}>
                  <option value="">(not mapped)</option>
                  {upload.columns.map((c) => <option key={c} value={c}>{c}</option>)}
                </select></td>
                <td>{s.column ? <span className="badge">{Math.round(s.confidence * 100)}%</span> : <span className="muted">no suggestion</span>}</td>
              </tr>))}</tbody></table></div>
          {missing.length > 0 && <div style={{ marginTop: 10 }}><Banner tone="warn">Map the required fields: {missing.join(", ")}</Banner></div>}
          {dupes.length > 0 && <div style={{ marginTop: 10 }}><Banner tone="warn">Column used twice: {dupes.join(", ")}</Banner></div>}
          <details style={{ marginTop: 12 }}><summary className="muted small">Preview first rows</summary>
            <div className="table-wrap"><table><thead><tr>{upload.columns.map((c) => <th key={c}>{c}</th>)}</tr></thead>
              <tbody>{upload.preview.map((r, i) => <tr key={i}>{upload.columns.map((c) => <td key={c}>{r[c]}</td>)}</tr>)}</tbody></table></div></details>
          <div style={{ marginTop: 14 }}>
            <button id="import-confirm" className="btn primary" disabled={busy !== null || missing.length > 0 || dupes.length > 0} onClick={doConfirm}>
              {busy === "confirm" ? "Validating…" : report ? "Re-run with this mapping" : "Confirm mapping and load"}</button>
          </div>
        </section>
      )}

      {report && (
        <section className="card" aria-labelledby="rep-h">
          <div className="row between"><h2 id="rep-h">3 · Import report</h2><QualityBadge flag={report.confidence >= 0.8 ? "high" : report.confidence >= 0.5 ? "medium" : "low"} /></div>
          <div className="grid cols-3" style={{ marginBottom: 14 }}>
            {[["Rows loaded", report.rows_loaded, "good"], ["Repaired", report.rows_repaired, "warn"], ["Quarantined", report.rows_quarantined, "bad"], ["Duplicates merged", report.duplicates_merged, "info"]]
              .map(([l, v, t]) => <div key={l as string} className="card"><div className="muted small">{l}</div><div className="kpi"><span className={`value delta ${t === "good" ? "good" : ""}`} style={{ fontSize: "1.6rem" }}>{v}</span></div></div>)}
          </div>
          {report.issues.length === 0 ? <EmptyState title="No issues found" hint="Every row passed validation." /> : (
            <div className="table-wrap"><table><thead><tr><th>Issue</th><th>Rows</th><th>Action</th><th>Example</th></tr></thead>
              <tbody>{report.issues.map((i) => <tr key={i.code}><td className="mono">{i.code}</td><td>{i.count}</td><td><span className="badge">{i.action.replace(/_/g, " ")}</span></td><td className="muted">{i.example}</td></tr>)}</tbody></table></div>
          )}
          {report.rows_quarantined > 0 && <div style={{ marginTop: 12 }}>
            <button className="btn" onClick={() => setShowQuarantine((s) => !s)}>{showQuarantine ? "Hide" : "Show"} quarantined rows</button></div>}
          {showQuarantine && <div style={{ marginTop: 12 }}>
            {quarantine.loading && <Loading rows={1} />}
            {quarantine.error && <ErrorState error={quarantine.error} onRetry={quarantine.reload} />}
            {quarantine.data && (quarantine.data.rows.length === 0 ? <EmptyState title="Nothing quarantined" /> : (
              <div className="table-wrap"><p className="small muted">Showing {quarantine.data.rows.length} of {quarantine.data.total}</p>
                <table><thead><tr>{Object.keys(quarantine.data.rows[0]).map((k) => <th key={k}>{k}</th>)}</tr></thead>
                  <tbody>{quarantine.data.rows.map((r, i) => <tr key={i}>{Object.values(r).map((v, j) => <td key={j}>{typeof v === "object" ? JSON.stringify(v) : String(v ?? "")}</td>)}</tr>)}</tbody></table></div>))}
          </div>}
        </section>
      )}
    </div>
  );
}
