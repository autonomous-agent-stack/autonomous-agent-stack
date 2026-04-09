/** @type {import('next').NextConfig} */
const isStaticExport = process.env.DASHBOARD_STATIC_EXPORT === '1'

const nextConfig = {
  reactStrictMode: true,
  ...(isStaticExport ? { output: 'export' } : {}),
  images: {
    unoptimized: true,
  },
}

module.exports = nextConfig
