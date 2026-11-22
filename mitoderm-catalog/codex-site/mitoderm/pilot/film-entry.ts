import type {EntryRect} from './vtech-entry';

type Box=[left:number,top:number,right:number,bottom:number];
type Turn=[degrees:number,along:number];

/** Where the pack stands in the first frame of each product film, as fractions of the frame: the place the pack
 * chosen on the home page comes down to (ProductEntry). Measured on the frames the pages show
 * (state/tasks/first-frames.cjs, first-frame-boxes.py); the phone box of a film cut from the wide one follows from its
 * phone window (state/films/<slug>/vertical-keys.json). Measure again when a film gets a new first frame.
 * `turn`: the pen leans in the collection and stands upright in the catalogue, but lies on the towel in its film -
 * degrees clockwise from the flying picture to the film, and the pen's length as a part of that picture's height. */
export const filmPack:Record<string,{desktop:Box;mobile:Box;turn?:{banner:Turn;card:Turn}}>={
 'exo-nad':{desktop:[.305,.119,.67,.907],mobile:[.06,.28,.925,.89]},
 'exocell-mask':{desktop:[.186,.033,.565,.989],mobile:[.21,.175,.74,.61]},
 'exotech-gel':{desktop:[.128,.515,.521,.974],mobile:[.152,.388,.894,.634]},
 'exosignal-hair':{desktop:[.08,.43,.58,.9],mobile:[.041,.342,.95,.614]},
 'exosignal-spray':{desktop:[.075,.03,.37,.93],mobile:[.169,.111,.831,.754]},
 'micro-boost-10':{desktop:[.103,.159,.264,.907],mobile:[.049,.189,.332,.606]},
 'cell-renew-1-5':{desktop:[.086,.205,.228,.935],mobile:[.05,.205,.323,.651]},
 'cellular-age-defense-2-5':{desktop:[.086,.193,.23,.967],mobile:[.01,.206,.259,.63]},
 'derma-recovery-cream':{desktop:[.059,.396,.274,.963],mobile:[.016,.317,.386,.627]},
 'mitopen':{desktop:[.161,.682,.515,.782],mobile:[.15,.521,.806,.58],turn:{banner:[47.44,1.299],card:[77.44,1.02]}},
 'mitoscan':{desktop:[.011,.637,.27,.963],mobile:[.017,.411,.415,.571]},
 'mitotech-cell-booster':{desktop:[.036,.62,.29,1],mobile:[.028,.41,.466,.618]},
};

/** The place of the pack on the screen in the film as it is shown now: the film covers its element (object-fit: cover)
 * and keeps the side its object-position names. */
export function filmPackRect(slug:string,film:HTMLVideoElement):EntryRect|null{
 const place=filmPack[slug];
 if(!place||!film.videoWidth||!film.videoHeight)return null;
 const frame=film.getBoundingClientRect();
 if(frame.width<1||frame.height<1)return null;
 const box=film.videoWidth<film.videoHeight?place.mobile:place.desktop;
 const scale=Math.max(frame.width/film.videoWidth,frame.height/film.videoHeight);
 const width=film.videoWidth*scale,height=film.videoHeight*scale;
 const [x,y]=getComputedStyle(film).objectPosition.split(' ').map(value=>value.endsWith('%')?parseFloat(value)/100:.5);
 const left=frame.left+(frame.width-width)*(Number.isFinite(x)?x:.5),top=frame.top+(frame.height-height)*(Number.isFinite(y)?y:.5);
 return {left:left+box[0]*width,top:top+box[1]*height,width:(box[2]-box[0])*width,height:(box[3]-box[1])*height};
}
