# Run in the Higgsfield media sandbox after staging the exact source videos.
# This recipe uses bidirectional motion compensation, not an opacity dissolve.
# Upload confirmed outputs through the provider separately; never store signed URLs.
import cv2, numpy as np, subprocess, os, json
from pathlib import Path
cv2.setNumThreads(2)
root=Path('/home/user/vtech-v4-flow-final');root.mkdir(exist_ok=True)
src=Path('/home/user/vtech-v4-matched')
def run(args):
    subprocess.run(args,check=True,stdout=subprocess.DEVNULL)
def encode_args(out,crf):
    return ['-an','-c:v','libx264','-preset','fast','-crf',str(crf),'-threads','2','-g','6','-keyint_min','6','-sc_threshold','0','-pix_fmt','yuv420p','-movflags','+faststart',str(out)]
metadata=[]
for variant,w,h,crf in [('desktop',1912,1080,21),('mobile',812,1440,22)]:
    d=root/variant;d.mkdir(exist_ok=True)
    for part,source in [('intro',src/f'intro-{variant}.mp4'),('bridge',src/f'bridge-matched-{variant}.mp4')]:
        run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(source),'-vf',f'fps=24,scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1',*encode_args(d/f'{part}.mp4',crf)])
    cap=cv2.VideoCapture(str(d/'intro.mp4'))
    count=int(cap.get(cv2.CAP_PROP_FRAME_COUNT));cap.set(cv2.CAP_PROP_POS_FRAMES,count-1)
    ok,a=cap.read();cap.release()
    if not ok:raise RuntimeError('Missing intro end')
    cap=cv2.VideoCapture(str(d/'bridge.mp4'));ok,b=cap.read();cap.release()
    if not ok:raise RuntimeError('Missing bridge start')
    small_size=(w//2,h//2)
    ga=cv2.cvtColor(cv2.resize(a,small_size),cv2.COLOR_BGR2GRAY)
    gb=cv2.cvtColor(cv2.resize(b,small_size),cv2.COLOR_BGR2GRAY)
    dis=cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
    ab=cv2.resize(dis.calc(ga,gb,None),(w,h))*2
    ba=cv2.resize(dis.calc(gb,ga,None),(w,h))*2
    x,y=np.meshgrid(np.arange(w,dtype=np.float32),np.arange(h,dtype=np.float32))
    samples=[]
    last=a
    for k in range(1,7):
        t=k/7
        wa=cv2.remap(a,x-t*ab[:,:,0],y-t*ab[:,:,1],cv2.INTER_CUBIC,borderMode=cv2.BORDER_REPLICATE)
        wb=cv2.remap(b,x-(1-t)*ba[:,:,0],y-(1-t)*ba[:,:,1],cv2.INTER_CUBIC,borderMode=cv2.BORDER_REPLICATE)
        frame=cv2.addWeighted(wa,1-t,wb,t,0)
        cv2.imwrite(str(d/f'flow-{k:02d}.png'),frame)
        samples.append({'t':round(t,4),'mae_from_A':round(float(np.abs(frame.astype(float)-a).mean()),3),'mae_from_B':round(float(np.abs(frame.astype(float)-b).mean()),3),'step_mae':round(float(np.abs(frame.astype(float)-last).mean()),3)})
        last=frame
        if k==3:
            pw=720 if variant=='desktop' else 360
            cv2.imwrite(str(root/f'mid-{variant}.jpg'),cv2.resize(frame,(pw,round(pw*h/w))),[cv2.IMWRITE_JPEG_QUALITY,85])
    if any(s['step_mae']<.1 for s in samples):raise RuntimeError('Nonmoving interpolation')
    if samples[0]['mae_from_A']>=samples[-1]['mae_from_A'] or samples[0]['mae_from_B']<=samples[-1]['mae_from_B']:
        raise RuntimeError('Interpolation does not progress from A to B')
    run(['ffmpeg','-hide_banner','-loglevel','error','-y','-framerate','24','-start_number','1','-i',str(d/'flow-%02d.png'),'-frames:v','6',*encode_args(d/'flow.mp4',crf)])
    (d/'concat.txt').write_text("file 'intro.mp4'\nfile 'flow.mp4'\nfile 'bridge.mp4'\n")
    out=root/f'camera-{variant}.mp4'
    run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',str(d/'concat.txt'),'-c','copy','-movflags','+faststart',str(out)])
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate,nb_frames:format=duration,size','-of','json',str(out)]))
    metadata.append({'variant':variant,'probe':probe,'flow_samples':samples,'flow_frames':6,'intro_frames':count})
(root/'metadata.json').write_text(json.dumps(metadata,indent=2))
print(json.dumps(metadata))

