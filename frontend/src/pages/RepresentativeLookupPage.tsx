import React, { useState, useEffect, useRef } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { MapPin, Search, Users, AlertCircle, ArrowLeft, ArrowRight, Heart, ExternalLink, FileText, Vote as VoteIcon, ChartNoAxesCombined, Landmark } from 'lucide-react';
import { motion } from 'framer-motion';
import { getApiBaseUrl } from '../api/client';
import { fetchPromises, type PromiseItem } from '../api/civic';
import { PoliticsSectorHeader } from '../components/SectorHeader';
import RepresentativeActPanel from '../components/RepresentativeActPanel';
import useEmbeddedFrameHeight from '../hooks/useEmbeddedFrameHeight';

// ── Types ──

interface Representative {
  person_id: string;
  display_name: string;
  party: string;
  chamber: string;
  state: string;
  district: string | null;
  photo_url: string | null;
  bioguide_id: string | null;
  is_active: boolean;
  profile_available?: boolean;
  official_url?: string | null;
  votes: Array<{
    question: string | null;
    vote_date: string | null;
    result: string | null;
    position: string;
    related_bill: string | null;
    source_url: string | null;
    source_name: string;
  }>;
  bills: Array<{
    bill_id: string;
    role: string;
    title: string;
    policy_area: string | null;
    status: string | null;
    latest_action: string | null;
    latest_action_date: string | null;
    source_url: string;
    source_name: string;
  }>;
  election_forecasts: Array<{
    id: number;
    question: string;
    candidate_option: { key: string; label: string; party?: string | null };
    closes_at: string | null;
    source_url: string;
    source_name: string;
    forecast_url: string;
  }>;
  promises: PromiseItem[];
  committees: Array<{ committee_name: string; role: string }>;
  trades: unknown[];
  donors: unknown[];
  anomalies: unknown[];
  sources: Array<{ name: string; url: string }>;
}

interface RepLookupResponse {
  zip: string;
  total: number;
  representatives: Representative[];
}

// ── Party tokens ──
// Hex pair enables opacity combinations like `${hex}20`/`${hex}33`/`${hex}10`
const PARTY_HEX: Record<string, string> = {
  D: '#4A7FDE',
  R: '#E05555',
  I: '#B06FD8',
};
const PARTY_TOKEN: Record<string, string> = {
  D: 'var(--color-dem)',
  R: 'var(--color-rep)',
  I: 'var(--color-ind)',
};

function partyHex(party: string): string {
  return PARTY_HEX[party?.charAt(0)] || '#7F8590';
}

function partyToken(party: string): string {
  return PARTY_TOKEN[party?.charAt(0)] || 'var(--color-text-2)';
}

function partyLabel(party: string): string {
  const map: Record<string, string> = { D: 'Democrat', R: 'Republican', I: 'Independent' };
  return map[party?.charAt(0)] || party;
}

function chamberLabel(chamber: string): string {
  if (!chamber) return '';
  const c = chamber.toLowerCase();
  if (c.includes('senate') || c === 'upper') return 'Senate';
  return 'House';
}

function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .map((w) => w[0])
    .slice(0, 2)
    .join('')
    .toUpperCase();
}

function officialPortraitUrl(rep: Representative): string | null {
  if (rep.photo_url) return rep.photo_url;
  const bioguideId = (rep.bioguide_id || '').trim().toUpperCase();
  if (!/^[A-Z]\d{6}$/.test(bioguideId)) return null;
  return `https://unitedstates.github.io/images/congress/225x275/${bioguideId}.jpg`;
}

function RepresentativePortrait({ rep, size = 56, radius = '50%' }: { rep: Representative; size?: number; radius?: number | string }) {
  const portraitUrl = officialPortraitUrl(rep);
  const sourceUrl = 'https://github.com/unitedstates/images#public-domain';
  const creditWidth = portraitUrl ? Math.max(size, 96) : size;

  return <div style={{ width: creditWidth, flexShrink: 0, textAlign: 'center' }}>
    <div style={{ position: 'relative', width: size, height: size, margin: '0 auto', borderRadius: radius, overflow: 'hidden', display: 'grid', placeItems: 'center', background: `${partyHex(rep.party)}1F`, border: '2px solid var(--color-border-hover)', color: 'var(--color-text-1)', fontFamily: "'Inter', sans-serif", fontSize: Math.max(13, Math.round(size * .29)), fontWeight: 750 }}>
      {initials(rep.display_name)}
      {portraitUrl && <img
        src={portraitUrl}
        alt={`Official portrait of ${rep.display_name}`}
        loading="lazy"
        onError={(event) => { event.currentTarget.style.display = 'none'; }}
        style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'center top' }}
      />}
    </div>
    {portraitUrl && <a href={sourceUrl} target="_blank" rel="noreferrer" style={{ display: 'inline-block', marginTop: 4, color: '#9eabbc', fontSize: 9, lineHeight: 1.2, textDecoration: 'none', whiteSpace: 'nowrap' }}>
      Public domain · GPO
    </a>}
  </div>;
}

// ── Page ──

export default function RepresentativeLookupPage() {
  const [searchParams] = useSearchParams();
  const isEmbedded = searchParams.get('embed') === '1';
  const issueSlug = searchParams.get('issue')?.trim() || '';
  const [zip, setZip] = useState('');
  const [submittedZip, setSubmittedZip] = useState('');
  const [reps, setReps] = useState<Representative[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dataUnavailable, setDataUnavailable] = useState(false);
  const [resolvedState, setResolvedState] = useState('');
  const [districtResolutionRequired, setDistrictResolutionRequired] = useState(false);
  const [generatedAt, setGeneratedAt] = useState('');
  const [searched, setSearched] = useState(false);
  const pageRef = useRef<HTMLDivElement | null>(null);

  useEmbeddedFrameHeight(isEmbedded, 'representatives', pageRef);

  const doSearch = async (zipCode: string) => {
    const cleaned = zipCode.trim().replace(/\D/g, '').slice(0, 5);
    if (cleaned.length < 5) return;

    setZip(cleaned);
    setLoading(true);
    setError(null);
    setDataUnavailable(false);
    setResolvedState('');
    setDistrictResolutionRequired(false);
    setSearched(true);
    setSubmittedZip(cleaned);

    try {
      // GET /lookup/{zip} returns the district-specific House rep + the
      // two senators for that ZIP (3 reps total). The previous
      // implementation called /representatives?zip= which falls back to
      // *all* members of the state when district resolution isn't done
      // — that produced the "15 reps for MI-2" bug. Now we hit the
      // district-aware endpoint and adapt the shape.
      const res = await fetch(
        `${getApiBaseUrl()}/lookup/${encodeURIComponent(cleaned)}`,
        { cache: 'no-store' },
      );
      if (res.status === 404) {
        setDataUnavailable(true);
        setReps([]);
        return;
      }
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const rawReps: any[] = Array.isArray(data?.representatives) ? data.representatives : [];
      setResolvedState(String(data?.state || ''));
      setGeneratedAt(String(data?.generated_at || ''));
      setDistrictResolutionRequired(data?.district_resolution_required === true);
      const adapted: Representative[] = rawReps.map((r) => ({
        person_id: String(r.person_id || ''),
        // /lookup returns `name`; the rest of the page expects `display_name`
        display_name: String(r.display_name || r.name || ''),
        party: String(r.party || ''),
        chamber: String(r.chamber || ''),
        state: String(r.state || data?.state || ''),
        district: r.district ?? null,
        photo_url: r.photo_url ?? null,
        bioguide_id: r.bioguide_id ? String(r.bioguide_id).toUpperCase() : null,
        is_active: r.is_active !== false,
        profile_available: r.profile_available !== false,
        official_url: r.official_url ?? null,
        votes: Array.isArray(r.votes) ? r.votes : [],
        bills: Array.isArray(r.bills) ? r.bills : [],
        election_forecasts: Array.isArray(r.election_forecasts) ? r.election_forecasts : [],
        promises: [],
        committees: Array.isArray(r.committees) ? r.committees : [],
        trades: Array.isArray(r.trades) ? r.trades : [],
        donors: Array.isArray(r.donors) ? r.donors : [],
        anomalies: Array.isArray(r.anomalies) ? r.anomalies : [],
        sources: Array.isArray(r.sources) ? r.sources : [],
      }));
      setReps(adapted);
      void Promise.all(adapted.map(async (rep) => {
        try {
          const result = await fetchPromises({ person_id: rep.person_id, limit: 3, sort: 'newest' });
          return { personId: rep.person_id, promises: Array.isArray(result.items) ? result.items : [] };
        } catch {
          return { personId: rep.person_id, promises: [] as PromiseItem[] };
        }
      })).then((promiseResults) => {
        const byPerson = new Map(promiseResults.map((item) => [item.personId, item.promises]));
        setReps((current) => current.map((rep) => byPerson.has(rep.person_id) ? { ...rep, promises: byPerson.get(rep.person_id) || [] } : rep));
      });
      setDataUnavailable(adapted.length === 0);
    } catch (err) {
      console.warn('[RepresentativeLookupPage] zip lookup failed:', err);
      const detail = err instanceof Error ? err.message : '';
      setError(
        detail
          ? `Unable to load data (${detail}). Please try again.`
          : 'Unable to load data. Please try again.',
      );
      setReps([]);
    } finally {
      setLoading(false);
    }
  };

  // Auto-search if zip is passed in URL (from landing page)
  useEffect(() => {
    const urlZip = searchParams.get('zip');
    if (urlZip && urlZip.replace(/\D/g, '').length === 5) {
      doSearch(urlZip);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // In the embedded ACT flow, reuse the ZIP entered in Step 1 and load
  // representatives immediately so the user never has to enter it twice.
  useEffect(() => {
    if (!isEmbedded) return;
    const receiveZip = (event: MessageEvent) => {
      if (event.origin !== window.location.origin || event.data?.type !== 'wtp:act-zip') return;
      const sharedZip = String(event.data.zip || '').replace(/\D/g, '').slice(0, 5);
      if (sharedZip.length === 5) void doSearch(sharedZip);
    };
    window.addEventListener('message', receiveZip);
    return () => window.removeEventListener('message', receiveZip);
    // doSearch uses only component state setters and the current API base.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isEmbedded]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    doSearch(zip);
  };

  const isValidZip = zip.trim().replace(/\D/g, '').length >= 5;

  return (
    <div
      ref={pageRef}
      style={{
        minHeight: isEmbedded ? undefined : '100vh',
        background: 'var(--color-bg)',
        color: 'var(--color-text-1)',
      }}
    >
      <div
        style={{
          maxWidth: 1400,
          margin: '0 auto',
          padding: isEmbedded ? '30px 24px 48px' : '40px 24px 64px',
        }}
      >
        {!isEmbedded && <motion.nav
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          style={{ marginBottom: 40 }}
        >
          <PoliticsSectorHeader />
        </motion.nav>}

        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1 }}
          style={{ marginBottom: isEmbedded ? 24 : 36 }}
        >
          <p
            style={{
              fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
              fontSize: 11,
              fontWeight: 600,
              letterSpacing: '0.3em',
              textTransform: 'uppercase',
              color: 'var(--color-text-3)',
              marginBottom: 10,
            }}
          >
            Find your rep
          </p>
          <h1
            style={{
              fontFamily: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
              fontWeight: 700,
              letterSpacing: '-0.045em',
              fontSize: isEmbedded ? 'clamp(32px, 5vw, 44px)' : 'clamp(36px, 5vw, 52px)',
              lineHeight: 1.05,
              color: 'var(--color-text-1)',
              marginBottom: 12,
            }}
          >
            Who represents you?
          </h1>
          <p
            style={{
              fontFamily: "'Inter', sans-serif",
              fontSize: 15,
              color: 'var(--color-text-2)',
              lineHeight: 1.6,
              maxWidth: 640,
            }}
          >
            Enter your zip code to find your congressional representatives. See their voting records, legislative activity, and financial data.
          </p>
          {issueSlug && (
            <p style={{ marginTop: 12, fontFamily: "'Inter', sans-serif", fontSize: 13, color: 'var(--color-text-2)' }}>
              Looking up representatives for this issue journey.{' '}
              <Link to={`/issues/${encodeURIComponent(issueSlug)}`} style={{ color: 'var(--color-accent-text)' }}>
                Return to official evidence
              </Link>
            </p>
          )}
        </motion.div>

        {/* Search form */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          style={{ marginBottom: isEmbedded ? 28 : 36 }}
        >
          <form
            onSubmit={handleSubmit}
            style={{ display: 'flex', gap: 12, maxWidth: 520, flexWrap: 'wrap' }}
          >
            <div style={{ position: 'relative', flex: 1, minWidth: 260 }}>
              <MapPin
                size={16}
                style={{
                  position: 'absolute',
                  left: 16,
                  top: '50%',
                  transform: 'translateY(-50%)',
                  color: 'var(--color-text-3)',
                  pointerEvents: 'none',
                }}
              />
              <input
                type="text"
                value={zip}
                onChange={(e) => setZip(e.target.value)}
                placeholder="Enter your zip code (e.g. 90210)"
                maxLength={10}
                style={{
                  width: '100%',
                  borderRadius: 12,
                  border: '1px solid var(--color-border)',
                  background: '#171a1f',
                  padding: '13px 16px 13px 44px',
                  fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
                  fontSize: 17,
                  letterSpacing: '0.08em',
                  color: 'var(--color-text-1)',
                  outline: 'none',
                  transition: 'border-color 150ms',
                }}
                onFocus={(e) => { e.currentTarget.style.borderColor = 'var(--color-accent)'; }}
                onBlur={(e) => { e.currentTarget.style.borderColor = 'var(--color-border)'; }}
              />
            </div>
            <button
              type="submit"
              disabled={!isValidZip || loading}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 8,
                borderRadius: 12,
                background: '#292d33',
                color: '#f4f6f8',
                fontFamily: "'Inter', sans-serif",
                fontSize: 13,
                fontWeight: 700,
                letterSpacing: '-0.01em',
                padding: '13px 24px',
                border: 'none',
                cursor: !isValidZip || loading ? 'not-allowed' : 'pointer',
                opacity: !isValidZip || loading ? 0.4 : 1,
                transition: 'opacity 150ms',
              }}
            >
              <Search size={15} />
              Look up
            </button>
          </form>
        </motion.div>

        {/* Loading */}
        {loading && (
          <div style={{ display: 'flex', justifyContent: 'center', padding: '60px 0' }}>
            <div
              style={{
                width: 28,
                height: 28,
                borderRadius: '50%',
                border: '2px solid var(--color-accent)',
                borderTopColor: 'transparent',
                animation: 'spin 1s linear infinite',
              }}
            />
          </div>
        )}

        {/* Error state */}
        {!loading && searched && error && !dataUnavailable && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            style={{
              borderRadius: 12,
              border: '1px solid rgba(230,57,70,0.25)',
              background: 'rgba(230,57,70,0.08)',
              padding: '40px 24px',
              textAlign: 'center',
            }}
          >
            <AlertCircle size={36} style={{ color: 'rgba(230,57,70,0.5)', margin: '0 auto 14px' }} />
            <p
              style={{
                fontFamily: "'Inter', sans-serif",
                fontSize: 14,
                color: 'var(--color-red)',
              }}
            >
              {error}
            </p>
          </motion.div>
        )}

        {/* Data unavailable / coming soon */}
        {!loading && searched && dataUnavailable && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            style={{
              borderRadius: 12,
              border: '1px solid var(--color-border)',
              background: 'var(--color-surface)',
              padding: '56px 24px',
              textAlign: 'center',
            }}
          >
            <MapPin size={44} style={{ color: 'var(--color-dem)', opacity: 0.3, margin: '0 auto 16px' }} />
            <h2
              style={{
                fontFamily: "'Playfair Display', Georgia, serif",
                fontStyle: 'italic',
                fontWeight: 900,
                fontSize: 'clamp(24px, 3vw, 32px)',
                color: 'var(--color-text-1)',
                marginBottom: 10,
              }}
            >
              Representative data is not yet available here
            </h2>
            <p
              style={{
                maxWidth: 440,
                margin: '0 auto',
                fontFamily: "'Inter', sans-serif",
                fontSize: 14,
                color: 'var(--color-text-2)',
                lineHeight: 1.6,
              }}
            >
              Zip code {submittedZip} resolves to {resolvedState || 'a U.S. state'}, but WeThePeople does not yet have current representatives for that state. Use the official congressional lookups below rather than changing a valid ZIP code.
            </p>
            <div style={{ marginTop: 28, display: 'flex', justifyContent: 'center', gap: 10, flexWrap: 'wrap' }}>
              <a
                href={`https://ziplook.house.gov/htbin/findrep_house?ZIP=${encodeURIComponent(submittedZip)}`}
                target="_blank"
                rel="noreferrer"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 8,
                  borderRadius: 10,
                  background: 'var(--color-accent)',
                  color: '#07090C',
                  fontFamily: "'Inter', sans-serif",
                  fontSize: 13,
                  fontWeight: 700,
                  textTransform: 'uppercase',
                  letterSpacing: '0.06em',
                  padding: '10px 18px',
                  textDecoration: 'none',
                }}
              >
                <Users size={14} />
                Official House lookup
              </a>
              <a
                href={`https://www.senate.gov/senators/senators-contact.htm${resolvedState ? `?State=${encodeURIComponent(resolvedState)}` : ''}`}
                target="_blank"
                rel="noreferrer"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 8,
                  borderRadius: 10,
                  border: '1px solid var(--color-border-hover)',
                  background: 'var(--color-surface-2)',
                  color: 'var(--color-text-1)',
                  fontFamily: "'Inter', sans-serif",
                  fontSize: 13,
                  fontWeight: 500,
                  padding: '10px 18px',
                  textDecoration: 'none',
                }}
              >
                Official Senate lookup
              </a>
            </div>
          </motion.div>
        )}

        {/* No results */}
        {!loading && searched && !dataUnavailable && reps.length === 0 && !error && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            style={{
              borderRadius: 12,
              border: '1px solid var(--color-border)',
              background: 'var(--color-surface)',
              padding: '56px 24px',
              textAlign: 'center',
            }}
          >
            <AlertCircle size={36} style={{ color: 'var(--color-text-3)', margin: '0 auto 14px' }} />
            <p style={{ fontFamily: "'Inter', sans-serif", fontSize: 14, color: 'var(--color-text-2)' }}>
              No representatives found for zip code {submittedZip}.
            </p>
            <p
              style={{
                marginTop: 4,
                fontFamily: "'Inter', sans-serif",
                fontSize: 12,
                color: 'var(--color-text-3)',
              }}
            >
              Please check the zip code and try again.
            </p>
          </motion.div>
        )}

        {/* Results */}
        {!loading && reps.length > 0 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5 }}
          >
            <p
              style={{
                marginBottom: 10,
                fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
                fontSize: 11,
                letterSpacing: '0.04em',
                color: 'var(--color-text-3)',
                textTransform: 'uppercase',
              }}
            >
              {reps.length} representative{reps.length !== 1 ? 's' : ''} for {submittedZip}
            </p>

            {/* State-level fallback banner — only render when the
                /lookup/{zip} endpoint couldn't resolve to a single
                House district and instead returned the full state
                delegation. The district-aware path returns 3 reps
                (1 House + 2 senators); anything more is a fallback. */}
            {districtResolutionRequired && (
              <div
                style={{
                  marginBottom: 16,
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: 10,
                  borderRadius: 10,
                  border: '1px solid var(--color-border)',
                  background: 'var(--color-accent-dim)',
                  padding: '12px 16px',
                }}
              >
                <AlertCircle size={15} style={{ marginTop: 2, color: 'var(--color-accent-text)', flexShrink: 0 }} />
                <p style={{ fontFamily: "'Inter', sans-serif", fontSize: 12, color: 'var(--color-text-2)', lineHeight: 1.55 }}>
                  <span style={{ fontWeight: 600, color: 'var(--color-text-1)' }}>House address needed</span> — This ZIP crosses House district boundaries. Your two senators are shown below.{' '}
                  <a
                    href={`https://ziplook.house.gov/htbin/findrep_house?ZIP=${encodeURIComponent(submittedZip)}`}
                    target="_blank"
                    rel="noreferrer"
                    style={{ color: 'var(--color-accent-text)', fontWeight: 600 }}
                  >
                    Enter your street address in the official House lookup
                  </a>{' '}
                  to identify your House representative.
                </p>
              </div>
            )}

            {reps.length > 3 && (
              <div
                style={{
                  marginBottom: 16,
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: 10,
                  borderRadius: 10,
                  border: '1px solid var(--color-border)',
                  background: 'var(--color-accent-dim)',
                  padding: '12px 16px',
                }}
              >
                <AlertCircle size={15} style={{ marginTop: 2, color: 'var(--color-accent-text)', flexShrink: 0 }} />
                <p
                  style={{
                    fontFamily: "'Inter', sans-serif",
                    fontSize: 12,
                    color: 'var(--color-text-2)',
                    lineHeight: 1.55,
                  }}
                >
                  <span style={{ fontWeight: 600, color: 'var(--color-text-1)' }}>State-level lookup</span> — We couldn't resolve this ZIP to a single House district, so we're showing every member of the state delegation. Your specific House rep may not be in this list.
                </p>
              </div>
            )}

            {/* State legislature link */}
            {reps.length > 0 && reps[0].state && (
              <div
                style={{
                  marginBottom: 16,
                  borderRadius: 12,
                  border: '1px solid var(--color-border)',
                  background: 'var(--color-surface)',
                  padding: 16,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: 12,
                  flexWrap: 'wrap',
                }}
              >
                <div>
                  <p
                    style={{
                      fontFamily: "'Inter', sans-serif",
                      fontSize: 14,
                      fontWeight: 600,
                      color: 'var(--color-text-1)',
                    }}
                  >
                    Explore {reps[0].state} state legislature
                  </p>
                  <p
                    style={{
                      marginTop: 2,
                      fontFamily: "'Inter', sans-serif",
                      fontSize: 12,
                      color: 'var(--color-text-3)',
                    }}
                  >
                    Browse state-level legislators and bills
                  </p>
                </div>
                <Link
                  to={`/politics/states/${reps[0].state.toLowerCase()}`}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 6,
                    borderRadius: 10,
                    background: 'var(--color-accent-dim)',
                    border: '1px solid var(--color-border)',
                    color: 'var(--color-accent-text)',
                    fontFamily: "'Inter', sans-serif",
                    fontSize: 12,
                    fontWeight: 600,
                    padding: '8px 14px',
                    textDecoration: 'none',
                  }}
                >
                  <MapPin size={14} />
                  State data
                </Link>
              </div>
            )}

            <nav aria-label="Representative action steps" className="mb-4 overflow-x-auto rounded-xl border border-white/[0.07] bg-white/[0.025] px-3 py-3 sm:px-4">
              <ol className="grid min-w-[620px] grid-cols-[1fr_auto_1fr_auto_1fr] items-center gap-3">
                <li className="flex items-center gap-3">
                  <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-slate-200 text-xs font-black text-slate-950">1</span>
                  <span><span className="block text-[9px] font-bold uppercase tracking-[0.18em] text-slate-500">Choose</span><span className="block text-sm font-semibold text-slate-200">A representative</span></span>
                </li>
                <ArrowRight className="h-5 w-5 text-slate-600" aria-hidden="true" />
                <li className="flex items-center gap-3">
                  <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full border border-white/10 bg-white/[0.05] text-xs font-black text-slate-300">2</span>
                  <span><span className="block text-[9px] font-bold uppercase tracking-[0.18em] text-slate-500">Review</span><span className="block text-sm font-semibold text-slate-200">Their public record</span></span>
                </li>
                <ArrowRight className="h-5 w-5 text-slate-600" aria-hidden="true" />
                <li className="flex items-center gap-3">
                  <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full border border-white/10 bg-white/[0.05] text-xs font-black text-slate-300">3</span>
                  <span><span className="block text-[9px] font-bold uppercase tracking-[0.18em] text-slate-500">Then</span><span className="block text-sm font-semibold text-slate-200">Contact the office</span></span>
                </li>
              </ol>
            </nav>

            <div
              id="representative-results-cards"
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
                gap: 14,
              }}
            >
              {reps.map((rep, idx) => (
                <motion.div
                  key={rep.person_id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3, delay: idx * 0.06 }}
                >
                  <RepCard rep={rep} issueSlug={issueSlug} />
                </motion.div>
              ))}
            </div>

            <section style={{ marginTop: 22 }} aria-labelledby="connected-records-heading">
              <div style={{ marginBottom: 12, display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap' }}>
                <div>
                  <p style={{ fontFamily: "'JetBrains Mono', 'Fira Code', monospace", fontSize: 12, fontWeight: 700, letterSpacing: '.16em', textTransform: 'uppercase', color: '#aeb8c6' }}>
                    Connected public record
                  </p>
                  <h2 id="connected-records-heading" style={{ marginTop: 6, fontFamily: "'Inter', sans-serif", fontSize: 24, fontWeight: 780, color: '#f4f7fb' }}>
                    What they did—and what comes next
                  </h2>
                </div>
                <p style={{ maxWidth: 560, fontFamily: "'Inter', sans-serif", fontSize: 15, lineHeight: 1.6, color: '#b9c2cf' }}>
                  Votes, bills, forecasts, and oversight data are joined to the same verified person record used by ACT.
                </p>
              </div>
              <div style={{ display: 'grid', gap: 14 }}>
                {reps.map((rep) => <ConnectedRepresentativeRecord key={`record-${rep.person_id}`} rep={rep} />)}
              </div>
              {generatedAt && <p style={{ marginTop: 10, textAlign: 'right', fontFamily: "'JetBrains Mono', monospace", fontSize: 9, color: 'var(--color-text-3)' }}>
                Record assembled {new Date(generatedAt).toLocaleString()}
              </p>}
            </section>
          </motion.div>
        )}

        {!isEmbedded && <div
          style={{
            marginTop: 48,
            borderRadius: 16,
            border: '1px solid var(--color-border)',
            background: 'var(--color-surface)',
            padding: 24,
          }}
        >
          <h2 style={{ fontFamily: "'Inter', sans-serif", fontSize: 22, fontWeight: 800, margin: 0 }}>
            Want to do both?
          </h2>
          <p style={{ fontFamily: "'Inter', sans-serif", fontSize: 14, lineHeight: 1.6, color: 'var(--color-text-2)', margin: '8px 0 0' }}>
            You can also check what is on your ballot and find where to vote.
          </p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, marginTop: 18 }}>
            <Link to="/elections" style={{ display: 'inline-flex', minHeight: 44, alignItems: 'center', justifyContent: 'center', borderRadius: 10, background: '#dda91f', color: '#0f172a', fontFamily: "'Inter', sans-serif", fontSize: 14, fontWeight: 800, padding: '0 18px', textDecoration: 'none' }}>
              Plan my vote
            </Link>
            <Link to="/act" style={{ display: 'inline-flex', minHeight: 44, alignItems: 'center', justifyContent: 'center', borderRadius: 10, border: '1px solid var(--color-border)', color: 'var(--color-text-1)', fontFamily: "'Inter', sans-serif", fontSize: 14, fontWeight: 700, padding: '0 18px', textDecoration: 'none' }}>
              Back to ACT choices
            </Link>
          </div>
        </div>}

        {/* Footer */}
        {!isEmbedded && <div
          style={{
            marginTop: 64,
            borderTop: '1px solid var(--color-border)',
            paddingTop: 20,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <Link
            to="/politics"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              fontFamily: "'Inter', sans-serif",
              fontSize: 13,
              color: 'var(--color-text-2)',
              textDecoration: 'none',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--color-text-1)'; }}
            onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--color-text-2)'; }}
          >
            <ArrowLeft size={14} /> Politics dashboard
          </Link>
          <span
            style={{
              fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
              fontSize: 10,
              letterSpacing: '0.04em',
              color: 'var(--color-text-3)',
            }}
          >
            WeThePeople
          </span>
        </div>}
      </div>
    </div>
  );
}

function shortDate(value: string | null): string {
  if (!value) return 'Date unavailable';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
}

function ConnectedRepresentativeRecord({ rep }: { rep: Representative }) {
  const recordText = { body: '#e1e7ef', muted: '#b5bfcc', label: '#c8d1dd', link: '#c6d9f2' };
  const panels = {
    shell: { borderRadius: 14, border: '1px solid #303845', background: '#141820', padding: 18 } as React.CSSProperties,
    label: { fontFamily: "'JetBrains Mono', monospace", fontSize: 12, fontWeight: 700, letterSpacing: '.11em', textTransform: 'uppercase' as const, color: recordText.label },
  };
  return <article style={{ borderRadius: 18, border: '1px solid #2a323e', background: '#0f1319', padding: 22 }}>
    <header style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 14, flexWrap: 'wrap', marginBottom: 18 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <RepresentativePortrait rep={rep} size={48} radius={12} />
        <div>
          <Link to={`/politics/people/${rep.person_id}`} style={{ color: '#f4f7fb', textDecoration: 'none', fontFamily: "'Inter', sans-serif", fontSize: 18, fontWeight: 750 }}>
            {rep.display_name}
          </Link>
          <p style={{ marginTop: 4, fontFamily: "'Inter', sans-serif", fontSize: 14, lineHeight: 1.55, color: recordText.muted }}>
            ACT, votes, bills, money, and forecasts use this same person record.
          </p>
        </div>
      </div>
      <Link to={`/politics/people/${rep.person_id}`} style={{ display: 'inline-flex', alignItems: 'center', gap: 7, minHeight: 40, borderRadius: 10, border: '1px solid #394250', background: '#161b22', padding: '0 14px', color: recordText.link, textDecoration: 'none', fontSize: 13, fontWeight: 700 }}>
        Full public record <ExternalLink size={12} />
      </Link>
    </header>

    <section
      aria-label={`Community forecast for ${rep.display_name}`}
      style={{ marginBottom: 14, display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap', borderRadius: 14, border: '1px solid #3b4657', background: 'linear-gradient(120deg, #172130 0%, #171b24 60%, #211d30 100%)', padding: '16px 18px' }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 13, minWidth: 0 }}>
        <span style={{ width: 40, height: 40, flexShrink: 0, display: 'grid', placeItems: 'center', borderRadius: 12, background: '#29384d', color: '#b7d1f3' }} aria-hidden="true">
          <ChartNoAxesCombined size={19} />
        </span>
        <div style={{ minWidth: 0 }}>
          <p style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10, fontWeight: 750, letterSpacing: '.13em', textTransform: 'uppercase', color: '#a9b8cb' }}>Community forecast</p>
          <h3 style={{ marginTop: 4, fontFamily: "'Inter', sans-serif", fontSize: 18, fontWeight: 780, color: '#f4f7fb' }}>
            What do you think happens next for {rep.display_name}?
          </h3>
          {rep.promises.length ? <p style={{ marginTop: 5, fontFamily: "'Inter', sans-serif", fontSize: 13, lineHeight: 1.55, color: '#c6cfdb' }}>
            Promise to watch: <Link to={`/civic/promises/${rep.promises[0].id}`} style={{ color: '#d8e6f8', fontWeight: 700 }}>{rep.promises[0].title}</Link>
          </p> : <p style={{ marginTop: 5, fontFamily: "'Inter', sans-serif", fontSize: 13, lineHeight: 1.55, color: '#b8c2cf' }}>
            No sourced promise is connected yet. We won’t guess.
          </p>}
        </div>
      </div>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <Link to={`/civic/promises?person_id=${encodeURIComponent(rep.person_id)}&person_name=${encodeURIComponent(rep.display_name)}`} style={{ display: 'inline-flex', minHeight: 40, alignItems: 'center', justifyContent: 'center', borderRadius: 10, border: '1px solid #485466', color: '#d7e0eb', padding: '0 13px', textDecoration: 'none', fontSize: 13, fontWeight: 700 }}>
          View promises
        </Link>
        <Link to={rep.election_forecasts[0]?.forecast_url || `/forecasts?person_id=${encodeURIComponent(rep.person_id)}`} style={{ display: 'inline-flex', minHeight: 40, alignItems: 'center', justifyContent: 'center', gap: 7, borderRadius: 10, background: '#d3dbe7', color: '#111722', padding: '0 14px', textDecoration: 'none', fontSize: 13, fontWeight: 800 }}>
          What happens next? <ArrowRight size={14} />
        </Link>
      </div>
    </section>

    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 12 }}>
      <section style={panels.shell}>
        <p style={{ ...panels.label, display: 'flex', alignItems: 'center', gap: 6 }}><VoteIcon size={12} /> Latest votes</p>
        {rep.votes.length ? rep.votes.slice(0, 3).map((vote, index) => <div key={`${vote.vote_date}-${index}`} style={{ marginTop: 11, paddingTop: index ? 11 : 0, borderTop: index ? '1px solid var(--color-border)' : undefined }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
            <span style={{ fontSize: 13, fontWeight: 800, color: vote.position.toLowerCase().includes('nay') ? '#f0b9b9' : '#b9dfca' }}>{vote.position}</span>
            <span style={{ fontSize: 12, color: recordText.muted }}>{shortDate(vote.vote_date)}</span>
          </div>
          <p style={{ marginTop: 6, fontSize: 14, lineHeight: 1.55, color: recordText.body }}>{vote.related_bill || vote.question || 'Congressional roll-call vote'}</p>
          {vote.source_url && <a href={vote.source_url} target="_blank" rel="noreferrer" style={{ marginTop: 7, display: 'inline-flex', alignItems: 'center', gap: 4, color: recordText.link, fontSize: 12, fontWeight: 650 }}>Congress.gov <ExternalLink size={11} /></a>}
        </div>) : <p style={{ marginTop: 12, fontSize: 14, lineHeight: 1.6, color: recordText.muted }}>No roll-call votes are available in the connected source yet.</p>}
      </section>

      <section style={panels.shell}>
        <p style={{ ...panels.label, display: 'flex', alignItems: 'center', gap: 6 }}><FileText size={12} /> Bills</p>
        {rep.bills.length ? rep.bills.slice(0, 3).map((bill, index) => <div key={`${bill.bill_id}-${bill.role}`} style={{ marginTop: 11, paddingTop: index ? 11 : 0, borderTop: index ? '1px solid var(--color-border)' : undefined }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
            <span style={{ fontSize: 12, fontWeight: 650, color: recordText.muted, textTransform: 'uppercase' }}>{bill.role}</span>
            {bill.policy_area && <span style={{ fontSize: 12, color: recordText.muted }}>· {bill.policy_area}</span>}
          </div>
          <a href={bill.source_url} target="_blank" rel="noreferrer" style={{ marginTop: 7, display: 'block', color: recordText.body, fontSize: 14, fontWeight: 550, lineHeight: 1.55, textDecoration: 'none' }}>{bill.title}</a>
          <p style={{ marginTop: 6, fontSize: 12, lineHeight: 1.45, color: recordText.muted }}>{bill.status || 'Status pending'} · {shortDate(bill.latest_action_date)}</p>
        </div>) : <p style={{ marginTop: 12, fontSize: 14, lineHeight: 1.6, color: recordText.muted }}>No sponsored or cosponsored bills are available in the connected source yet.</p>}
      </section>

      <section style={panels.shell}>
        <p style={{ ...panels.label, display: 'flex', alignItems: 'center', gap: 6 }}><ChartNoAxesCombined size={12} /> Next-election outlook</p>
        {rep.election_forecasts.length ? rep.election_forecasts.map((forecast) => <div key={forecast.id} style={{ marginTop: 11 }}>
          <p style={{ fontSize: 14, lineHeight: 1.6, color: recordText.body }}>{forecast.question}</p>
          <p style={{ marginTop: 6, fontSize: 12, lineHeight: 1.45, color: recordText.muted }}>Closes {shortDate(forecast.closes_at)} · source-backed civic forecast</p>
          <Link to={forecast.forecast_url} style={{ marginTop: 9, display: 'inline-flex', alignItems: 'center', gap: 4, color: recordText.link, fontSize: 13, fontWeight: 650 }}>Open Bets <ExternalLink size={11} /></Link>
        </div>) : <div style={{ marginTop: 12 }}>
          <p style={{ fontSize: 14, lineHeight: 1.65, color: recordText.body }}>No sourced forecast is published for {rep.display_name}’s next election yet. This will connect automatically when a verified contest market is available.</p>
          <Link to="/forecasts" style={{ marginTop: 9, display: 'inline-flex', alignItems: 'center', gap: 4, color: recordText.link, fontSize: 13, fontWeight: 650 }}>Browse all sourced forecasts <ExternalLink size={11} /></Link>
        </div>}
      </section>

      <section style={panels.shell}>
        <p style={{ ...panels.label, display: 'flex', alignItems: 'center', gap: 6 }}><Landmark size={12} /> Money & oversight</p>
        <div style={{ marginTop: 12, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
          {[
            ['Committees', rep.committees.length],
            ['Recent trades', rep.trades.length],
            ['Donor groups', rep.donors.length],
            ['Alerts', rep.anomalies.length],
          ].map(([label, value]) => <div key={String(label)} style={{ borderRadius: 10, border: '1px solid #2c3440', background: '#1b2028', padding: '12px' }}>
            <strong style={{ display: 'block', color: '#f4f7fb', fontSize: 18, fontWeight: 800 }}>{value}</strong>
            <span style={{ display: 'block', marginTop: 3, fontSize: 12, lineHeight: 1.35, color: recordText.muted }}>{label}</span>
          </div>)}
        </div>
        <Link to={`/politics/people/${rep.person_id}`} style={{ marginTop: 12, display: 'inline-flex', alignItems: 'center', gap: 4, color: recordText.link, fontSize: 13, fontWeight: 650 }}>Inspect sources <ExternalLink size={11} /></Link>
      </section>
    </div>
  </article>;
}

// ── Rep Card ──

function RepCard({ rep, issueSlug }: { rep: Representative; issueSlug?: string }) {
  const hex = partyHex(rep.party);
  const token = partyToken(rep.party);
  const isSenate = chamberLabel(rep.chamber) === 'Senate';

  return (
    <div
      style={{
        borderRadius: 12,
        border: '1px solid var(--color-border)',
        background: 'var(--color-surface)',
        padding: 20,
        transition: 'all 200ms',
      }}
      onMouseEnter={(e) => { e.currentTarget.style.borderColor = 'var(--color-border-hover)'; }}
      onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'var(--color-border)'; }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 14,
        }}
      >
          <RepresentativePortrait rep={rep} />
          <div style={{ minWidth: 0, flex: 1 }}>
            {rep.profile_available === false && rep.official_url ? <a href={rep.official_url} target="_blank" rel="noreferrer" style={{ textDecoration: 'none' }}><h3
              style={{
                fontFamily: "'Inter', sans-serif",
                fontSize: 16,
                fontWeight: 600,
                color: 'var(--color-text-1)',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {rep.display_name}
            </h3></a> : <Link to={`/politics/people/${rep.person_id}`} style={{ textDecoration: 'none' }}><h3
              style={{ fontFamily: "'Inter', sans-serif", fontSize: 16, fontWeight: 600, color: 'var(--color-text-1)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
            >{rep.display_name}</h3></Link>}
            <p
              style={{
                marginTop: 2,
                fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
                fontSize: 11,
                color: 'var(--color-text-3)',
              }}
            >
              {rep.state}{rep.district ? `, District ${rep.district}` : ''}
            </p>
          </div>
      </div>

        <div style={{ marginTop: 14, display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          <span
            style={{
              borderRadius: 999,
              padding: '4px 10px',
              fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
              fontSize: 10,
              fontWeight: 700,
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
              background: `${hex}1F`,
              color: token,
            }}
          >
            {partyLabel(rep.party)}
          </span>
          <span
            style={{
              borderRadius: 999,
              background: 'var(--color-surface-2)',
              padding: '4px 10px',
              fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
              fontSize: 10,
              fontWeight: 700,
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
              color: 'var(--color-text-2)',
            }}
          >
            {chamberLabel(rep.chamber)}
          </span>
          {isSenate && (
            <span
              style={{
                borderRadius: 999,
                background: 'rgba(61,184,122,0.15)',
                padding: '4px 10px',
                fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
                fontSize: 10,
                fontWeight: 700,
                color: 'var(--color-green)',
              }}
            >
              Your senator
            </span>
          )}
          {!rep.is_active && (
            <span
              style={{
                borderRadius: 999,
                background: 'rgba(230,57,70,0.12)',
                padding: '3px 10px',
                fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
                fontSize: 10,
                color: 'var(--color-red)',
              }}
            >
              Inactive
            </span>
          )}
        </div>

        <RepresentativeActPanel personId={rep.person_id} displayName={rep.display_name} issueSlug={issueSlug} />

        {/* Contribute to campaign */}
        <a
          href={(() => {
            const q = encodeURIComponent(rep.display_name);
            const p = rep.party?.charAt(0);
            if (p === 'D') return `https://secure.actblue.com/search?q=${q}`;
            if (p === 'R') return `https://secure.winred.com/search?query=${q}`;
            return `https://www.fec.gov/data/candidates/?search=${q}`;
          })()}
          target="_blank"
          rel="noopener noreferrer"
          onClick={(e) => e.stopPropagation()}
          style={{
            marginTop: 14,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 6,
            borderRadius: 10,
            padding: '9px 12px',
            fontFamily: "'Inter', sans-serif",
            fontSize: 12,
            fontWeight: 600,
            background: 'rgba(255,255,255,.025)',
            color: 'var(--color-text-2)',
            border: '1px solid var(--color-border)',
            textDecoration: 'none',
            transition: 'background 150ms',
          }}
          onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,.055)'; }}
          onMouseLeave={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,.025)'; }}
        >
          <Heart size={13} /> Contribute to campaign
        </a>
    </div>
  );
}
