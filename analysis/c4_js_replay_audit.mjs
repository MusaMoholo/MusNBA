// Check the shipped browser accumulator against every source-bound saved example.
import {readFileSync,writeFileSync,existsSync} from 'node:fs';
import {createHash} from 'node:crypto';
globalThis.location=new URL('http://localhost/');
const {replayState,BOX}=await import('../scripts/webapp/replay.mjs');
const read=path=>JSON.parse(readFileSync(path,'utf8'));
const digest=path=>createHash('sha256').update(readFileSync(path)).digest('hex');
const out='analysis/experiments/20261124_c4_js_replay_audit_v1.json';if(existsSync(out))throw Error('immutable audit exists');
const report=read('analysis/experiments/20261124_c4_retained_capture_v1.json');
let examples=0,cutpoints=0,boxes=0,overtime=0,maxMinuteError=0;const sources={};
for(const row of report.games){
 const file=`data/views/api/game/${row.game}/replay.json`,payload=read(file),game=read(`data/views/api/game/${row.game}.json`);
 if(payload.source_id!==game.replay.source_id||payload.examples.length!==5)throw Error('view source/selection differs');
 sources[file]=digest(file);
 for(const e of payload.examples){
  for(const n of [0,Math.floor(e.events.length/2),e.events.length]){
   const state=replayState(e,n,payload.players),score=[0,0];
   for(const p of payload.players)score[p.side]+=state.lines[p.id].pts;
   if(JSON.stringify(score)!==JSON.stringify(state.score))throw Error('prefix player points differ from scoreboard');
   cutpoints++;
  }
  const end=replayState(e,e.events.length,payload.players);
  if(JSON.stringify(end.score)!==JSON.stringify(e.final_score))throw Error('final score differs');
  for(const p of payload.players){
   const actual=end.lines[p.id],expected=e.final_box[p.id];
   for(const key of BOX)if(actual[key]!== (key==='reb'?expected.oreb+expected.dreb:expected[key]))throw Error('browser final box differs:'+key);
   const error=Math.abs(actual.min-expected.min);if(error>1e-8)throw Error('browser minutes differ');maxMinuteError=Math.max(maxMinuteError,error);boxes++;
  }
  if(end.period>4)overtime++;examples++;
 }
}
const result={kind:'shipped browser replay accumulator, all saved examples and zero/midpoint/final prefixes',games:report.games.length,examples,cutpoints,player_boxes:boxes,overtime_examples:overtime,max_minute_error:maxMinuteError,view_sha256:sources,module_sha256:digest('scripts/webapp/replay.mjs'),status:'pass'};
writeFileSync(out,JSON.stringify(result,null,2)+'\n');console.log(result);
