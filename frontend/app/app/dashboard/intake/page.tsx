"use client";

import { useState } from "react";
import { useCatalyst } from "@/lib/catalyst";
import { useAsync, errorMessage } from "@/lib/useAsync";
import { getDataQuality, intakeChat, sampleChat, sampleOrdersCsvUrl, uploadImport } from "@/lib/api";
import type { ImportReport } from "@/lib/types";
import StateBoundary from "@/components/catalyst/StateBoundary";
import ImportReportView from "@/components/catalyst/ImportReportView";
import FileDropzone from "@/components/catalyst/FileDropzone";
import ChatPasteBox from "@/components/catalyst/ChatPasteBox";
import ChatIntakeResult from "@/components/catalyst/ChatIntakeResult";

type Kind = "orders" | "costs" | "insights";
const KINDS: { kind: Kind; title: string; hint: string }[] = [
  { kind: "orders", title: "Orders", hint: "A sheet of your orders: date, what was bought, amount, and how they found you (friend, friend of a friend, stranger)." },
  { kind: "costs", title: "Costs", hint: "What each product costs you: material, making, packaging, courier." },
  { kind: "insights", title: "Instagram insights", hint: "Reach, profile visits and follows per post, exported from Instagram." },
];

export default function Intake() {
  const s = useCatalyst();
  const id = s.businessId as string;
  const dq = useAsync(() => getDataQuality(id), `dq-${id}`);
  const [reports, setReports] = useState<Partial<Record<Kind, ImportReport>>>({});
  const [busyKind, setBusyKind] = useState<Kind | null>(null);
  const [chatBusy, setChatBusy] = useState(false);
  const [chatResult, setChatResult] = useState<Awaited<ReturnType<typeof intakeChat>> | null>(null);
  const [note, setNote] = useState<string | null>(null);

  async function upload(kind: Kind, file: File) {
    setBusyKind(kind); setNote(null);
    try {
      const r = await uploadImport(id, kind, file);
      setReports((p) => ({ ...p, [kind]: r.report }));
      dq.reload();
    } catch (e) { setNote(errorMessage(e)); } finally { setBusyKind(null); }
  }

  async function paste(text: string) {
    setChatBusy(true); setNote(null);
    try { setChatResult(await intakeChat(id, text)); } catch (e) { setNote(errorMessage(e)); } finally { setChatBusy(false); }
  }

  async function useSample() {
    if (!s.key) return;
    try { await paste((await sampleChat(s.key, s.week)).text); } catch (e) { setNote(errorMessage(e)); }
  }

  return (
    <div className="stack" style={{ gap: 24 }}>
      <header className="page-head">
        <h1>Your data</h1>
        <p className="sub">
          {s.isDemo
            ? "This demo business already came with a messy orders sheet. Below is what the importer found and repaired. You can still try your own files or paste chats."
            : "Add your orders, costs and Instagram insights, and paste recent messages. We repair what we can, set aside what we cannot, and tell you how much to trust the result."}
        </p>
      </header>
      {note && <div className="banner" role="alert">{note}</div>}

      <section className="stack" aria-label="Data quality">
        <h2>How good is the data</h2>
        <StateBoundary loading={dq.loading} error={dq.error} onRetry={dq.reload} empty={dq.data?.imports.length === 0} emptyMessage="Nothing imported yet. Upload an orders sheet below.">
          {dq.data && <ImportReportView report={dq.data} />}
        </StateBoundary>
      </section>

      <section className="stack" aria-label="Upload files">
        <h2>Upload a sheet</h2>
        {s.key && (
          <p className="muted small">
            No file handy? <a href={sampleOrdersCsvUrl(s.key, s.week)} download>Download the messy sample orders sheet</a>, then upload it here to watch the repairs.
            {s.isDemo && " (On a demo business an upload only shows the report; it does not change the generated data.)"}
          </p>
        )}
        <div className="grid cols-3">
          {KINDS.map((k) => (
            <div key={k.kind} className="stack">
              <h3 style={{ margin: 0 }}>{k.title}</h3>
              <FileDropzone kind={k.kind} hint={k.hint} busy={busyKind === k.kind} onFile={(f) => void upload(k.kind, f)} />
              {reports[k.kind] && <ImportReportView report={reports[k.kind] as ImportReport} />}
            </div>
          ))}
        </div>
      </section>

      <section className="stack" aria-label="Paste messages">
        <h2>Paste recent messages</h2>
        <p className="muted small">Direct messages, comments or WhatsApp. Names, phone numbers and handles are removed before anything is stored.</p>
        <ChatPasteBox onSubmit={(t) => void paste(t)} onUseSample={s.key ? () => void useSample() : undefined} busy={chatBusy} />
        {chatResult && (
          <ChatIntakeResult messagesRead={chatResult.messages_read} leadsCreated={chatResult.leads_created} leadsUpdated={chatResult.leads_updated} notALead={chatResult.not_a_lead} privacyNote={chatResult.privacy} />
        )}
      </section>
    </div>
  );
}
