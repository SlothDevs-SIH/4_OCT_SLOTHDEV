"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useBusiness } from "@/lib/BusinessContext";
import {
  createBusiness,
  uploadImport,
  getDataQuality,
  intakeChat,
  sampleChat,
  sampleOrdersCsvUrl,
  CreateBusinessForm,
} from "@/lib/api";
import { DataQuality, ImportReport } from "@/lib/types";
import CatalystShell from "@/components/catalyst/CatalystShell";
import IntakeStepper from "@/components/catalyst/IntakeStepper";
import InterviewForm from "@/components/catalyst/InterviewForm";
import FileDropzone from "@/components/catalyst/FileDropzone";
import ChatPasteBox from "@/components/catalyst/ChatPasteBox";
import ChatIntakeResult from "@/components/catalyst/ChatIntakeResult";
import ImportReportView from "@/components/catalyst/ImportReportView";
import StateBoundary from "@/components/catalyst/StateBoundary";

const STEPS = ["Business", "Orders", "Costs & Posts", "Customer Chats", "Ingestion Report"];

const INITIAL_FORM: CreateBusinessForm = {
  name: "My Artisanal Kitchen",
  kind: "Home Bakery & Confectionery",
  products: [
    { name: "Sourdough Boule", category: "Breads", price: 350, unit_cost: 110 },
    { name: "Belgian Truffle Cake 1kg", category: "Cakes", price: 1400, unit_cost: 480 },
  ],
  channels: ["whatsapp", "instagram_dm"],
  team_size: 1,
  weekly_hours: 45,
  capacity_orders_per_week: 35,
  ad_budget_inr: 0,
  goal: { statement: "Reach 25 orders per week from non-friends", horizon_days: 30 },
  serves_cities: ["Mumbai", "Thane"],
  context_feed: "india_festivals",
  payment: "UPI / GPay",
  order_link: "https://wa.me/catalog/crumbandco",
};

export default function IntakePage() {
  const router = useRouter();
  const { businessId, setBusinessId } = useBusiness();

  const [currentStep, setCurrentStep] = useState(0);
  const [form, setForm] = useState<CreateBusinessForm>(INITIAL_FORM);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  // Uploaded artifacts state
  const [report, setReport] = useState<ImportReport | DataQuality | null>(null);
  const [chatOutcome, setChatOutcome] = useState<{
    messagesRead: number;
    leadsCreated: number;
    leadsUpdated: number;
    notALead: number;
    privacyNote: string;
  } | null>(null);

  // Load existing data quality if available
  useEffect(() => {
    if (businessId) {
      getDataQuality(businessId)
        .then((q) => setReport(q))
        .catch(() => {});
    }
  }, [businessId]);

  const handleSaveBusiness = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const created = await createBusiness(form);
      setBusinessId(created.business_id);
      setCurrentStep(1);
    } catch (err: any) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };

  const handleUploadFile = async (kind: "orders" | "costs", file: File) => {
    setBusy(true);
    setError(null);
    try {
      const res = await uploadImport(businessId, kind, file);
      setReport(res.report);
      setCurrentStep((prev) => prev + 1);
    } catch (err: any) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };

  const handleChatSubmit = async (text: string) => {
    setBusy(true);
    setError(null);
    try {
      const res = await intakeChat(businessId, text);
      setChatOutcome({
        messagesRead: res.messages_read,
        leadsCreated: res.leads_created,
        leadsUpdated: res.leads_updated,
        notALead: res.not_a_lead,
        privacyNote: res.privacy,
      });
      // Also refresh quality report
      const dq = await getDataQuality(businessId).catch(() => null);
      if (dq) setReport(dq);
      setCurrentStep(4);
    } catch (err: any) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };

  const handleUseSampleChat = async () => {
    setBusy(true);
    try {
      const sample = await sampleChat(businessId, 1);
      await handleChatSubmit(sample.text);
    } catch (err: any) {
      setError(err);
      setBusy(false);
    }
  };

  return (
    <CatalystShell>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-black text-white tracking-tight">
            Workspace Ingestion & Configuration
          </h1>
          <p className="text-sm text-slate-400">
            Feed your actual operations, orders, and customer chat logs into the decision engine.
          </p>
        </div>

        <StateBoundary error={error}>
          <IntakeStepper
            steps={STEPS}
            current={currentStep}
            onStepClick={(step) => setCurrentStep(step)}
          >
            {/* Step 0: Business profile interview */}
            {currentStep === 0 && (
              <div className="space-y-4">
                <h3 className="text-lg font-bold text-white">Step 1: Operational Model</h3>
                <p className="text-xs text-slate-400">
                  Configure your product economics, weekly production ceiling, and local geography.
                </p>
                <InterviewForm
                  value={form}
                  onChange={setForm}
                  onSubmit={handleSaveBusiness}
                  busy={busy}
                />
              </div>
            )}

            {/* Step 1: Orders CSV upload */}
            {currentStep === 1 && (
              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-bold text-white">Step 2: Order Ledger CSV</h3>
                  <p className="text-xs text-slate-400">
                    Upload your past 4-12 weeks of customer deliveries or storefront checkout exports.
                  </p>
                </div>

                <FileDropzone
                  kind="orders"
                  onFile={(file) => handleUploadFile("orders", file)}
                  busy={busy}
                  hint="Drag & drop your orders.csv export or click to browse"
                />

                <div className="flex items-center justify-between text-xs pt-2">
                  <a
                    href={sampleOrdersCsvUrl(businessId, 1)}
                    target="_blank"
                    rel="noreferrer"
                    className="text-indigo-400 hover:text-indigo-300 underline"
                  >
                    ⬇ Download Sample Orders CSV format
                  </a>
                  <button
                    type="button"
                    onClick={() => setCurrentStep(2)}
                    className="text-slate-400 hover:text-white"
                  >
                    Skip step →
                  </button>
                </div>
              </div>
            )}

            {/* Step 2: Costs and Posts */}
            {currentStep === 2 && (
              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-bold text-white">Step 3: Marketing & Packaging Costs</h3>
                  <p className="text-xs text-slate-400">
                    Upload monthly ingredient costs, packaging expenses, and organic reach campaign notes.
                  </p>
                </div>

                <FileDropzone
                  kind="costs"
                  onFile={(file) => handleUploadFile("costs", file)}
                  busy={busy}
                  hint="Drag & drop your costs.csv or monthly expenses export"
                />

                <div className="flex justify-end pt-2">
                  <button
                    type="button"
                    onClick={() => setCurrentStep(3)}
                    className="text-xs font-semibold text-slate-400 hover:text-white"
                  >
                    Skip step →
                  </button>
                </div>
              </div>
            )}

            {/* Step 3: Chat log paste */}
            {currentStep === 3 && (
              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-bold text-white">Step 4: Customer Inquiry Logs</h3>
                  <p className="text-xs text-slate-400">
                    Paste raw customer chat histories to parse inbound demand, price objections, and lead status.
                  </p>
                </div>

                <ChatPasteBox
                  onSubmit={handleChatSubmit}
                  onUseSample={handleUseSampleChat}
                  busy={busy}
                />

                {chatOutcome && (
                  <ChatIntakeResult
                    messagesRead={chatOutcome.messagesRead}
                    leadsCreated={chatOutcome.leadsCreated}
                    leadsUpdated={chatOutcome.leadsUpdated}
                    notALead={chatOutcome.notALead}
                    privacyNote={chatOutcome.privacyNote}
                  />
                )}
              </div>
            )}

            {/* Step 4: Final Ingestion & Quality Report */}
            {currentStep === 4 && (
              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-bold text-white">Step 5: Ingestion & Quality Verification</h3>
                  <p className="text-xs text-slate-400">
                    Review your clean data foundation before entering the diagnostics dashboard.
                  </p>
                </div>

                {report ? (
                  <ImportReportView report={report} />
                ) : (
                  <div className="p-6 text-center text-xs text-slate-400 border border-white/10 rounded-xl">
                    Data ingestion processed successfully.
                  </div>
                )}

                <div className="flex justify-end pt-4 border-t border-white/10">
                  <button
                    type="button"
                    onClick={() => router.push(`/dashboard?biz=${encodeURIComponent(businessId)}&week=1`)}
                    className="px-6 py-2.5 rounded-xl text-sm font-bold text-white bg-indigo-600 hover:bg-indigo-500 shadow-lg shadow-indigo-600/30 transition-colors"
                  >
                    Proceed to Dashboard →
                  </button>
                </div>
              </div>
            )}
          </IntakeStepper>
        </StateBoundary>
      </div>
    </CatalystShell>
  );
}
