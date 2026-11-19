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

// The opening footage dissolves between two takes around frames 66–76 of 121
// (a double exposure). Scroll crosses that stretch in a sliver of the opening
// so nobody rests on a ghosted frame; the rest of the clip keeps its pace and
// still starts on the film's last frame and ends on the opened kit.
const clipDissolve={start:66/121,end:76/121,span:.02} as const;

export function mapVTechKitClipTime(progress:number){
 const {start,end,span}=clipDissolve,centre=(start+end)/2,from=centre-span/2,to=centre+span/2;
 if(progress<=from)return progress*start/from;
 if(progress>=to)return end+(progress-to)*(1-end)/(1-to);
 return start+(progress-from)*(end-start)/span;
}

export function mapVTechKitProgress(local:number){
 const openingRaw=phase(local,vtechKitTiming.openStart,vtechKitTiming.openEnd);
 return {
  video:phase(local,0,vtechKitTiming.returnEnd),
  // The opening footage continues the film from its last frame and ends on
  // the opened kit together with the layer animation it replaces.
  clip:phase(local,vtechKitTiming.returnEnd,vtechKitTiming.openEnd),
  pack:smooth(phase(local,vtechKitTiming.returnEnd,vtechKitTiming.flightEnd)),
  reveal:phase(local,vtechKitTiming.revealStart,vtechKitTiming.revealEnd),
  opening:smooth(openingRaw),
  openingRaw,
 };
}
