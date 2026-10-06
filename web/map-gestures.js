(function(root){
 'use strict';
 function attach(element,map){
  let initialZoom=null;
  const setZoom=value=>{if(Number.isFinite(value))map.setZoom(Math.max(0,Math.min(21,value)));};
  // Trackpads emit Ctrl+wheel for pinch; keep that gesture inside the map.
  element.addEventListener('wheel',event=>{
   if(!event.ctrlKey)return;
   event.preventDefault();event.stopImmediatePropagation();
   if(initialZoom!==null)return;
   const unit=event.deltaMode===1?16:event.deltaMode===2?200:1;
   setZoom(map.getZoom()-event.deltaY*unit/200);
  },{capture:true,passive:false});
  // WebKit supplies gesture events instead of Ctrl+wheel on some Macs.
  element.addEventListener('gesturestart',event=>{
   event.preventDefault();event.stopImmediatePropagation();initialZoom=map.getZoom();
  },{capture:true,passive:false});
  element.addEventListener('gesturechange',event=>{
   if(initialZoom===null||!(event.scale>0))return;
   event.preventDefault();event.stopImmediatePropagation();setZoom(initialZoom+Math.log2(event.scale));
  },{capture:true,passive:false});
  element.addEventListener('gestureend',event=>{
   event.preventDefault();event.stopImmediatePropagation();initialZoom=null;
  },{capture:true,passive:false});
 }
 if(typeof module!=='undefined'&&module.exports)module.exports=attach;
 else root.attachMapGestures=attach;
})(typeof window==='undefined'?globalThis:window);
