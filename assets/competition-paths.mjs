// Exact arithmetic on retained season paths. No generation, fitting or fetches.
const SHAPES = {seed:30,wins:30,playoff_seed:30,reach:30,cup_rank:30,cup_group:30,cup_champion:1,champion:1,series:60,cup_matches:21};
export function decodePaths(data) {
  if (data?.schema !== 'nba-competitions-2026-v1' || !data.paths) return null;
  const W=data.worlds;
  if (!Number.isSafeInteger(W)||W<1||data.ids?.length!==30||data.weights?.length!==W) throw Error('Invalid competition path shape');
  const a={};
  for (const [key,width] of Object.entries(SHAPES)) {
    const text=atob(data.paths[key]||'');
    if (text.length!==W*width) throw Error('Invalid '+key+' path length');
    a[key]=Uint8Array.from(text,c=>c.charCodeAt(0));
  }
  let total=0;
  for(const w of data.weights) {if(!Number.isSafeInteger(w)||w<=0)throw Error('Invalid path mass');total+=w;}
  if(!Number.isSafeInteger(total)||total!==data.mass)throw Error('Invalid total path mass');
  return {W,a,weights:data.weights,total,ids:data.ids};
}
export function conditionMask(paths, team, event) {
  const i=paths.ids.indexOf(team);if(i<0)throw Error('Unknown condition team');
  return Uint8Array.from({length:paths.W},(_,w)=>{
    const at=w*30+i;
    switch(event) {
      case 'all':return 1;
      case 'cup_qf':return paths.a.cup_rank[at]<=4;
      case 'cup_title':return paths.a.cup_champion[w]===i;
      case 'top6':return paths.a.seed[at]<=6;
      case 'playoffs':return paths.a.reach[at]>=1;
      case 'finals':return paths.a.reach[at]>=4;
      case 'title':return paths.a.champion[w]===i;
      default:throw Error('Unknown condition');
    }
  });
}
export function stageSummary(paths,mask) {
  let mass=0,count=0;const stages=Array.from({length:30},()=>({cup_qf:0,cup_sf:0,cup_final:0,cup_title:0,playoffs:0,round2:0,conference:0,finals:0,title:0}));
  for(let w=0;w<paths.W;w++)if(!mask||mask[w]) {
    const weight=paths.weights[w];mass+=weight;count++;
    for(let t=0;t<30;t++) {
      const s=stages[t],r=paths.a.reach[w*30+t];
      if(paths.a.cup_rank[w*30+t]<=4)s.cup_qf+=weight;
      for(const [name,v] of [['playoffs',1],['round2',2],['conference',3],['finals',4],['title',5]])if(r>=v)s[name]+=weight;
      if(paths.a.cup_champion[w]===t)s.cup_title+=weight;
      if([12,13,15,16].some(j=>paths.a.cup_matches[w*21+j]===t))s.cup_sf+=weight;
      if(paths.a.cup_matches[w*21+18]===t||paths.a.cup_matches[w*21+19]===t)s.cup_final+=weight;
    }
  }
  return {mass,count,teams:Object.fromEntries(paths.ids.map((id,i)=>[id,Object.fromEntries(Object.entries(stages[i]).map(([k,n])=>[k,mass?n/mass:null]))]))};
}
export function matchups(paths,stage,mask) {
  const rows=new Map();let support=0;
  for(let w=0;w<paths.W;w++)if(!mask||mask[w]) {
    const weight=paths.weights[w];support+=weight;
    const slots=stage.startsWith('cup_')? (stage==='cup_qf'?[0,1,2,3]:stage==='cup_sf'?[4,5]:[6]):(stage==='round1'?[0,1,2,3,4,5,6,7]:stage==='round2'?[8,9,10,11]:stage==='conference'?[12,13]:[14]);
    for(const j of slots) {
      const cup=stage.startsWith('cup_'),stride=cup?21:60,base=w*stride+j*(cup?3:4),a=paths.a[cup?'cup_matches':'series'];
      const h=a[base],v=a[base+1],winner=a[base+2];const low=Math.min(h,v),high=Math.max(h,v),key=low+':'+high;
      if(!rows.has(key))rows.set(key,{a:paths.ids[low],b:paths.ids[high],mass:0,aWins:0,length:[0,0,0,0]});
      const r=rows.get(key);r.mass+=weight;if(winner===low)r.aWins+=weight;
      if(!cup)r.length[a[base+3]-4]+=weight;
    }
  }
  return {support,rows:[...rows.values()].map(r=>({...r,p:support?r.mass/support:null,pA:r.mass?r.aWins/r.mass:null,length:r.length.map(n=>r.mass?n/r.mass:null)})).sort((a,b)=>b.mass-a.mass||a.a.localeCompare(b.a))};
}
