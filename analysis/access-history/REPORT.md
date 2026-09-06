# Who actually visits www.petergrecian.co.uk

Analysis of the complete request history, 2026-02-17 to 2026-09-06, run on
2026-09-06 before the CloudWatch log group was age-limited.

## Sources, and why it took two of them

| Source | Span | Rows | Has |
|---|---|---|---|
| `/aws/lambda/mywebsite` (CloudWatch, exported to S3) | 2026-02-17 → 2026-09-06, complete | 2,141,647 | path, IP, duration |
| `cv-access-logs` (DynamoDB) | 2026-02-25 → 03-27, then 08-07 → 09-06 | 1,466,625 | path, IP, **user-agent**, referer |

Neither is sufficient alone. CloudWatch has every request but **never logged the
user-agent**, and it put the path and the IP in *separate* records joinable only
on RequestId. DynamoDB has the user-agent — the single most useful field for
telling a crawler from a person — but a 30-day TTL has eaten everything between
2026-03-27 and 2026-08-07. The Feb–Mar block survives only because those items
predate the `ttl` attribute; they are a fossil, not retention.

So: **volume comes from CloudWatch, identity comes from DynamoDB.**

The CloudWatch export was verified against Lambda's own `Invocations` metric for
the period: 2,141,647 rows parsed against 2,141,662 invocations, a gap of 15 —
the requests in flight while the export ran.

## The headline: 2,141,647 requests, ~20 of them strangers

Of 202 days of traffic:

| | requests | share |
|---|---|---|
| **An Amazon Route53 health check on `/`** | 1,305,219 | **61%** |
| The pi-fleet dashboard reporting in (`/pi-fleet`) | 99,964 | 4.7% |
| The calendaralarm poller (`/calendaralarm/api/rules`) | 31,254 | 1.5% |
| Search-engine and AI crawlers | ~21,500 | 1% |
| Scanner probes for software this site does not run | 7,173 | 0.3% |
| Everything else, including every human | the remainder | — |

And in the window where the user-agent survives (62 days of data):

- **101 human visits, of which 81 are Peter's own address.**
- **20 visits by someone else, from 16 distinct addresses — about 2.3 a week.**

That is the whole answer to "is a human arriving a notable event": yes. It
happens roughly twice a week, and four times out of five a "human" visit is the
site's own author.

## The Route53 health check — 1.3M invocations, now stopped

The largest single fact in the history is a health check nobody was looking for.
`Amazon-Route53-Health-Check-Service` hit `/` from 39 checker addresses at
**~30 requests a minute, 43,500 a day, every day from 2026-02-25 to
2026-03-27**, then stopped dead. No health check exists in the account now, so
it was deleted around 2026-03-27 — and with it, 95% of the site's traffic.

This reframes the site's history. February and March averaged **41,000
requests a day**; April onward averages **2,000**. Any comparison across that
boundary is comparing two different sites.

| month | days | requests | per day |
|---|---|---|---|
| 2026-02 | 12 | 505,065 | 42,088 |
| 2026-03 | 31 | 1,267,647 | 40,891 |
| 2026-04 | 30 | 58,212 | 1,940 |
| 2026-05 | 31 | 102,074 | 3,292 |
| 2026-06 | 30 | 78,367 | 2,612 |
| 2026-07 | 31 | 54,726 | 1,765 |
| 2026-08 | 31 | 59,696 | 1,925 |
| 2026-09 | 6 | 15,860 | 2,643 |

## What "looks human" turned out to mean

The idea that prompted this was right not to want a classifier. Three shape
signals separate people from machines, and all three are cheap:

1. **A browser fetches the page's assets.** A scanner asks for one path and
   leaves. This is the strongest signal available.
2. **A person follows a link.** Two distinct real pages from one address inside
   half an hour is a browse, not a probe.
3. **A person does not ask for paths that do not exist.** Any request outside
   the real route set disqualifies the whole visit.

Three traps found while building it, each of which produced a wrong answer first:

- **The logged IP is the entire `X-Forwarded-For` chain**, client *and* the
  Cloudflare edge that relayed it. The edge address rotates per request, so
  taking the field whole shatters one visitor into one "visit" per hop. This
  alone inflated the visit count from 9,296 to 21,454.
- **`GoogleOther` and `Google-InspectionTool` contain no "bot" token** and wear
  a complete Chrome user-agent. A UA filter looking for `bot|crawl|spider`
  passes them straight through: they produced 724 "human visits" in a single
  day before crawler IP ranges were added as a second check.
- **A lone `/favicon.png` request is not a visit.** Requiring at least one real
  page alongside the assets removed the rest of the noise.

The honest limit: the astro gallery images are presigned S3 URLs on the
bucket's own hostname, so image fetches never appear in these logs at all.
Asset-following is visible only for CSS, favicons, and the `/thumbs/` and
`/fullres` routes.

## The 20 strangers

Small enough to read individually, which is the point.

- **2026-03-05, `212.161.46.97`** — 745 requests over 106 minutes, entering at
  `/contents`. Someone read the whole site.
- **`66.103.29.122`** — four separate visits across March, always entering at
  `/contents`. A returning reader.
- **2026-08-29, 15:46–16:10** — four different addresses within 25 minutes, one
  arriving from `https://www.google.com/`. That is what sharing the link looks
  like in the data.
- **2026-09-05, `85.203.46.24`** — 53 requests in 125 seconds, no referer,
  walking `/gotg`, `/site-test`, `/memspeed`, `/springcam`, `/pi-fleet`. A real
  browser user-agent from a hosting range. Genuinely ambiguous; the heuristic
  calls it human and it may be a well-dressed scraper. Expect a couple of these
  a month.

Entry pages for strangers: `/contents` (12), `/` (5), then one each for
`/skycam/clouds`, `/us-vs-the-machines`, and an astro night page. **`/contents`
is the front door**, not `/`.

## What this means for alerting

At ~2.3 stranger visits a week, an informational alert per human visit is
sustainable — but only with the two rules the idea already called for, and one
more this analysis adds:

1. **Exclude the owner.** 81 of 101 human visits are Peter's own address. An
   alert that fires when he looks at his own site is worthless.
2. **Dedupe per visitor per day.** The March 5th visitor made 745 requests in
   one sitting; that is one alert, not 745.
3. **Rate-cap the channel regardless.** The 2026-09-06 scanner burst was 2,600
   requests in ten minutes. A misfiring detector on an uncapped path would have
   paged 2,600 times.

## Reproducing this

    tools/analyse_visitors.py '~/tmp/mywebsite-access/access-*.jsonl.gz'
    tools/analyse_access_history.py ~/tmp/mywebsite-cwlogs --out analysis/access-history/cloudwatch

Outputs: `daily.csv`, `visits.csv`, `human_visits.csv`, `stranger_visits.csv`,
`summary.json`. The raw CloudWatch history is preserved at
`s3://backup-peter/mywebsite-cloudwatch-logs/` (13,572 objects, 149 MB gzipped).

From 2026-09-06 the handler emits one structured JSON line per request, so none
of this parsing applies to new data — it is a query now.
