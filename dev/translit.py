#!/usr/bin/env python3
"""Katakana -> romaji (Hepburn-ish) plus fuzzy matching against a dictionary of English names."""
import re,difflib
K={'ア':'a','イ':'i','ウ':'u','エ':'e','オ':'o','カ':'ka','キ':'ki','ク':'ku','ケ':'ke','コ':'ko','サ':'sa','シ':'shi','ス':'su','セ':'se','ソ':'so',
'タ':'ta','チ':'chi','ツ':'tsu','テ':'te','ト':'to','ナ':'na','ニ':'ni','ヌ':'nu','ネ':'ne','ノ':'no','ハ':'ha','ヒ':'hi','フ':'fu','ヘ':'he','ホ':'ho',
'マ':'ma','ミ':'mi','ム':'mu','メ':'me','モ':'mo','ヤ':'ya','ユ':'yu','ヨ':'yo','ラ':'ra','リ':'ri','ル':'ru','レ':'re','ロ':'ro','ワ':'wa','ヲ':'wo','ン':'n',
'ガ':'ga','ギ':'gi','グ':'gu','ゲ':'ge','ゴ':'go','ザ':'za','ジ':'ji','ズ':'zu','ゼ':'ze','ゾ':'zo','ダ':'da','ヂ':'ji','ヅ':'zu','デ':'de','ド':'do',
'バ':'ba','ビ':'bi','ブ':'bu','ベ':'be','ボ':'bo','パ':'pa','ピ':'pi','プ':'pu','ペ':'pe','ポ':'po','ヴ':'vu',
'ァ':'a','ィ':'i','ゥ':'u','ェ':'e','ォ':'o','ャ':'ya','ュ':'yu','ョ':'yo','ッ':'*','ー':'-'}
H={chr(ord(c)-0x60):v for c,v in K.items() if 'ァ'<=c<='ヶ'}  # hiragana
def romaji(s):
    out=''; i=0
    while i<len(s):
        c=s[i]; nxt=s[i+1] if i+1<len(s) else ''
        base=K.get(c) or H.get(c)
        if base is None: out+=c; i+=1; continue
        if nxt and nxt in 'ャュョ' and base.endswith('i'):   # kya, sha, cha, ja...
            y=K[nxt][1]; stem=base[:-1]
            if stem=='sh' or stem=='ch' or stem=='j': out+=stem+y
            else: out+=stem+'y'+y
            i+=2; continue
        if nxt and nxt in 'ァィゥェォ' and base in ('fu','vu','u','te','de','chi','ji','shi','tsu','ku','gu'):
            v=K[nxt]; stem={'fu':'f','vu':'v','u':'w','te':'t','de':'d','chi':'ch','ji':'j','shi':'sh','tsu':'ts','ku':'kw','gu':'gw'}[base]
            out+=stem+v; i+=2; continue
        out+=base; i+=1
    out=re.sub(r'\*(.)',r'\1\1',out)        # sokuon doubles the next consonant
    out=out.replace('-','')                  # long vowel marks dropped
    out=re.sub(r'([aeiou])\1',r'\1',out)     # collapse doubled vowels
    out=out.replace('ou','o')
    return out
def key(s):
    s=s.lower(); s=re.sub(r"[^a-z]",'',s)
    s=s.replace('ph','f').replace('th','t').replace('ck','k').replace('c','k').replace('q','k').replace('x','ks').replace('l','r').replace('v','b').replace('w','u').replace('y','i')
    s=re.sub(r'(.)\1',r'\1',s)
    return s
def best_match(kana,names,cutoff=0.8):
    r=romaji(kana); k=key(r)
    cands={key(n):n for n in names}
    m=difflib.get_close_matches(k,list(cands),n=1,cutoff=cutoff)
    return (cands[m[0]],difflib.SequenceMatcher(None,k,key(cands[m[0]])).ratio()) if m else (None,0)
def pretty(kana):
    r=romaji(kana); return r[:1].upper()+r[1:]

def anglicize(kana):
    """romaji with Western-name conventions: long marks -> r, final u dropped, ru->l before consonants, etc."""
    out=''; i=0; s=kana
    while i<len(s):
        c=s[i]; nxt=s[i+1] if i+1<len(s) else ''
        base=K.get(c) or H.get(c)
        if base is None: out+=c; i+=1; continue
        if nxt and nxt in 'ャュョ' and base.endswith('i'):
            y=K[nxt][1]; stem=base[:-1]; out+=(stem+y if stem in ('sh','ch','j') else stem+'y'+y); i+=2; continue
        if nxt and nxt in 'ァィゥェォ' and base in ('fu','vu','u','te','de','chi','ji','shi','tsu','ku','gu'):
            out+={'fu':'f','vu':'v','u':'w','te':'t','de':'d','chi':'ch','ji':'j','shi':'sh','tsu':'ts','ku':'kw','gu':'gw'}[base]+K[nxt]; i+=2; continue
        out+=base; i+=1
    out=re.sub(r'\*(.)',r'\1\1',out)
    out=re.sub(r'([ao])-',r'\1r',out); out=re.sub(r'u-','oo',out); out=re.sub(r'i-','ee',out); out=re.sub(r'e-','ay',out); out=out.replace('-','')
    out=out.replace('vu','v')
    out=re.sub(r'kkusu$','x',out); out=re.sub(r'ssu$','ss',out)
    out=re.sub(r'ru(?=[^aeiouy]|$)','l',out)
    out=re.sub(r'([kgszdbmptfh]|ts|sh|ch|j)u$',r'\1',out)
    out=re.sub(r'(d|t)o$',r'\1',out)
    out=re.sub(r'([bdgkmpstz])\1',r'\1',out)
    out=out.replace('ou','o').replace('aa','a').replace('ii','i').replace('uu','u')
    return out[:1].upper()+out[1:]
def match2(kana,names,cutoff=0.86):
    a=anglicize(kana); ka=key(a)
    cands={}
    for n in names: cands.setdefault(key(n),n)
    m=difflib.get_close_matches(ka,list(cands),n=3,cutoff=cutoff)
    for c in m:
        if c[:1]==ka[:1]: return cands[c]
    return None
