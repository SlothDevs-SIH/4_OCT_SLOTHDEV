/**
 * Dev proxy until the gateway (port 8000) is used. The browser always calls same-origin `/api/v1/*`
 * unless NEXT_PUBLIC_API_BASE is set (then these rewrites are unused).
 *
 * Ownership of paths follows contracts/API_CONTRACT.md sections 3 (data_engine) and 4 (decision_engine).
 * Anything not listed as a decision_engine path goes to data_engine.
 */
const DATA = process.env.DATA_ENGINE_ORIGIN || "http://localhost:8001";
const DECISION = process.env.DECISION_ENGINE_ORIGIN || "http://localhost:8002";
const GATEWAY = process.env.GATEWAY_ORIGIN || "";

const decisionPaths = [
  "/api/v1/decision/:path*",
  "/api/v1/intervention-templates",
  "/api/v1/businesses/:id/signals",
  "/api/v1/businesses/:id/recommendations",
  "/api/v1/businesses/:id/recommendations/:path*",
  "/api/v1/businesses/:id/plans",
  "/api/v1/businesses/:id/chat",
  "/api/v1/recommendations/:path*",
  "/api/v1/plans/:path*",
  "/api/v1/tasks/:path*",
];

/** @type {import('next').NextConfig} */
const nextConfig = {
  allowedDevOrigins: ["127.0.0.1"],        // lets a second browser profile (127.0.0.1) test without sharing the session
  async rewrites() {
    if (GATEWAY) return [{ source: "/api/v1/:path*", destination: `${GATEWAY}/api/v1/:path*` }];
    return {
      beforeFiles: [],
      afterFiles: [
        ...decisionPaths.map((source) => ({ source, destination: `${DECISION}${source}` })),
        { source: "/api/v1/:path*", destination: `${DATA}/api/v1/:path*` },
      ],
      fallback: [],
    };
  },
};

export default nextConfig;
