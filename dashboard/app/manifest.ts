import type { MetadataRoute } from 'next'

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: 'AAS Study Dashboard',
    short_name: 'AAS Study',
    description: 'iPad study dashboard for GoodNotes and MarginNote4 workflows',
    start_url: '/study',
    display: 'standalone',
    background_color: '#020617',
    theme_color: '#0f172a',
    icons: [
      {
        src: '/icon.svg',
        sizes: 'any',
        type: 'image/svg+xml',
        purpose: 'any',
      },
    ],
  }
}
