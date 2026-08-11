export type WatchProvider = 'youtube' | 'tiktok' | 'facebook'

export type ProviderDelivery = {
  provider: string | null
  provider_video_id: string | null
  canonical_url: string
}

const PROVIDER_IDS: Record<WatchProvider, RegExp> = {
  youtube: /^[A-Za-z0-9_-]{11}$/,
  tiktok: /^\d{15,25}$/,
  facebook: /^\d{5,25}$/,
}

const CANONICAL_HOSTS: Record<WatchProvider, Set<string>> = {
  youtube: new Set(['youtube.com', 'www.youtube.com', 'youtu.be']),
  tiktok: new Set(['tiktok.com', 'www.tiktok.com']),
  facebook: new Set(['facebook.com', 'www.facebook.com', 'fb.watch']),
}

export function getValidatedProvider(delivery: ProviderDelivery): WatchProvider | null {
  const provider = delivery.provider?.toLowerCase()
  if (provider !== 'youtube' && provider !== 'tiktok' && provider !== 'facebook') return null
  if (!delivery.provider_video_id || !PROVIDER_IDS[provider].test(delivery.provider_video_id)) return null
  try {
    const url = new URL(delivery.canonical_url)
    if (url.protocol !== 'https:' || !CANONICAL_HOSTS[provider].has(url.hostname.toLowerCase())) return null
  } catch {
    return null
  }
  return provider
}

export function getOfficialEmbedUrl(delivery: ProviderDelivery): string | null {
  const provider = getValidatedProvider(delivery)
  if (!provider) return null
  const id = delivery.provider_video_id as string
  if (provider === 'youtube') {
    return `https://www.youtube-nocookie.com/embed/${id}?autoplay=1&playsinline=1&controls=1&cc_load_policy=1`
  }
  if (provider === 'tiktok') {
    return `https://www.tiktok.com/player/v1/${id}?autoplay=1&controls=1&progress_bar=1&play_button=1&volume_control=1&fullscreen_button=1`
  }
  return `https://www.facebook.com/plugins/video.php?href=${encodeURIComponent(delivery.canonical_url)}&show_text=false&autoplay=true`
}

export function getProviderPrivacyUrl(provider: WatchProvider): string {
  if (provider === 'youtube') return 'https://policies.google.com/privacy'
  if (provider === 'tiktok') return 'https://www.tiktok.com/legal/page/us/privacy-policy/en'
  return 'https://www.facebook.com/privacy/policy/'
}

export function getProviderLabel(provider: WatchProvider): string {
  if (provider === 'youtube') return 'YouTube'
  if (provider === 'tiktok') return 'TikTok'
  return 'Facebook'
}
