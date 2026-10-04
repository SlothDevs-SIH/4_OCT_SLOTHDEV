"use client";

import React from "react";
import { CreateBusinessForm } from "@/lib/api";
import { Product } from "@/lib/types";

export interface InterviewFormProps {
  value: CreateBusinessForm;
  onChange: (value: CreateBusinessForm) => void;
  onSubmit: (e: React.FormEvent) => void;
  busy?: boolean;
  className?: string;
}

export default function InterviewForm({
  value,
  onChange,
  onSubmit,
  busy = false,
  className = "",
}: InterviewFormProps) {
  const handleAddProduct = () => {
    const updated = [
      ...value.products,
      { name: "", category: null, price: 0, unit_cost: null },
    ];
    onChange({ ...value, products: updated });
  };

  const handleUpdateProduct = (index: number, patch: Partial<Product>) => {
    const updated = value.products.map((p, idx) =>
      idx === index ? { ...p, ...patch } : p
    );
    onChange({ ...value, products: updated });
  };

  const handleRemoveProduct = (index: number) => {
    const updated = value.products.filter((_, idx) => idx !== index);
    onChange({ ...value, products: updated });
  };

  return (
    <form onSubmit={onSubmit} className={`space-y-6 ${className}`}>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <label className="flex flex-col gap-1.5 text-xs font-semibold text-slate-300">
          <span>Business Name *</span>
          <input
            type="text"
            required
            value={value.name}
            onChange={(e) => onChange({ ...value, name: e.target.value })}
            placeholder="e.g. Saffron & Sweet Home Bakery"
            className="w-full rounded-xl bg-slate-950/60 border border-white/10 px-3.5 py-2 text-sm text-white focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
          />
        </label>

        <label className="flex flex-col gap-1.5 text-xs font-semibold text-slate-300">
          <span>Category / Kind *</span>
          <input
            type="text"
            required
            value={value.kind || ""}
            onChange={(e) => onChange({ ...value, kind: e.target.value })}
            placeholder="e.g. Artisanal Bakery, Soy Candles, Crochet"
            className="w-full rounded-xl bg-slate-950/60 border border-white/10 px-3.5 py-2 text-sm text-white focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
          />
        </label>
      </div>

      {/* Repeatable Products */}
      <div className="space-y-3 pt-2">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
            Core Products & Margins
          </span>
          <button
            type="button"
            onClick={handleAddProduct}
            className="text-xs font-semibold text-teal-300 hover:text-teal-200 bg-teal-500/10 px-2.5 py-1 rounded-md border border-teal-500/30"
          >
            + Add Product
          </button>
        </div>

        <div className="space-y-2">
          {value.products.map((prod, idx) => (
            <div
              key={idx}
              className="grid grid-cols-1 sm:grid-cols-4 gap-2 p-3 rounded-xl bg-white/[0.02] border border-white/5 items-center"
            >
              <input
                type="text"
                value={prod.name}
                onChange={(e) => handleUpdateProduct(idx, { name: e.target.value })}
                placeholder="Product name"
                className="w-full rounded-lg bg-slate-950/50 border border-white/10 px-2.5 py-1.5 text-xs text-white"
              />
              <input
                type="text"
                value={prod.category || ""}
                onChange={(e) => handleUpdateProduct(idx, { category: e.target.value || null })}
                placeholder="Category"
                className="w-full rounded-lg bg-slate-950/50 border border-white/10 px-2.5 py-1.5 text-xs text-white"
              />
              <input
                type="number"
                value={prod.price || ""}
                onChange={(e) => handleUpdateProduct(idx, { price: Number(e.target.value) })}
                placeholder="Price (₹)"
                className="w-full rounded-lg bg-slate-950/50 border border-white/10 px-2.5 py-1.5 text-xs text-white"
              />
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  value={prod.unit_cost ?? ""}
                  onChange={(e) =>
                    handleUpdateProduct(idx, {
                      unit_cost: e.target.value ? Number(e.target.value) : null,
                    })
                  }
                  placeholder="Unit cost (₹)"
                  className="w-full rounded-lg bg-slate-950/50 border border-white/10 px-2.5 py-1.5 text-xs text-white"
                />
                <button
                  type="button"
                  onClick={() => handleRemoveProduct(idx)}
                  className="p-1.5 text-slate-500 hover:text-rose-400 text-xs rounded"
                  title="Remove product"
                >
                  ✕
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Operational Capacity & Constraints */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">
        <label className="flex flex-col gap-1.5 text-xs font-semibold text-slate-300">
          <span>Weekly Production Hours</span>
          <input
            type="number"
            value={value.weekly_hours}
            onChange={(e) => onChange({ ...value, weekly_hours: Number(e.target.value) })}
            className="w-full rounded-xl bg-slate-950/60 border border-white/10 px-3.5 py-2 text-sm text-white"
          />
        </label>

        <label className="flex flex-col gap-1.5 text-xs font-semibold text-slate-300">
          <span>Weekly Max Orders Capacity</span>
          <input
            type="number"
            value={value.capacity_orders_per_week ?? ""}
            onChange={(e) =>
              onChange({
                ...value,
                capacity_orders_per_week: e.target.value ? Number(e.target.value) : null,
              })
            }
            placeholder="e.g. 50 orders/wk"
            className="w-full rounded-xl bg-slate-950/60 border border-white/10 px-3.5 py-2 text-sm text-white"
          />
        </label>

        <label className="flex flex-col gap-1.5 text-xs font-semibold text-slate-300">
          <span>Weekly Ad Budget (₹)</span>
          <input
            type="number"
            value={value.ad_budget_inr}
            onChange={(e) => onChange({ ...value, ad_budget_inr: Number(e.target.value) })}
            className="w-full rounded-xl bg-slate-950/60 border border-white/10 px-3.5 py-2 text-sm text-white"
          />
        </label>
      </div>

      {/* Goal & Market Feed */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <label className="flex flex-col gap-1.5 text-xs font-semibold text-slate-300">
          <span>Target Goal Statement</span>
          <input
            type="text"
            value={value.goal.statement}
            onChange={(e) =>
              onChange({
                ...value,
                goal: { ...value.goal, statement: e.target.value },
              })
            }
            placeholder="e.g. Reach 20 weekly orders from non-friends"
            className="w-full rounded-xl bg-slate-950/60 border border-white/10 px-3.5 py-2 text-sm text-white"
          />
        </label>

        <label className="flex flex-col gap-1.5 text-xs font-semibold text-slate-300">
          <span>Context / Demand Calendar Feed</span>
          <select
            value={value.context_feed || "india_festivals"}
            onChange={(e) => onChange({ ...value, context_feed: e.target.value })}
            className="w-full rounded-xl bg-slate-950/60 border border-white/10 px-3.5 py-2 text-sm text-white"
          >
            <option value="india_festivals">India Festivals & Wedding Seasons</option>
            <option value="f1_calendar">F1 Grand Prix Race Calendar</option>
          </select>
        </label>
      </div>

      {/* Channels, link, payment */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <label className="flex flex-col gap-1.5 text-xs font-semibold text-slate-300">
          <span>Cities Served</span>
          <input
            type="text"
            value={value.serves_cities?.join(", ") || ""}
            onChange={(e) =>
              onChange({
                ...value,
                serves_cities: e.target.value.split(",").map((c) => c.trim()),
              })
            }
            placeholder="Mumbai, Pune, Thane"
            className="w-full rounded-xl bg-slate-950/60 border border-white/10 px-3.5 py-2 text-sm text-white"
          />
        </label>

        <label className="flex flex-col gap-1.5 text-xs font-semibold text-slate-300">
          <span>Order Link / Catalog URL</span>
          <input
            type="url"
            value={value.order_link || ""}
            onChange={(e) => onChange({ ...value, order_link: e.target.value || null })}
            placeholder="https://wa.me/catalog/..."
            className="w-full rounded-xl bg-slate-950/60 border border-white/10 px-3.5 py-2 text-sm text-white"
          />
        </label>

        <label className="flex flex-col gap-1.5 text-xs font-semibold text-slate-300">
          <span>Accepted Payment Method</span>
          <input
            type="text"
            value={value.payment || ""}
            onChange={(e) => onChange({ ...value, payment: e.target.value || null })}
            placeholder="UPI / GPay, COD, Bank Transfer"
            className="w-full rounded-xl bg-slate-950/60 border border-white/10 px-3.5 py-2 text-sm text-white"
          />
        </label>
      </div>

      <div className="pt-2 flex justify-end">
        <button
          type="submit"
          disabled={busy}
          className="px-6 py-2.5 rounded-xl text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 shadow-md shadow-indigo-600/30 transition-colors focus-visible:outline-2 focus-visible:outline-indigo-400"
        >
          {busy ? "Saving Workspace..." : "Save Workspace Profile"}
        </button>
      </div>
    </form>
  );
}
