/* Progressive enhancement: every submission is independently validated by Django. */
document.querySelector('[data-print]')?.addEventListener('click',()=>window.print());
const expenseForm=document.querySelector('[data-expense-form]');
if(expenseForm){
 const amount=expenseForm.elements.amount,preview=expenseForm.querySelector('[data-split-preview]'),custom=expenseForm.querySelector('[data-custom-shares]'),items=expenseForm.querySelector('[data-items]'),steps=[...expenseForm.querySelectorAll('[data-step]')],nav=expenseForm.querySelector('.wizard-nav');let step=0;
 const money=n=>new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format(n/100);
 amount.inputMode='decimal';
 function selected(){return [...expenseForm.querySelectorAll('[name="participants"]:checked')]}
 function update(){let method=expenseForm.querySelector('[name="split_method"]:checked')?.value,members=selected(),total=Math.round(Number(amount.value)*100);custom.hidden=['equal','itemized'].includes(method);items.hidden=method!=='itemized';expenseForm.querySelector('[data-share-label]').textContent=method==='percent'?'Each roommate’s percentage · must total 100%':method==='shares'?'Share weights · for example 2, 1, 1':'Each roommate’s exact amount (USD)';let inputs=[...custom.querySelectorAll('input[name^="share_"]')];inputs.forEach(f=>{let id=f.name.replace('share_','');f.disabled=['equal','itemized'].includes(method)||!members.some(m=>m.value===id)});if(!Number.isFinite(total)||total<=0||!members.length){preview.textContent='Choose a positive amount and at least one roommate.';return}let rows=[],error='';if(method==='equal'){let ids=members.map(m=>Number(m.value)).sort((a,b)=>a-b),base=Math.floor(total/ids.length),rem=total%ids.length;rows=members.map(m=>({member:m,amount:base+(ids.indexOf(Number(m.value))<rem?1:0)}))}else if(method==='itemized'){let sums=Object.fromEntries(members.map(m=>[m.value,0]));for(let line of expenseForm.elements.item_lines.value.trim().split('\n')){let parts=line.split('|').map(s=>s.trim());if(parts.length!==3||!parts[0]||!Object.hasOwn(sums,parts[2])||!/^\d+(\.\d{1,2})?$/.test(parts[1])){error='Use description | amount | selected roommate ID on each line.';break}sums[parts[2]]+=Math.round(Number(parts[1])*100)}if(!error&&Object.values(sums).reduce((a,b)=>a+b,0)!==total)error='Line items must total '+money(total)+'.';rows=members.map(m=>({member:m,amount:sums[m.value]}))}else{let weights=members.map(m=>Number(expenseForm.elements['share_'+m.value].value||0)),sum=weights.reduce((a,b)=>a+b,0);if(weights.some(n=>!Number.isFinite(n)||n<0))error='Enter nonnegative values.';else if(method==='custom'){let cents=weights.map(w=>Math.round(w*100));if(cents.reduce((a,b)=>a+b,0)!==total)error='Exact amounts must total '+money(total)+'.';rows=members.map((m,i)=>({member:m,amount:cents[i]}))}else if(sum<=0||(method==='percent'&&Math.abs(sum-100)>.000001))error=method==='percent'?'Percentages must total 100%.':'Enter at least one positive share weight.';else{let raw=weights.map(w=>total*w/sum),cents=raw.map(Math.floor),left=total-cents.reduce((a,b)=>a+b,0),order=raw.map((v,i)=>({i,r:v-cents[i],id:Number(members[i].value)})).sort((a,b)=>b.r-a.r||a.id-b.id);for(let i=0;i<left;i++)cents[order[i].i]++;rows=members.map((m,i)=>({member:m,amount:cents[i]}))}}preview.replaceChildren();let title=document.createElement('strong');title.textContent=error||'Each person pays';preview.append(title);if(!error)rows.forEach(row=>{let p=document.createElement('p'),label=row.member.closest('label')?.textContent.trim()||'Roommate';p.textContent=label+' · '+money(row.amount);preview.append(p)});let review=expenseForm.querySelector('[data-review]');review.textContent=expenseForm.elements.title.value+' · '+money(total)+' · '+expenseForm.elements.paid_by.selectedOptions[0]?.textContent+' paid. '+preview.textContent;}
 function show(){steps.forEach((s,i)=>s.hidden=i!==step);nav.hidden=false;nav.querySelector('[data-back]').hidden=step===0;nav.querySelector('[data-next]').hidden=step===3;update();steps[step].querySelector('input:not([type=hidden]),textarea,button')?.focus()}
 if(!expenseForm.dataset.errors){expenseForm.querySelector('.wizard-keypad').hidden=false;show()}else{nav.hidden=true;update()}
 expenseForm.querySelector('[data-next]').onclick=()=>{let valid=[...steps[step].querySelectorAll('input:not([type=hidden]),select,textarea')].filter(el=>!el.disabled).every(el=>el.reportValidity());if(valid){step=Math.min(step+1,3);show()}};
 expenseForm.querySelector('[data-back]').onclick=()=>{step=Math.max(0,step-1);show()};
 expenseForm.querySelectorAll('[data-key]').forEach(b=>b.onclick=()=>{amount.value=b.dataset.key==='back'?amount.value.slice(0,-1):amount.value+b.dataset.key;update()});
 expenseForm.querySelectorAll('[data-chip]').forEach(b=>b.onclick=()=>{amount.value=b.dataset.total;expenseForm.elements.title.value=b.dataset.chip;update()});
 expenseForm.addEventListener('input',update);expenseForm.addEventListener('change',update);
 // Reveal every field for native validation if submitting from the review step.
 expenseForm.addEventListener('submit',()=>{steps.forEach(s=>s.hidden=false)});
 function refreshReference(){
  const method=expenseForm.querySelector('[name="split_method"]:checked')?.value;
  const selectedIds=new Set(selected().map(m=>m.value));
  const ticketTitle=expenseForm.querySelector('[data-ticket-title]');
  if(ticketTitle)ticketTitle.textContent=expenseForm.elements.title.value||'Your shared expense';
  const ticketTotal=expenseForm.querySelector('[data-ticket-total]');
  if(ticketTotal)ticketTotal.textContent=money(Math.round(Number(amount.value||0)*100));
  expenseForm.querySelectorAll('[data-ticket-member]').forEach(el=>el.hidden=!selectedIds.has(el.dataset.ticketMember));
  custom.querySelectorAll('input[name^="share_"]').forEach(field=>{
   const label=field.labels[0]; if(label){if(!field.dataset.personLabel)field.dataset.personLabel=label.textContent.replace(/\s*\(USD\):?$/, '').trim();label.textContent=field.dataset.personLabel+(method==='percent'?' (%)':method==='shares'?' (shares)':' (USD)');}
   let slider=field.parentElement.querySelector('[data-bind-share]');
   if(!slider){slider=document.createElement('input');slider.type='range';slider.className='roommate-slider';slider.dataset.bindShare=field.name;slider.setAttribute('aria-label',field.labels[0]?.textContent.trim()+' split slider');field.after(slider)}
   slider.setAttribute('aria-label',(field.dataset.personLabel||'Roommate')+(method==='percent'?' percentage':method==='shares'?' share weight':' amount')+' slider');
   slider.min='0';slider.max=String(method==='percent'?100:method==='shares'?Math.max(10,Number(field.value)||0):Math.max(Number(amount.value)||1,Number(field.value)||0));
   slider.step=method==='shares'?'1':'.01';slider.value=field.value||0;slider.disabled=field.disabled;slider.hidden=field.disabled;
  });
 }
 expenseForm.addEventListener('input',event=>{if(event.target.dataset.bindShare){expenseForm.elements[event.target.dataset.bindShare].value=event.target.value}},true);
 expenseForm.addEventListener('input',refreshReference);
 expenseForm.addEventListener('change',refreshReference);
 expenseForm.addEventListener('click',()=>queueMicrotask(refreshReference));
 refreshReference();

}
