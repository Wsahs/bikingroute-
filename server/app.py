"""Local routing API with explicit mapped access-point selection."""
import argparse,json,math,mimetypes,os,threading,urllib.parse
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from server.routing import plan,eligible,SearchLimitError
from server.import_osm import meters
from server.addresses import AddressIndex
from server.evidence import nearby
from server.access import access_points
from server.directions import RoadNames,directions
ROOT=Path(__file__).resolve().parents[1]

def demo():
 return {'nodes':[dict(id=n,lat=26.35,lon=-80.1) for n in ['start','finish']], 'edges':[dict(id=str(i),**{'from':'start','to':'finish'},length_m=d,kind=k,bicycle_allowed=True,assessed=True,quiet_verified=True,geometry=[[-80.1,26.35],[-80.099,26.35]]) for i,(d,k) in enumerate([(6000,'trail'),(300,'street')])], 'metadata':{'demo':True,'coverage_complete':False}}

class Application:
 def __init__(self,graph=None,data_dir=None):self.graph=graph;self.data_dir=Path(data_dir) if data_dir else None;self.cache={};self.versions={};self.lock=threading.Lock();self.road_names=None
 def load(self,dataset):
  if dataset=='demo':return demo()
  if dataset not in ('boca','hollywood'):raise ValueError('Unknown dataset')
  if self.graph is not None:return self.graph
  if self.data_dir:
   with self.lock:
    path=self.data_dir/(dataset+'-network.json')
    if path.exists():
     version=path.stat().st_mtime_ns
     if self.versions.get(dataset)!=version:
      self.cache[dataset]=json.loads(path.read_text());self.versions[dataset]=version
    return self.cache.get(dataset)
 def with_directions(self,result,dataset):
  if dataset=='boca' and self.data_dir and self.road_names is None:
   with self.lock:
    source=self.data_dir/'sources/pbc-roads.geojson'
    if self.road_names is None and source.exists():self.road_names=RoadNames(json.loads(source.read_text())['features'])
  for key in ('primary','alternative'):
   if result.get(key):result[key]['directions']=directions(result[key]['segments'],self.road_names if dataset=='boca' else None)
  return result
 def dispatch(self,method,path,payload=None):
  u=urllib.parse.urlparse(path);q=urllib.parse.parse_qs(u.query);path=u.path
  try:
   if method=='POST' and not isinstance(payload,dict):raise ValueError('Expected JSON object')
   if path.startswith('/api/google/'):
    from server.google_maps import dispatch
    return dispatch(method,path,q,payload or {})
   dataset=(payload or {}).get('dataset',q.get('dataset',['boca'])[0])
   if path=='/api/addresses' and method=='GET':
    if dataset not in ('boca','hollywood'):raise ValueError('Unknown dataset')
    database=(self.data_dir or ROOT/'data')/'addresses.sqlite'
    return 200,{'results':AddressIndex(database).search(q.get('q',[''])[0],dataset) if database.exists() else [],'source':'Local county address records'}
   g=self.load(dataset)
   mode=(payload or {}).get('mode',q.get('mode',['sidewalk'])[0])
   if mode not in ('sidewalk','bicycle'):raise ValueError('Unknown mode')
   def allowed(edge):return eligible(dict(edge,quiet_verified=True) if mode=='bicycle' and edge.get('kind')=='street' else edge)
   if path=='/api/status':return 200,{'coverage':g['metadata'] if g else {'coverage_complete':False,'available':False},'regions':[{'id':k,'available':self.graph is not None or bool(self.data_dir and (self.data_dir/(k+'-network.json')).exists())} for k in ['boca','hollywood']]}
   if path=='/api/route' and method=='POST':
    if any(not isinstance(payload.get(k),str) or not payload[k] for k in ['start','end']):raise ValueError('Select mapped access points')
    speed=payload.get('speed_mph',10)
    if isinstance(speed,bool) or not isinstance(speed,(float,int)) or not math.isfinite(speed) or not 1<=speed<=35:raise ValueError('Speed must be between 1 and 35 mph')
    if not g:return 503,{'code':'coverage_unavailable','error':'No imported network for this area'}
    if payload.get('mode','sidewalk')=='bicycle':
     from server.bicycle import plan_bicycle
     return 200,self.with_directions(plan_bicycle(g,payload['start'],payload['end'],speed*.44704),dataset)
    if payload.get('mode','sidewalk')!='sidewalk':raise ValueError('Unknown mode')
    return 200,self.with_directions(plan(g,payload['start'],payload['end'],speed*.44704),dataset)
   if path=='/api/access':
    lat=float(q.get('lat',[''])[0]);lon=float(q.get('lon',[''])[0])
    if not math.isfinite(lat) or not math.isfinite(lon) or not -90<=lat<=90 or not -180<=lon<=180:raise ValueError('Invalid coordinates')
    if not g:return 503,{'error':'Coverage unavailable'}
    points=access_points(g,allowed,lat,lon)
    evidence=nearby((self.data_dir or ROOT/'data')/'evidence.sqlite',lat,lon)
    return 200,{'points':points,'sidewalk_evidence':evidence,'warning':'Straight-line distance only. Address-to-path access has not been verified.'}
   if path=='/api/network':
    if not g:return 503,{'error':'Coverage unavailable'}
    seen=set();features=[]
    for e in g['edges']:
     key=tuple(sorted((e['from'],e['to'])))
     if not allowed(e) or not e.get('geometry') or key in seen:continue
     seen.add(key);features.append({'type':'Feature','properties':{k:e.get(k) for k in ['id','kind','name','source']},'geometry':{'type':'LineString','coordinates':e['geometry']},'access':{'start':e['from'],'end':e['to']}})
    segment_count=len(features)
    if q.get('display')==['1']:
     groups={}
     for feature in features:
      props=feature['properties'];key=(props.get('source'),props.get('kind'),props.get('name'))
      if key not in groups:groups[key]={'type':'Feature','properties':props,'geometry':{'type':'MultiLineString','coordinates':[]}}
      groups[key]['geometry']['coordinates'].append(feature['geometry']['coordinates'])
     features=list(groups.values())
    return 200,{'type':'FeatureCollection','features':features,'segment_count':segment_count,'coverage':g['metadata']}
   return 404,{'error':'Endpoint not found'}
  except (ValueError,TypeError,KeyError) as e:return 400,{'error':str(e)}
  except SearchLimitError as e:return 503,{'code':'search_incomplete','error':str(e)}

def serve(host,port):
 config=ROOT/'.env'
 if config.exists():
  for line in config.read_text().splitlines():
   name,separator,value=line.partition('=')
   if separator and name in ('GOOGLE_MAPS_API_KEY','GOOGLE_MAPS_BROWSER_KEY'):
    os.environ.setdefault(name,value.strip())
 app=Application(data_dir=ROOT/'data')
 class Handler(BaseHTTPRequestHandler):
  def do_GET(self):self.respond()
  def do_POST(self):self.respond()
  def respond(self):
   try:
    if self.path.startswith('/api/'):
     payload=None
     if self.command=='POST':
      n=int(self.headers.get('Content-Length','0'))
      if not 0<n<=16384:raise ValueError('Invalid request size')
      payload=json.loads(self.rfile.read(n))
     code,result=app.dispatch(self.command,self.path,payload);body=json.dumps(result).encode();mime='application/json'
    else:
     name=urllib.parse.unquote(urllib.parse.urlparse(self.path).path)
     f=(ROOT/'web'/('live.html' if name=='/' else name.lstrip('/'))).resolve()
     if ROOT/'web' not in f.parents or not f.is_file():self.send_error(404);return
     code=200;body=f.read_bytes();mime=mimetypes.guess_type(str(f))[0] or 'application/octet-stream'
    self.send_response(code);self.send_header('Content-Type',mime);self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
   except (ValueError,json.JSONDecodeError):self.send_error(400,'Invalid request')
 print('Sidepath: http://%s:%d'%(host,port),flush=True);ThreadingHTTPServer((host,port),Handler).serve_forever()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--host',default='127.0.0.1');p.add_argument('--port',type=int,default=8765);a=p.parse_args();serve(a.host,a.port)
