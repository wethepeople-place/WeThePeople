import { describe, expect, it } from 'vitest'

import { getOfficialEmbedUrl, getValidatedProvider } from './providers'

describe('Watch provider adapters', () => {
  it.each([
    ['youtube', 'M7lc1UVf-VE', 'https://www.youtube.com/watch?v=M7lc1UVf-VE', 'youtube-nocookie.com/embed/M7lc1UVf-VE'],
    ['tiktok', '6718335390845095173', 'https://www.tiktok.com/@scout2015/video/6718335390845095173', 'tiktok.com/player/v1/6718335390845095173'],
    ['facebook', '1160066519498071', 'https://www.facebook.com/uscensusbureau/videos/1160066519498071/', 'facebook.com/plugins/video.php'],
  ])('builds a supported %s embed from validated record fields', (provider, provider_video_id, canonical_url, expected) => {
    const delivery = { provider, provider_video_id, canonical_url }
    expect(getValidatedProvider(delivery)).toBe(provider)
    expect(getOfficialEmbedUrl(delivery)).toContain(expected)
    expect(getOfficialEmbedUrl(delivery)).toContain('autoplay=1')
  })

  it.each([
    { provider: 'youtube', provider_video_id: '<script>', canonical_url: 'https://www.youtube.com/watch?v=x' },
    { provider: 'tiktok', provider_video_id: '6718335390845095173', canonical_url: 'https://evil.example/video/6718335390845095173' },
    { provider: 'facebook', provider_video_id: '1160066519498071', canonical_url: 'javascript:alert(1)' },
    { provider: 'unknown', provider_video_id: '123456789012345', canonical_url: 'https://example.com/video' },
  ])('fails closed for unsafe or unsupported metadata', (delivery) => {
    expect(getValidatedProvider(delivery)).toBeNull()
    expect(getOfficialEmbedUrl(delivery)).toBeNull()
  })
})
