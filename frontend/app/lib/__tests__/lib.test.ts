import { describe, expect, it, vi, afterEach } from "vitest";
import { ApiError, buildUrl, messageFromBody, request } from "../http";
import { duplicateColumns, missingRequired, toPayload, validateCsvFile, validateOnboarding, type OnboardingForm } from "../validation";
import { deltaTone, formatFact, formatPct } from "../format";

const okForm: OnboardingForm = {
  name: "Asha Tea", business_model: "d2c", category: "D2C", city: "Pune", goalStatement: "Grow repeat purchases", primaryKpi: "repeat_rate",
  horizonDays: "90", weeklyAdBudget: "1000", extraSpend: "0", noSpendIncrease: true, slaHours: "4", weeklyHours: "8", maxMinutesPerDay: "120",
};

afterEach(() => vi.unstubAllGlobals());

describe("http", () => {
  it("builds urls and drops empty query values", () => {
    expect(buildUrl("/x", { a: 1, b: undefined, c: "", d: "z" })).toBe("/api/v1/x?a=1&d=z");
  });
  it("reads the backend error contract", () => {
    expect(messageFromBody({ error: { code: "blocked", message: "nope" } }, "f")).toEqual({ code: "blocked", message: "nope" });
    expect(messageFromBody(null, "fallback")).toEqual({ code: "error", message: "fallback" });
  });
  it("maps HTTP errors to ApiError with status and code", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ error: { code: "business_exists", message: "dup" } }), { status: 409 })));
    await expect(request("/businesses")).rejects.toMatchObject({ kind: "http", status: 409, code: "business_exists", message: "dup" });
  });
  it("maps network failure and timeout", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new TypeError("failed"); }));
    await expect(request("/x")).rejects.toMatchObject({ kind: "network" });
    vi.stubGlobal("fetch", vi.fn(async () => { throw new DOMException("aborted", "AbortError"); }));
    await expect(request("/x")).rejects.toMatchObject({ kind: "timeout" });
  });
  it("flags invalid JSON on success as parse error", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("<html>", { status: 200 })));
    await expect(request("/x")).rejects.toMatchObject({ kind: "parse" });
  });
  it("has friendly 501 and 500 messages", () => {
    expect(new ApiError("http", "x", 501).friendly).toMatch(/not implemented/i);
    expect(new ApiError("http", "boom", 500).friendly).toMatch(/Backend error/);
  });
});

describe("validation", () => {
  it("accepts a valid onboarding form and builds the backend payload", () => {
    expect(validateOnboarding(okForm)).toEqual({});
    const p = toPayload(okForm);
    expect(p.constraints.forbidden_actions).toEqual(["increase_total_ad_spend"]);
    expect(p.capacity).toEqual({ weekly_hours: 8, max_minutes_per_day: 120 });
  });
  it("mirrors backend limits", () => {
    const e = validateOnboarding({ ...okForm, name: "A", goalStatement: "x", horizonDays: "3", slaHours: "0", weeklyHours: "99", maxMinutesPerDay: "1.5", weeklyAdBudget: "-1" });
    expect(Object.keys(e).sort()).toEqual(["goalStatement", "horizonDays", "maxMinutesPerDay", "name", "slaHours", "weeklyAdBudget", "weeklyHours"]);
  });
  it("validates CSV files", () => {
    expect(validateCsvFile(null)).toMatch(/Choose/);
    expect(validateCsvFile(new File(["a"], "x.txt"))).toMatch(/\.csv/);
    expect(validateCsvFile(new File([], "x.csv"))).toMatch(/empty/);
    expect(validateCsvFile(new File(["a,b"], "x.csv"))).toBeNull();
  });
  it("finds missing required and duplicate mappings", () => {
    const up = { suggested_mapping: { order_id: { column: null, confidence: 0, required: true }, discount: { column: null, confidence: 0, required: false } } };
    expect(missingRequired(up, {})).toEqual(["order_id"]);
    expect(missingRequired(up, { order_id: "ID" })).toEqual([]);
    expect(duplicateColumns({ a: "X", b: "X", c: "Y" })).toEqual(["X"]);
  });
});

describe("format", () => {
  it("treats CAC rising as worse and repeat rate rising as better", () => {
    expect(deltaTone("cac", 49)).toBe("bad");
    expect(deltaTone("repeat_rate", 30)).toBe("good");
    expect(deltaTone("cac", 0.1)).toBe("flat");
    expect(deltaTone("cac", null)).toBe("flat");
  });
  it("formats facts", () => {
    expect(formatFact({ kpi: "cac", value: 612, unit: "INR" })).toBe("₹612");
    expect(formatFact({ kpi: "repeat_rate", value: 0.214, unit: "ratio" })).toBe("21.4%");
    expect(formatPct(49.3)).toBe("+49.3%");
    expect(formatPct(null)).toBe("n/a");
  });
});
