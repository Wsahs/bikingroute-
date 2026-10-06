import heapq,math
from server.routing import Network,_route,SearchLimitError

def plan_bicycle(graph,start,end,speed):
 net=Network(dict(graph,edges=[dict(e,quiet_verified=True) if e['kind']=='street' else e for e in graph['edges']]))
 if start not in net.nodes or end not in net.nodes:raise ValueError('Choose mapped access points')
 queue=[(0,start)];dist={start:0};prev={};visited=0
 result={'status':'insufficient_data','primary':None,'alternative':None,'coverage':net.metadata,'warnings':['Only mapped bicycle-permitted connections are included. Coverage is incomplete.']}
 while queue:
  d,a=heapq.heappop(queue)
  if d!=dist[a]:continue
  visited+=1
  if visited>200000:raise SearchLimitError('Route search limit reached')
  if a==end:
   edges=[]
   while a!=start:e=prev[a];edges.append(e);a=e['from']
   result.update(status='primary',primary=_route(edges[::-1],speed));return result
  for e in net.adj[a]:
   b=e['to'];nd=d+e['length_m']
   if nd<dist.get(b,math.inf):dist[b]=nd;prev[b]=e;heapq.heappush(queue,(nd,b))
 return result
