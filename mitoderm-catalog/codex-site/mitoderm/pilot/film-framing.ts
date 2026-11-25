// Framing is tied to source time, so reverse scrolling follows the same camera move.
// Only SPRAY's application detail is reframed; pack entry/exit and other films stay native.
export function filmFraming(slug:string,frame:number,mobile:boolean){
 const neutral={scale:1,x:35,y:0};
 if(slug!=='exosignal-spray')return neutral;
 const keys=mobile
  ?[[500,1],[548,1.38],[664,1.38],[735,1]]
  :[[500,1],[548,1.48],[664,1.48],[735,1]];
 if(frame<=keys[0][0]||frame>=keys.at(-1)![0])return neutral;
 for(let i=1;i<keys.length;i++){
  const [end,to]=keys[i], [start,from]=keys[i-1];
  if(frame<=end){
   const t=(frame-start)/(end-start), ease=t*t*(3-2*t);
   return {scale:from+(to-from)*ease,x:mobile?20:35,y:0};
  }
 }
 return neutral;
}
