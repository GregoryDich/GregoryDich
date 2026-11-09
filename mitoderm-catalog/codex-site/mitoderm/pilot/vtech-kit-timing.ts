// The closed pack starts moving at .33 and the kit is open at .565. This
// halves the previous .33–.80 handoff without shortening the final open hold.
export const vtechKitTiming={
 returnEnd:.33,
 flightEnd:.415,
 revealStart:.405,
 revealEnd:.44,
 openStart:.415,
 openEnd:.565,
} as const;

const phase=(value:number,start:number,end:number)=>Math.min(1,Math.max(0,(value-start)/(end-start)));
const smooth=(value:number)=>value*value*(3-2*value);

export function mapVTechKitProgress(local:number){
 const openingRaw=phase(local,vtechKitTiming.openStart,vtechKitTiming.openEnd);
 return {
  video:phase(local,0,vtechKitTiming.returnEnd),
  pack:smooth(phase(local,vtechKitTiming.returnEnd,vtechKitTiming.flightEnd)),
  reveal:phase(local,vtechKitTiming.revealStart,vtechKitTiming.revealEnd),
  opening:smooth(openingRaw),
  openingRaw,
 };
}
