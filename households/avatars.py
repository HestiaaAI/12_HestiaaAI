"""Locally drawn avatars. Only enumerated values reach SVG markup."""
from django import forms
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.views.decorators.cache import never_cache
from .models import UserAvatar

CHOICES = {
    "skin": [("#f5d0b0", "Peach"), ("#e8b58d", "Sand"), ("#ce9269", "Honey"), ("#a96d48", "Caramel"), ("#774a32", "Walnut"), ("#4b3026", "Espresso")],
    "hair_style": [("short", "Short"), ("bob", "Bob"), ("long", "Long"), ("curls", "Curls"), ("bun", "Bun"), ("pixie", "Pixie cut"), ("waves", "Long waves"), ("ponytail", "Ponytail"), ("braids", "Twin braids"), ("afro", "Afro"), ("fade", "Fade"), ("fringe", "Textured fringe"), ("none", "No hair")],
    "face_shape": [("oval", "Oval"), ("round", "Round"), ("square", "Soft square"), ("heart", "Heart")],
    "outfit": [("tee", "T-shirt"), ("hoodie", "Hoodie"), ("collar", "Collared shirt"), ("sweater", "Cable sweater"), ("jacket", "Denim jacket")],
    "mouth": [("smile", "Soft smile"), ("grin", "Big grin"), ("calm", "Relaxed"), ("open", "Laughing")],
    "hair_color": [("#302821", "Dark brown"), ("#171d20", "Black"), ("#795039", "Chestnut"), ("#d0aa64", "Blonde"), ("#a2583d", "Copper"), ("#b8b5ad", "Silver")],
    "eyes": [("almond", "Almond"), ("lashes", "Lashes"), ("round", "Round"), ("soft", "Soft"), ("happy", "Happy")],
    "brows": [("soft", "Soft"), ("bold", "Bold"), ("arched", "Arched")],
    "glasses": [("none", "No glasses"), ("round", "Round"), ("square", "Square")],
    "facial_hair": [("none", "Clean shaven"), ("mustache", "Mustache"), ("beard", "Beard")],
    "clothes": [("#4f7d76", "Teal"), ("#d39375", "Terracotta"), ("#a3ad8a", "Sage"), ("#e9c882", "Butter"), ("#6c6887", "Plum")],
    "accessory": [("none", "No accessory"), ("bandana", "Bandana"), ("headband", "Headband"), ("crown", "Little crown")],
    "earrings": [("none", "No earrings"), ("studs", "Gold studs"), ("hoops", "Hoops")],
    "background": [("#e1ebde", "Sage"), ("#f5d5bd", "Peach"), ("#f8edcd", "Cream"), ("#d9e5e9", "Mist"), ("#e8dfed", "Lilac")],
}

class AvatarForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for key, choices in CHOICES.items():
            self.fields[key] = forms.ChoiceField(choices=choices, label=key.replace('_', ' ').capitalize(), initial=choices[0][0])


def normalized(options):
    return {key: options.get(key) if options.get(key) in dict(values) else values[0][0] for key, values in CHOICES.items()}


def render_avatar(options):
    o = normalized(options)
    # A small original vector portrait; no uploaded content or remote image requests.
    back = '<path d="M43 99Q27 48 62 35Q112 8 139 49L148 140H39Z"/>'
    hairs = {
        'short': '<path d="M48 76Q37 25 87 27Q140 19 143 75L126 58L116 40Q85 65 53 54Z"/>',
        'bob': '<path d="M44 94Q29 24 89 26Q150 22 146 98L129 76L123 47Q87 65 53 54Z"/>',
        'long': '<path d="M43 92Q32 24 90 26Q146 21 146 94L131 77L120 44Q86 66 53 57Z"/>',
        'curls': ''.join(f'<circle cx="{x}" cy="{y}" r="17"/>' for x,y in [(48,61),(51,40),(72,28),(96,26),(119,34),(134,51),(139,72)]),
        'bun': '<circle cx="92" cy="23" r="22"/><path d="M46 72Q43 29 90 30Q140 28 140 74L126 58Q83 63 56 49Z"/>',
        'pixie': '<path d="M47 75Q35 30 83 24Q134 16 140 63L126 54L123 35Q105 60 65 62L52 81Z"/>',
        'waves': '<path d="M44 78Q28 26 79 24Q139 13 144 72L130 78L121 43Q95 62 57 56Z"/><path d="M45 66q-22 30-7 51q-14 24 7 43h18q-17-22-6-38q-13-27 3-52ZM132 62q27 36 11 58q14 22-5 41h-18q16-22 7-40q12-23-2-48Z"/>',
        'ponytail': '<ellipse cx="145" cy="85" rx="19" ry="49"/><path d="M46 74Q39 28 90 27Q139 22 141 74L126 55Q86 57 57 45Z"/><path d="M137 50l10 4" stroke="#d39375" stroke-width="6"/>',
        'braids': '<path d="M45 78Q31 27 88 24Q147 20 141 80L127 57Q107 51 91 39Q75 54 55 57Z"/>'+''.join(f'<ellipse cx="{x}" cy="{y}" rx="9" ry="12"/>' for x in (44,140) for y in (90,108,126,144)),
        'afro': ''.join(f'<circle cx="{x}" cy="{y}" r="23"/>' for x,y in [(40,68),(39,44),(58,24),(84,18),(110,20),(133,35),(145,59)]) ,
        'fade': '<path d="M48 77V53Q48 23 89 24Q132 20 136 52v26l-10-18v-9q-32 11-69 0v11Z"/>',
        'fringe': '<path d="M46 77Q35 25 88 24Q143 19 140 78l-14-18-8 10-9-13-13 13-7-13-16 12-6-12-14 17Z"/>',
        'none': '',
    }
    texture = '<path d="M57 46q11-16 29-16M61 51q16-16 31-17M110 33q17 6 22 20" fill="none" stroke="#fff5df" stroke-opacity=".23" stroke-width="2" stroke-linecap="round"/>'
    for name in hairs:
        if name != 'none':
            hairs[name] += texture
    accessories = {
        'none':'',
        'bandana':'<path d="M44 55q47-23 98 0l-2 17q-47-22-94 0Z" fill="#ae6158" stroke="#78443c" stroke-width="1.2"/><path d="M54 58l5 5 5-7m17-5 5 6 6-6m19 4 5 7 6-4" fill="none" stroke="#fff4dc" stroke-width="2"/><path d="M139 58l16-5-3 19-12-7Z" fill="#ae6158"/>',
        'headband':'<path d="M47 61q40-38 91 0" fill="none" stroke="#d7b478" stroke-width="8"/><path d="M48 58q42-34 88 0" fill="none" stroke="#fff2c8" stroke-width="2"/>',
        'crown':'<path d="M65 37l-5-23 18 12 13-22 14 22 18-12-5 23Z" fill="#d8b773" stroke="#a68146" stroke-width="1.5"/><circle cx="91" cy="25" r="3" fill="#83a79a"/><path d="M66 35h50" stroke="#fff0c4" stroke-width="3"/>',
    }
    earrings = {
        'none':'',
        'studs':'<g fill="#dcba79" stroke="#a28248" stroke-width="1"><circle cx="49" cy="105" r="3"/><circle cx="134" cy="105" r="3"/></g>',
        'hoops':'<g fill="none" stroke="#c29a51" stroke-width="3"><ellipse cx="48" cy="113" rx="6" ry="9"/><ellipse cx="135" cy="113" rx="6" ry="9"/></g>',
    }
    faces = {
        'oval': '<path d="M49 72q0-36 43-36q42 0 42 36v24q-1 40-42 43q-42-4-43-43Z"/>',
        'round': '<path d="M47 76q0-38 45-38q44 0 44 38v20q0 43-44 43q-45 0-45-43Z"/>',
        'square': '<path d="M49 72q0-35 43-35q42 0 42 35v34q0 30-25 32H75q-26-2-26-32Z"/>',
        'heart': '<path d="M47 74q0-38 45-38q44 0 44 38q0 40-44 68q-45-28-45-68Z"/>',
    }
    outfits = {
        'tee': '<path d="M71 139q21 21 42 0" fill="none" stroke="#fff" stroke-opacity=".5" stroke-width="4"/>',
        'hoodie': '<path d="M69 134q-23 9-19 27l23-8q19 21 38 0l24 8q3-18-22-27l-7 11H78Z" fill="#fff" fill-opacity=".24"/><path d="M78 151v25m28-25v25" stroke="#f8edcd" stroke-width="3"/><path d="M68 179q24-15 48 0" fill="none" stroke="#203a38" stroke-opacity=".3" stroke-width="2"/>',
        'collar': '<path d="M74 134l18 15-17 15-13-23ZM109 134l-17 15 17 15 13-23Z" fill="#fffdf5"/><path d="M92 150v34" stroke="#fffdf5" stroke-opacity=".7" stroke-width="2"/><g fill="#fffdf5"><circle cx="97" cy="165" r="2"/><circle cx="97" cy="178" r="2"/></g>',
        'sweater': '<path d="M73 136q19 17 38 0l5 10q-24 20-48 0Z" fill="#fff" fill-opacity=".3"/><path d="M58 159l5 6-5 6 5 6m20-18 5 6-5 6 5 6m20-18 5 6-5 6 5 6m20-18 5 6-5 6 5 6" fill="none" stroke="#fffdf5" stroke-opacity=".5" stroke-width="2"/>',
        'jacket': '<path d="M74 138l18 14 18-14v46H74Z" fill="#fffdf5"/><path d="M67 139l20 21-15 12-10-25m55-8-20 21 15 12 10-25" fill="none" stroke="#fff" stroke-opacity=".65" stroke-width="3"/><path d="M44 169h20v12H44m76-12h20v12h-20" fill="none" stroke="#fff" stroke-opacity=".6" stroke-width="2"/>',
    }
    mouths = {
        'smile': '<path d="M78 115q7-5 14-1q7-4 14 1q-14 17-28 0Z" fill="#b66c68"/><path d="M79 116q13 5 26 0" fill="none" stroke="#874a47" stroke-width="1.3"/>',
        'grin': '<path d="M76 112q16 8 32 0q-3 20-16 20q-13 0-16-20" fill="#854b43"/><path d="M79 115q13 5 26 0l-2 6H81Z" fill="#fffdf5"/>',
        'calm': '<path d="M81 118q11 3 22 0" fill="none" stroke="#8d4b42" stroke-width="3" stroke-linecap="round"/>',
        'open': '<ellipse cx="92" cy="119" rx="12" ry="10" fill="#854b43"/><path d="M85 125q7-5 14 0" fill="none" stroke="#d98a87" stroke-width="4"/>',
    }
    def detailed_eye(x, lashes=False):
        return f'<path d="M{x-11} 86q10-12 22 0q-11 12-22 0Z" fill="#fffaf2" stroke="#503b36" stroke-width="1.4"/><ellipse cx="{x}" cy="86" rx="4.6" ry="5.6" fill="#826044"/><ellipse cx="{x}" cy="86" rx="2.6" ry="4" fill="#292c2b"/><circle cx="{x+1.3}" cy="84" r="1.3" fill="white"/><path d="M{x-11} 86q10-12 22 0" fill="none" stroke="#3e302e" stroke-width="2"/>' + (f'<path d="M{x-10} 83l-3-4m7 2-1-4m17 6 3-4" stroke="#3e302e" stroke-width="1.5" stroke-linecap="round"/>' if lashes else '')
    eye_shapes = {
        'almond': detailed_eye(71)+detailed_eye(111),
        'lashes': detailed_eye(71,True)+detailed_eye(111,True),
        'round': detailed_eye(71)+detailed_eye(111),
        'soft': '<ellipse cx="71" cy="87" rx="4" ry="3"/><ellipse cx="111" cy="87" rx="4" ry="3"/>',
        'happy': '<path d="M65 88q6-8 12 0M105 88q6-8 12 0" fill="none" stroke="#302b29" stroke-width="3" stroke-linecap="round"/>',
    }
    glasses = {
        'none':'',
        'round':'<circle cx="71" cy="87" r="13"/><circle cx="111" cy="87" r="13"/><path d="M84 85h14M58 84l-9-4M124 84l9-4"/>',
        'square':'<rect x="56" y="75" width="29" height="23" rx="5"/><rect x="97" y="75" width="29" height="23" rx="5"/><path d="M85 83h12"/>',
    }
    facial = {
        'none':'',
        'mustache':'<path d="M91 104q-12-7-20 7q13 1 20-4q7 5 20 4q-8-14-20-7"/>',
        'beard':'<path d="M56 103q6 38 35 38q30 0 35-38l-14 14q-21 13-42 0Z"/>',
    }
    brow = '<path d="M63 74q8-5 16 0M103 74q8-5 16 0"/>' if o['brows'] == 'arched' else '<path d="M64 75h14M104 75h14"/>'
    return f'''<svg class="face-avatar" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 184 184" role="img" aria-label="Custom cartoon avatar">
<circle cx="92" cy="92" r="91" fill="{o['background']}" data-color="background"/>
<g fill="{o['hair_color']}" data-color="hair_color"><g data-back-hair style="display:{'inline' if o['hair_style'] in ('bob','long','waves') else 'none'}">{back}</g></g>
<path d="M29 184q0-48 46-48h33q46 0 47 48Z" fill="{o['clothes']}" data-color="clothes"/>
{''.join(f'<g data-outfit="{k}" style="display:{"inline" if k==o["outfit"] else "none"}">{v}</g>' for k,v in outfits.items())}
<g fill="{o['skin']}" data-color="skin"><path d="M77 120h29v25q-15 16-29 0Z"/><ellipse cx="49" cy="94" rx="9" ry="13"/><ellipse cx="134" cy="94" rx="9" ry="13"/>{''.join(f'<g data-face="{k}" style="display:{"inline" if k==o["face_shape"] else "none"}">{v}</g>' for k,v in faces.items())}</g>
<g fill="{o['hair_color']}" data-color="hair_color">{''.join(f'<g data-hair="{k}" style="display:{"inline" if k==o["hair_style"] else "none"}">{v}</g>' for k,v in hairs.items())}</g>
<g stroke="{o['hair_color']}" data-stroke="hair_color" stroke-width="{4 if o['brows']=='bold' else 2.5}" stroke-linecap="round" fill="none" data-brows>{brow}</g>
<ellipse cx="62" cy="103" rx="9" ry="4" fill="#d98a87" opacity=".17"/><ellipse cx="121" cy="103" rx="9" ry="4" fill="#d98a87" opacity=".17"/>
<g fill="#302b29">{''.join(f'<g data-eyes="{k}" style="display:{"inline" if k==o["eyes"] else "none"}">{v}</g>' for k,v in eye_shapes.items())}</g>
<path d="M91 88l-4 13h7" fill="none" stroke="#815943" stroke-opacity=".5" stroke-width="2" stroke-linecap="round"/>
{''.join(f'<g data-mouth="{k}" style="display:{"inline" if k==o["mouth"] else "none"}">{v}</g>' for k,v in mouths.items())}
<g fill="{o['hair_color']}" data-color="hair_color">{''.join(f'<g data-facial="{k}" style="display:{"inline" if k==o["facial_hair"] else "none"}">{v}</g>' for k,v in facial.items())}</g>
<g fill="none" stroke="#364c49" stroke-width="3">{''.join(f'<g data-glasses="{k}" style="display:{"inline" if k==o["glasses"] else "none"}">{v}</g>' for k,v in glasses.items())}</g>
{''.join(f'<g data-accessory="{k}" style="display:{"inline" if k==o["accessory"] else "none"}">{v}</g>' for k,v in accessories.items())}
{''.join(f'<g data-earrings="{k}" style="display:{"inline" if k==o["earrings"] else "none"}">{v}</g>' for k,v in earrings.items())}</svg>'''

@login_required
@never_cache
def avatar_editor(request):
    saved = UserAvatar.objects.filter(user=request.user).first()
    form = AvatarForm(request.POST or None, initial=normalized(saved.options if saved else {}))
    if request.method == 'POST' and form.is_valid():
        UserAvatar.objects.update_or_create(user=request.user, defaults={'options': form.cleaned_data})
        return redirect('/accounts/avatar/?saved=1')
    values = {key: form[key].value() for key in CHOICES}
    colors = {'skin','hair_color','clothes','background'}
    groups = []
    for key in CHOICES:
        groups.append({'key': key, 'label': {'clothes':'Clothing color','brows':'Eyebrows','mouth':'Expression'}.get(key, key.replace('_',' ').capitalize()), 'errors': form[key].errors, 'color': key in colors,
            'choices': [{'value': value, 'label': label, 'selected': values[key] == value,
                         'portrait': '' if key in colors else render_avatar({**normalized(values), key:value})} for value,label in CHOICES[key]]})
    return render(request, 'registration/avatar.html', {'form': form, 'portrait': render_avatar(values), 'saved': request.GET.get('saved') == '1', 'groups':groups})
