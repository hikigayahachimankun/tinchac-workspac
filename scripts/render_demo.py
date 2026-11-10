"""Mux real browser capture with local Vietnamese TTS; no model/service calls.

ffmpeg and espeak-ng are external authoring tools, not app dependencies.
"""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile
import textwrap
import wave

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--video', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--ffmpeg', default='ffmpeg')
    parser.add_argument('--espeak', default='espeak-ng')
    parser.add_argument('--espeak-data-parent', type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    storyboard = json.loads((ROOT / 'docs/demo_storyboard.json').read_text())
    rate = 22050
    audio = bytearray(220 * rate * 2)
    durations = []
    with tempfile.TemporaryDirectory(prefix='tinchac-demo-audio-') as directory:
        for index, scene in enumerate(storyboard):
            text, wav = Path(directory) / f'{index}.txt', Path(directory) / f'{index}.wav'
            text.write_text(scene['text'])
            command = [args.espeak, '-v', 'vi', '-s', '165', '-f', str(text), '-w', str(wav)]
            if args.espeak_data_parent:
                command.append('--path=' + str(args.espeak_data_parent))
            subprocess.run(command, check=True)
            with wave.open(str(wav)) as speech:
                assert (speech.getframerate(), speech.getnchannels(), speech.getsampwidth()) == (rate, 1, 2)
                data = speech.readframes(speech.getnframes())
            duration = len(data) / (rate * 2)
            if duration > scene['end'] - scene['start']:
                raise ValueError(f'Speech exceeds scene {index}: {duration:.2f}s')
            offset = scene['start'] * rate * 2
            audio[offset:offset + len(data)] = data
            durations.append(round(duration, 3))
        combined = Path(directory) / 'narration.wav'
        with wave.open(str(combined), 'wb') as destination:
            destination.setparams((1, 2, rate, 0, 'NONE', 'not compressed'))
            destination.writeframes(audio)
        # Watermark independent of scroll position; captions were captured in the browser.
        from PIL import Image, ImageDraw, ImageFont
        watermark = Path(directory) / 'fixture.png'
        stamp = Image.new('RGBA', (475, 40), (18, 43, 42, 240))
        draw = ImageDraw.Draw(stamp)
        draw.text((12, 7), 'FIXTURE · Local RC · Không gọi Gemini', fill='white',
                  font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 20))
        stamp.save(watermark)
        # Editorial end card updates the acceptance status after independent CI.
        end_card = Path(directory) / 'end-card.png'
        card = Image.new('RGBA', (1280, 126), (18, 43, 42, 255))
        pen = ImageDraw.Draw(card)
        font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 20)
        pen.text((32, 12), 'Giới hạn trước bàn giao T16 / T17 · FIXTURE RC', fill='white', font=font)
        pen.multiline_text((32, 43), '\n'.join(textwrap.wrap(storyboard[-1]['caption'], width=105)),
                           fill='white', font=font, spacing=4)
        card.save(end_card)
        subprocess.run([args.ffmpeg, '-n', '-i', str(args.video), '-i', str(combined),
            '-i', str(watermark), '-i', str(end_card), '-filter_complex',
            "[0:v][2:v]overlay=W-w-12:12[marked];[marked][3:v]overlay=0:H-h:enable='gte(t,205)',fps=25[v]",
            '-map', '[v]', '-map', '1:a', '-t', '220', '-c:v', 'libx264', '-preset', 'fast',
            '-crf', '27', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '96k',
            '-map_metadata', '-1', '-movflags', '+faststart', str(args.output)], check=True,
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    print(json.dumps({'output': str(args.output), 'duration_seconds': 220,
                      'narration': 'local espeak-ng vi synthetic voice', 'scene_speech_seconds': durations}, indent=2))


if __name__ == '__main__':
    main()
