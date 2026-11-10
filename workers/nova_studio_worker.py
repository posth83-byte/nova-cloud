"""NOVA Studio GPU worker: ComfyUI still generation + cinematic MP4 assembly.

Requirements: ComfyUI running on localhost:8188 with a compatible SD1.5 checkpoint,
Python packages in workers/requirements.txt, and the NOVA worker token in env.
The renderer creates animated camera moves from AI-generated scene frames; it is
not frame-by-frame text-to-video and does not claim Pixar-equivalent quality.
"""
import asyncio, json, os, socket, tempfile, time, urllib.parse, urllib.request, urllib.error, uuid
from pathlib import Path
import edge_tts
import imageio_ffmpeg

BASE=os.getenv("NOVA_STUDIO_URL","https://nova-cloud-c4t9.onrender.com").rstrip("/")
TOKEN=os.getenv("NOVA_STUDIO_WORKER_TOKEN","")
COMFY=os.getenv("COMFYUI_URL","http://127.0.0.1:8188").rstrip("/")
CHECKPOINT=os.getenv("COMFYUI_CHECKPOINT","v1-5-pruned-emaonly.safetensors")
WORKER_ID=socket.gethostname()[:60]
VOICE=os.getenv("NOVA_STUDIO_VOICE","sv-SE-MattiasNeural")
FFMPEG=imageio_ffmpeg.get_ffmpeg_exe()

def http_json(url,payload=None,headers=None,timeout=30):
 data=None if payload is None else json.dumps(payload).encode()
 h={"Accept":"application/json"}
 if data is not None:h["Content-Type"]="application/json"
 if headers:h.update(headers)
 req=urllib.request.Request(url,data=data,headers=h)
 with urllib.request.urlopen(req,timeout=timeout) as r:return json.loads(r.read().decode())

def cloud(path,payload=None):
 return http_json(BASE+path,payload,{"Authorization":"Bearer "+TOKEN,"X-Worker-ID":WORKER_ID},45)

def form_cloud(path,fields,files=None):
 boundary="----NOVA"+uuid.uuid4().hex
 chunks=[]
 for name,value in fields.items():
  chunks.extend([("--"+boundary+"\r\n").encode(),('Content-Disposition: form-data; name="%s"\r\n\r\n'%name).encode(),str(value).encode(),b"\r\n"])
 for name,(filename,content,ctype) in (files or {}).items():
  chunks.extend([("--"+boundary+"\r\n").encode(),('Content-Disposition: form-data; name="%s"; filename="%s"\r\n'%(name,filename)).encode(),("Content-Type: "+ctype+"\r\n\r\n").encode(),content,b"\r\n"])
 chunks.append(("--"+boundary+"--\r\n").encode())
 req=urllib.request.Request(BASE+path,data=b"".join(chunks),headers={"Authorization":"Bearer "+TOKEN,"X-Worker-ID":WORKER_ID,"Content-Type":"multipart/form-data; boundary="+boundary})
 with urllib.request.urlopen(req,timeout=120) as r:return json.loads(r.read().decode())

def heartbeat(job_id,phase,progress):
 form_cloud("/api/nova-studio/worker/%s/heartbeat"%job_id,{"phase":phase,"progress":progress,"worker_id":WORKER_ID})

def make_workflow(prompt,seed,width,height):
 return {
  "1":{"class_type":"CheckpointLoaderSimple","inputs":{"ckpt_name":CHECKPOINT}},
  "2":{"class_type":"CLIPTextEncode","inputs":{"text":prompt,"clip":["1",1]}},
  "3":{"class_type":"CLIPTextEncode","inputs":{"text":"low quality, blurry, deformed hands, extra limbs, text, watermark, logo, bad anatomy","clip":["1",1]}},
  "4":{"class_type":"EmptyLatentImage","inputs":{"width":width,"height":height,"batch_size":1}},
  "5":{"class_type":"KSampler","inputs":{"seed":seed,"steps":22,"cfg":7.0,"sampler_name":"dpmpp_2m","scheduler":"karras","denoise":1.0,"model":["1",0],"positive":["2",0],"negative":["3",0],"latent_image":["4",0]}},
  "6":{"class_type":"VAEDecode","inputs":{"samples":["5",0],"vae":["1",2]}},
  "7":{"class_type":"SaveImage","inputs":{"filename_prefix":"nova_studio","images":["6",0]}}
 }

def generate_image(prompt,seed,width,height,out_path):
 queued=http_json(COMFY+"/prompt",{"prompt":make_workflow(prompt,seed,width,height),"client_id":"nova-"+WORKER_ID})
 pid=queued.get("prompt_id")
 if not pid:raise RuntimeError("ComfyUI returnerade inget prompt_id: "+str(queued)[:300])
 deadline=time.time()+240
 while time.time()<deadline:
  history=http_json(COMFY+"/history/"+pid)
  item=history.get(pid) or {}
  outputs=item.get("outputs") or {}
  for node in outputs.values():
   for image in node.get("images",[]):
    query=urllib.parse.urlencode({"filename":image["filename"],"subfolder":image.get("subfolder",""),"type":image.get("type","output")})
    with urllib.request.urlopen(COMFY+"/view?"+query,timeout=60) as r:Path(out_path).write_bytes(r.read())
    if Path(out_path).stat().st_size<5000:raise RuntimeError("ComfyUI-bilden blev för liten.")
    return
  if item.get("status",{}).get("status_str")=="error":raise RuntimeError("ComfyUI misslyckades med scenen.")
  time.sleep(2)
 raise TimeoutError("ComfyUI överskred 240 sekunder för en scen.")

def scene_prompt(topic,index,total):
 base=("high-end cinematic stylized 3D family animation, expressive appealing character design, "
       "beautiful detailed environment, soft global illumination, rich materials, dramatic but warm lighting, "
       "professional animated feature film composition, coherent art direction, no lettering, no watermark. ")
 if "blå" in topic.casefold() or "gul" in topic.casefold():
  base+=("Recurring characters must stay visually consistent: Blå is a small rounded blue character, calm and thoughtful, "
         "with large friendly eyes; Gul is a small rounded bright yellow character, playful and mischievous, "
         "with large friendly eyes. Both have simple readable silhouettes and expressive faces. ")
 beats=["wide establishing shot introducing the setting","medium shot with clear character action and emotion",
        "dynamic cinematic angle showing the main turning point","warm expressive final shot with a visual punchline"]
 return base+"Story subject: "+topic+". Shot "+str(index+1)+" of "+str(total)+": "+beats[index]+"."

def run_ffmpeg(args):
 import subprocess
 p=subprocess.run([FFMPEG,"-y","-threads","2",*args],capture_output=True,text=True,timeout=240)
 if p.returncode:raise RuntimeError((p.stderr or "FFmpeg failed")[-1200:])

def assemble(images,job,directory):
 aspect=job.get("aspect","9:16")
 width,height=(960,540) if aspect=="16:9" else ((720,720) if aspect=="1:1" else (540,960))
 duration=max(5,int(job.get("duration_seconds",20)))
 per_scene=duration/len(images)
 clips=[]
 for index,image in enumerate(images):
  clip=str(Path(directory)/("scene_%02d.mp4"%index))
  frames=max(24,int(per_scene*24))
  vf=("scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d,"
      "zoompan=z='min(zoom+0.00065,1.08)':d=%d:s=%dx%d:fps=24,format=yuv420p"%
      (width,height,width,height,frames,width,height))
  run_ffmpeg(["-loop","1","-i",image,"-t","%.3f"%per_scene,"-vf",vf,"-an","-c:v","libx264","-preset","veryfast","-crf","27","-pix_fmt","yuv420p",clip])
  clips.append(clip)
 concat_file=str(Path(directory)/"concat.txt")
 Path(concat_file).write_text("".join("file '%s'\n"%p.replace("'","") for p in clips),encoding="utf-8")
 silent=str(Path(directory)/"silent.mp4")
 run_ffmpeg(["-f","concat","-safe","0","-i",concat_file,"-c","copy",silent])
 topic=str(job.get("prompt","din berättelse")).strip().replace("\\n"," ")[:55]
 topic=str(job.get("prompt","din berättelse")).strip().replace("\\n"," ")[:55]
 captions=[
  "Allt börjar med: "+topic+".",
  "En första idé verkar äntligen fungera.",
  "Men så dyker ett oväntat problem upp.",
  "Och det här är bara början på äventyret."
 ]
 audio_parts=[]
 for i,line in enumerate(captions):
  raw_audio=str(Path(directory)/("voice_%02d.mp3"%i))
  padded_audio=str(Path(directory)/("voice_pad_%02d.m4a"%i))
  asyncio.run(edge_tts.Communicate(line,VOICE).save(raw_audio))
  run_ffmpeg(["-i",raw_audio,"-af","apad","-t","%.3f"%per_scene,"-c:a","aac","-b:a","96k",padded_audio])
  audio_parts.append(padded_audio)
 audio_list=str(Path(directory)/"audio_concat.txt")
 Path(audio_list).write_text("".join("file '%s'\\n"%p.replace("'","") for p in audio_parts),encoding="utf-8")
 audio=str(Path(directory)/"narration.m4a")
 run_ffmpeg(["-f","concat","-safe","0","-i",audio_list,"-c","copy",audio])
 final=str(Path(directory)/"film.mp4")
 run_ffmpeg(["-i",silent,"-i",audio,"-map","0:v:0","-map","1:a:0","-c:v","copy","-c:a","aac","-b:a","128k","-shortest","-movflags","+faststart",final])
 srt=str(Path(directory)/"subtitles.srt")
 def stamp(sec):
  ms=int(sec*1000); h=ms//3600000; m=(ms%3600000)//60000; ss=(ms%60000)//1000; milli=ms%1000
  return "%02d:%02d:%02d,%03d"%(h,m,ss,milli)
 with open(srt,"w",encoding="utf-8") as f:
  for i,line in enumerate(captions):
   start=i*per_scene; end=(i+1)*per_scene
   f.write("%d\\n%s --> %s\\n%s\\n\\n"%(i+1,stamp(start),stamp(end),line))
 return final,srt

def process(job):
 job_id=job["id"]
 with tempfile.TemporaryDirectory(prefix="nova-studio-") as directory:
  aspect=job.get("aspect","9:16")
  width,height=(512,512) if aspect=="1:1" else ((768,512) if aspect=="16:9" else (512,768))
  images=[]
  for i in range(4):
   heartbeat(job_id,"generating",5+i*17)
   image=str(Path(directory)/("frame_%02d.png"%i))
   generate_image(scene_prompt(job["prompt"],i,4),abs(hash(job_id+str(i)))%(2**32),width,height,image)
   images.append(image)
  heartbeat(job_id,"assembling",78)
  video,srt=assemble(images,job,directory)
  heartbeat(job_id,"uploading",92)
  video_bytes=Path(video).read_bytes()
  srt_bytes=Path(srt).read_bytes()
  result=form_cloud("/api/nova-studio/worker/%s/complete"%job_id,
    {"worker_id":WORKER_ID},
    {"video":("film.mp4",video_bytes,"video/mp4"),"subtitles":("subtitles.srt",srt_bytes,"text/plain")})
  print("NOVA Studio färdig:",job_id,result)

def main():
 if not TOKEN:raise SystemExit("NOVA_STUDIO_WORKER_TOKEN saknas i Windows miljövariabler.")
 try:http_json(COMFY+"/system_stats")
 except Exception as exc:raise SystemExit("ComfyUI svarar inte på localhost:8188: "+str(exc))
 print("NOVA Studio worker online. Checkpoint:",CHECKPOINT,"GPU ansluten via ComfyUI.")
 while True:
  try:
   claim=cloud("/api/nova-studio/worker/claim",{})
   job=claim.get("job")
   if job:
    try:process(job)
    except Exception as exc:
     try:form_cloud("/api/nova-studio/worker/%s/fail"%job["id"],{"worker_id":WORKER_ID,"error":str(exc)[:1200]})
     except Exception as report_exc:print("Kunde inte rapportera fel:",report_exc)
     print("Jobbet misslyckades:",str(exc)[:400])
   else:time.sleep(8)
  except urllib.error.HTTPError as exc:
   print("Cloud HTTP-fel:",exc.code);time.sleep(15)
  except Exception as exc:
   print("Worker-fel:",str(exc)[:300]);time.sleep(15)
if __name__=="__main__":main()
