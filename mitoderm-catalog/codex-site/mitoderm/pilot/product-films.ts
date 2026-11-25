// Scroll films for ProductCinema pages, keyed by product slug. Paths go through
// mediaUrl(); a path that resolves to an empty URL keeps the image-only stage on
// that viewport. chapters[i] belongs to shot i of the page (REGISTRY.json order);
// start and end are frame numbers, start===end holds that frame. A slug without
// an entry keeps the image-only stage.
// anchor:'left' keeps the left edge of the desktop film when the window is narrower than 16:9: for a film whose pack
// stands at the very left and whose right third is empty background.
// quiet:[from,to] (parts of a chapter, 0..1) names the stretch where the camera brings a face under the caption: on a
// wide screen the caption fades for that stretch (ProductCinema, data-caption-quiet); on a phone it stays.
export type ProductFilm={desktop:string;mobile:string;fps:number;frames:number;anchor?:'left';scrollVh?:number[];chapters:Array<{start:number;end:number;quiet?:[from:number,to:number]}>};
export const productFilms:Record<string,ProductFilm>={
 // Desktop and portrait films: 834 frames, a keyframe every 12. The page skips the
 // rejected wiping segment in both versions; the original media itself is unchanged.
 'exo-nad':{desktop:'/assets/world/exo-nad-film.mp4',mobile:'/assets/world/exo-nad-film-mobile.mp4',fps:24,frames:834,scrollVh:[1.15,.8,1.4,.7,1.3,.6,.55,1.2],chapters:[
  {start:0,end:108},   // 01 kit
  {start:108,end:198}, // 02 consultation
  {start:198,end:306}, // 03 EXO BIPHASIC PEEL
  {start:306,end:338}, // 04 neutralizer only; excluded cloth/wiping tail (owner correction, 25 Nov)
  {start:427,end:520}, // 05 LONGEVITY SERUM
  {start:520,end:616}, // 06 close
  {start:616,end:707}, // 07 evidence
  {start:707,end:834}  // 08 complete system
 ]},
 // 1912x1080 and 1080x1912, 984 frames, a keyframe every 12 (state/films/exocell-mask/assemble.sh). Version 3 (22/11):
 // two live clips added as the owner asked on 21/11 - the layers come apart and the paper part leaves (04), the white
 // mask is laid on the face (05, running into the smoothing); version 2 held a still in 04 and cut straight to 05.
 'exocell-mask':{desktop:'/assets/world/exocell-mask-film.mp4',mobile:'/assets/world/exocell-mask-film-mobile.mp4',fps:24,frames:984,chapters:[
  {start:0,end:108},   // 01 pack
  {start:108,end:228}, // 02 consultation
  {start:228,end:348}, // 03 the sachet is open, the mask comes out
  {start:348,end:468}, // 04 the layers come apart, the white mask stays
  {start:468,end:666}, // 05 the white mask is laid on the face and smoothed
  {start:666,end:738}, // 06 absorption
  {start:738,end:846}, // 07 finish
  {start:846,end:984}  // 08 pack
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
 ]},
 // A connected film: one unbroken visit, no hard cuts. 1912x1080 and 1080x1920, 1667 frames, a keyframe every 12
 // (state/films/exosignal-hair/film-assemble.sh with film-16x9.spec). The phone film is a moving window cut out of
 // the desktop one (vertical-from-horizontal.py with vertical-keys.json). A chapter starts inside a clip, where the
 // next scene is already recognisable, not at the joint of two clips. Chapters 04, 07, 09 and 10 were added on
 // 20/11 at the owner's word: the scan on the tablet, the serum inside the skin, the weeks of the course and the
 // follow-up scan; their captions are quoted from mitoderm.com (the old site) and the treatment protocol.
 'exosignal-hair':{desktop:'/assets/world/exosignal-hair-film.mp4',mobile:'/assets/world/exosignal-hair-film-mobile.mp4',fps:24,frames:1638,chapters:[
  {start:0,end:91},      // 01 pack
  {start:91,end:219},    // 02 consultation
  {start:219,end:300},   // 03 MITOSCAN on the parting
  {start:300,end:500},   // 04 the MITOSCAN screen, she points at it
  {start:500,end:667},   // 05 the ampoule
  {start:667,end:812},   // 06 MITOPEN and the syringe along the parting
  {start:812,end:1036},  // 07 inside the skin: micro-channels
  {start:1036,end:1115}, // 08 massage
  {start:1115,end:1205}, // 09 the weeks of the course
  {start:1205,end:1360}, // 10 the follow-up scan
  {start:1360,end:1521}, // 11 the end of the visit
  {start:1521,end:1638}  // 12 pack
 ]},
 // A connected film: clinic, home and clinic again in one movement. 1912x1080 and 1080x1920, 1208 frames, a keyframe
 // every 12 (state/films/exosignal-spray/film-16x9.spec). Twice the product stays in the frame while the place behind
 // it changes (clinic to home, home to clinic): the spray is what links the two. The phone film is a moving window
 // cut out of the desktop one (vertical-keys.json).
 'exosignal-spray':{desktop:'/assets/world/exosignal-spray-film.mp4',mobile:'/assets/world/exosignal-spray-film-mobile.mp4',fps:24,frames:1208,scrollVh:[1.15,1.2,1.05,1.5,2.4,1.1,1,1],chapters:[
  {start:0,end:105},     // 01 pack in the clinic
  {start:105,end:262},   // 02 consultation
  {start:262,end:370},   // 03 the bottle in his hand
  {start:370,end:548},   // 04 at home in the evening
  {start:548,end:800},   // 05 part, spray, massage
  {start:800,end:938},   // 06 the pack on the bathroom counter
  {start:938,end:1100},  // 07 the follow-up visit
  {start:1100,end:1208}  // 08 pack
 ]},
 // A connected film of a home-care serum: her morning at the mirror, into the skin and out, the cream, then the same
 // box in the clinic. 1912x1080 and 1080x1920, 849 frames, a keyframe every 12 (state/films/cell-renew-1-5/
 // film-16x9.spec). The box is the real pack render placed into the frames, so the two focus pulls and the change of
 // place are dissolves between frames with an identical box. Chapter 03 (the massage) stands before chapter 04
 // (what is inside) because the camera enters the skin from the massage.
 'cell-renew-1-5':{desktop:'/assets/world/cell-renew-1-5-film.mp4',mobile:'/assets/world/cell-renew-1-5-film-mobile.mp4',fps:24,frames:849,chapters:[
  {start:0,end:75},    // 01 the pack at home
  {start:75,end:190},  // 02 at the mirror
  {start:190,end:290}, // 03 the massage
  {start:290,end:455}, // 04 inside the skin
  {start:455,end:575}, // 05 the cream
  {start:575,end:655}, // 06 the pack at home
  {start:655,end:725}, // 07 the same pack in the clinic
  {start:725,end:849}  // 08 the cosmetologist explains the home care
 ]},
 // A connected film of a home-care serum: the cosmetologist looks at her skin in the clinic, the same box in the evening
 // at her home, the mirror, the massage, into the skin and out, the cream, the box again, back in the clinic.
 // 1912x1080 and 1080x1920, 940 frames, a keyframe every 12 (state/films/cellular-age-defense-2-5/film-16x9.spec).
 // The box is the real pack render placed into the frames, so the focus pulls and both changes of place are
 // dissolves between frames with an identical box. Chapter 03 (the massage) stands before chapter 04 (what is
 // inside) because the camera enters the skin from the massage.
 'cellular-age-defense-2-5':{desktop:'/assets/world/cellular-age-defense-2-5-film.mp4',mobile:'/assets/world/cellular-age-defense-2-5-film-mobile.mp4',fps:24,frames:940,chapters:[
  {start:0,end:80},    // 01 the pack in the clinic
  {start:80,end:190},  // 02 the skin examination
  {start:190,end:462}, // 03 at home: the mirror, the massage
  {start:462,end:596}, // 04 inside the skin
  {start:596,end:690}, // 05 the cream
  {start:690,end:760}, // 06 the pack at home
  {start:760,end:826}, // 07 the same pack in the clinic
  {start:826,end:940}  // 08 the cosmetologist and the patient
 ]},
 // A connected film: the cream as the last step in the clinic, the same box in the morning at her home, she applies the
 // cream herself, into the skin and out, the box, the clinic again. Three Kling 4.0 clips shot in native 1080p on
 // Atlas Cloud (T3, D1, D2 - state/films/derma-recovery-cream/requests.json); the focus pulls and both changes of place
 // are dissolves between frames with the real box unmoving, the way back to the box is a soft-focus join
 // (film-16x9.spec). 1912x1080 and 1080x1920, 940 frames. Replaces the draft built of stills (wire-draft.json).
 'derma-recovery-cream':{desktop:'/assets/world/derma-recovery-cream-film.mp4',mobile:'/assets/world/derma-recovery-cream-film-mobile.mp4',fps:24,frames:940,chapters:[
  {start:0,end:80},    // 01 the pack in the clinic
  {start:80,end:190},  // 02 the cream after the treatment
  {start:190,end:462}, // 03 at home in the morning: she applies the cream
  {start:462,end:596}, // 04 inside the skin
  {start:596,end:690}, // 05 after: the skin is comfortable
  {start:690,end:760}, // 06 the pack at home
  {start:760,end:826}, // 07 the same pack in the clinic
  {start:826,end:940}  // 08 the cosmetologist and the patient
 ]},
 // A connected film of a device page made of the page's own scenes (22/11). The system in the frame is the customer's
 // real photo (protocols/print/img/mitoscan.webp) placed on a plate generated without any device; the camera move to
 // the system and back is rendered frame by frame from the full-size photo (state/films/mitoscan/build-system-frames.py,
 // film-16x9.spec). The look with the naked eye (C1), the handset on the parting (C2) and the look at the screen (C3)
 // are three Kling 4.0 clips shot in native 1080p on Atlas Cloud after the owner's ok on the still sheet
 // (state/films/mitoscan/requests.json). The picture on the display is a stand-in until real screen captures arrive.
 // 1912x1080 and 1080x1920, 830 frames. The earlier draft (wire-draft.json) was built of the diagnosis clips of the
 // EXOSIGNAL HAIR film, where the system was drawn by a model.
 'mitoscan':{desktop:'/assets/world/mitoscan-film.mp4',mobile:'/assets/world/mitoscan-film-mobile.mp4',fps:24,frames:830,anchor:'left',chapters:[
  {start:0,end:124},   // 01 the system on the table
  {start:124,end:237}, // 02 the look with the naked eye
  {start:237,end:350}, // 03 the handset on the parting
  {start:350,end:457}, // 04 the patient sees the screen
  {start:457,end:566}, // 05 the system close: the scan on its display
  {start:566,end:644}, // 06 the system: one screen
  {start:644,end:714}, // 07 the system, the consultation behind it
  {start:714,end:830}  // 08 the cosmetologist and the patient
 ]},
 // A connected film of a device page, version 3 (22/11): the page's own scenes with its own patient. The pen on the
 // towel is the customer's cut-out photo placed on a plate generated without any device; the camera moves on it are
 // rendered frame by frame (state/films/mitopen/build-pen-frames.py, film-16x9.spec). The live examination (E), the
 // pen at work on the cheek with the way into the skin (D) and the product in the micro-channels (BL) are three
 // Kling 4.0 clips shot in native 1080p on Atlas Cloud after the owner's ok on the still sheet
 // (state/films/mitopen/requests.json, own_scenes_22_11). 1912x1080 and 1080x1920, 952 frames. Version 2 (wire-v2.json)
 // borrowed three clips of the EXOSIGNAL HAIR film.
 'mitopen':{desktop:'/assets/world/mitopen-film.mp4',mobile:'/assets/world/mitopen-film-mobile.mp4',fps:24,frames:952,chapters:[
  {start:0,end:134},                  // 01 the pen close, the camera pulls back
  {start:134,end:289},                // 02 the examination
  {start:289,end:409},                // 03 the ring and the button
  {start:409,end:505,quiet:[0.62,1]}, // 04 microneedling: the pen works on the cheek
  {start:505,end:672,quiet:[0,0.16]}, // 05 into the skin: micro-channels
  {start:672,end:736},                // 06 the pen
  {start:736,end:838},                // 07 the pen, the consultation behind it
  {start:838,end:952}                 // 08 the cosmetologist and the patient
 ]},
 // A connected film of one visit to the clinic, version 2 (22/11): the pack, the skin examination, dry skin, the serum
 // laid on the cheek from the real syringe (a close-up; the owner's photos of 22/11), the massage, the question about
 // tingling, into the skin (spicules of two lengths, the next product going down along them), the mask, the pack again.
 // 1912x1080 and 1080x1920, 1081 frames, a keyframe every 12 (state/films/micro-boost-10/film-16x9.spec).
 // The chapters follow the treatment, not the order of the page sections. Version 1 (no syringe): wire-v1.json.
 'micro-boost-10':{desktop:'/assets/world/micro-boost-10-film.mp4',mobile:'/assets/world/micro-boost-10-film-mobile.mp4',fps:24,frames:1081,chapters:[
  {start:0,end:82},      // 01 the pack in the clinic
  {start:82,end:166},    // 02 the skin examination
  {start:166,end:427},   // 03 dry skin, the syringe, the massage
  {start:427,end:586},   // 04 does it tingle?
  {start:586,end:832},   // 05 inside the skin
  {start:832,end:941},   // 06 the mask on the face
  {start:941,end:1011},  // 07 the pack, the people behind it
  {start:1011,end:1081}  // 08 the pack held
 ]},
 // A film for a coming-soon page, version 3 (22/11) - a clinic procedure with microneedling, and the kit opens as on the
 // owner's example of 22/11: the real box in the clinic, a focus pull to the two women, the kit opening on the table (an
 // exact 3D model built from his print files: the lid goes back on a ribbon, the guide inside the lid, four powder vials
 // and four ampoules that look as on his card), clear drops of the solution and the pen at work on the cheek, the solution
 // going down the micro-channels, back to the box. Live clips T1, W, BL (Kling 4.0, 1080p); the opening O is rendered, not
 // generated; in the film the kit stands lower and at 0.89 of its rendered size, so the open lid clears the site header
 // (extra field at the top and right from one still of the same shot). The scenes meet in soft focus. 1912x1080 and
 // 1080x1920, 654 frames, one chapter: the page copy has an intro only (state/films/mitotech-cell-booster/). Version 2
 // (no opening): wire-v2.json; version 1: wire-v1.json. 23/11: the box in the first and last scene carries the owner's
 // current print R15 (his word of 23/11), changed in the frames of clip T1 without a re-shoot (pack-print-in-clip.py);
 // the film before that: desktop 924b099b-3196-4f40-8452-fac1dfa452dc.mp4, phone 14eae525-abc5-49fa-ac6f-4997dd39ee47.mp4.
 'mitotech-cell-booster':{desktop:'/assets/world/mitotech-cell-booster-film.mp4',mobile:'/assets/world/mitotech-cell-booster-film-mobile.mp4',fps:24,frames:654,anchor:'left',chapters:[
  {start:0,end:654}  // 01 the box in the clinic, the kit opens, the drops and the pen, the solution in the micro-channels, the box
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
 ],
 // \u00a0 keeps a product name and "PDRN 2%" on one line; \u2060 keeps the line from breaking after the hyphen of "ו-".
 'exosignal-hair':[
  {title:'EXOSIGNAL HAIR',body:'האות שזקיקי השיער מחכים לו',tag:'אקסוזומים סינתטיים · טיפולי קרקפת'},
  {title:'לנשירת שיער יש נקודת פתיחה',body:'המטופלים שלכם רואים את זה במראה. תנו להם תוכנית שמתחילה במדידה.',tag:'למה?'},
  {title:'אבחון · MITOSCAN',body:'ניתן להשתמש במצלמת MITOSCAN לסקירת הקרקפת, מצב הזקיקים, דלילות ודלקות',tag:'אבחון'},
  {title:'מתעדים את נקודת המוצא.',body:'בוחנים את מראה הקרקפת והשיער ומתעדים את האזורים שנבחרו למעקב.',tag:'תיעוד מקצועי'},
  {title:'אמפולה אחת, שמונה פפטידים',body:'מבנים אקסוזומליים סינתטיים נושאים PDRN\u00a02%, חומצה היאלורונית, שמונה פפטידים ביומימטיים, תאי גזע מתפוח וויטמיני\u00a0B.',tag:'מה בפנים'},
  {title:'מודדים, פותחים, מחדירים',body:'MITOPEN פותח את מסלול החדירה ו-\u2060EXOSIGNAL\u00a0HAIR מיושם על הקרקפת המטופלת',tag:'פרוטוקול'},
  {title:'מהפעולה להמחשה.',body:'הדמיה סכמטית של אזור העבודה ושל יישום הסרום על הקרקפת.',tag:'המחשה חזותית'},
  {title:'ספיגת הסרום',body:'לאחר העבודה יש לעסות עם הכפפות את הקרקפת בעדינות עד לספיגה מלאה של החומר.',tag:'ספיגת הסרום'},
  {title:'תדירות וסדרת טיפולים',body:'טיפול אחד בכל 14 יום. מומלץ לבצע לפחות 4 טיפולים רצופים.',tag:'סדרת טיפולים'},
  {title:'חוזרים לאותו אזור.',body:'מתעדים את הקרקפת באזורים שנבחרו למעקב. הסרט מדגים ביקור; תיעוד המקרים מופיע בהמשך העמוד.',tag:'מעקב מקצועי'},
  {title:'מומחי Mitoderm מוסמכים',body:'Exosignal\u00a0Hair הוא טיפול אמפולות מדויק המיושם במפגשים במרפאה.',tag:'ערכה ועובדות'},
  {title:'הכניסו את EXOSIGNAL\u00a0HAIR לקליניקה שלכם',body:'לשימוש מקצועי בלבד, מיועד לשילוב עם MITOPEN ו-\u2060MITOSCAN.',tag:'הצעה'}
 ],
 'exosignal-spray':[
  {title:'EXOSIGNAL SPRAY',body:'תמיכה בקרקפת בין הביקורים.',tag:'טיפוח ביתי'},
  {title:'הימים שבין הטיפולים חשובים.',body:'EXOSIGNAL\u00a0HAIR הוא הטיפול בקליניקה. דלילות שיער, שיער שביר וחוסר איזון בקרקפת דורשים תמיכה בימים שבין הטיפולים.',tag:'למי מומלץ'},
  {title:'מהקליניקה לשגרה בבית.',body:'אותו מוצר ממשיך עם המטופל אל הטיפוח הביתי של הקרקפת.',tag:'המשך בבית'},
  {title:'מכוונים לקרקפת.',body:'מחלקים את השיער כדי לחשוף את אזור המריחה.',tag:'הכנה לשימוש'},
  {title:'התזה. עיסוי עדין.',body:'מתיזים ישירות על הקרקפת ומעסים בעדינות, בהתאם להוראות השימוש.',tag:'אופן השימוש'},
  {title:'EXOSIGNAL SPRAY · 15 מ״ל',body:'התרסיס הביתי מסדרת EXOSIGNAL. להנחיות שימוש והתאמה פנו לקליניקה המטפלת.',tag:'המוצר הביתי'},
  {title:'שגרה שמתאימה לכם.',body:'מבררים עם הקליניקה איך ממשיכים בשימוש ומתי חוזרים למעקב.',tag:'ליווי מקצועי'},
  {title:'תמיכה רציפה בזקיקים בין הביקורים',body:'זמין דרך הקליניקות השותפות של מיטודרם. התייעצו עם המומחה שלכם כיצד EXOSIGNAL\u00a0SPRAY משתלב בתוכנית הטיפול שלכם.',tag:'הצעה'}
 ],
 'cell-renew-1-5':[
  {title:'CELL RENEW 1.5%',body:'חידוש, בכל יום.',tag:'סרום BIOSPICULE™ · טיפוח ביתי'},
  {title:'רואים את זה קודם במראה.',body:'עור עמום ועייף למראה, נקבוביות פעורות, גוון בלתי אחיד, כתמים פוסט דלקתיים – מה שהמטופלים מבחינים בו בבית, בין הביקורים.',tag:'למה?'},
  {title:'זה אינו פילינג ביתי רגיל.',body:'תחושת עקצוץ עדינה ואופיינית בזמן העיסוי – הספיקולות בפעולה. ללא לחץ רב וללא שפשוף. עור במראה רענן וזוהר.',tag:'הרגישו'},
  {title:'הספיקולות פותחות. הרכיבים הפעילים בעקבותיהן.',body:'ה-Hydrolyzed\u00a0Sponge בריכוז 1.5% מכין את שכבת העור החיצונית לקבלת הפורמולה: Niacinamide, Galactomyces\u00a0ferment, Sodium\u00a0DNA, חומצה סליצילית + חומצה ציטרית.',tag:'מה בפנים'},
  {title:'מריחה. שיקום. הגנה.',body:'על עור נקי ויבש, עסו בעדינות עד לספיגה; לאחר מכן DERMA\u00a0RECOVERY\u00a0CREAM; בשעות היום – מסנן קרינה. כשהעור מסתגל, עברו ל-2.5%.',tag:'פרוטוקול'},
  {title:'30\u00a0מ״ל. בכל יום.',body:'CELL\u00a0RENEW\u00a01.5% – 30\u00a0ml ℮ 1.0\u00a0fl.\u00a0oz. Advanced\u00a0Biospicule\u00a0Technology. מתאים לכל סוגי העור.',tag:'ערכה ועובדות'},
  {title:'התחילו את שגרת הטיפוח בבית.',body:'זמין דרך הקליניקות השותפות של מיטודרם. עברו ל-CELLULAR\u00a0AGE\u00a0DEFENSE\u00a02.5% ככל שהעור מסתגל; לאחריו יש למרוח תמיד DERMA\u00a0RECOVERY\u00a0CREAM.',tag:'הצעה'},
  {title:'מומחי Mitoderm מוסמכים',body:'כל מומחה כאן מוכשר ומוסמך להעניק פרוטוקולים מקוריים של Mitoderm. מצאו מרפאה מהימנה בקרבתכם וקבעו ייעוץ.',tag:'מצאו מומחה'}
 ],
 'cellular-age-defense-2-5':[
  {title:'CELLULAR AGE DEFENSE 2.5%',body:'עוברים ל-2.5%.',tag:'סרום BIOSPICULE™ · טיפוח ביתי'},
  {title:'כשהקמטים מתחילים להטריד.',body:'קמטים וקמטוטים, אובדן אלסטיות, עור עייף ועמום – לעור הזקוק לתוכנית טיפוח אינטנסיבית יותר מ-1.5%.',tag:'למי מתאים הסרום?'},
  {title:'תרגישו את זה. אל תשפשפו.',body:'עשויה להופיע תחושת עקצוץ מורגשת במגע – עסו בעדינות, לעולם לא בחוזקה. לאחר מכן מרחו DERMA\u00a0RECOVERY\u00a0CREAM לשמירה על נוחות העור.',tag:'יתרונות'},
  {title:'יותר ספיקולות. חמישה פפטידים. Bakuchiol.',body:'ה-Hydrolyzed\u00a0Sponge בריכוז 2.5% מעדן את המרקם ומצמצם את הנקבוביות; Bakuchiol ו-Adenosine פועלים על הקמטוטים; חמישה פפטידים תומכים במוצקות ובאלסטיות.',tag:'רכיבים פעילים'},
  {title:'מריחה. שיקום. הגנה.',body:'על עור נקי ויבש, עסו בעדינות; לאחר מכן DERMA\u00a0RECOVERY\u00a0CREAM; בשעות היום – מסנן קרינה. העור עדיין לא מורגל בספיקולות? התחילו ב-CELL\u00a0RENEW\u00a01.5%.',tag:'אופן השימוש'},
  {title:'30\u00a0מ״ל. התוכנית האינטנסיבית.',body:'CELLULAR\u00a0AGE\u00a0DEFENSE\u00a02.5% – 30\u00a0ml ℮ 1.0\u00a0fl.\u00a0oz. Advanced\u00a0Biospicule\u00a0Technology. מתאים לכל סוגי העור.',tag:'נפח'},
  {title:'משדרגים את השגרה.',body:'זמין דרך הקליניקות השותפות של מיטודרם. לאחריו יש למרוח תמיד DERMA\u00a0RECOVERY\u00a0CREAM. לקליניקות: פנו אלינו בנוגע לתמחור ולשלבי הטיפוח הביתי.',tag:'הצעה'},
  {title:'מומחי Mitoderm מוסמכים',body:'כל מומחה כאן מוכשר ומוסמך להעניק פרוטוקולים מקוריים של Mitoderm. מצאו מרפאה מהימנה בקרבתכם וקבעו ייעוץ.',tag:'מצאו מומחה'}
 ],
 'derma-recovery-cream':[
  {title:'DERMA RECOVERY CREAM',body:'כל פרוטוקול מסתיים כאן.',tag:'סדרת BIOSPICULE™ · SNAIL COLLAGEN'},
  {title:'לחידוש יש גם אחרי.',body:'לאחר שימוש בספיקולות או פרוצדורה בקליניקה, העור עשוי להרגיש יבש, מתוח או מתקלף. זה הרגע שבו שגרת הטיפוח זקוקה לשלב המשלים.',tag:'למה?'},
  {title:'אחרי הסרומים. אחרי הקליניקה. מדי יום.',body:'לאחר CELL\u00a0RENEW\u00a01.5% או CELLULAR\u00a0AGE\u00a0DEFENSE\u00a02.5%; לאחר פרוטוקולי V-TECH, EXO-NAD ו-MICRO\u00a0BOOST\u00a010%; בוקר וערב, על עור נקי.',tag:'מתי למרוח'},
  {title:'ללא ספיקולות. שבעה רכיבים פעילים מרכזיים.',body:'ללא ספיקולות כלל – פנתנול, Madecassoside, אלנטואין, חמאת שיאה, ניאצינאמיד, קולגן מפורק ופוליסכרידים מטוהרים מריר החילזון.',tag:'מה בפנים'},
  {title:'נוחות בזמן שהעור מתחדש.',body:'לחות, רכות ונוחות בזמן שהעור מתחדש – פחות חספוס, קילוף ותחושת מתיחה, ותמיכה במחסום הלחות.',tag:'הרגישו'},
  {title:'50\u00a0מ״ל. בוקר וערב.',body:'DERMA\u00a0RECOVERY\u00a0CREAM, 50\u00a0ml ℮ 1.69\u00a0fl.\u00a0oz – קרם קולגן מזין לשימוש יומיומי, למראה עור בריא וזוהר. לכל סוגי העור.',tag:'ערכה ועובדות'},
  {title:'השלימו כל פרוטוקול בשיקום.',body:'זמין דרך הקליניקות השותפות של מיטודרם. לאחר MICRO\u00a0BOOST\u00a010% הקרם חובה גם בבית. קליניקות: פנו אלינו לפרטים על מחירים.',tag:'הצעה'},
  {title:'מומחי Mitoderm מוסמכים',body:'כל מומחה כאן מוכשר ומוסמך להעניק פרוטוקולים מקוריים של Mitoderm. מצאו מרפאה מהימנה בקרבתכם וקבעו ייעוץ.',tag:'מצאו מומחה'}
 ],
 'mitoscan':[
  {title:'MITOSCAN',body:'מודדים את מה שחשוב.',tag:'MITOSCAN'},
  {title:'התרשמות אינה תוכנית.',body:'בעין בלתי מזוינת, צפיפות השיער, מספר הזקיקים וקוטר השערה נשארים סמויים – כך שהמטרות וסדרת הטיפולים נשענות על התרשמות בלבד.',tag:'למה?'},
  {title:'×50. ×200. על המסך.',body:'הדמיה באיכות HD בהגדלה ×50 ו-×200 חושפת פרטים שאינם נראים בעין: צפיפות שיער, מספר זקיקים, קוטר שערה ומצב הקרקפת.',tag:'מה בפנים'},
  {title:'מבט משותף על הקרקפת.',body:'צילום מוגדל מסייע להסביר את אזור הבדיקה ואת תוכנית המעקב. תצוגת המסך בסרט היא המחשה.',tag:'צילום והסבר'},
  {title:'סריקה. הסבר. מעקב.',body:'צלמו אזורים ספציפיים בהגדלה ×50 ו-×200, הציגו את הנתונים על המסך בפגישת האבחון הראשונה והשוו את אותם אזורים לאורך סדרת הטיפולים.',tag:'איך זה עובד'},
  {title:'מערכת אחת. מסך אחד.',body:'1× MITOSCAN – מערכת מתקדמת לאבחון הקרקפת והשיער: הגדלה ×50 ו-×200, הדמיית HD. לשימוש מקצועי בלבד.',tag:'מפרט טכני'},
  {title:'הכניסו את MITOSCAN לקליניקה שלכם',body:'לשימוש מקצועי בלבד. המומחה שלנו ייעץ לכם בנושאי הדרכה ותמחור.',tag:'הצעה'},
  {title:'מכירים את המכשיר.',body:'לתיאום הדגמה של MITOSCAN והיכרות עם אפשרויות התיעוד בקליניקה.',tag:'הדגמה מקצועית'}
 ],
 'mitopen':[
  {title:'MITOPEN',body:'מסלול החדירה לרכיבים הפעילים.',tag:'מכשור מקצועי לקליניקה'},
  {title:'דיוק שאפשר לשחזר.',body:'האזור, עובי העור והאינדיקציה – כל אחד מהם דורש עומק וצפיפות משלו. פרוטוקול מדויק ואחיד מתחיל בכלי העבודה.',tag:'אינדיקציות'},
  {title:'מ-0.25 עד 2.5\u00a0מ״מ. חמש מהירויות.',body:'עומק מתכוונן 0.25–2.5\u00a0מ״מ בהתאם לאזור ולאינדיקציה; עד חמש מהירויות לשליטה בצפיפות המיקרו־תעלות ובעוצמת הגירוי.',tag:'מפרט טכני'},
  {title:'שקט. אלחוטי. בשליטה.',body:'ארגונומי, אלחוטי ושקט – נוח לקוסמטיקאית, מדויק עבור המטופלת, ותוכנן לתמוך בהחדרת החומרים הפעילים.',tag:'יתרונות'},
  {title:'הגדרה. מיקרונידלינג. החדרה.',body:'בחרו עומק ומהירות בהתאם לאזור, צרו מיקרו־תעלות אחידות ולאחר מכן יישמו את V-TECH\u00a0SYSTEM בפנים או את EXOSIGNAL\u00a0HAIR בקרקפת.',tag:'פרוטוקול'},
  {title:'עט אחד. פנים וקרקפת.',body:'1× MITOPEN – עט מיקרונידלינג מקצועי ואלחוטי עם עומק מחט ומהירות מתכווננים. לשימוש מקצועי בלבד.',tag:'ערכה ועובדות'},
  {title:'הכניסו את MITOPEN לקליניקה שלכם',body:'לשימוש מקצועי בלבד. המומחה שלנו ייעץ לכם בנושאי הדרכה, פרוטוקולים ותמחור.',tag:'הצעה'},
  {title:'מומחי Mitoderm מוסמכים',body:'שני המכשירים מופעלים בידי אנשי מקצוע שעברו הכשרה, כחלק מפרוטוקול קליני.',tag:'מצאו מומחה'}
 ],
 'micro-boost-10':[
  {title:'MICRO BOOST 10%',body:'מיליוני מיקרו-מחטים. מזרק אחד.',tag:'BIOSPICULE™ · טיפול מקצועי לקליניקה'},
  {title:'יותר מפילינג.',body:'פילינג מסתפק בחידוש פני העור. המטופלים מבקשים חידוש והובלת חומרים בביקור אחד – תחליף לטיפול המסורתי במיקרונידלינג.',tag:'אינדיקציות'},
  {title:'שלושה שלבים. ההחלטה שלכם.',body:'כמות החומר, משך העיסוי ועוצמת הטיפול נקבעים בהתאם לאבחון העור שאתם מבצעים; לאחר מכן המסלולים המיקרוסקופיים הפתוחים מובילים פנימה את V-TECH או Longevity\u00a0Serum ואת EXOCELL\u00a0MASK.',tag:'פרוטוקול הטיפול בקליניקה'},
  {title:'צפו לעקצוץ.',body:'תחושת עקצוץ אופיינית במהלך העיסוי – והספיקולות עשויות להמשיך לעורר את העור עד 72 שעות לאחר שהמטופלת עוזבת.',tag:'הרגישו'},
  {title:'שני אורכים. שני עומקים.',body:'40% ספיקולות קצרות (80–100 מיקרון) פועלות באזור החיצוני של האפידרמיס; 60% ארוכות (300–360 מיקרון) מגיעות עמוק יותר. מטוהרות וממוינות – לא אבקה גולמית.',tag:'רכיבים פעילים'},
  {title:'מומחי Mitoderm מוסמכים',body:'ה-Micro Boost בריכוז 10% מיושם במרפאה כדי להכין את העור לטיפול אינטנסיבי.',tag:'מצאו מומחה'},
  {title:'מזרק אחד. טיפול אחד.',body:'3\u00a0ml ℮ 0.10\u00a0fl.\u00a0oz. – שליטה מקצועית בכמות החומר לטיפול אחד בקליניקה. לשימוש מקצועי בלבד.',tag:'ערכה ועובדות'},
  {title:'הכניסו אותו לקליניקה שלכם.',body:'לשימוש מקצועי בלבד. לאחר הטיפול ייתכנו אדמומיות זמנית, יובש או קילוף. המומחה שלנו ייעץ לכם על פרוטוקולים ותמחור.',tag:'הצעה'}
 ],
 'mitotech-cell-booster':[
  {title:'MITOTECH CELL BOOSTER',body:'בוסטר תאי בשני בקבוקונים לפרוטוקולים בקליניקה בשילוב עם MITOPEN או MICRO\u00a0BOOST\u00a010%.',tag:'מקצועי'}
 ]
};
