"""Record a real xterm executing terminal_walkthrough.sh; run under xvfb-run."""
from pathlib import Path
import subprocess, time
from PIL import ImageGrab, Image, ImageDraw, ImageFont


def main():
    directory = Path(__file__).parent
    dest = directory / 'cli_walkthrough.mp4'
    term = subprocess.Popen(['xterm','-T','SmartStudy CLI - Real Execution',
           '-geometry','120x34+10+5','-fa','DejaVu Sans Mono','-fs','12',
           '-bg','#111927','-fg','#e8f0ff','-e','bash',str(directory/'terminal_walkthrough.sh')])
    enc = subprocess.Popen(['ffmpeg','-y','-v','error','-f','rawvideo','-pixel_format','rgb24',
       '-video_size','1120x840','-framerate','1','-i','-', '-c:v','libx264',
       '-preset','veryfast','-crf','28','-pix_fmt','yuv420p',str(dest)],stdin=subprocess.PIPE)
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',16)
    try:
        for i in range(48):  # 48-second terminal capture at 1fps
            time.sleep(0.9)
            screenshot = ImageGrab.grab(bbox=(0,0,1120,795)).convert('RGB')
            canvas = Image.new('RGB',(1120,840),'#101929')
            canvas.paste(screenshot,(0,0))
            ImageDraw.Draw(canvas).text((20,810), 'F02 / F05 / F06 / F07 / F08 / F10 / F12  |  Actual CLI output',
                                        font=font,fill='white')
            enc.stdin.write(canvas.tobytes())
    finally:
        if enc.stdin: enc.stdin.close()
        enc.wait(timeout=20)
        if term.poll() is None: term.terminate()
    print(dest)


if __name__ == '__main__': main()
