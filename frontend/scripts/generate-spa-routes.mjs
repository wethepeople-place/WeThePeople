import { mkdir, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const frontendRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const repositoryRoot = path.resolve(frontendRoot, '..')
const distRoot = path.join(frontendRoot, 'dist')
const indexHtml = await readFile(path.join(distRoot, 'index.html'), 'utf8')
const fixture = JSON.parse(await readFile(path.join(repositoryRoot, 'data', 'watch_housing_rent.json'), 'utf8'))

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

await writeRoute(['watch'], indexHtml)
await writeRoute(['saved'], indexHtml)
await writeRoute(['politics', 'find-rep'], indexHtml)

for (const video of fixture.videos ?? []) {
  if (!/^[A-Za-z0-9_-]{1,100}$/.test(video.video_id)) throw new Error(`Unsafe Watch route identity: ${video.video_id}`)
  const canonicalUrl = `https://app.wethepeople.place/watch/${video.video_id}`
  const title = `${video.caption} | WeThePeople.place`
  const description = `${video.creator_label} · Source: ${video.source.publisher}`
  const html = indexHtml
    .replace(/<title>.*?<\/title>/, `<title>${escapeAttribute(title)}</title>`)
    .replace(/<meta property="og:url" content="[^"]*" \/>/, `<meta property="og:url" content="${escapeAttribute(canonicalUrl)}" />`)
    .replace(/<meta property="og:title" content="[^"]*" \/>/, `<meta property="og:title" content="${escapeAttribute(title)}" />`)
    .replace(/<meta property="og:description" content="[^"]*" \/>/, `<meta property="og:description" content="${escapeAttribute(description)}" />`)
  await writeRoute(['watch', video.video_id], html)
}
