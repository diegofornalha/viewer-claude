/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  experimental: {
    outputFileTracingRoot: undefined
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://claude-viewer-backend:3041/api/:path*',
      },
    ]
  }
}

module.exports = nextConfig