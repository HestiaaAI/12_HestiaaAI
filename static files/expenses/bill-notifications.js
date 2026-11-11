(() => {
 const enable=document.querySelector('[data-enable-push]'), disable=document.querySelector('[data-disable-push]'), status=document.querySelector('[data-push-status]');
 if(!enable)return;
 const csrf=document.querySelector('[name=csrfmiddlewaretoken]').value;
 const supported=window.isSecureContext && 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window;
 async function post(url,data){const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':csrf},body:JSON.stringify(data)});if(!r.ok)throw new Error('Could not save notification settings. Please try again.');}
 if(!supported){status.textContent='Push is unavailable in this browser. Use a supported browser or an installed home-screen app. In-app reminders still work.';enable.disabled=true;disable.disabled=true;return;}
 enable.addEventListener('click',async()=>{
  enable.disabled=true;
  try{
   // Permission is requested only after this explicit user gesture.
   const permission=await Notification.requestPermission();
   if(permission!=='granted')throw new Error('Notifications were not allowed. You can change this in browser settings.');
   const config=await (await fetch('/expenses/push/config/')).json();
   if(!config.publicKey)throw new Error('Phone push is not configured on this server yet.');
   const key=Uint8Array.from(atob(config.publicKey.replace(/-/g,'+').replace(/_/g,'/')+'='.repeat((4-config.publicKey.length%4)%4)),c=>c.charCodeAt(0));
   const registration=await navigator.serviceWorker.register('/hestia-worker.js',{scope:'/'});
   await navigator.serviceWorker.ready;
   const subscription=await registration.pushManager.getSubscription() || await registration.pushManager.subscribe({userVisibleOnly:true,applicationServerKey:key});
   await post('/expenses/push/subscribe/',subscription.toJSON());
   status.textContent='Notifications enabled on this device. Scheduled reminders will appear here and in Hestia.';
  }catch(error){status.textContent=error.message;}finally{enable.disabled=false;}
 });
 disable.addEventListener('click',async()=>{
  try{const registration=await navigator.serviceWorker.getRegistration('/');const sub=registration && await registration.pushManager.getSubscription();if(sub){await post('/expenses/push/unsubscribe/',{endpoint:sub.endpoint});await sub.unsubscribe();}status.textContent='Phone notifications turned off on this device. In-app reminders remain available.';}catch(error){status.textContent=error.message;}
 });
})();
