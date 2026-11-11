(() => {
const form = document.querySelector('.avatar-studio');
if (!form) return;
const svg = form.querySelector('[data-avatar-preview] svg');
function update() {
  const value = key => form.elements[key].value;
  for (const key of ['skin','hair_color','clothes','background']) {
    svg.querySelectorAll(`[data-color="${key}"]`).forEach(el => el.setAttribute('fill', value(key)));
    svg.querySelectorAll(`[data-stroke="${key}"]`).forEach(el => el.setAttribute('stroke', value(key)));
  }
  for (const [field, attr] of [['hair_style','hair'],['eyes','eyes'],['glasses','glasses'],['facial_hair','facial'],['face_shape','face'],['outfit','outfit'],['mouth','mouth'],['accessory','accessory'],['earrings','earrings']])
    svg.querySelectorAll(`[data-${attr}]`).forEach(el => el.style.display = el.dataset[attr] === value(field) ? 'inline' : 'none');
  svg.querySelector('[data-back-hair]').style.display = ['bob','long','waves'].includes(value('hair_style')) ? 'inline' : 'none';
  const brows = svg.querySelector('[data-brows]');
  brows.setAttribute('stroke-width', value('brows') === 'bold' ? '4' : '2.5');
  brows.querySelector('path').setAttribute('d', value('brows') === 'arched' ? 'M63 74q8-5 16 0M103 74q8-5 16 0' : 'M64 75h14M104 75h14');
}
form.addEventListener('change', update);
update();
})();
