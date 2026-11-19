// The film ends at .33; the closed pack then flies until .47 and opens from
// .47 to .88, so the kit keeps moving until it is fully open. Only the last
// .12 of the scene (plus a short story tail) holds the open kit still.
export const vtechKitTiming={
 returnEnd:.33,
 flightEnd:.47,
 revealStart:.455,
 revealEnd:.50,
 openStart:.47,
 openEnd:.88,
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
