/* In-cart checks are separate from receipt confirmation and never change balances. */
document.querySelectorAll('.note-check-form input[type=checkbox]').forEach(box=>{
 box.addEventListener('change',async()=>{
  const row=box.closest('.note-line'),caption=row.querySelector('[data-check-caption]'),status=document.querySelector('[data-note-status]'),oldText=caption.textContent,wanted=box.checked;
  row.classList.toggle('is-checked',wanted);caption.textContent=wanted?'In the cart · receipt pending':'To pick up';box.disabled=true;status.textContent='Saving…';
  try{
   const data=new FormData(box.form);if(wanted)data.set('checked','on');else data.delete('checked');
   const response=await fetch(box.form.action,{method:'POST',body:data,headers:{'X-Requested-With':'XMLHttpRequest'},credentials:'same-origin'});
   const result=await response.json();if(!response.ok||typeof result.checked!=='boolean')throw Error(result.error||'Could not save the check. Try again.');
   box.checked=result.checked;row.classList.toggle('is-checked',result.checked);status.textContent='Saved to the shared note.';
  }catch(error){box.checked=!wanted;row.classList.toggle('is-checked',!wanted);caption.textContent=oldText;status.textContent=error.message==='Failed to fetch'?'You’re offline. This check was not saved. Try again when connected.':error.message}
  finally{box.disabled=false}
 });
});
