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
 ]},
 // 1912x1080 and 1080x1912, 822 frames, a keyframe every 12 (state/films/exotech-gel/assemble.sh).
 'exotech-gel':{desktop:'/assets/world/exotech-gel-film.mp4',mobile:'/assets/world/exotech-gel-film-mobile.mp4',fps:24,frames:822,chapters:[
  {start:0,end:108}, // 01 pack
  {start:108,end:228}, // 02 recommendation in the clinic
  {start:228,end:336}, // 03 the open box
  {start:336,end:420}, // 04 at home: a thin layer
  {start:420,end:492}, // 05 massaged in
  {start:492,end:576}, // 06 every day
  {start:576,end:684}, // 07 the next visit
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
 ],
 // \u00a0 keeps "30 מ״ל" on one line; \u200f and \u200e keep the comma and the ™ on the right side of the Latin names.
 'exotech-gel':[
  {title:'EXOTECH GEL',body:'שומרים על תוצאות הקליניקה גם בבית.',tag:'EXOTECH GEL'},
  {title:'לאחר טיפול בקליניקה',body:'ההמשך הביתי של הטיפול המקצועי.',tag:'לאחר טיפול בקליניקה'},
  {title:'צנצנת כדורית אחת. 30\u00a0מ״ל. יומיומי.',body:'חמישה רכיבים פעילים: אקסוזומים סינתטיים, PDRN, פפטידים ביומימטיים עם זהב ונחושת, חומצה היאלורונית ופוליסכרידים ממקור חלזון.',tag:'רכיבים פעילים'},
  {title:'מריחת שכבה דקה',body:'למרוח שכבה דקה על עור נקי ולעסות עד לספיגה',tag:'אופן השימוש'},
  {title:'קליל. מעניק לחות. אף פעם לא מכביד.',body:'מרקם הג׳ל הקליל מעניק תחושת רעננות ולחות מבלי להכביד על העור.',tag:'יתרונות'},
  {title:'שימוש יומיומי',body:'ג׳ל טיפוח מתקדם לשימוש ביתי, שפותח כדי להמשיך ולתמוך בתהליכים שהחלו בטיפול המקצועי בקליניקה.',tag:'טיפוח ביתי'},
  {title:'ההתחדשות מתחילה בקליניקה.',body:'עור יבש, מיובש, עייף או מזדקן זקוק להמשך התהליך בין הביקורים.',tag:'למי מתאים'},
  {title:'המשך טיפול מקצועי גם בבית',body:'משתלב עם V-TECH,\u200f EXO-NAD וסדרת BIOSPICULE™\u200e.',tag:'הצעה'}
 ]
};
