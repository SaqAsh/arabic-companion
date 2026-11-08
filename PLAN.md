# Arabic Companion — implementation plan

Prepared 8 November 2026. Target: Windows desktop, Chrome audio, beginner Arabic class conversations.

Status: implementation specification; the application has not been built or tested. The attached Python example is incomplete and is not a working starting application.

## The first usable result

Open the app, select the speakers or headphones Chrome uses, start capture before a short Arabic question, then press **Stop & Process**. A floating window shows the recognized Arabic, its English meaning, and a short suggested reply with vowelled Arabic and large, readable transliteration. The window remains responsive throughout.

Complete this manual workflow before adding automatic speech detection. Manual capture remains available afterward for slow speech and difficult audio.

## Decisions for version 1

| Area | Decision | Reason or boundary |
|---|---|---|
| Runtime | Python 3.11, 64-bit Windows | Establish one supported development environment and pin dependencies after a Windows installation check. |
| Audio capture | PyAudioWPatch, WASAPI loopback | Its device enumeration and loopback helpers are intended for Windows speaker capture. [1] |
| Capture scope | Selected playback device | Ordinary endpoint loopback includes audio from other apps on that device; this is not Chrome-tab isolation. [2] |
| Transcription | OpenAI file transcription, configurable model; initial candidate `gpt-transcribe` | Current documentation recommends it for bounded recorded speech. Confirm account access in the initial smoke test. [3] |
| Reply generation | One structured-output text-model request, validated with Pydantic | Return translation, reply, and pronunciation text together. Select an available supported text model during the smoke test and retain its ID in configuration. Schema correctness does not establish language correctness. [4] |
| UI | PySide6, normal resizable window with always-on-top option | Retain standard move, resize, and close behavior before adding optional transparency. |
| Background work | Capture worker and processing worker; Qt signals update the UI | Blocking audio/API calls run outside the GUI thread. [5] |
| Automatic mode | Silero VAD added after the manual workflow passes | Detect speech boundaries locally; avoid continuous cloud uploads of silence. [6] |
| Personalization | Editable profile and reviewed phrase list | Do not invent personal answers or assume the Arabic spelling of a name. |

Assumptions: internet access and a locally configured API credential are available for the initial version. The app sends captured clips and relevant text to the configured provider. It does not persist recordings or conversation logs by default; diagnostic recording is explicit. Keep the key outside source control and release archives.

Local faster-whisper transcription is a later backend option if offline transcription becomes a requirement. It needs its own accuracy and hardware timing checks; local transcription alone would not make API reply generation offline.

## Build order and completion gates

### 0. Establish a runnable environment

- Create the package, virtual environment, dependency file, configuration example, and ignore rules.
- Provide a demo mode that runs without a credential or audio device.
- Verify PySide6 and PyAudioWPatch install on the target Windows/Python combination.
- Test one short Arabic audio request and one schema-constrained language request. Store the tested model IDs and dependency versions.
- Report missing credentials, model access, and unavailable devices clearly.

**Done when:** the demo opens on Windows and both live API checks succeed. API availability is a dependency, not an assumed result.

### 1. Prove that browser audio is captured correctly

- Enumerate playback loopback devices, choose the current default initially, and expose a device selector and level meter.
- Capture at the device's supported sample rate and channel count.
- Make an explicit diagnostic recording of about ten seconds of Chrome speech, then stop capture before replaying it.
- Check that the recording contains the browser voice at normal speed. A microphone must not be opened by this app.
- Keep manual clips bounded to 20 seconds; show the limit and require another capture for longer questions.

**Done when:** a saved diagnostic clip sounds correct through the user's actual speakers/headphones, and silence, missing devices, and device removal produce understandable states.

### 2. Complete one question-to-reply exchange

- Accept an existing WAV fixture as well as a freshly captured clip, so audio capture and language processing can be debugged independently.
- Transcribe the original Arabic. Keep the unmodified transcript separate from any corrected or vowelled rendering.
- Send the transcript, reviewed vocabulary, confirmed profile fields, and a small amount of confirmed conversation context to the reply model.
- Validate the response against a typed schema. Handle refusals, incomplete responses, malformed output, and missing facts explicitly.
- Return one short reply, normally one sentence; show an editable placeholder when a necessary personal fact is absent.
- Record stage durations and API usage without recording the conversation content.

**Done when:** at least ten clear test questions produce readable, relevant results, and silent input or an API failure does not fabricate a reply.

### 3. Connect the floating window

- Show separate areas for **Heard**, **English meaning**, and **Suggested reply**.
- Make reply transliteration the largest text. Use separate RTL Arabic and LTR English/transliteration widgets with word wrapping.
- Add device selection, Start, Stop & Process, Cancel, Pause, Clear, and an always-on-top toggle.
- Expose Listening, Transcribing, Preparing reply, Ready, Paused, and Error states.
- Allow transcript correction and regeneration without recapturing audio.
- Keep suggested replies out of confirmed conversation history until the user marks them as used. The app does not know what the user actually said because microphone capture is off.

**Done when:** a real Chrome question reaches the window through the entire pipeline; moving, resizing, pausing, and closing still work during slow requests.

**This is the first usable release.**

### 4. Add automatic capture and recovery

- Downmix and resample continuously to 16 kHz mono using a stateful, anti-aliased resampler. Do not merely relabel the sample rate.
- Feed Silero frames of the size required by the pinned model; the documented 16 kHz implementation uses 512 samples per inference step. [6]
- Start with roughly 250 ms pre-roll and 800 ms end-of-speech silence. These are tuning defaults, not measured optimum values. Keep manual Stop & Process available.
- Retain a 20-second utterance cap. If forced to cut a turn, flag it as possibly incomplete rather than confidently answering a fragment.
- Bound audio buffers and request queues. Permit one active processing request and one waiting utterance; if additional speech exceeds capacity, show an explicit overload state and request repetition instead of silently losing context.
- Tag work with session and utterance IDs. After Pause, Clear, Cancel, or device change, invalidate old work so late results cannot repopulate the display.
- Apply explicit request timeouts and limited retries for temporary failures. Avoid duplicate SDK and application retry loops. Never retry authentication failures automatically.
- Handle device removal by stopping capture and asking for device selection. Cleanly close streams and workers on exit.

**Done when:** ten minutes of conversation playback runs without frozen UI, growing queues, duplicated replies, or results appearing after cancellation.

### 5. Validate the language and make launch repeatable

- Create a small evaluation set from available course audio or reviewed practice recordings, including greetings, names, where someone is from, studies, and short follow-up questions. The actual course vocabulary has not been supplied in this attachment.
- Use 20 clear questions and at least five difficult cases: silence, background noise, a long pause, a clipped question, and an unknown personal detail. Include both masculine and feminine address where relevant.
- Review transcript meaning, English translation, response relevance, vowel marks, and transliteration separately. Compare output with manually checked answers rather than another unchecked model response.
- Test sample-rate conversion at 44.1 and 48 kHz, device disconnects, cancellation during a slow request, and a simulated API outage.
- Add a Windows launcher and setup guide. Build an executable on Windows only after the source version passes its checks; verify it on a clean Windows environment.

**Release targets:** at least 18/20 clear questions correctly understood with a relevant, readable answer; no invented personal facts; no replies from silent fixtures; and no stale updates after cancellation. This is a small release gate, not a broad claim of 90% real-world accuracy.

Measure delay from the end of the question to the rendered reply. Aim initially for a median of 3–5 seconds on short, clear questions, and record the slow cases too. This is a target, not a guarantee. Profile segmentation, transcription, and generation separately before choosing streaming or a different model.

## Module boundaries

| File | Responsibility |
|---|---|
| `app.py` | Startup, configuration validation, worker lifetime |
| `audio/capture.py` | Windows loopback enumeration and audio capture |
| `audio/segmenter.py` | Manual boundaries, later VAD, resampling, bounded buffering |
| `services/transcriber.py` | Audio-to-Arabic adapter and transcription errors |
| `services/coach.py` | Translation, reply generation, vocabulary/profile instructions |
| `models.py` | Typed audio, transcript, result, and error contracts |
| `controller.py` | Request scheduling, session IDs, cancellation, confirmed context |
| `ui/overlay.py` | Presentation and user controls only |
| `config/profile.json` | Confirmed user facts; leave unknowns empty |
| `config/vocabulary.json` | Reviewed phrases and pronunciation conventions |
| `tests/` | Audio boundaries, stale-result suppression, schema/error handling |
| `eval/` | Reviewed fixtures and manual language evaluation records |

## Result contract and language rules

The application owns `session_id`, `utterance_id`, `transcript_raw`, timestamps, and measured durations. Do not ask the language model to invent these fields.

The generated result contains:

- `heard_transliteration` and `english_meaning`.
- `reply_arabic`, `reply_transliteration`, and `reply_english`, nullable when no usable answer can be formed.
- `needs_clarification`, `missing_profile_fields`, and a short explanation when necessary.

Use beginner Modern Standard Arabic by default. Keep vowelled Arabic and transliteration aligned, and prefer a consistent learner convention such as `aa`, `ii`, and `uu` for long vowels and `sh`, `kh`, and `gh` for those consonants. Review connected pronunciation and sentence-final case endings in the phrase list; do not present simple character substitution as reliable pronunciation.

Do not automatically convert a transcript into a familiar classroom question just because it resembles one. Treat incoming speech as conversation content, not instructions to change application behavior. Do not display an LLM-invented confidence percentage. Use observable problems such as clipping, absent speech, incomplete output, and user correction to trigger review; these checks cannot detect every transcription mistake.

## Scope and estimated effort

The initial scope is short-turn Arabic conversations, endpoint audio capture, translation, reply suggestions, and readable transliteration. Browser-tab isolation, microphone transcription, spoken playback, pronunciation scoring, full conversational voice agents, and polished transparent-window behavior are later features.

Planning estimate: roughly 1–2 focused development days for the first usable release, followed by another 1–2 days for automatic mode, tuning, recovery, and packaging. Re-estimate after testing the actual Windows audio device. The current work environment is Linux, so it cannot establish that Windows loopback or the packaged desktop app works on the target PC.

The next implementation task is milestone 0 followed immediately by the Windows capture diagnostic. Its output must be a correctly recorded browser question before adding the rest of the pipeline.

## Primary references

Sources checked 8 November 2026. These establish interface capabilities; quality and latency targets above remain proposed acceptance criteria.

1. [PyAudioWPatch project and loopback helpers](https://github.com/s0d3s/PyAudioWPatch)
2. [Microsoft: WASAPI loopback recording](https://learn.microsoft.com/en-us/windows/win32/coreaudio/loopback-recording)
3. [OpenAI: file transcription](https://developers.openai.com/api/docs/guides/speech-to-text)
4. [OpenAI: structured model outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
5. [Qt for Python: QThread](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QThread.html)
6. [Silero VAD implementation and supported frame sizes](https://github.com/snakers4/silero-vad/blob/master/src/silero_vad/utils_vad.py)
