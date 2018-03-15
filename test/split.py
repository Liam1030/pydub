import argparse
import os
from pydub import AudioSegment
from pydub.silence import split_on_silence

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--path')
    args = parser.parse_args()
    wav_file = args.path
    dir_name = os.path.dirname(args.path)
    dirs = dir_name.split('/')

    speech = AudioSegment.from_wav(wav_file)
    chunks = split_on_silence(speech, min_silence_len=300, silence_thresh=-40,
                              seek_step=100, min_voice_len=4000, max_voice_len=16000)
    for i in range(0, len(chunks)):
        chunks[i].export("%s/%s_%03d.wav" % (dir_name, dirs[-1], i), format='wav', parameters=["-ar", "16000", "-ac", "1"])

if __name__ == '__main__':
    main()
