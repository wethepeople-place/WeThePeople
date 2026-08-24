import { mkdir, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const frontendRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const repositoryRoot = path.resolve(frontendRoot, '..')
const distRoot = path.join(frontendRoot, 'dist')
const indexHtml = await readFile(path.join(distRoot, 'index.html'), 'utf8')
const fixture = JSON.parse(await readFile(path.join(repositoryRoot, 'data', 'watch_housing_rent.json'), 'utf8'))
const agenda = JSON.parse(await readFile(path.join(repositoryRoot, 'data', 'agenda_2026_apnorc.json'), 'utf8'))

const escapeAttribute = (value) => String(value)
  .replaceAll('&', '&amp;')
  .replaceAll('"', '&quot;')
  .replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;')

async function writeRoute(segments, html) {
  const directory = path.join(distRoot, ...segments)
  await mkdir(directory, { recursive: true })
  await writeFile(path.join(directory, 'index.html'), html, 'utf8')
}

function withSocialMetadata(html, { canonicalUrl, title, description }) {
  return html
    .replace(/<title>.*?<\/title>/, `<title>${escapeAttribute(title)}</title>`)
    .replace(/<meta property="og:url" content="[^"]*" \/>/, `<meta property="og:url" content="${escapeAttribute(canonicalUrl)}" />`)
    .replace(/<meta property="og:title" content="[^"]*" \/>/, `<meta property="og:title" content="${escapeAttribute(title)}" />`)
    .replace(/<meta property="og:description" content="[^"]*" \/>/, `<meta property="og:description" content="${escapeAttribute(description)}" />`)
}

await writeRoute(['watch'], indexHtml)
await writeRoute(['politics', 'find-rep'], indexHtml)
await writeRoute(['act'], indexHtml)
await writeRoute(['act', 'moderation'], indexHtml)
await writeRoute(['discuss'], withSocialMetadata(indexHtml, {
  canonicalUrl: 'https://app.wethepeople.place/discuss',
  title: 'Civic Discussions | WeThePeople.place',
  description: 'Evidence-linked civic conversations, newest first, with private bookmarks and transparent moderation.',
}))
await writeRoute(['elections'], indexHtml)
await writeRoute(['forecasts'], withSocialMetadata(indexHtml, {
  canonicalUrl: 'https://app.wethepeople.place/forecasts',
  title: 'Community Forecasts | WeThePeople.place',
  description: 'Private, non-monetary civic forecasts grounded in official election and legislative sources.',
}))

for (const issue of agenda.items ?? []) {
  if (!/^[a-z0-9-]{1,100}$/.test(issue.slug)) throw new Error(`Unsafe Issue route identity: ${issue.slug}`)
  await writeRoute(['issues', issue.slug], withSocialMetadata(indexHtml, {
    canonicalUrl: `https://app.wethepeople.place/issues/${issue.slug}`,
    title: `${issue.title} Issue Hub | WeThePeople.place`,
    description: issue.summary,
  }))
}

for (const video of fixture.videos ?? []) {
  if (!/^[A-Za-z0-9_-]{1,100}$/.test(video.video_id)) throw new Error(`Unsafe Watch route identity: ${video.video_id}`)
  const canonicalUrl = `https://app.wethepeople.place/watch/${video.video_id}`
  const title = `${video.caption} | WeThePeople.place`
  const description = `${video.creator_label} · Source: ${video.source.publisher}`
  const html = withSocialMetadata(indexHtml, { canonicalUrl, title, description })
  await writeRoute(['watch', video.video_id], html)
}
