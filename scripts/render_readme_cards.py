#!/usr/bin/env python3
"""Render self-contained, GitHub <img>-safe animated SVG profile cards.
Run: python scripts/render_readme_cards.py
Refresh data: python scripts/render_readme_cards.py --refresh (requires GITHUB_TOKEN)
Static preview: STATIC=1 python scripts/render_readme_cards.py
"""
import base64
import calendar
import datetime as dt
import html
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'cards'
DATA = ROOT / 'data' / 'contributions.json'
STATIC = os.environ.get('STATIC', '').lower() in ('1', 'true', 'yes')
USERNAME = 'HARSHx17'
# Existing README uses lime #39FF14 and cyan #0891B2. Portfolio CSS could not be verified.
BG = '#07111d'; PANEL = '#0d1d2b'; STROKE = '#254356'; INK = '#ecf7f8'
MUTED = '#8cabb8'; ACCENT = '#39ff14'; CYAN = '#35d8ed'; BLUE = '#0891b2'
# Edit these two paths if your site uses other fonts. The Action installs fonts-inter.
FONT_CANDIDATES = [
    '/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf',
    '/usr/share/fonts/truetype/inter/Inter-Bold.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
]
MONO_CANDIDATES = [
    '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',
    '/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf',
]


def esc(value): return html.escape(str(value), quote=True)


def refresh():
    token = os.getenv('GITHUB_TOKEN') or os.getenv('GH_TOKEN')
    if not token:
        raise RuntimeError('GITHUB_TOKEN is required for --refresh')
    today = dt.datetime.now(dt.timezone.utc).date()
    start = today - dt.timedelta(days=365)
    query = '''query($login:String!,$from:DateTime!,$to:DateTime!){user(login:$login){contributionsCollection(from:$from,to:$to){contributionCalendar{weeks{contributionDays{date contributionCount}}}}}}'''
    payload = json.dumps({'query': query, 'variables': {'login':USERNAME,
        'from':start.isoformat()+'T00:00:00Z','to':today.isoformat()+'T23:59:59Z'}}).encode()
    req = urllib.request.Request('https://api.github.com/graphql', data=payload,
        headers={'Authorization':'Bearer '+token,'Content-Type':'application/json', 'User-Agent':'harshx17-profile-cards'})
    with urllib.request.urlopen(req, timeout=30) as response:
        result = json.load(response)
    if result.get('errors'):
        raise RuntimeError('GitHub GraphQL: '+str(result['errors']))
    collection = result['data']['user']['contributionsCollection']['contributionCalendar']
    days = [day for week in collection['weeks'] for day in week['contributionDays']]
    days = sorted(({'date': x['date'], 'count': int(x['contributionCount'])} for x in days
                   if start.isoformat() <= x['date'] <= today.isoformat()), key=lambda x:x['date'])
    DATA.parent.mkdir(parents=True,exist_ok=True)
    DATA.write_text(json.dumps({'username':USERNAME,'updated_at':today.isoformat(),'days':days},indent=2)+'\n')
    print(f'Refreshed {len(days)} days from GitHub')


def load():
    if not DATA.exists(): return []
    raw = json.loads(DATA.read_text())
    rows = raw.get('days', []) if isinstance(raw,dict) else raw
    result = {}
    for row in rows:
        try:
            date = dt.date.fromisoformat(row['date'])
            count = max(0,int(row.get('count',row.get('contributionCount',0))))
            result[date] = count
        except (ValueError,KeyError,TypeError): continue
    return sorted(result.items())


def embedded_font(candidates, name):
    if shutil.which('pyftsubset') is None:
        print('WARNING: pyftsubset missing; using SVG fallback fonts',file=sys.stderr)
        return ''
    path = next((x for x in candidates if Path(x).exists()), None)
    if not path:
        print('WARNING: font not found; using SVG fallback fonts',file=sys.stderr)
        return ''
    # Subset in a temporary directory. No font binaries are redistributed separately.
    from tempfile import TemporaryDirectory
    with TemporaryDirectory() as tmp:
        dst = Path(tmp)/'subset.woff'
        subprocess.run(['pyftsubset',path,'--output-file='+str(dst),'--flavor=woff',
                        '--unicodes=U+0020-007E,U+00A0,U+2022,U+2014,U+2013,U+2192,U+2197',
                        '--layout-features=*'],check=True,capture_output=True)
        blob = base64.b64encode(dst.read_bytes()).decode('ascii')
    return "@font-face{font-family:'"+name+"';src:url(data:font/woff;base64,"+blob+") format('woff');font-display:block;}"

FONTS = ''

def fonts():
    global FONTS
    FONTS = embedded_font(FONT_CANDIDATES,'Display')+embedded_font(MONO_CANDIDATES,'Mono')


def text(x,y,s,size=22,color=INK,weight=400,cls='',family='Display',extra=''):
    return f'<text x="{x}" y="{y}" fill="{color}" font-family="{family},sans-serif" font-size="{size}" font-weight="{weight}" class="{cls}" {extra}>{esc(s)}</text>'


def svg(w,h,body,delay=0, extra_css='', defs=''):
    common = '''
    .enter{opacity:0;transform:translateY(14px);animation:rise .9s cubic-bezier(.2,.9,.2,1) forwards}
    .pop{opacity:0;animation:appear .6s ease forwards}
    .grow{transform:scaleY(0);transform-origin:center bottom;transform-box:fill-box;animation:bar .75s cubic-bezier(.2,.8,.3,1) forwards}
    .cell{opacity:0;animation:appear .22s ease forwards}
    .pulse{animation:pulse 3.2s ease-in-out infinite}
    @keyframes rise{to{opacity:1;transform:translateY(0)}}
    @keyframes appear{to{opacity:1}}
    @keyframes bar{to{transform:scaleY(1)}}
    @keyframes pulse{50%{opacity:.42}}
    @media(prefers-reduced-motion:reduce){*,*::before,*::after{animation:none!important;transition:none!important}
      .enter,.pop,.cell{opacity:1!important;transform:none!important}.grow{transform:none!important}
      .smil-effect{display:none!important}}
    '''
    if STATIC: common += '\n*{animation:none!important;transition:none!important}.enter,.pop,.cell{opacity:1!important;transform:none!important}.grow{transform:none!important}.smil-effect{display:none!important}'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img">'
        f'<title>Harshvardhan Pathak GitHub profile card</title><defs>{defs}</defs><style><![CDATA[{FONTS}{common}{extra_css}]]></style>'
        f'<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="22" fill="{PANEL}" stroke="{STROKE}"/>'
        f'<rect x="22" y="22" width="5" height="26" rx="2" fill="{ACCENT}"/>'
        f'{body}</svg>')


def write(filename,body,w=1000,h=250,delay=0,css='',defs=''):
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/filename).write_text(svg(w,h,body,delay,css,defs),encoding='utf-8')


def hero():
    # Optional portrait: set PORTRAIT_PATH to a local PNG/JPEG (max 350 KB advised).
    body = text(45,46,'HARSHX17  /  DEVELOPER PROFILE',14,CYAN,600,'enter',family='Mono',extra='style="animation-delay:.10s"')
    body += text(45,128,'Harshvardhan',68,INK,700,'enter',extra='style="animation-delay:.25s"')
    body += text(45,195,'Pathak.',68,ACCENT,700,'enter',extra='style="animation-delay:.42s"')
    body += text(48,247,'Full-stack + Android developer  /  CSE at MUJ',19,MUTED,400,'enter',extra='style="animation-delay:.62s"')
    body += text(48,288,'BUILD  /  SHIP  /  IMPROVE',14,CYAN,500,'enter',family='Mono',extra='style="animation-delay:.75s"')
    portrait=os.getenv('PORTRAIT_PATH','').strip()
    defs=''
    if portrait and Path(portrait).is_file():
        p=Path(portrait)
        if p.stat().st_size > 350_000: raise ValueError('Portrait is over 350 KB; compress it first')
        mime='image/png' if p.suffix.lower()=='.png' else 'image/jpeg'
        encoded=base64.b64encode(p.read_bytes()).decode()
        defs='<clipPath id="portraitClip"><circle cx="841" cy="152" r="95"/></clipPath>'
        body += f'<image x="746" y="57" width="190" height="190" preserveAspectRatio="xMidYMid slice" clip-path="url(#portraitClip)" href="data:{mime};base64,{encoded}"/>'
    else:
        body += f'<circle cx="842" cy="153" r="102" fill="{BG}" stroke="{STROKE}"/>'
        body += f'<circle cx="842" cy="153" r="78" fill="none" stroke="{BLUE}" stroke-width="1.5" stroke-dasharray="3 11"/>'
        body += text(841,170,'H.',85,ACCENT,700,'enter',extra='text-anchor="middle" style="animation-delay:.5s"')
        body += f'<circle cx="914" cy="82" r="8" fill="{ACCENT}" class="pulse"/>'
    # Decorative SMIL highlight. The overlay is hidden in reduced-motion and STATIC modes.
    defs += '<linearGradient id="scan" x1="-150%" y1="0%" x2="-50%" y2="0%"><stop offset="0%" stop-color="'+CYAN+'" stop-opacity="0"/><stop offset="50%" stop-color="'+CYAN+'" stop-opacity=".85"/><stop offset="100%" stop-color="'+CYAN+'" stop-opacity="0"/><animate attributeName="x1" values="-150%;150%" dur="6s" begin="1s" repeatCount="indefinite"/><animate attributeName="x2" values="-50%;250%" dur="6s" begin="1s" repeatCount="indefinite"/></linearGradient>'
    body += '<rect x="48" y="305" width="900" height="2" fill="url(#scan)" class="smil-effect"/>'
    write('hero.svg',body,h=330,defs=defs)


def tile(filename,idx,title,subtitle,accent):
    d=1.05+idx*.16
    body=text(24,46,f'0{idx+1}  /  {title.upper()}',14,accent,600,'enter',family='Mono',extra=f'style="animation-delay:{d:.2f}s"')
    body+=text(24,115,title,36,INK,700,'enter',extra=f'style="animation-delay:{d+.15:.2f}s"')
    body+=text(24,146,subtitle,13,MUTED,400,'enter',extra=f'style="animation-delay:{d+.3:.2f}s"')
    body+=text(291,51,'↗',28,accent,600,'enter',extra='text-anchor="end"')
    body+=f'<rect x="24" y="170" width="272" height="3" rx="1" fill="{accent}" opacity=".65"/>'
    write(filename,body,w=320,h=194)


def stats(days):
    known=bool(days)
    totals=defaultdict(int)
    for date,count in days: totals[(date.year,date.month)]+=count
    active=sum(1 for _,x in days if x>0)
    best=max(days,key=lambda x:x[1]) if days else None
    streak=0
    if days:
        mapping=dict(days)
        day=days[-1][0]
        if mapping.get(day,0)==0: day-=dt.timedelta(days=1)
        while mapping.get(day,0)>0:
            streak+=1;day-=dt.timedelta(days=1)
    return known,totals,active,best,streak


def activity(days):
    known,totals,active,best,streak=stats(days)
    body=text(45,49,'01  /  CONTRIBUTION ACTIVITY',15,CYAN,600,'enter',family='Mono',extra='style="animation-delay:1.55s"')
    body+=text(45,101,'The work, month by month.',39,INK,700,'enter',extra='style="animation-delay:1.7s"')
    if not known:
        body+=text(48,192,'Waiting for first daily GitHub data refresh.',22,MUTED,400,'enter')
    else:
        latest=days[-1][0]
        months=[]
        for shift in range(11,-1,-1):
            y=latest.year+(latest.month-1-shift)//12
            m=(latest.month-1-shift)%12+1
            months.append((y,m))
        highest=max(1,max(totals.get(m,0) for m in months))
        for i,(y,m) in enumerate(months):
            value=totals.get((y,m),0)
            bh=max(3,round(value/highest*112)) if value else 3
            x=51+i*76
            ytop=285-bh
            color=ACCENT if value==highest else BLUE
            body+=f'<rect x="{x}" y="{ytop}" width="42" height="{bh}" rx="5" fill="{color}" class="grow" style="animation-delay:{1.9+i*.075:.3f}s"/>'
            body+=text(x+21,306,calendar.month_abbr[m],13,MUTED,500,'',family='Mono',extra='text-anchor="middle"')
        topday=f'{best[0].strftime("%d %b %Y")} ({best[1]})' if best else 'None'
        for i,(a,b) in enumerate([('ACTIVE DAYS',str(active)),('CURRENT STREAK',str(streak)+' days'),('BUSIEST DAY',topday)]):
            x=50+i*315
            body+=text(x,358,a,13,MUTED,600,'',family='Mono')
            body+=text(x,392,b,23,ACCENT if i==1 else INK,700,'enter',extra=f'style="animation-delay:{2.9+i*.12:.2f}s"')
        body+=text(948,49,f'{sum(x for _,x in days)} CONTRIBUTIONS',13,ACCENT,600,'',family='Mono',extra='text-anchor="end"')
    write('activity.svg',body,h=423)


def graph(days):
    body=text(45,47,'02  /  CONTRIBUTION GRID',15,CYAN,600,'enter',family='Mono',extra='style="animation-delay:3.1s"')
    if not days:
        body+=text(45,133,'Contribution grid fills after the first refresh.',20,MUTED)
    else:
        end=days[-1][0]
        # Leftmost week starts on Sunday, as in GitHub's calendar.
        start=end-dt.timedelta(days=363)
        start-=dt.timedelta(days=(start.weekday()+1)%7)
        mapping=dict(days)
        vals=list(mapping.values()); high=max(vals,default=1)
        for week in range(53):
            for weekday in range(7):
                date=start+dt.timedelta(days=week*7+weekday)
                if date>end:continue
                val=mapping.get(date,0)
                level=0 if val==0 else max(1,min(4,math.ceil(val/max(high,1)*4)))
                palette=[BG,'#12433e','#147b68','#12b88a',ACCENT]
                x=46+week*17; y=75+weekday*17
                body+=f'<rect x="{x}" y="{y}" width="13" height="13" rx="3" fill="{palette[level]}" class="cell" style="animation-delay:{3.35+week*.028+weekday*.009:.3f}s"/>'
        body+=text(47,222,'LESS',12,MUTED,500,family='Mono')
        for i,col in enumerate([BG,'#12433e','#147b68','#12b88a',ACCENT]):
            body+=f'<rect x="{103+i*17}" y="211" width="12" height="12" rx="2" fill="{col}"/>'
        body+=text(200,222,'MORE',12,MUTED,500,family='Mono')
    write('graph.svg',body,h=244)


FEATURES=[
    ('Field Workforce Management','ANDROID  /  OPERATIONS',
     'Geofenced attendance, offline sync and a dashboard for field teams.',
     'Kotlin  ·  Jetpack Compose  ·  Firebase', 'workforce.svg'),
    ('Buzz Pass','WEB  /  EVENTS',
     'Event registrations, QR check-in and role-based management.',
     'React  ·  Node.js  ·  MongoDB', 'buzz-pass.svg'),
    ('ColdFlow','SAAS  /  EMAIL',
     'Campaign automation, SMTP delivery and lead imports.',
     'Next.js  ·  MongoDB  ·  Nodemailer','coldflow.svg'),
]


def repo_card(entry,idx):
    title,tag,desc,stack,filename=entry
    base=4.2+idx*.25
    body=text(47,51,f'0{idx+1}  /  FEATURED PROJECT  /  {tag}',14,CYAN,600,'enter',family='Mono',extra=f'style="animation-delay:{base:.2f}s"')
    body+=text(47,118,title,39,INK,700,'enter',extra=f'style="animation-delay:{base+.1:.2f}s"')
    body+=text(48,166,desc,18,MUTED,400,'enter',extra=f'style="animation-delay:{base+.22:.2f}s"')
    body+=f'<rect x="47" y="192" width="900" height="1" fill="{STROKE}"/>'
    body+=text(48,229,stack,16,ACCENT,500,'enter',family='Mono',extra=f'style="animation-delay:{base+.3:.2f}s"')
    body+=text(949,52,'↗',26,ACCENT,600,extra='text-anchor="end"')
    write(filename,body,h=256)


def main():
    if '--refresh' in sys.argv: refresh()
    fonts()
    days=load()
    hero()
    tile('portfolio.svg',0,'Portfolio','Projects & experience',CYAN)
    tile('linkedin.svg',1,'LinkedIn','Connect with me',ACCENT)
    tile('email.svg',2,'Email','Say hello', '#82a8ff')
    activity(days);graph(days)
    for i,feature in enumerate(FEATURES):repo_card(feature,i)
    print('Rendered',len(list(OUT.glob('*.svg'))),'SVG cards. STATIC=',STATIC,'Data days=',len(days))

if __name__=='__main__':main()
