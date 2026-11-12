(() => {
 const data=document.getElementById('settlement-amounts'), person=document.getElementById('id_receiver'), amount=document.getElementById('id_amount');
 if(!data || !person || !amount)return;
 const choices=JSON.parse(data.textContent);
 function update(){const max=choices[person.value]||0;amount.max=(max/100).toFixed(2);amount.value=max?(max/100).toFixed(2):'';}
 person.addEventListener('change',update);
 if(person.value){amount.max=((choices[person.value]||0)/100).toFixed(2);if(!amount.value)update();}
})();
