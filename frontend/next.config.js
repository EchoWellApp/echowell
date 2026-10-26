// Next.js configuration (TRD 04 FE-043, FE-044; TRD 21 ENV-033).
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  env: {
    NEXT_PUBLIC_GIT_SHA: process.env.COMMIT_REF || process.env.GIT_SHA || "unknown",
  },
};

module.exports = nextConfig;
