const test=require('node:test'),assert=require('node:assert/strict');
const attach=require('../map-gestures.js');
function setup(){const listeners={};let zoom=13;attach({addEventListener(name,fn){listeners[name]=fn;}},{getZoom:()=>zoom,setZoom:v=>zoom=v});return {listeners,zoom:()=>zoom};}
function event(fields){return {...fields,preventDefault(){this.prevented=true;},stopImmediatePropagation(){this.stopped=true;}};}
test('trackpad pinch zooms map and prevents page zoom',()=>{const x=setup(),e=event({ctrlKey:true,deltaY:-100,deltaMode:0});x.listeners.wheel(e);assert(x.zoom()>13);assert(e.prevented);assert(e.stopped);});
test('ordinary scrolling stays with Google Maps',()=>{const x=setup(),e=event({ctrlKey:false,deltaY:20});x.listeners.wheel(e);assert.equal(x.zoom(),13);assert(!e.prevented);});
test('WebKit pinch uses starting zoom and scale',()=>{const x=setup();x.listeners.gesturestart(event({scale:1}));x.listeners.gesturechange(event({scale:2}));assert.equal(x.zoom(),14);x.listeners.gesturechange(event({scale:.5}));assert.equal(x.zoom(),12);});
test('overlapping WebKit and wheel events cannot zoom the page or double-zoom',()=>{const x=setup();x.listeners.gesturestart(event({scale:1}));const e=event({ctrlKey:true,deltaY:-100,deltaMode:0});x.listeners.wheel(e);assert.equal(x.zoom(),13);assert(e.prevented);});
