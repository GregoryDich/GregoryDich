import {mediaUrl} from '../media';

export type EntryRect={left:number;top:number;width:number;height:number};

// Measured from the deployed clip's exact first frames. Both the page and the
// cross-route handoff use this geometry, so the product meets the table frame.
export const entryMedia={
 poster:mediaUrl('/assets/world/vtech-intro-poster.webp'),
 clip:mediaUrl('/assets/world/vtech-intro.mp4'),
 width:1912,height:1080,
 box:{left:727,top:31,width:466,height:1014},
 silhouette:'polygon(0% 1.6%, 90% 0%, 95% 0%, 100% 1.7%, 100% 98%, 91% 100%, 1% 99.6%, 0% 97%)',
} as const;

export const mobileMedia={
 poster:mediaUrl('/assets/world/vtech-intro-mobile-poster.webp'),
 clip:mediaUrl('/assets/world/vtech-intro-mobile.mp4'),
 width:406,height:720,
 box:{left:104,top:197,width:193,height:435},
 silhouette:'polygon(0% 2%, 91% 0%, 95% 0%, 100% 2%, 100% 97%, 94% 100%, 2% 99%, 0% 97%)',
} as const;

export function getEntryMedia(width:number){return width<=860?mobileMedia:entryMedia;}

/** The height the film takes on a stage of this size. A wide window narrower than 16:10 (a tablet held sideways)
 * keeps the whole film width at the top of the stage instead of enlarging it to the stage height - the same media
 * query as in vtech-story.css; everywhere else the film covers the stage. */
export function getFilmHeight(width:number,height:number){
 if(typeof window==='undefined'||!window.matchMedia('(min-width:861px) and (max-aspect-ratio:159/100)').matches)return height;
 return Math.min(height,width*9/16);
}

export function getEntryBoxRect(width:number,height:number):EntryRect{
 const media=getEntryMedia(typeof window==='undefined'?width:window.innerWidth);
 const film=getFilmHeight(width,height);
 const scale=Math.max(width/media.width,film/media.height);
 return {
  left:(width-media.width*scale)/2+media.box.left*scale,
  top:(film-media.height*scale)/2+media.box.top*scale,
  width:media.box.width*scale,
  height:media.box.height*scale,
 };
}
