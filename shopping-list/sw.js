const CACHE="shopping-list-v6";
const APP_FILES=["./","./index.html","./manifest.webmanifest","./icon.svg"];
self.addEventListener("install",event=>event.waitUntil((async()=>{
 const cache=await caches.open(CACHE);
 await cache.addAll(APP_FILES);
 await self.skipWaiting();
})()));
self.addEventListener("activate",event=>event.waitUntil((async()=>{
 const keys=await caches.keys();
 await Promise.all(keys.filter(key=>key.startsWith("shopping-list-")&&key!==CACHE).map(key=>caches.delete(key)));
 await self.clients.claim();
})()));
self.addEventListener("fetch",event=>{
 const request=event.request;
 if(request.method!=="GET"||new URL(request.url).origin!==self.location.origin)return;
 if(request.mode==="navigate"){
  event.respondWith(fetch(request).then(response=>{
   if(response.ok){const copy=response.clone();caches.open(CACHE).then(cache=>cache.put("./",copy))}
   return response;
  }).catch(()=>caches.match("./")));
  return;
 }
 event.respondWith(caches.match(request).then(cached=>cached||fetch(request)));
});

self.addEventListener("push",event=>{
 let data={};
 try{data=event.data?event.data.json():{}}catch(_){}
 const title=data.title||"Ny vara i inköpslistan";
 const options={
  body:data.body||"En ny vara har lagts till",
  icon:"./icon.svg",
  badge:"./icon.svg",
  tag:data.tag||"shopping-list-update",
  renotify:true,
  data:{url:data.url||"./"}
 };
 event.waitUntil(self.registration.showNotification(title,options));
});

self.addEventListener("notificationclick",event=>{
 event.notification.close();
 event.waitUntil((async()=>{
  const windows=await self.clients.matchAll({type:"window",includeUncontrolled:true});
  for(const client of windows){
   if("focus" in client)return client.focus();
  }
  if(self.clients.openWindow)return self.clients.openWindow("./");
 })());
});
