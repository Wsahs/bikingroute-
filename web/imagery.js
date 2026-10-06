(function(root){
'use strict';
function tileURL({x,y,z}){
 const half=20037508.342789244,span=2*half/2**z;
 const bbox=[-half+x*span,half-(y+1)*span,-half+(x+1)*span,half-y*span];
 return 'https://gis.pbcgov.org/image/rest/services/Aerialphotgraphy_2026_WebMercator/ImageServer/exportImage?'+new URLSearchParams({bbox:bbox.join(','),bboxSR:'3857',imageSR:'3857',size:'256,256',format:'jpg',f:'image',adjustAspectRatio:'false'});
}
const api={tileURL};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.SidepathImagery=api;
})(typeof window==='undefined'?{}:window);
