/* Photos stay in this browser. Only reviewed text and explicit AI-name consent are submitted. */
const count=document.querySelector('#id_receipts-TOTAL_FORMS');
function addReceiptCard(){
 const total=Number(count.value);if(total>=5)return null;
 document.querySelector('#receipt-inputs').insertAdjacentHTML('beforeend',document.querySelector('#receipt-empty').innerHTML.replaceAll('__prefix__',String(total)));
 count.value=String(total+1);document.querySelector('#add-receipt').disabled=total+1>=5;
 return document.querySelector('#receipt-inputs').lastElementChild;
}
document.querySelector('#add-receipt')?.addEventListener('click',addReceiptCard);
function validReceiptPhoto(file){return ['image/jpeg','image/png','image/webp'].includes(file.type)&&file.size<=10*1024*1024}
async function readReceiptPhoto(card,file,worker){
 const status=card.querySelector('[data-ocr-status]');
 status.textContent='Reading '+file.name+'…';
 const result=await worker.recognize(file,{rotateAuto:true});
 if(!result.data.text.trim()||result.data.text.length>16000)throw Error('Unreadable receipt');
 card.querySelector('textarea').value=result.data.text;resetBillReview(card);
 status.textContent=file.name+' read. Choose who paid, review the bill, then tick to fill the totals.';
}
document.addEventListener('click',async event=>{
 const button=event.target.closest('[data-read-photo]');if(!button)return;
 const card=button.closest('.receipt-input'),file=card.querySelector('[data-photo]').files[0],status=card.querySelector('[data-ocr-status]');
 const payer=card.querySelector('[name$="-payer"]');
 if(!payer.value){status.textContent='Choose who paid before scanning this receipt.';payer.reportValidity();return}
 if(!file||!validReceiptPhoto(file)){status.textContent='Choose a JPEG, PNG or WebP photo under 10 MB.';return}
 if(!window.Tesseract){status.textContent='Scanner unavailable. Paste the receipt text instead.';return}
 button.disabled=true;let worker;
 try{worker=await Tesseract.createWorker('eng');await readReceiptPhoto(card,file,worker)}
 catch{status.textContent='Could not read this photo. Try again or paste receipt text.'}
 finally{try{await worker?.terminate()}finally{button.disabled=false}}
});

function normalizedBillText(text){
 const lines=text.split(/\r?\n/).map(line=>line.trim()).filter(Boolean),matches=lines.map(line=>line.match(/^(\d{1,3})[.)]?\s+(.+)$/)),numbers=matches.filter(Boolean).map(m=>Number(m[1]));
 const consecutive=numbers.length>=3&&numbers.length>=lines.length*.7&&numbers.every((n,i)=>!i||n===numbers[i-1]+1),quantityPrefix=matches.some(m=>m&&/^(?:x|×|lb|kg|oz)\b/i.test(m[2]));
 return lines.map((line,i)=>{if(consecutive&&!quantityPrefix&&matches[i])line=matches[i][2];return line.replace(/^\d{1,4}[.)]?\s+(?=(?:sub[ -]*total|grand[ -]*total|total|tax|sales[ -]*tax|discount|coupon|savings|cash|change|payment|amount|balance)\b)/i,'')}).join('\n');
}
function fillReceiptTotals(card,overwrite=false){
 const text=normalizedBillText(card.querySelector('textarea').value);let found=[];
 const rules={total:/^\s*(?:grand\s+total|total|amount\s+due)\b[^\n\d]*\$?(\d+[.,]\d{2})\s*$/gmi,tax:/^\s*(?:sales\s+tax|tax)\b[^\n\d]*\$?(\d+[.,]\d{2})\s*$/gmi,discount:/^\s*(?:discount|coupon|savings)\b[^\n\d]*\$?(\d+[.,]\d{2})\s*$/gmi};
 Object.entries(rules).forEach(([name,pattern])=>{
  const values=[...text.matchAll(pattern)].map(m=>m[1].replace(',','.')),unique=[...new Set(values)],field=card.querySelector('[name$="-'+name+'"]');
  if(unique.length===1&&(overwrite||!field.value||Number(field.value)===0||field.value===field.dataset.detected)){field.value=unique[0];field.dataset.detected=unique[0];found.push(name)}
 });
 return found;
}
function resetBillReview(card){
 const tick=card.querySelector('[data-reviewed-bill]');if(tick)tick.checked=false;
 const status=card.querySelector('[data-totals-status]');if(status)status.textContent='Review the bill, then tick to fill the totals.';
 card.querySelectorAll('[name$="-total"],[name$="-tax"],[name$="-discount"]').forEach(field=>{if(field.dataset.detected&&field.value===field.dataset.detected){field.value=field.name.endsWith('-total')?'':'0';delete field.dataset.detected}});
}
document.addEventListener('input',event=>{if(event.target.matches('.receipt-input textarea'))resetBillReview(event.target.closest('.receipt-input'))});
document.addEventListener('change',event=>{
 const tick=event.target;if(!tick.matches('[data-reviewed-bill]')||!tick.checked)return;
 const card=tick.closest('.receipt-input'),text=card.querySelector('textarea'),status=card.querySelector('[data-totals-status]');
 if(!text.value.trim()){tick.checked=false;status.textContent='Scan or paste your bill before reviewing it.';text.focus();return}
 const found=fillReceiptTotals(card,true);
 status.textContent=found.includes('total')?'Detected totals filled below. Check them before continuing.':'The bill is reviewed, but its total was missing or ambiguous. Enter the amounts below.';
});
document.querySelector('[data-receipt-upload]')?.addEventListener('invalid',event=>{event.target.closest('details')?.setAttribute('open','')},true);
document.querySelector('[data-receipt-upload]')?.addEventListener('submit',()=>{const button=document.querySelector('[data-match-submit]');button.disabled=true;button.textContent='Matching your bill…'});

const data=document.querySelector('#purchase-preview-data');
if(data){
 const candidates=JSON.parse(data.textContent),receipts=JSON.parse(document.querySelector('#receipt-preview-data').textContent),cards=[...document.querySelectorAll('.receipt-review-line')];
 const money=n=>new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format(n/100);
 function allocate(total,weights){let sum=weights.reduce((a,b)=>a+b,0),raw=weights.map(w=>total*w/sum),shares=raw.map(Math.floor),remaining=total-shares.reduce((a,b)=>a+b,0),order=raw.map((r,i)=>({i,r:r-shares[i]})).sort((a,b)=>b.r-a.r||a.i-b.i);for(let i=0;i<remaining;i++)shares[order[i].i]++;return shares}
 function updateAll(){
  Object.entries(receipts).forEach(([number,receipt])=>{
   const group=cards.filter(card=>card.dataset.receipt===number).sort((a,b)=>Number(a.querySelector('[name$="-line_id"]').value)-Number(b.querySelector('[name$="-line_id"]').value)),prices=group.map(card=>{let value=card.querySelector('[name$="-amount"]').value;return /^\d+(\.\d{1,2})?$/.test(value)?Math.round(Number(value)*100):NaN}),subtotal=prices.reduce((a,b)=>a+b,0),valid=prices.every(n=>Number.isFinite(n)&&n>0)&&subtotal+receipt.tax_cents-receipt.discount_cents===receipt.total_cents;
   const final=valid?allocate(receipt.total_cents,prices):[];
   group.forEach((card,index)=>{
    const entry=candidates[card.querySelector('select').value],preview=card.querySelector('[data-line-preview]');
    if(!valid){preview.textContent='These receipt lines + tax − discount must equal '+money(receipt.total_cents)+'. Check prices before confirming.';return}
    if(!entry){
      const chosen=[...card.querySelectorAll('input[type=checkbox][name$=recipients]:checked')];
      if(!chosen.length){preview.textContent='Unmatched: place this item in one or more roommate baskets.';return}
      const values=allocate(final[index],chosen.map(()=>1));preview.replaceChildren();
      const title=document.createElement('strong');title.textContent='Final line total '+money(final[index])+' · including allocated tax/discount';preview.append(title);
      chosen.forEach((input,i)=>{const label=input.closest('label');const p=document.createElement('p');p.textContent=(label?label.textContent.trim():'Roommate')+' · '+money(values[i]);preview.append(p)});return;
    }
    const ids=Object.keys(entry.weights).sort((a,b)=>Number(a)-Number(b)),shares=allocate(final[index],ids.map(id=>entry.weights[id]));preview.replaceChildren();
    const title=document.createElement('strong');title.textContent='Final line total '+money(final[index])+' · including allocated tax/discount';preview.append(title);
    ids.forEach((id,i)=>{const p=document.createElement('p');p.textContent=entry.names[id]+' · '+money(shares[i]);preview.append(p)});
   });
  });
 }
 cards.forEach(card=>{card.addEventListener('input',updateAll);card.addEventListener('change',updateAll)});updateAll();
}
