// Shared definitions and world-wise arithmetic. Undefined denominators stay NaN.
export const ADVANCED_METRICS = [
 ['fgpct','Field-goal%','FGM / FGA',true,false],
 ['fg3pct','3-point FG%','3PM / 3PA',true,false],
 ['ftpct','Free-throw%','FTM / FTA',true,false],
 ['efg','Effective FG%','(FGM + 0.5 × 3PM) / FGA',true,false],
 ['ts','True shooting%','PTS / (2 × (FGA + 0.44 × FTA))',true,false],
 ['two','2-point FG%','(FGM − 3PM) / (FGA − 3PA)',true,false],
 ['threeShare','3-point attempt rate','3PA / FGA',true,false],
 ['ftRate','Free-throw attempt rate','FTA / FGA',true,false],
 ['astTov','Assists per turnover','AST / TOV',false,false],
 ['poss','Estimated possessions','FGA − OREB + TOV + 0.44 × FTA',false,true],
 ['ortg','Offensive rating · estimate','PTS / estimated possessions × 100',false,true],
 ['drtg','Defensive rating · estimate','Opponent PTS / their estimated possessions × 100',false,true],
 ['net','Net rating · estimate','Offensive rating − defensive rating',false,true],
 ['oreb','Offensive rebound share','OREB / (OREB + opponent DREB)',true,true],
 ['dreb','Defensive rebound share','DREB / (DREB + opponent OREB)',true,true],
 ['assist','Assisted field goals','AST / FGM',true,true],
 ['turnover','Turnover rate · estimate','TOV / estimated possessions',true,true],
 ['steals','Steal rate · estimate','STL / opponent estimated possessions',true,true],
];
export const METRIC_INPUTS = {
  twoMade:['fgm','fg3m'],twoAtt:['fga','fg3a'],twoPct:['twoMade','twoAtt'],
  fgpct:['fgm','fga'],fg3pct:['fg3m','fg3a'],ftpct:['ftm','fta'],efg:['fgm','fg3m','fga'],
  ts:['pts','fga','fta'],threeShare:['fg3a','fga'],ftRate:['fta','fga'],astTov:['ast','tov'],
  poss:['fga','oreb','tov','fta'],ortg:['pts','poss'],drtg:['pts','poss'],net:['ortg','drtg'],
  orebShare:['oreb','dreb'],drebShare:['dreb','oreb'],assist:['ast','fgm'],turnover:['tov','poss'],steals:['stl','poss'],
  fantasy:['pts','reb','ast','stl','blk','tov'],
};
const combine=(arrays,fn)=>arrays.every(Boolean)?Float64Array.from(arrays[0],(_,i)=>fn(...arrays.map(a=>a[i]))):null;
const ratio=(a,b,scale=100)=>combine([a,b],(x,y)=>Number.isFinite(x)&&Number.isFinite(y)&&y>0?scale*x/y:NaN);
export function derivedMetric(key,get,opponent=null) {
  const c=get,o=opponent;
  if(key==='twoMade')return combine([c('fgm'),c('fg3m')],(a,b)=>a-b);
  if(key==='twoAtt')return combine([c('fga'),c('fg3a')],(a,b)=>a-b);
  const fraction={fgpct:['fgm','fga'],twoPct:['twoMade','twoAtt'],fg3pct:['fg3m','fg3a'],ftpct:['ftm','fta'],threeShare:['fg3a','fga'],ftRate:['fta','fga'],astTov:['ast','tov'],ortg:['pts','poss'],assist:['ast','fgm'],turnover:['tov','poss']}[key];
  if(fraction)return ratio(c(fraction[0]),c(fraction[1]),key==='astTov'?1:100);
  if(key==='efg')return ratio(combine([c('fgm'),c('fg3m')],(a,b)=>a+.5*b),c('fga'));
  if(key==='ts')return ratio(c('pts'),combine([c('fga'),c('fta')],(a,b)=>2*(a+.44*b)));
  if(key==='fantasy')return combine([c('pts'),c('reb'),c('ast'),c('stl'),c('blk'),c('tov')],(p,r,a,s,b,t)=>(10*p+12*r+15*a+30*s+30*b-10*t)/10);
  if(key==='poss')return combine([c('fga'),c('oreb'),c('tov'),c('fta')],(f,r,t,ft)=>f-r+t+.44*ft);
  if(o&&key==='drtg')return ratio(o('pts'),o('poss'));
  if(o&&key==='net')return combine([c('ortg'),c('drtg')],(a,b)=>a-b);
  if(o&&['orebShare','drebShare'].includes(key)) {
    const a=c(key==='orebShare'?'oreb':'dreb'),b=o(key==='orebShare'?'dreb':'oreb');
    return ratio(a,combine([a,b],(x,y)=>x+y));
  }
  if(o&&key==='steals')return ratio(c('stl'),o('poss'));
  return undefined;
}
export const scenarioMetricKey=(key,kind)=>key==='two'?'twoPct':kind==='team'&&['oreb','dreb'].includes(key)?key+'Share':key;
