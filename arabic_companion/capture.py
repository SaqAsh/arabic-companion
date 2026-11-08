"""Bounded Windows playback capture; never opens a microphone."""
import argparse
import sys
import wave
from pathlib import Path


def record(seconds=10, device=None, output='recordings/question.wav'):
    if sys.platform != 'win32':
        raise RuntimeError('WASAPI capture requires Windows.')
    if not 1 <= seconds <= 20:
        raise ValueError('Capture duration must be between 1 and 20 seconds.')
    import pyaudiowpatch as pa
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    with pa.PyAudio() as audio:
        devices = list(audio.get_loopback_device_info_generator())
        if device is None:
            info = audio.get_default_wasapi_loopback()
        else:
            info = next((d for d in devices if d['index'] == device), None)
            if info is None:
                raise ValueError('Select a loopback device from --list.')
        rate = int(info['defaultSampleRate'])
        channels = int(info['maxInputChannels'])
        print(f"Capturing {info['name']} for {seconds} seconds", flush=True)
        with audio.open(format=pa.paInt16, channels=channels, rate=rate,
                        input=True, input_device_index=info['index'],
                        frames_per_buffer=1024) as stream:
            with wave.open(str(path), 'wb') as wav:
                wav.setnchannels(channels)
                wav.setsampwidth(audio.get_sample_size(pa.paInt16))
                wav.setframerate(rate)
                remaining = rate * seconds
                while remaining:
                    count = min(1024, remaining)
                    wav.writeframesraw(stream.read(count))
                    remaining -= count
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--device', type=int)
    parser.add_argument('--seconds', type=int, default=10)
    parser.add_argument('--output', default='recordings/question.wav')
    args = parser.parse_args()
    try:
        if args.list:
            if sys.platform != 'win32':
                raise RuntimeError('Device enumeration requires Windows.')
            import pyaudiowpatch as pa
            with pa.PyAudio() as audio:
                for d in audio.get_loopback_device_info_generator():
                    print(f"{d['index']}: {d['name']}")
        else:
            print(f'Saved: {record(args.seconds, args.device, args.output)}')
    except (RuntimeError, ValueError, OSError) as exc:
        parser.exit(1, f'Audio error: {exc}\n')


if __name__ == '__main__':
    main()
