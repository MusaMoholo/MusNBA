// Validated exact world/player pooled-zone counts; no inference, synthetic locations or missing-value fills.
export const ZONE_KEYS=['rim','paint','mid','corner3','above3'];
export const ZONE_LABELS=['Rim','Paint outside rim','Midrange','Corner three','Above-break three'];
export const ZONE_VARS=ZONE_KEYS.flatMap((key,i)=>[
 [`zone_${key}_fga`,`${ZONE_LABELS[i]} attempts`],
 [`zone_${key}_fgm`,`${ZONE_LABELS[i]} makes`],
 [`zone_${key}_fgpct`,`${ZONE_LABELS[i]} FG%`],
 [`zone_${key}_share`,`${ZONE_LABELS[i]} attempt share%`],
]);
export function parseZoneVariable(key) {
 const found=/^zone_(rim|paint|mid|corner3|above3)_(fga|fgm|fgpct|share)$/.exec(key);
 return found?{zone:ZONE_KEYS.indexOf(found[1]),stat:found[2]}:null;
}
function bytes(s) {
 if(typeof s!=='string')throw new Error('Missing zone bytes');
 return Uint8Array.from(atob(s),c=>c.charCodeAt(0));
}
export function decodeZones(raw,worlds,players,{boxColumn=null}={}) {
 const fields=['zone_schema','zone_attempts_u16_le','zone_makes_u16_le','zone_keys'];
 if(!fields.some(k=>k in raw))return null;
 if(raw.zone_schema!==1||JSON.stringify(raw.zone_keys)!==JSON.stringify(ZONE_KEYS)||!Number.isSafeInteger(worlds)||worlds<1||!Number.isSafeInteger(players)||players<1)throw new Error('Unsupported zone metadata');
 const a=bytes(raw.zone_attempts_u16_le),m=bytes(raw.zone_makes_u16_le),length=worlds*players*5*2;
 if(a.length!==length||m.length!==length)throw new Error('Zone dimensions differ from saved worlds');
 const attempts=new DataView(a.buffer,a.byteOffset,a.byteLength),makes=new DataView(m.buffer,m.byteOffset,m.byteLength);
 for(let w=0;w<worlds;w++)for(let p=0;p<players;p++) {
  let fga=0,fgm=0,fg3a=0,fg3m=0;
  for(let z=0;z<5;z++) {
   const off=((w*players+p)*5+z)*2,x=attempts.getUint16(off,true),y=makes.getUint16(off,true);
   if(y>x)throw new Error('Zone makes exceed attempts');
   fga+=x;fgm+=y;if(z>=3){fg3a+=x;fg3m+=y;}
  }
  if(boxColumn)for(const [key,value] of Object.entries({fga,fgm,fg3a,fg3m})) {
   const expected=boxColumn(w,p,key);
   if(expected==null||expected!==value)throw new Error('Zone counts do not match the exact player box');
  }
 }
 return {worlds,players,column(player,zone,kind) {
  if(!Number.isInteger(player)||player<0||player>=players||!Number.isInteger(zone)||zone<0||zone>=5||!['fga','fgm'].includes(kind))throw new Error('Unknown zone column');
  const view=kind==='fga'?attempts:makes,out=new Float64Array(worlds);
  for(let w=0;w<worlds;w++)out[w]=view.getUint16(((w*players+player)*5+zone)*2,true);
  return out;
 }};
}
export function zoneValues(spec,getZone,totalAttempts) {
 if(!spec)return null;
 const numerator=getZone(spec.zone,spec.stat==='fgm'||spec.stat==='fgpct'?'fgm':'fga');
 if(!numerator)return null;
 if(['fga','fgm'].includes(spec.stat))return numerator;
 const denominator=spec.stat==='fgpct'?getZone(spec.zone,'fga'):totalAttempts;
 return denominator?numerator.map((x,i)=>denominator[i]>0?100*x/denominator[i]:NaN):null;
}
