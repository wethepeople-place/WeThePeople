export type StateCalendarElection = {
  id: string;
  name: string;
  election_day: string;
  division_id: string;
  description: string | null;
  registration_deadline: string | null;
  source: { name: string; url: string; kind: 'official_calendar' };
};

const MISSOURI_2027_SOURCE = {
  name: 'Missouri Secretary of State',
  url: 'https://www.sos.mo.gov/elections/calendar/2027cal',
  kind: 'official_calendar' as const,
};

const MISSOURI_2027: StateCalendarElection[] = [
  { id: 'mo-2027-02-02', name: 'February bond election date', election_day: '2027-02-02', division_id: 'ocd-division/country:us/state:mo', description: 'Bond elections may be held; no other issue may be included.', registration_deadline: '2027-01-06', source: MISSOURI_2027_SOURCE },
  { id: 'mo-2027-03-02', name: 'Charter city and county election date', election_day: '2027-03-02', division_id: 'ocd-division/country:us/state:mo', description: 'Available to charter cities and charter counties only.', registration_deadline: '2027-02-03', source: MISSOURI_2027_SOURCE },
  { id: 'mo-2027-04-06', name: 'General Municipal Election Day', election_day: '2027-04-06', division_id: 'ocd-division/country:us/state:mo', description: 'Missouri general municipal election date.', registration_deadline: '2027-03-10', source: MISSOURI_2027_SOURCE },
  { id: 'mo-2027-08-03', name: 'August public election date', election_day: '2027-08-03', division_id: 'ocd-division/country:us/state:mo', description: 'Available for public elections.', registration_deadline: '2027-07-07', source: MISSOURI_2027_SOURCE },
  { id: 'mo-2027-11-02', name: 'November public election date', election_day: '2027-11-02', division_id: 'ocd-division/country:us/state:mo', description: 'Available for public elections.', registration_deadline: '2027-10-06', source: MISSOURI_2027_SOURCE },
];

const ILLINOIS_2027_SOURCE = {
  name: 'Illinois State Board of Elections',
  url: 'https://www.elections.il.gov/agencyforms/1%20ELECTION%20CALENDAR/2027%20Election%20Calendar%20FINAL.pdf',
  kind: 'official_calendar' as const,
};

const ILLINOIS_2027: StateCalendarElection[] = [
  {
    id: 'il-2027-04-06',
    name: 'April 6, 2027 Consolidated Election',
    election_day: '2027-04-06',
    division_id: 'ocd-division/country:us/state:il',
    description: 'Local offices such as municipal, school, park, library, and other districts may appear based on your address.',
    registration_deadline: null,
    source: ILLINOIS_2027_SOURCE,
  },
];

const CALENDARS: Record<string, StateCalendarElection[]> = { IL: ILLINOIS_2027, MO: MISSOURI_2027 };

const NATIONAL_2028_SOURCE = {
  name: 'USA.gov',
  url: 'https://www.usa.gov/election-day',
  kind: 'official_calendar' as const,
};

function nationalGeneralElection(stateCode: string): StateCalendarElection {
  return {
    id: `${stateCode.toLowerCase()}-2028-general`,
    name: 'November 7, 2028 General Election',
    election_day: '2028-11-07',
    division_id: `ocd-division/country:us/state:${stateCode.toLowerCase()}`,
    description: 'Federal general election date. State and local contests may also appear on the ballot.',
    registration_deadline: null,
    source: NATIONAL_2028_SOURCE,
  };
}

export function getOfficialStateCalendar(stateCode: string, today = new Date()): StateCalendarElection[] {
  const todayKey = today.toISOString().slice(0, 10);
  return [...(CALENDARS[stateCode] || []), nationalGeneralElection(stateCode)]
    .filter((item) => item.election_day >= todayKey);
}
