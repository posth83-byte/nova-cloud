"""NOVA Studio control plane. Worker-only routes use a server-side bearer secret."""
import hmac, json, os, re, urllib.error, urllib.parse, urllib.request, uuid
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Header, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask
from pydantic import BaseModel, Field

router=APIRouter()
URL=os.getenv("SUPABASE_URL","").strip().rstrip("/")
KEY=os.getenv("SUPABASE_SECRET_KEY","").strip() or os.getenv("SUPABASE_SERVICE_ROLE_KEY","").strip()
TOKEN=os.getenv("NOVA_STUDIO_WORKER_TOKEN","").strip()
BUCKET="nova-videos"
MAX_BYTES=48*1024*1024

class JobRequest(BaseModel):
 prompt:str=Field(min_length=8,max_length=2400)
 style:str=Field(default="cinematic-family-animation",max_length=80)
 aspect:str=Field(default="9:16",pattern="^(9:16|16:9|1:1)$")
 duration_seconds:int=Field(default=20,ge=5,le=180)

def db(method,path,data=None,ctype="application/json",prefer=None):
 if not URL or not KEY: raise RuntimeError("Supabase saknas för NOVA Studio.")
 headers={"apikey":KEY,"Authorization":"Bearer "+KEY,"Accept":"application/json"}
 if data is not None: headers["Content-Type"]=ctype
 if prefer: headers["Prefer"]=prefer
 req=urllib.request.Request(URL+path,data=data,headers=headers,method=method)
 try:
  with urllib.request.urlopen(req,timeout=35) as res:
   raw=res.read(2_000_000); return json.loads(raw.decode()) if raw else []
 except urllib.error.HTTPError as exc:
  raise RuntimeError("Supabase HTTP %s: %s"%(exc.code,exc.read().decode(errors="replace")[:700])) from exc

def auth(value):
 token=(value or "").removeprefix("Bearer ").strip()
 if not TOKEN or not hmac.compare_digest(token,TOKEN):
  raise HTTPException(status_code=401,detail="Ogiltig NOVA Studio worker-token.")

def get_row(job_id):
 rows=db("GET","/rest/v1/nova_studio_jobs?id=eq.%s&select=*"%urllib.parse.quote(job_id))
 return rows[0] if rows else None

@router.get("/api/nova-studio/health")
def health():
 online=[]
 if URL and KEY:
  try:
   cutoff=urllib.parse.quote((datetime.now(timezone.utc)-timedelta(seconds=60)).isoformat())
   online=db("GET","/rest/v1/nova_studio_workers?last_seen=gte.%s&select=worker_id,status,current_job,last_seen"%cutoff)
  except Exception: online=[]
 return {"service":"nova-studio-control-plane","status":"online","worker_token_configured":bool(TOKEN),
         "supabase_configured":bool(URL and KEY),"workers_online":len(online),
         "worker_online_count":len(online),"generation":"local-comfyui-worker","paid_generation_api":False}

@router.post("/api/nova-studio/jobs")
def create_job(request:JobRequest):
 try:
  db("POST","/rest/v1/nova_studio_jobs",json.dumps({"prompt":request.prompt.strip(),"style":request.style,
    "aspect":request.aspect,"duration_seconds":request.duration_seconds}).encode(),prefer="return=representation")
  if not isinstance(rows,list) or not rows: raise RuntimeError("Jobbet sparades inte.")
  return {"status":"queued","job":{k:rows[0].get(k) for k in ("id","status","phase","progress","created_at")},"engine":"NOVA Studio local GPU"}
 except Exception as exc: raise HTTPException(status_code=503,detail=str(exc)[:700]) from exc

@router.get("/api/nova-studio/jobs/{job_id}")
def job_status(job_id:str):
 try:
  row=get_row(job_id)
  if not row: raise HTTPException(status_code=404,detail="Jobbet hittades inte.")
  return {k:row.get(k) for k in ("id","status","phase","progress","result","error","created_at","updated_at","completed_at")}
 except HTTPException: raise
 except Exception as exc: raise HTTPException(status_code=503,detail=str(exc)[:700]) from exc

@router.post("/api/nova-studio/worker/claim")
def claim(authorization:str=Header(default=""),x_worker_id:str=Header(default="")):
 auth(authorization)
 worker_id=(x_worker_id or "").strip()[:80] or "nova-worker-"+uuid.uuid4().hex[:12]
 if not re.fullmatch(r"[A-Za-z0-9_.:-]{3,80}",worker_id): raise HTTPException(status_code=400,detail="Ogiltigt worker-id.")
 try:
  db("POST","/rest/v1/rpc/recover_stale_nova_studio_jobs",json.dumps({"p_stale_seconds":240}).encode())
  rows=db("POST","/rest/v1/rpc/claim_nova_studio_job",json.dumps({"p_worker_id":worker_id}).encode())
  if isinstance(rows,dict): rows=[rows]
  return {"job":rows[0] if rows else None,"worker_id":worker_id}
 except Exception as exc: raise HTTPException(status_code=503,detail=str(exc)[:700]) from exc

@router.post("/api/nova-studio/worker/{job_id}/heartbeat")
def heartbeat(job_id:str,phase:str=Form(...),progress:int=Form(...),worker_id:str=Form(...),authorization:str=Header(default="")):
 auth(authorization)
 if phase not in ("generating","assembling","uploading") or not 0<=progress<=99:
  raise HTTPException(status_code=400,detail="Ogiltig fas eller progress.")
 try:
  rows=db("PATCH","/rest/v1/nova_studio_jobs?id=eq.%s&worker_id=eq.%s&status=in.(leased,generating,assembling,uploading)"%(urllib.parse.quote(job_id),urllib.parse.quote(worker_id)),
   json.dumps({"status":phase,"phase":phase.capitalize(),"progress":progress,"locked_at":datetime.now(timezone.utc).isoformat(),
   "updated_at":datetime.now(timezone.utc).isoformat()}).encode(),prefer="return=representation")
  db("PATCH","/rest/v1/nova_studio_workers?worker_id=eq.%s"%urllib.parse.quote(worker_id),
     json.dumps({"status":"busy","current_job":job_id,"last_seen":datetime.now(timezone.utc).isoformat()}).encode())
  return {"updated":bool(rows) if isinstance(rows,list) else True}
 except Exception as exc: raise HTTPException(status_code=503,detail=str(exc)[:700]) from exc

@router.post("/api/nova-studio/worker/{job_id}/complete")
async def complete(job_id:str,video:UploadFile=File(...),subtitles:UploadFile=File(None),worker_id:str=Form(...),authorization:str=Header(default="")):
 auth(authorization)
 if video.content_type not in ("video/mp4","application/octet-stream"):
  raise HTTPException(status_code=415,detail="Videofilen måste vara MP4.")
 data=await video.read(MAX_BYTES+1)
 if len(data)<1024 or len(data)>MAX_BYTES or data[4:8]!=b"ftyp":
  raise HTTPException(status_code=400,detail="MP4-filen är tom, för stor eller ogiltig.")
 try:
  row=get_row(job_id)
  if not row or row.get("worker_id") != worker_id or row.get("status") not in ("leased","generating","assembling","uploading"):
   raise HTTPException(status_code=409,detail="Jobbet är inte aktivt.")
  prefix="studio/%s/"%job_id; video_path=prefix+"film.mp4"
  db("POST","/storage/v1/object/"+BUCKET+"/"+video_path,data,"video/mp4")
  result={"video_path":video_path,"video_bytes":len(data)}
  if subtitles:
   srt=await subtitles.read(2_000_001)
   if len(srt)>2_000_000: raise HTTPException(status_code=413,detail="Undertextfilen är för stor.")
   srt_path=prefix+"subtitles.srt"
   db("POST","/storage/v1/object/"+BUCKET+"/"+srt_path,srt,"text/plain; charset=utf-8")
   result["subtitles_path"]=srt_path
  db("PATCH","/rest/v1/nova_studio_jobs?id=eq.%s&worker_id=eq.%s"%(urllib.parse.quote(job_id),urllib.parse.quote(worker_id)),
   json.dumps({"status":"completed","phase":"Färdig – MP4 sparad privat","progress":100,"result":result,
    "completed_at":datetime.now(timezone.utc).isoformat(),"updated_at":datetime.now(timezone.utc).isoformat()}).encode(),prefer="return=representation")
  db("PATCH","/rest/v1/nova_studio_workers?worker_id=eq.%s"%urllib.parse.quote(worker_id),
      json.dumps({"status":"idle","current_job":None,"last_seen":datetime.now(timezone.utc).isoformat()}).encode())
  return {"status":"completed","result":result}
 except HTTPException: raise
 except Exception as exc: raise HTTPException(status_code=503,detail=str(exc)[:700]) from exc

@router.post("/api/nova-studio/worker/{job_id}/fail")
def fail(job_id:str,error:str=Form(...),worker_id:str=Form(...),authorization:str=Header(default="")):
 auth(authorization)
 try:
  db("PATCH","/rest/v1/nova_studio_jobs?id=eq.%s&worker_id=eq.%s"%(urllib.parse.quote(job_id),urllib.parse.quote(worker_id)),
   json.dumps({"status":"failed","phase":"Arbetaren rapporterade fel","error":error[:1200],
    "updated_at":datetime.now(timezone.utc).isoformat()}).encode(),prefer="return=representation")
  db("PATCH","/rest/v1/nova_studio_workers?worker_id=eq.%s"%urllib.parse.quote(worker_id),
      json.dumps({"status":"idle","current_job":None,"last_seen":datetime.now(timezone.utc).isoformat()}).encode())
  return {"status":"failed"}
 except Exception as exc: raise HTTPException(status_code=503,detail=str(exc)[:700]) from exc

def _stream_private_object(path,media_type,filename):
 if not URL or not KEY: raise HTTPException(status_code=503,detail="Privat lagring är inte konfigurerad.")
 url=URL+"/storage/v1/object/"+BUCKET+"/"+path
 req=urllib.request.Request(url,headers={"apikey":KEY,"Authorization":"Bearer "+KEY})
 try: upstream=urllib.request.urlopen(req,timeout=60)
 except urllib.error.HTTPError as exc:
  if exc.code==404: raise HTTPException(status_code=404,detail="Filen finns inte i privat lagring.")
  raise HTTPException(status_code=502,detail="Kunde inte hämta den färdiga filen.")
 return StreamingResponse(iter(lambda:upstream.read(65536),b""),media_type=media_type,
   headers={"Content-Disposition":'inline; filename="%s"'%filename},
   background=BackgroundTask(upstream.close))

@router.get("/api/nova-studio/jobs/{job_id}/video")
def studio_video(job_id:str):
 try:
  row=get_row(job_id)
  if not row or row.get("status")!="completed" or not (row.get("result") or {}).get("video_path"):
   raise HTTPException(status_code=404,detail="Färdig video hittades inte.")
  return _stream_private_object(row["result"]["video_path"],"video/mp4","nova-studio.mp4")
 except HTTPException: raise
 except Exception as exc: raise HTTPException(status_code=503,detail=str(exc)[:700]) from exc

@router.get("/api/nova-studio/jobs/{job_id}/subtitles")
def studio_subtitles(job_id:str):
 try:
  row=get_row(job_id)
  path=(row.get("result") or {}).get("subtitles_path") if row else None
  if not path: raise HTTPException(status_code=404,detail="Undertexter hittades inte.")
  return _stream_private_object(path,"text/plain; charset=utf-8","nova-studio.srt")
 except HTTPException: raise
 except Exception as exc: raise HTTPException(status_code=503,detail=str(exc)[:700]) from exc
