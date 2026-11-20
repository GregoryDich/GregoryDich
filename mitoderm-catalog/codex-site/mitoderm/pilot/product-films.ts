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
 ]},
 // 1912x1080 and 1080x1912, 822 frames, a keyframe every 12 (state/films/exocell-mask/assemble.sh).
 'exocell-mask':{desktop:'/assets/world/exocell-mask-film.mp4',mobile:'/assets/world/exocell-mask-film-mobile.mp4',fps:24,frames:822,chapters:[
  {start:0,end:108},   // 01 pack
  {start:108,end:228}, // 02 consultation
  {start:228,end:348}, // 03 the sachet is open, the mask comes out
  {start:348,end:420}, // 04 the layers
  {start:420,end:504}, // 05 the mask on the face
  {start:504,end:576}, // 06 absorption
  {start:576,end:684}, // 07 finish
  {start:684,end:822}  // 08 pack
 ]}
};
// Chapter captions of the series films, in page order, word for word from the approved page copy
// (state/films/<slug>/storyboard.json, "captions"). A slug without an entry keeps the generic copy.
export const productCaptions:Record<string,Array<{title:string;body:string;tag:string}>>={
 'exocell-mask':[
  {title:'EXOCELL MASK',body:'השלב המסכם והמרגיע לאחר טיפולים מקצועיים.',tag:'EXOCELL MASK'},
  {title:'רוגע לאחר הפרוצדורה',body:'העור זקוק ללחות ולתמיכה במחסום האפידרמלי.',tag:'למה?'},
  {title:'5 מסכות, אריזה אחת',body:'מסכות ביו־צלולוז חד־פעמיות עם סרום פעיל.',tag:'ערכה ועובדות'},
  {title:'מסכה כפולה',body:'שכבה לבנה ושכבה כחולה',tag:'מסכה כפולה'},
  {title:'1 · הנחת המסכה',body:'כמעט ללא כיסי אוויר',tag:'הנחת המסכה'},
  {title:'2 · ספיגה',body:'מגע לח ורציף עם הסרום',tag:'ספיגה'},
  {title:'3 · סיום',body:'בסיום: DERMA RECOVERY CREAM והגנה מהשמש.',tag:'סיום'},
  {title:'הכניסו את EXOCELL MASK לקליניקה שלכם',body:'לשימוש מקצועי בלבד.',tag:'הצעה'}
 ]
};
