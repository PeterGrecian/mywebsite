# Lambda startup, cold starts and cost — measured 2026-09-11

Everything here is measured on `mywebsite`, not inferred. It exists because the
same three questions keep getting re-derived from first principles and answered
wrongly: *is the site slow to start, would a framework make it slower, and what
stops a flood becoming a bill.*

Local timings are from **zog** (Crostini, arm64, Python 3.13) and are
indicative of shape, not of Lambda's exact numbers. Production figures are from
CloudWatch on `/aws/lambda/mywebsite` (512 MB, python3.12, zip package).

---

## 1. The headline: cold starts are 1.1% of traffic

| | |
|---|---|
| Invocations, 24h | **1,981** |
| Cold starts (`Init Duration` lines), same window | **22** |
| Cold start rate | **1.1%** |
| `Init Duration` | min 558, **p50 668**, max 826 ms |

One request every ~43 seconds is enough of a trickle to keep an execution
environment alive, so **98.9% of requests never run module import at all**.

The aggregate cost of every cold start in a day is `22 x 0.668 s` ≈ **15
seconds of latency**, spread over 22 visitors, and about **$0.0001** in
GB-seconds.

**Consequence: startup optimisation is not worth doing here.** Any change that
only touches INIT is worth a few seconds a day in total. Measure the cold-start
share before optimising startup — on a busier or a spikier site the answer
would differ.

---

## 2. Where the 668 ms actually goes

The module's own code is a small minority of it. Measured locally with `boto3`
stubbed out vs. real:

| Component | Cost |
|---|---|
| `import boto3` | **324 ms** |
| First SSM client build | 67 ms |
| SSM `GetParameters` at import (`_COLD_START_PARAMS`) | ~50–150 ms (network) |
| Python runtime boot | ~100–150 ms (inferred) |
| `mywebsite.py` own code | 24.5 ms → **13.7 ms** after the route-table refactor |
| One lazily-imported route module | ~2 ms |

So roughly **390 ms of the 668 is `boto3` import plus one blocking SSM round
trip** performed during INIT. Deferring the SSM fetch to first use is the
largest single startup win available — and by §1 it is worth about 3 seconds a
day, which is why it has not been prioritised.

### Package size is not the lever

A 237 KB package already sits on a ~660 ms floor. The mechanism usually
attributed to "package size" is really *number of modules to import*, which is
measured directly below. Download/unpack is weak below ~50 MB.

---

## 3. INIT is billed (since 2025-08-01) — and still logged separately

AWS standardised INIT billing on **1 August 2025**. It previously did not apply
to on-demand invocations of **zip-packaged functions using managed runtimes**,
which is exactly this function. Custom runtimes, OCI packaging and Provisioned
Concurrency already billed it.

**The reporting did not change, which is the trap.** `Init Duration` is still
its own field in the REPORT line and its own CloudWatch metric — it is now also
*included in* `Billed Duration`:

```
before:  Billed Duration: 251 ms    Init Duration: 100.77 ms
after:   Billed Duration: 351 ms    Init Duration: 100.77 ms
```

Reading a REPORT line still looks like it supports "INIT is free". It is not.

**Consequence:** the lazy imports scattered through the route handlers are now
**billing-neutral**. Before the change, deferring work out of INIT into the
handler moved it from an unbilled phase to a billed one — a mild
pessimisation. Now both are billed identically, so laziness is purely a latency
choice and there is no cost argument either way.

Source: <https://aws.amazon.com/blogs/compute/aws-lambda-standardizes-billing-for-init-phase/>

---

## 4. The execution environment is a live process, not a shell loop

Worth stating because the wrong model leads to wrong conclusions about all of
the above.

An execution environment runs **your Python interpreter**, with `boto3` already
in `sys.modules`, blocked on an HTTP GET to the Runtime API `/next` endpoint.
An invocation calls your handler in that same process, posts the response, and
loops back.

```
INIT   (once per execution environment)
   run mywebsite.py top to bottom:
     import boto3                          324 ms
     _COLD_START_PARAMS = get_parameters()  network call
     ... define handlers ...
   then block on GET /next

INVOKE (many times; 1,959 of 1,981 reused an existing environment)
   lambda_handler(event, context)   <- only this re-runs
   module globals inherited, locals fresh
   POST response, back to /next
```

**The script runs once; the function runs many times.** What is "warm" is the
script's *leftovers* — everything it left in memory. Three independent
confirmations: the AWS lifecycle docs; the 22-of-1,981 `Init Duration` ratio
(if every invocation started fresh, all 1,981 would log one); and this
codebase's own reliance on it — `_SSM_CLIENTS`, `_S3_CLIENTS`,
`_DYNAMODB_RESOURCES` and `_COLD_START_PARAMS` are module globals that would do
nothing if the process died between invocations.

*Where the "bash loop" intuition comes from:* AWS's **custom runtime** tutorial
ships a `bootstrap` that really is a bash `while true; do curl .../next; done`.
That applies to custom runtimes only; managed runtimes keep the interpreter
alive instead. (Even there, the shell process persists across iterations.)

### The design lever this gives you

**Module level is paid once per environment; handler body is paid on every
invocation.** That is the whole optimisation grammar for this codebase, and it
is why the two findings below sit where they do.

---

## 5. Would Flask be slower? Yes, and it does not matter

Measured locally (Flask 3.x + Mangum in a clean venv):

| | Current | With Flask |
|---|---|---|
| `mywebsite.py` import | 24.5 ms | 24.5 ms |
| Flask import | — | **108.5 ms** |
| Route modules | ~1–5 ms (one, lazily) | **+28.3 ms** (all, eagerly — decorators register at import) |
| **Module import total** | **~27 ms** | **~161 ms** |
| Routing, per warm request | 8.8 µs (77-condition scan) | ~2 µs + ~0.3 ms WSGI shim |
| Package | 237 KB | ~5 MB vendored |

The `+134 ms` lands on **22 requests a day** (§1) — about 3 seconds daily in
total. It is not a meaningful regression, and an early framing of this as "6x
slower startup" was misleading because it compared against a 27 ms figure that
excluded the 641 ms the function pays anyway.

**Flask was rejected on other grounds:** the dict route table gets the same
routing wins (converters, method routing, `url_for`-style single-form paths,
error handlers) at zero dependency cost and with lazy imports intact. What
Flask uniquely adds is the request/response object, `flask run` for local
development, and `test_client()`. If hand-rolled cookie handling or the
deploy-to-see-a-change loop ever become the real irritation, revisit — the
handlers take a request bundle and would lift to view functions.

---

## 6. Cost liability: a flood is billed on three meters at once

The concern is not the monthly bill, it is that **a DoS converts into a bill**
with nothing bounding the total.

Every Lambda invocation is billed — warm *and* cold. Only a Cloudflare edge-cache
hit is free. A flood drives **Lambda + DynamoDB + CloudWatch** simultaneously.

| Control | Setting | Notes |
|---|---|---|
| Cloudflare rate limit | 20 req / 10 s per IP **per colo** (`cloudflare/waf.tf`) | Single-source only; multiplies across IPs and colos |
| API Gateway throttle | 50/s sustained, 100 burst (`terraform/api-gateway.tf:31`) | Bounds the **rate**, not the cost per request |
| Lambda reserved concurrency | **20** (`terraform/lambda.tf`) | Bounds the billed quantity — added 2026-09-11 |

Before the cap the function could scale to the account ceiling of **1000**:

```
1000 concurrent x 0.512 GB x $0.0000166667/GB-s x 86400 s  =  ~$737/day
  20 concurrent x 0.512 GB x $0.0000166667/GB-s x 86400 s  =  ~$14.75/day
```

20 is ~1000x observed usage: average concurrency is near 0.01 and
`ConcurrentExecutions` reports **no datapoints at all** over 7 days. The failure
mode of setting it too low is a 429 to a real visitor, so raise it deliberately
if traffic ever approaches it.

### The per-request meters matter more than duration

`log_connection()` used to run **before any routing**, so every favicon fetch,
`robots.txt` and probe for `/wp-login.php` bought a DynamoDB write — on 100% of
invocations. It now sits behind the route lookup and skips static assets and
unclaimed paths. Nothing goes dark: `_access_log()` still emits a CloudWatch
line per request, so scanners stay visible where recording them is cheap.

It also built `boto3.resource('dynamodb')` on **every invocation** — the same
mistake `s3_client()` and `ssm_client()` already document, on the hottest path
in the site. Now cached per region in `dynamodb_resource()`.

---

## 7. Traffic shape, for context

24h sample of `cv-access-logs`, top paths:

```
77  /calendaralarm/api/rules     <- the once-a-minute poller on pip
10  /springcam/fullres
 6  /skycam/fullres
 2  /springcam/gallery
 2  /skycam/play
```

The poller dominates by a wide margin. See `STATE.md` in the
`mywebsite-tweaks` strand for the agreed shape (poll every 10 minutes during
the day, off at night — roughly a 20x cut), which belongs to calendaralarm's
timer on pip, not to this repo.

---

## 8. Route resolution after the table refactor

For completeness — and to record that it was never the point:

| | Before (if/elif chain) | After (route table) |
|---|---|---|
| Worst case, no match | 8.8 µs | **2.3 µs** |
| Exact hit | (same scan) | **0.07 µs** |
| `mywebsite.py` import | 24.5 ms | **13.7 ms** |
| Route modules eager-imported | 0 | **0** (laziness preserved) |

Against a page that spends hundreds of ms in S3 and DynamoDB, none of this is
perceptible. The refactor was for **readability and safety** — and it paid for
itself immediately by exposing `/gardencam/timing`, which had been returning
500 on every request because it read a variable that only existed as a local
because some *other* branch of the same 2,865-line function assigned it.
