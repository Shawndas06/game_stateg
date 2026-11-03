"""Offline asset preparation. Runtime needs only the committed MP3/WebP/MP4 files.

pip install -r requirements-media.txt
python scripts/build_media.py --model /path/to/ru_RU-denis-medium.onnx
"""
import argparse
import json
import subprocess
import tempfile
import wave
from pathlib import Path

import imageio_ffmpeg
from piper import PiperVoice,SynthesisConfig

ROOT=Path(__file__).resolve().parents[1]
MEDIA=ROOT/'web/public/media'
FFMPEG=imageio_ffmpeg.get_ffmpeg_exe()


def ffmpeg(*args):
    subprocess.run([FFMPEG,'-hide_banner','-loglevel','error','-y',*map(str,args)],check=True)


def stamp(seconds):
    ms=round(seconds*1000)
    return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02}.{ms%1000:03}'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--model',required=True);args=parser.parse_args()
    lines=json.loads((ROOT/'web/src/narration.json').read_text())
    voice=PiperVoice.load(args.model,use_cuda=False)
    (MEDIA/'voice').mkdir(parents=True,exist_ok=True)
    for name in ['cover','advisor','succession']:
        source=MEDIA/(name+'.png')
        if source.exists():ffmpeg('-i',source,'-c:v','libwebp','-quality','86',MEDIA/(name+'.webp'))
    with tempfile.TemporaryDirectory(prefix='osman-media-') as folder:
        temp=Path(folder);durations={}
        for key,line in lines.items():
            wav=temp/(key+'.wav')
            with wave.open(str(wav),'wb') as out:voice.synthesize_wav(line['text'],out,SynthesisConfig(length_scale=1.08))
            with wave.open(str(wav),'rb') as data:durations[key]=round(data.getnframes()/data.getframerate(),3)
            ffmpeg('-i',wav,'-af','loudnorm=I=-18:TP=-2:LRA=7','-c:a','libmp3lame','-b:a','64k',MEDIA/'voice'/(key+'.mp3'))
            print('voice',key,durations[key],flush=True)
        keys=['succession_farewell','succession_inherit','succession_orhan']
        joined=temp/'succession.wav';timing=[];elapsed=.8
        with wave.open(str(joined),'wb') as out:
            out.setparams((1,2,22050,0,'NONE','not compressed'));out.writeframes(b'\0\0'*round(22050*.8))
            for key in keys:
                timing.append((elapsed,elapsed+durations[key],lines[key]['text']))
                with wave.open(str(temp/(key+'.wav')),'rb') as data:out.writeframes(data.readframes(data.getnframes()))
                out.writeframes(b'\0\0'*round(22050*.6));elapsed+=durations[key]+.6
        duration=round(elapsed+1,3);frames=round(duration*24)
        captions='WEBVTT\n\n'+'\n\n'.join(f'{stamp(a)} --> {stamp(b)}\n{text}' for a,b,text in timing)+'\n'
        (MEDIA/'succession.vtt').write_text(captions)
        # Original slow camera movement over one illustrated farewell; no claim
        # that this is a live-action historical reconstruction.
        zoom=f'if(lt(on,{frames}*.7),1.45,max(1.02,1.45-(on-{frames}*.7)/({frames}*.3)*.43))'
        pan=f'(iw-iw/zoom)*min(1,on/({frames}*.7))'
        visual=f"scale=1920:-1,zoompan=z='{zoom}':x='{pan}':y=0:d={frames}:s=1280x720:fps=24,fade=t=in:d=0.8,fade=t=out:st={duration-1}:d=1"
        # Burned-in Russian captions remain readable on WebViews without VTT.
        visual+=f",subtitles=filename='{MEDIA/'succession.vtt'}':force_style='FontName=Georgia,FontSize=22,Outline=2,MarginV=32'"
        pad=f'aevalsrc=0.008*sin(2*PI*110*t)+0.006*sin(2*PI*164.81*t)+0.004*sin(2*PI*220*t):s=22050:d={duration}'
        ffmpeg('-loop','1','-i',MEDIA/'succession.webp','-i',joined,'-f','lavfi','-i',pad,
               '-filter_complex',f'[0:v]{visual}[v];[1:a]loudnorm=I=-18:TP=-2:LRA=7[voice];[2:a]afade=t=in:d=2,afade=t=out:st={duration-2}:d=2[pad];[voice][pad]amix=inputs=2:normalize=0[a]',
               '-map','[v]','-map','[a]','-t',duration,'-c:v','libx264','-preset','medium','-crf','24','-pix_fmt','yuv420p','-c:a','aac','-b:a','80k','-movflags','+faststart',MEDIA/'succession.mp4')
        (MEDIA/'manifest.json').write_text(json.dumps({'voice':'ru_RU-denis-medium','clips':durations,'film':{'duration':duration,'width':1280,'height':720}},ensure_ascii=False,indent=2)+'\n')
        print('film',duration,'seconds',flush=True)


if __name__=='__main__':main()
