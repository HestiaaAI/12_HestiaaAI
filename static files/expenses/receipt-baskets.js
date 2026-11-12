(() => {
 document.addEventListener('change',event=>{
  const card=event.target.closest('.receipt-review-line');if(!card)return;
  if(event.target.matches('select') && event.target.value)card.querySelectorAll('input[name$=recipients]').forEach(input=>input.checked=false);
  if(event.target.matches('input[name$=recipients]') && event.target.checked)card.querySelector('select').value='';
 },true);
 const studio=document.querySelector('.unmatched-studio');if(!studio)return;
 const cards=[...studio.querySelectorAll('[data-unmatched]')], targets=[...studio.querySelectorAll('[data-basket]')],status=studio.querySelector('[data-basket-status]');let selected=null;
 if(!cards.length){studio.hidden=true;return;}
 function choose(card){selected=card;cards.forEach(c=>c.classList.toggle('basket-selected',c===card));status.textContent='Choose a basket for '+card.querySelector('h2').textContent+'.';}
 function refresh(){
  studio.querySelectorAll('[data-basket-chips]').forEach(el=>el.replaceChildren());
  cards.forEach(card=>{
   const picked=[...card.querySelectorAll('input[name$=recipients]:checked')];
   const names=picked.map(input=>input.closest('label').textContent.trim());
   card.querySelector('[data-basket-assignment]').textContent=names.length?'🧺 '+names.join(' + '):'Not assigned yet';card.classList.toggle('basket-assigned',names.length>0);card.hidden=names.length>0;
   picked.forEach(input=>{const area=studio.querySelector(`[data-basket-chips="${input.value}"]`);if(area){const chip=document.createElement('span');chip.textContent=card.querySelector('h2').textContent.replace(/^Receipt \d+ · /,'');chip.tabIndex=0;chip.setAttribute('role','button');chip.setAttribute('aria-label','Review or reassign '+chip.textContent);
    function reopen(){card.hidden=false;choose(card);card.querySelector('details').open=true;card.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'center'});}
    chip.addEventListener('click',event=>{event.stopPropagation();reopen();});chip.addEventListener('keydown',event=>{if(['Enter',' '].includes(event.key)){event.preventDefault();event.stopPropagation();reopen();}});area.append(chip);}});
  });
 }
 function place(target){
  if(!selected){status.textContent='Tap an unmatched item first, then choose its basket.';return;}
  const card=selected,id=target.dataset.basket;
  card.querySelector('select').value='';
  card.querySelectorAll('input[name$=recipients]').forEach(input=>input.checked=id==='all'||input.value===id);
  card.classList.remove('basket-landed');void card.offsetWidth;card.classList.add('basket-landed');
  card.dispatchEvent(new Event('change',{bubbles:true}));refresh();status.textContent=cards.every(c=>c.hidden)?'All unmatched items are in baskets. Tap an item in a basket to review it.':'Item moved to its basket. Choose the next unmatched item.';selected=null;cards.forEach(c=>c.classList.remove('basket-selected'));
 }
 cards.forEach(card=>{
  card.addEventListener('click',event=>{if(!event.target.closest('input,select,summary,textarea,label'))choose(card);});
  card.addEventListener('keydown',event=>{if(event.target===card && ['Enter',' '].includes(event.key)){event.preventDefault();choose(card);}});
  card.addEventListener('dragstart',event=>{choose(card);event.dataTransfer.setData('text/plain','receipt-item');event.dataTransfer.effectAllowed='move';});
  card.addEventListener('change',()=>{const chosen=card.querySelectorAll('input[name$=recipients]:checked');if(chosen.length)card.querySelector('select').value='';refresh();});
 });
 targets.forEach(target=>{target.addEventListener('click',()=>place(target));target.addEventListener('dragover',event=>{event.preventDefault();target.classList.add('basket-hover');});target.addEventListener('dragleave',()=>target.classList.remove('basket-hover'));target.addEventListener('drop',event=>{event.preventDefault();target.classList.remove('basket-hover');place(target);});});refresh();
})();
