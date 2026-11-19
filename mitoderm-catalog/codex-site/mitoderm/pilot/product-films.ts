// Scroll films for ProductCinema pages, keyed by product slug. Paths go through
// mediaUrl(); a path that resolves to an empty URL keeps the image-only stage on
// that viewport. chapters[i] belongs to shot i of the page (REGISTRY.json order);
// start and end are frame numbers, start===end holds that frame. A slug without
// an entry keeps the image-only stage.
export type ProductFilm={desktop:string;mobile:string;fps:number;frames:number;chapters:Array<{start:number;end:number}>};
export const productFilms:Record<string,ProductFilm>={
 // 1912x1080, 834 frames, a keyframe every 12. The 9:16 film is not cut yet:
 // its URL in media-urls.json is empty, so phones stay image-only until it is set.
 'exo-nad':{desktop:'/assets/world/exo-nad-film.mp4',mobile:'/assets/world/exo-nad-film-mobile.mp4',fps:24,frames:834,chapters:[
  {start:0,end:108},   // 01 kit
  {start:108,end:198}, // 02 consultation
  {start:198,end:306}, // 03 EXO BIPHASIC PEEL
  {start:306,end:427}, // 04 pH NORMALIZER, rinse, dry
  {start:427,end:520}, // 05 LONGEVITY SERUM
  {start:520,end:616}, // 06 close
  {start:616,end:707}, // 07 evidence
  {start:707,end:834}  // 08 complete system
 ]}
};
