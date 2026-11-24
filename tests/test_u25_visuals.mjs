import assert from 'node:assert/strict';
import test from 'node:test';
globalThis.location=new URL('http://localhost/');
const {quantileStrip,probabilityBar,ratingsPlot,setMeta}=await import('../scripts/webapp/ui.mjs');
test('quantiles preserve missingness, reject reversed ranges, and render a point mass honestly',()=>{
 assert.equal(quantileStrip({exact_q:[null,1,2,3,4]}),'');
 assert.equal(quantileStrip({exact_q:[0,2,1,3,4]}),'');
 const html=quantileStrip({exact_q:[2,2,2,2,2]});assert.match(html,/cx="100"/);assert.match(html,/2.0 to 2.0/);
});
test('probability bars distinguish unsupported probabilities from zero',()=>{
 for(const p of [null,undefined,NaN,-.1,1.1])assert.equal(probabilityBar(p),'');
 assert.match(probabilityBar(0),/width:0%/);assert.match(probabilityBar(.375),/width:37.5%/);
});
test('ratings chart excludes missing ratings, preserves team links and defence direction',()=>{
 setMeta({teams:{'1':{name:'One',abbr:'ONE'},'2':{name:'Two',abbr:'TWO'}}});
 const html=ratingsPlot([{id:'1',ortg:120,drtg:100},{id:'2',ortg:110,drtg:115},{id:'3',ortg:null,drtg:90}]);
 assert.match(html,/#\/team\/1/);assert.doesNotMatch(html,/#\/team\/3/);
 const ys=[...html.matchAll(/<circle cx="[^"]+" cy="([^"]+)"/g)].map(x=>Number(x[1]));assert.ok(ys[0]<ys[1]);
});
