"""Google Places and cycling routes. Keys come from runtime configuration."""
import json,os,re,urllib.request,urllib.error,urllib.parse

def request(url,payload,fields):
 key=os.environ.get('GOOGLE_MAPS_API_KEY','')
 if not key:return 503,{'error':'Google Maps is not configured. Add a server key to local runtime configuration.'}
 req=urllib.request.Request(url,json.dumps(payload).encode() if payload is not None else None,{'Content-Type':'application/json','X-Goog-Api-Key':key,'X-Goog-FieldMask':fields})
 try:
  with urllib.request.urlopen(req,timeout=20) as response:return 200,json.load(response)
 except urllib.error.HTTPError as e:
  return 502,{'error':{403:'Google has denied access to this service for the configured key.',429:'Google’s daily demo quota has been reached. Try again tomorrow.'}.get(e.code,'Google could not complete this request. Please try again.'),'provider_status':e.code}
 except (urllib.error.URLError,TimeoutError):return 502,{'error':'Google Maps could not be reached. Please try again.'}

def dispatch(method,path,q,payload):
 if path=='/api/google/config' and method=='GET':return 200,{'browserKey':os.environ.get('GOOGLE_MAPS_BROWSER_KEY','')}
 if path in ('/api/google/autocomplete','/api/google/place') and method=='GET':
  session=q.get('session',[''])[0]
  if session and not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',session):return 400,{'error':'Invalid search session.'}
  if path.endswith('/autocomplete'):
   query=q.get('q',[''])[0].strip()
   if not query:return 200,{'suggestions':[]}
   if len(query)>200:return 400,{'error':'Search is too long.'}
   body={'input':query,'includedRegionCodes':['us'],'languageCode':'en','locationBias':{'circle':{'center':{'latitude':26.365,'longitude':-80.12},'radius':50000}}}
   if session:body['sessionToken']=session
   code,result=request('https://places.googleapis.com/v1/places:autocomplete',body,'suggestions.placePrediction.placeId,suggestions.placePrediction.text.text')
   if code!=200:return code,result
   return 200,{'suggestions':[{'id':p['placeId'],'label':p['text']['text']} for item in result.get('suggestions',[]) if (p:=item.get('placePrediction')) and p.get('placeId') and p.get('text',{}).get('text')]}
  place_id=q.get('id',[''])[0]
  if not re.fullmatch(r'[A-Za-z0-9_-]{1,300}',place_id):return 400,{'error':'Select a valid place suggestion.'}
  suffix='?'+urllib.parse.urlencode({'sessionToken':session}) if session else ''
  return request('https://places.googleapis.com/v1/places/'+place_id+suffix,None,'id,displayName,formattedAddress,location')
 if path=='/api/google/search' and method=='GET':
  query=q.get('q',[''])[0].strip()
  if len(query)<3:return 200,{'places':[]}
  if len(query)>200:return 400,{'error':'Search is too long.'}
  return request('https://places.googleapis.com/v1/places:searchText',{'textQuery':query,'pageSize':5,'locationBias':{'circle':{'center':{'latitude':26.365,'longitude':-80.12},'radius':40000}}},'places.id,places.displayName,places.formattedAddress,places.location')
 if path=='/api/google/route' and method=='POST':
  if any(not isinstance(payload.get(k),str) or not payload[k].strip() or len(payload[k])>300 for k in ('origin','destination')):return 400,{'error':'Select both addresses from Google’s suggestions.'}
  return request('https://routes.googleapis.com/directions/v2:computeRoutes',{'origin':{'placeId':payload['origin']},'destination':{'placeId':payload['destination']},'travelMode':'BICYCLE','computeAlternativeRoutes':True,'languageCode':'en-US','units':'IMPERIAL'},'routes.distanceMeters,routes.duration,routes.polyline.encodedPolyline,routes.legs.steps,routes.warnings,routes.description')
 return 404,{'error':'Endpoint not found'}
