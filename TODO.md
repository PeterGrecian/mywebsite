# mywebsite TODO

## Bugs

- Contents page: links change the location bar but not the contents
- Cloudflare purge appears faulty — investigate
- **Player step-mode advances 2 frames per ArrowLeft/ArrowRight on 60 fps starcam videos.** FPS detection via rVFC mediaTime medians (commit fb20f3d) still underestimates by 2x even after rejecting seek-induced samples (v.seeking + dt<0.07 s filter). Likely cause: browsers snap currentTime seeks to the previous keyframe, and starcam mp4s have default GOP=250 (= 4 s keyframe interval at 60 fps), so single-frame seeks may decode forward through a GOP and present a frame ≥2 ahead of where requested. **Fix candidates:** (a) re-encode starcam with `-g 30` (0.5 s keyframe interval) — encoder-side change in `Berrylands/gardencam/starcam_processor.py`, costs some compression efficiency; (b) use rVFC for the step itself (request next presented frame instead of arithmetic seek); (c) maintain a frame-index → mediaTime map populated during playback, then seek to the *next mapped time* rather than +1/FPS. Skycam at 24 fps is unaffected (less sensitive to step-arithmetic rounding). Live on prod at /starcam/player.

## Active

- **Skycam player: hide the "up next" overlay during cast loop.**
  Currently using one-item Queue + `RepeatMode.ALL` to loop on
  Chromecast — works, but DMR shows "your video will play in N seconds…"
  + filename across the picture near each loop boundary. Annoying on
  short clips, tolerable on day-long videos. Other approaches that
  failed: (1) `mediaInfo.loop = true` (ignored by DMR), (2) JS listener
  for IDLE/FINISHED → re-`loadMedia()` (no IDLE event fired). Worth
  investigating: a custom CAF receiver (own app ID) that suppresses
  the overlay; whether newer Chromecast generations behave differently.
- Better repo name and docs — this is the website publishing core; document how it works
- T3 logging: capture `stop` query param (parklands/surbiton) for usage breakdowns
- Retire `newhome.petergrecian.co.uk` — was the PWA test subdomain, test is over.
  Remove the custom domain from the `petergrecian-homepage` Pages project
  (API: DELETE /accounts/:id/pages/projects/petergrecian-homepage/domains/newhome.petergrecian.co.uk).
  Note: this kills the only currently-installable PWA entry point. If we want a
  PWA at `www.petergrecian.co.uk`, the `/` route would need to be moved from
  Lambda to Pages — bigger change, decide separately.

## Future

### Logging: migrate from DynamoDB to CloudWatch

Current: Lambda → DynamoDB → manual export → S3.
Better: Lambda → CloudWatch Logs → S3 (→ Athena/Grafana).

CloudWatch already captures duration, memory, errors, prints. DynamoDB logging is redundant; free tier covers this volume easily.

### Lambda monolith

`mywebsite.py` is ~3600 lines, mostly dispatching to route modules in `lambda/routes/`. Full microservices split (one Lambda per service) would help independent scaling and deploys but is a big undertaking for marginal gain at current scale. Revisit if any single route becomes a bottleneck.
