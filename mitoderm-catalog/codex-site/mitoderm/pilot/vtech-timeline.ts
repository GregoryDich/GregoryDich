// Measured from the two confirmed 873-frame / 24 fps v5 masters. Boundaries
// include each bridge, so changing HTML chapters never skips a video frame.
export type VTechTimeline={duration:number;chapters:Array<{id:string;start:number;end:number}>;packStart:number;packEnd:number};
const measured:VTechTimeline={duration:873/24,chapters:[
 {id:'vtech-hero',start:0,end:121/24},
 {id:'vtech-consultation',start:121/24,end:230/24},
 {id:'vtech-pen',start:230/24,end:388/24},
 {id:'vtech-serum',start:388/24,end:546/24},
 {id:'vtech-mask',start:546/24,end:649/24},
 {id:'vtech-results',start:649/24,end:752/24},
 {id:'vtech-kit',start:752/24,end:873/24},
],packStart:752/24,packEnd:873/24};
export const vtechTimeline:{desktop:VTechTimeline;mobile:VTechTimeline}={desktop:measured,mobile:measured};
