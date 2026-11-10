"""NOVA Studio Windows worker bootstrap; only outbound cloud + localhost ComfyUI."""
import json,os,socket,time,urllib.request,urllib.error
BASE=os.getenv("NOVA_STUDIO_URL","https://nova-cloud-c4t9.onrender.com").rstrip("/")
TOKEN=os.getenv("NOVA_STUDIO_WORKER_TOKEN","")
COMFY=os.getenv("COMFYUI_URL","http://127.0.0.1:8188").rstrip("/")
WORKER_ID=socket.gethostname()[:60]
def call(path,payload=None):
 data=None if payload is None else json.dumps(payload).encode()
 req=urllib.request.Request(BASE+path,data=data,headers={"Authorization":"Bearer "+TOKEN,"Content-Type":"application/json","X-Worker-ID":WORKER_ID})
 with urllib.request.urlopen(req,timeout=30) as r:return json.loads(r.read().decode())
def main():
 if not TOKEN:raise SystemExit("NOVA_STUDIO_WORKER_TOKEN saknas i Windows miljövariabler.")
 try:
  with urllib.request.urlopen(COMFY+"/system_stats",timeout=5) as r:json.loads(r.read().decode())
 except Exception as e:raise SystemExit("ComfyUI svarar inte på localhost: "+str(e))
 print("NOVA Studio worker ansluten. Väntar på jobb.")
 while True:
  try:
   item=call("/api/nova-studio/worker/claim",{})
   job=item.get("job")
   if job:
    # Fail closed: this bootstrap does not fake a render. A versioned ComfyUI
    # graph + FFmpeg adapter must be installed before a job can be completed.
    print("Mottog jobb",job.get("id"),"– renderadapter saknas ännu.")
    time.sleep(10)
   else:time.sleep(8)
  except urllib.error.HTTPError as e:
   print("Cloud HTTP",e.code);time.sleep(15)
  except Exception as e:
   print("Worker-fel:",str(e)[:250]);time.sleep(15)
if __name__=="__main__":main()
