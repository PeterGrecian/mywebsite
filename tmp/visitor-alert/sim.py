import json,collections,re,sys,urllib.parse
rows=[]
for f in sys.argv[1:]:
    rows+=[{x['field']:x['value'] for x in r} for r in json.load(open(f))['results']]
seen=set(); uniq=[]
for x in rows:
    k=x.get('@ptr') or json.dumps(x,sort_keys=True)
    if k in seen: continue
    seen.add(k); uniq.append(x)
BOT=re.compile(r'bot|crawl|spider|slurp|curl|wget|python|go-http|java|okhttp|axios|node-fetch|httpx|aiohttp|libwww|headless|lighthouse|petal|semrush|censys|scan|sniff|research|preview|facebookexternal|calendaralarm|inspection|googleother|google-|associationservice|redirectmap',re.I)
FAV={'/favicon.ico','/favicon.png','/favicon.svg'}
OWN={'81.96.235.31'}
def trig(x):
    ua=x.get('ua','')
    if not ua.startswith('Mozilla/') or BOT.search(ua): return None
    if x['ip'] in OWN: return None
    if x['ip'].startswith('66.249.'): return None
    if x.get('status')!='200': return None
    p=x['path']
    if p in FAV: return 'favicon'
    ref=x.get('ref','')
    u=urllib.parse.urlparse(ref)
    if u.hostname and u.hostname.endswith('petergrecian.co.uk') and (u.path or '/')!=p: return 'link'
    return None
hits=collections.OrderedDict()
for x in sorted(uniq,key=lambda x:x['@timestamp']):
    t=trig(x)
    if t:
        k=(x['@timestamp'][:10],x['ip'])
        hits.setdefault(k,(x['@timestamp'],t,x['path'],x.get('ref','')[:60],x['ua'][:60]))
print(len(uniq),'rows', uniq and min(x['@timestamp'] for x in uniq), max(x['@timestamp'] for x in uniq))
for k,v in hits.items(): print(k[1][:28].ljust(28),*v)
print(len(hits),'alerts'); print(collections.Counter(k[0] for k in hits))
