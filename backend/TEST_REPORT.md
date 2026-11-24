# Emergency analysis test report

## Results

- Backend suite: 424 passed, 1 skipped; no failing tests (425 collected).
- Flutter suite: 11 passed.
- React dashboard production build: passed.

The backend run emitted existing FastAPI lifecycle deprecation warnings and
skipped `app/core/test_db.py::test`, an async test not configured with an
async-test plugin. The Flutter run resolved existing dependencies without
changing the dependency manifest. The dashboard build emitted Vite/Rolldown
deprecation and large-chunk warnings; the build completed successfully.

## Coverage represented by the suite

Existing and updated tests cover multilingual medical and accident reports,
fire/explosion, personal safety and crime, child safety, disaster/flood risk,
explicit victim counts, current versus historical/resolved/hypothetical/
negated reports, ambiguous requests, location extraction, service
recommendations, malformed/model-unavailable responses, schema normalization,
and persistence/API integration behavior. Complete-analysis regression cases
cover English, Hindi, Gujarati, and Marathi reports, separate assistance from
operational units, and validate configured emergency contact labels. The Hindi
Flutter-shaped report was submitted through the existing FastAPI endpoint with
Ollama mocked, then retrieved through GET; tests verify the complete persisted
analysis schema, priority, dispatch/contact recommendations, original
transcript, GPS, and unrelated metadata. New cases also verify that chest pain
does not imply injury, bleeding, or unconsciousness; negated injury does not
inflate accident priority; unexpected analysis exceptions terminate cleanly;
severity and operational priority remain distinct; uncalibrated emotion and
confidence estimates remain unavailable; and body-part phrases are not used
as locations.

## Limitations

- These are synthetic and regression cases, not expert validation or evidence
  of clinical or real-world triage accuracy.
- A live Ollama/Qwen call and production database deployment were not part of
  this test run; the ASGI integration test uses the repository's configured
  database and a mocked model response.
- Multilingual slang, transliteration, speech-recognition errors, dialects, and
  locations remain bounded by the maintained rules and lexicon.
- Panic, stress, and confidence remain unavailable because the system has no
  calibrated text or acoustic estimator; no value is inferred from absence of
  evidence.
