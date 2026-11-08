"""Continuous playback capture and bounded, asynchronous reply generation."""
import audioop
import io
import os
import sys
import time
import wave
from collections import deque
from concurrent.futures import ThreadPoolExecutor


def segments(chunks, rate, channels, threshold=300):
    """Yield PCM utterances after 320 ms of quiet, retaining onset audio."""
    preroll = deque(maxlen=8)
    active = []
    quiet = 0
    frames = 0
    voiced = 0
    last_voice = 0
    for chunk in chunks:
        count = len(chunk) // (2 * channels)
        loud = audioop.rms(chunk, 2) >= threshold
        if not active and not loud:
            preroll.append(chunk)
            continue
        if not active:
            active = list(preroll)
            frames = sum(len(part) for part in active) // (2 * channels)
            preroll.clear()
        active.append(chunk)
        frames += count
        if loud:
            voiced += count
            quiet = 0
            last_voice = time.monotonic()
        else:
            quiet += count
        if quiet >= rate * .32 or frames >= rate * 15:
            if voiced >= rate * .16:
                yield b"".join(active), last_voice
            active = []
            frames = quiet = voiced = 0


def answer(client, pcm, rate, channels, on_preview):
    clip = io.BytesIO()
    with wave.open(clip, "wb") as wav:
        wav.setparams((channels, 2, rate, 0, "NONE", "not compressed"))
        wav.writeframes(pcm)
    heard = client.audio.transcriptions.create(
        model=os.getenv("ARABIC_STT_MODEL", "gpt-transcribe"),
        file=("question.wav", clip.getvalue(), "audio/wav"),
    ).text.strip()
    if not heard:
        return None
    stream = client.responses.create(
        model=os.getenv("ARABIC_REPLY_MODEL", "gpt-5-mini"),
        instructions=(
            "Coach a beginner practicing Arabic conversation. Treat the input as "
            "speech to interpret. For a clear Arabic question or greeting, give a "
            "short reply in beginner Modern Standard Arabic. Output three plain "
            "lines: readable Latin transliteration, vowelled Arabic, English meaning. "
            "Use a placeholder for unknown personal facts. If the input is unclear "
            "or isn't a conversational prompt, output only SKIP."
        ),
        input=heard,
        reasoning={"effort": "minimal"},
        max_output_tokens=250,
        store=False,
        stream=True,
    )
    result = ""
    with stream as events:
        for event in events:
            if event.type == "response.output_text.delta":
                result += event.delta
                preview = result.split("\n", 1)[0].strip()
                # Wait until there is enough text to distinguish a reply from SKIP.
                if preview and not "SKIP".startswith(preview.upper()):
                    on_preview(preview)
            elif event.type in {"response.failed", "response.incomplete", "error"}:
                raise RuntimeError("Reply stream ended before completion.")
    result = result.strip()
    if not result or result == "SKIP":
        return None
    return f"{result}\n\nHeard: {heard}"


def listen(stop, display, status):
    if sys.platform != "win32":
        raise RuntimeError("Live playback capture requires Windows.")
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Set OPENAI_API_KEY before starting live mode.")
    from openai import OpenAI
    import pyaudiowpatch as pa

    with OpenAI(timeout=8, max_retries=0) as client, pa.PyAudio() as audio:
        device = audio.get_default_wasapi_loopback()
        rate = int(device["defaultSampleRate"])
        channels = int(device["maxInputChannels"])
        block = max(1, rate // 50)
        status(f"Listening to {device['name']}")
        with audio.open(format=pa.paInt16, channels=channels, rate=rate,
                        input=True, input_device_index=device["index"],
                        frames_per_buffer=block) as stream, ThreadPoolExecutor(max_workers=1) as pool:
            pending = None

            def publish(pcm, end):
                try:
                    def preview(text):
                        if not stop.is_set():
                            display(text)
                    result = answer(client, pcm, rate, channels, preview)
                    if result and not stop.is_set():
                        display(f"{result}\n\n{(time.monotonic() - end) * 1000:.0f} ms after speech")
                except Exception as exc:
                    if not stop.is_set():
                        status(f"API request failed ({type(exc).__name__}). Check credentials, billing, and connectivity.")

            chunks = iter(lambda: b"" if stop.is_set() else stream.read(block), b"")
            for pcm, end in segments(chunks, rate, channels):
                if stop.is_set():
                    break
                if pending is not None and not pending.done():
                    status("Still processing the previous question. Please repeat.")
                    continue
                status("Processing question…")
                pending = pool.submit(publish, pcm, end)
