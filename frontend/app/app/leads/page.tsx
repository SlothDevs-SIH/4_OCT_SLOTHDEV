"use client";

import React, { useState, useEffect } from "react";
import { useBusiness } from "@/lib/BusinessContext";
import { getLeadList, tagLead } from "@/lib/api";
import { LeadList, Relationship } from "@/lib/types";
import CatalystShell from "@/components/catalyst/CatalystShell";
import LeadListView from "@/components/catalyst/LeadListView";
import StateBoundary from "@/components/catalyst/StateBoundary";

export default function LeadsPage() {
  const { businessId, week } = useBusiness();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [leadList, setLeadList] = useState<LeadList | null>(null);

  const fetchLeads = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getLeadList(businessId, week);
      setLeadList(data);
    } catch (err: any) {
      setError(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLeads();
  }, [businessId, week]);

  const handleTagRelationship = async (leadId: string, rel: Relationship) => {
    try {
      await tagLead(leadId, { relationship: rel });
      // Update local state
      setLeadList((prev) => {
        if (!prev) return prev;
        const updateLead = (l: any) =>
          l.lead_id === leadId ? { ...l, relationship: rel } : l;
        return {
          ...prev,
          hot: prev.hot.map(updateLead),
          warm: prev.warm.map(updateLead),
          cold: prev.cold.map(updateLead),
          disqualified: prev.disqualified.map(updateLead),
        };
      });
    } catch (err: any) {
      setError(err);
    }
  };

  return (
    <CatalystShell>
      <div className="space-y-8">
        <div>
          <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight">
            Customer Inquiries & Ranked Leads
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Intent signals extracted from WhatsApp and Instagram threads. Tag friend vs stranger to refine acquisition metrics.
          </p>
        </div>

        <StateBoundary loading={loading} error={error} onRetry={fetchLeads}>
          {leadList && (
            <LeadListView
              leadList={leadList}
              onTagRelationship={handleTagRelationship}
            />
          )}
        </StateBoundary>
      </div>
    </CatalystShell>
  );
}
