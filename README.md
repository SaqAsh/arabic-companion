# Arabic Companion

Windows desktop assistant for beginner Arabic conversations. Initial milestone implemented: a floating window and a bounded WASAPI audio capture diagnostic. Translation, transcription, and response generation are pending. No API key is needed for this milestone.

## Run on Windows (PowerShell)

Install 64-bit Python 3.11, extract this repository, and open PowerShell in its directory:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\arabic-companion.exe
```

Play Arabic audio in Chrome and click **Capture 10 seconds**. Once recording finishes, open `recordings/question.wav` to verify sound and playback speed. This diagnostic intentionally saves audio locally; recordings are excluded from Git. It captures the selected playback device, including other applications, and does not open your microphone.

For a different playback device:

```powershell
.\.venv\Scripts\arabic-audio.exe --list
.\.venv\Scripts\arabic-audio.exe --device 12 --seconds 10
```

Replace 12 with an actual loopback index from the list. Capture uses the device's supported format. Do not replay a recording during another capture. If capture fails, verify Chrome is using the same output device and that another application has not opened the device exclusively.

## Development status

- Implemented: package entry points, always-on-top window, background 10-second capture, device listing and CLI selection, actionable errors.
- Next: WAV-to-Arabic transcription, typed translation/reply contract, then overlay integration.
- Later: automatic speech boundaries, cancellation, device selection in the GUI, evaluation fixtures, executable packaging.
- Validation here: Python compilation and CLI argument/platform checks. Actual WASAPI behavior and GUI rendering require Windows validation; neither has been verified on a Windows machine yet.

See PLAN.md for the complete implementation specification. This starter implements a bounded diagnostic, not every planned control.

## GitHub

This archive includes an initialized Git repository and its first commit. No GitHub remote has been created. After creating an empty private repository named `arabic-companion`, connect it:

```powershell
git remote add origin https://github.com/YOUR_USERNAME/arabic-companion.git
git push -u origin main
```

## Live practice

Set `OPENAI_API_KEY` in your PowerShell session before launching. Start the
app and click **Start live practice**. Audio above the level threshold opens a
clip, and roughly 320 ms of quiet closes it. Clips are sent to the transcription
API in memory, and the suggested reply and measured delay appear in the window.
The threshold detects audio level, so music and other apps can trigger capture.
Use the mode with practice audio you are allowed to send to the API.

The defaults are `gpt-transcribe` and `gpt-5-mini`. You can override them
with `ARABIC_STT_MODEL` and `ARABIC_REPLY_MODEL`. API use requires billing.
