"""Сборка styles/styles.css (запуск из корня хаба: python tools/build_styles.py styles/src styles/styles.css): каждый пакет (styles-src/<id>.css) ограничивается своим стилем.
   :root/html → :root:root[data-style="id"] (специфичность выше палитр app.css в обеих темах);
   остальные селекторы получают префикс; блок /*@hub*/…/*@endhub*/ — только для хаба;
   @keyframes переименовываются (<id>-имя), @font-face выбрасываются (шрифты грузит suite.js)."""
import re,sys,os,shutil
SRC,OUT=sys.argv[1],sys.argv[2]
ORDER=['azure','aquarelle','glare','neon','ether','glass','graphite']
def strip_comments(t):
    out=[];i=0
    while i<len(t):
        if t.startswith('/*@hub*/',i): out.append('\x01');i+=8;continue
        if t.startswith('/*@endhub*/',i): out.append('\x02');i+=11;continue
        if t.startswith('/*',i): j=t.index('*/',i+2); i=j+2; continue
        out.append(t[i]); i+=1
    return ''.join(out)
def split_top(s,ch=','):
    parts=[];d=0;q=None;cur=''
    for c in s:
        if q:
            cur+=c
            if c==q: q=None
            continue
        if c in '"\'': q=c
        elif c in '([': d+=1
        elif c in ')]': d-=1
        if c==ch and d==0: parts.append(cur); cur=''
        else: cur+=c
    parts.append(cur); return parts
def scope_sel(sel,sid,hub):
    s=sel.strip(); pre=f':root:root[data-style="{sid}"]'+('[data-app="hub"]' if hub else '')
    if s.startswith('['): return pre+s
    for lead in ['html:root:root:root','html:root:root',':root:root',':root','html']:
        if s.startswith(lead) and (len(s)==len(lead) or s[len(lead)] in ' [:.>#~+'):
            return pre+s[len(lead):]
    return pre+' '+s
def parse(t,i=0,hub=False):
    """→ список узлов: ('rule',sel,body) | ('at',head,children|None,body) ; учитывает строки и вложенность; hub наследуется во вложенные @media"""
    nodes=[];buf=''
    while i<len(t):
        c=t[i]
        if c=='\x01': hub=True; i+=1; continue
        if c=='\x02': hub=False; i+=1; continue
        if c in '"\'':
            j=i+1
            while t[j]!=c: j+=1
            buf+=t[i:j+1]; i=j+1; continue
        if c=='{':
            head=buf.strip(); buf=''
            if head.startswith('@media') or head.startswith('@supports'):
                kids,i=parse(t,i+1,hub); nodes.append(('at',head,kids,None,hub))
            else:
                d=1;j=i+1;q=None
                while d:
                    ch=t[j]
                    if q:
                        if ch==q: q=None
                    elif ch in '"\'': q=ch
                    elif ch=='{': d+=1
                    elif ch=='}': d-=1
                    j+=1
                body=t[i+1:j-1]
                if head.startswith('@'): nodes.append(('at',head,None,body,hub))
                else: nodes.append(('rule',head,body,None,hub))
                i=j
            continue
        if c=='}': return nodes,i+1
        buf+=c; i+=1
    return nodes,i
def emit(nodes,sid,kf,ind=''):
    out=[]
    for n in nodes:
        if n[0]=='rule':
            _,sel,body,_,hub=n
            sels=[scope_sel(x,sid,hub) for x in split_top(sel) if x.strip()]
            for k,v in kf.items(): body=re.sub(r'(animation(?:-name)?\s*:[^;]*?)\b'+re.escape(k)+r'\b',lambda m:m.group(1)+v,body)
            out.append(f"{ind}{', '.join(sels)} {{{body.strip()}}}")
        else:
            _,head,kids,body,hub=n
            if head.startswith('@font-face'): continue
            if head.startswith('@keyframes'):
                name=head.split()[1]; out.append(f"{ind}@keyframes {kf[name]} {{{body.strip()}}}"); continue
            if kids is not None:
                out.append(f"{ind}{head} {{\n"+emit(kids,sid,kf,ind+'  ')+f"\n{ind}}}")
            else: out.append(f"{ind}{head} {{{body}}}")
    return '\n'.join(out)
res=['/* styles.css — стили оформления набора утилит (собран tools/build_styles.py из styles-src/*.css; вручную не править).\n   Подключается suite.js только когда выбран не «Журнал». Каждый пакет ограничен :root[data-style="…"]. */']
for sid in ORDER:
    p=os.path.join(SRC,sid+'.css')
    if not os.path.exists(p): continue
    t=strip_comments(open(p,encoding='utf-8').read())
    kf={m:f'{sid}-{m}' for m in re.findall(r'@keyframes\s+([\w-]+)',t)}
    nodes,_=parse(t)
    res.append(f'\n/* ===================== {sid} ===================== */\n'+emit(nodes,sid,kf))
os.makedirs(os.path.dirname(OUT),exist_ok=True)
open(OUT,'w',encoding='utf-8').write('\n'.join(res)+'\n')
print('ok',OUT,os.path.getsize(OUT)//1024,'KB')
