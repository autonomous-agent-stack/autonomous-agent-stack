/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  images: {
    domains: ['api.github.com', 'avatars.githubusercontent.com'],
  },
  experimental: {
    // Optimize for mobile
    optimizeCss: true,
  },
}

module.exports = nextConfig
