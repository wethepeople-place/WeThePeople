import type { EvidenceSeries } from '../api/issues';

// Reviewed, comparable national series used when the general evidence API has
// not yet published a historical series for an Agenda topic. Never combine
// incompatible vintages just to make a chart look longer.
export const ISSUE_TRENDS: Record<string, EvidenceSeries> = {
  immigration: {
    key: 'census-net-international-migration-2021-2025',
    title: 'Net international migration to the United States',
    unit: 'people',
    geography: { type: 'country', id: 'US' },
    source: {
      url: 'https://www2.census.gov/programs-surveys/popest/datasets/2020-2025/state/totals/NST-EST2025-ALLDATA.csv',
      publisher: 'U.S. Census Bureau, Population Estimates Program',
      retrieved_at: '2026-11-11T00:00:00Z',
    },
    observations: [
      { date: '2021-07-01', value: 376026, source_record_id: 'INTERNATIONALMIG2021', source: { url: 'https://www2.census.gov/programs-surveys/popest/datasets/2020-2025/state/totals/NST-EST2025-ALLDATA.csv', publisher: 'U.S. Census Bureau, Population Estimates Program', retrieved_at: '2026-11-11T00:00:00Z' } },
      { date: '2022-07-01', value: 1672112, source_record_id: 'INTERNATIONALMIG2022', source: { url: 'https://www2.census.gov/programs-surveys/popest/datasets/2020-2025/state/totals/NST-EST2025-ALLDATA.csv', publisher: 'U.S. Census Bureau, Population Estimates Program', retrieved_at: '2026-11-11T00:00:00Z' } },
      { date: '2023-07-01', value: 2264137, source_record_id: 'INTERNATIONALMIG2023', source: { url: 'https://www2.census.gov/programs-surveys/popest/datasets/2020-2025/state/totals/NST-EST2025-ALLDATA.csv', publisher: 'U.S. Census Bureau, Population Estimates Program', retrieved_at: '2026-11-11T00:00:00Z' } },
      { date: '2024-07-01', value: 2734468, source_record_id: 'INTERNATIONALMIG2024', source: { url: 'https://www2.census.gov/programs-surveys/popest/datasets/2020-2025/state/totals/NST-EST2025-ALLDATA.csv', publisher: 'U.S. Census Bureau, Population Estimates Program', retrieved_at: '2026-11-11T00:00:00Z' } },
      { date: '2025-07-01', value: 1262202, source_record_id: 'INTERNATIONALMIG2025', source: { url: 'https://www2.census.gov/programs-surveys/popest/datasets/2020-2025/state/totals/NST-EST2025-ALLDATA.csv', publisher: 'U.S. Census Bureau, Population Estimates Program', retrieved_at: '2026-11-11T00:00:00Z' } },
    ],
  },
};
