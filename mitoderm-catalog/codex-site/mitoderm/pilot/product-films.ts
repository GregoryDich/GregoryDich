// Scroll films for ProductCinema pages, keyed by product slug. Paths go through
// mediaUrl(). chapters[i] belongs to shot i of the page (REGISTRY.json order);
// start and end are frame numbers, start===end holds that frame. A slug without
// an entry keeps the image-only stage.
export type ProductFilm={desktop:string;mobile:string;fps:number;frames:number;chapters:Array<{start:number;end:number}>};
export const productFilms:Record<string,ProductFilm>={};
