import React from 'react';
import LongformDoc, {
  type LongformSection,
} from '../components/LongformDoc';
import { LEGAL_LAST_UPDATED } from '../config';

// Content for the Terms of Use page. Four sections covering acceptable use,
// licensing of our aggregated data, liability limits, and the governing-law
// clause. Rendered via the shared <LongformDoc> template.
const SECTIONS: LongformSection[] = [
  {
    num: 1,
    id: 'use',
    title: 'Acceptable use',
    body: [
      'You may read, quote, cite, link to, and re-publish our data with attribution. You may not scrape at abusive rates (>1 req/sec sustained). API keys available free at /api.',
    ],
  },
  {
    num: 2,
    id: 'license',
    title: 'Data license',
    body: [
      'Our aggregated data is CC-BY 4.0. Underlying government data is public domain in most jurisdictions. Our editorial writing (Journal articles) is CC-BY-NC 4.0.',
    ],
  },
  {
    num: 3,
    id: 'liability',
    title: 'Limitation of liability',
    body: [
      'Site provided as-is. We are not liable for decisions made based on our data. If the stakes of your decision are high, verify against primary sources.',
    ],
  },
  {
    num: 4,
    id: 'forecasts',
    title: 'Civic Forecasts',
    body: [
      'Civic Forecasts are free predictions for civic learning, not bets, wagers, polls, endorsements, official results, voting advice, or financial contracts. We do not accept stakes or provide money, prizes, payouts, transferable credits, or anything else of value based on an outcome. You must be at least 13 to submit a Forecast. Individual choices stay private; community totals appear only after the stated privacy threshold is met. We may lock, void, correct, or remove a Forecast when its source, wording, deadline, or outcome cannot be verified reliably.',
    ],
  },
  {
    num: 5,
    id: 'jurisdiction',
    title: 'Jurisdiction',
    body: [
      'Governed by the laws of Delaware, USA. Disputes resolved in Delaware Chancery Court.',
    ],
  },
];

export default function TermsOfUsePage() {
  return (
    <LongformDoc
      overline="Terms"
      title="The rules for using this site."
      lastUpdated={LEGAL_LAST_UPDATED}
      sections={SECTIONS}
    />
  );
}
