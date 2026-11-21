// Scroll films for ProductCinema pages, keyed by product slug. Paths go through
// mediaUrl(); a path that resolves to an empty URL keeps the image-only stage on
// that viewport. chapters[i] belongs to shot i of the page (REGISTRY.json order);
// start and end are frame numbers, start===end holds that frame. A slug without
// an entry keeps the image-only stage.
// anchor:'left' keeps the left edge of the desktop film when the window is narrower than 16:9: for a film whose pack
// stands at the very left and whose right third is empty background.
export type ProductFilm={desktop:string;mobile:string;fps:number;frames:number;anchor?:'left';chapters:Array<{start:number;end:number}>};
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
 'exosignal-spray':{desktop:'/assets/world/exosignal-spray-film.mp4',mobile:'/assets/world/exosignal-spray-film-mobile.mp4',fps:24,frames:1208,chapters:[
  {start:0,end:105},     // 01 pack in the clinic
  {start:105,end:262},   // 02 consultation
  {start:262,end:370},   // 03 the bottle in his hand
  {start:370,end:548},   // 04 at home in the evening
  {start:548,end:800},   // 05 part, spray, massage
  {start:800,end:938},   // 06 the pack on the bathroom counter
  {start:938,end:1100},  // 07 the follow-up visit
  {start:1100,end:1208}  // 08 pack
 ]},
 // A short film for a coming-soon page: the real box in the clinic, one focus pull (Kling 4.0, 1080p), then the same
 // box at the client's home - the protocol gives the rest of the solution for home use and an 8-week home programme.
 // 1912x1080 and 1080x1920, 468 frames, one chapter: the page copy has an intro only (state/films/mitotech-cell-booster/).
 'mitotech-cell-booster':{desktop:'/assets/world/mitotech-cell-booster-film.mp4',mobile:'/assets/world/mitotech-cell-booster-film-mobile.mp4',fps:24,frames:468,anchor:'left',chapters:[
  {start:0,end:468}  // 01 the box in the clinic, the treatment, the same box at her home
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
  {title:'הנתונים על המסך',body:'נשירת שיער מסטרס · אלופציה אנדרוגנטית · איזון הקרקפת (עודף סבום, גרד, אדמומיות) · שיער דק/שביר/יבש',tag:'מה רואים על המסך'},
  {title:'אמפולה אחת, שמונה פפטידים',body:'מבנים אקסוזומליים סינתטיים נושאים PDRN\u00a02%, חומצה היאלורונית, שמונה פפטידים ביומימטיים, תאי גזע מתפוח וויטמיני\u00a0B.',tag:'מה בפנים'},
  {title:'מודדים, פותחים, מחדירים',body:'MITOPEN פותח את מסלול החדירה ו-\u2060EXOSIGNAL\u00a0HAIR מיושם על הקרקפת המטופלת',tag:'פרוטוקול'},
  {title:'3 = 1 + 1',body:'לאחר פציעה מבוקרת מטפטפים את החומר על העור ולמעשה נותנים לעור מחסן של פקטורי גדילה, פפטידים, חלבונים ותאי גזע מצמחים כך שהעור משתמש במאגרים חדשים ובונה את עצמו מחדש.',tag:'בתוך העור'},
  {title:'ספיגת הסרום',body:'לאחר העבודה יש לעסות עם הכפפות את הקרקפת בעדינות עד לספיגה מלאה של החומר.',tag:'ספיגת הסרום'},
  {title:'תדירות וסדרת טיפולים',body:'טיפול אחד בכל 14 יום. מומלץ לבצע לפחות 4 טיפולים רצופים.',tag:'סדרת טיפולים'},
  {title:'מעקב לפני / אחרי',body:'הפחתת נשירה ודלקת מקומית · שיפור מצב הקרקפת והמיקרו-סירקולציה · שיפור בנפח, מרקם וברק · תמיכה בהארכת שלב האנגן (צמיחה)',tag:'מעקב'},
  {title:'מומחי Mitoderm מוסמכים',body:'Exosignal\u00a0Hair הוא טיפול אמפולות מדויק המיושם במפגשים במרפאה.',tag:'ערכה ועובדות'},
  {title:'הכניסו את EXOSIGNAL\u00a0HAIR לקליניקה שלכם',body:'לשימוש מקצועי בלבד, מיועד לשילוב עם MITOPEN ו-\u2060MITOSCAN.',tag:'הצעה'}
 ],
 'exosignal-spray':[
  {title:'EXOSIGNAL SPRAY',body:'תמיכה בקרקפת בין הביקורים.',tag:'טיפוח ביתי'},
  {title:'הימים שבין הטיפולים חשובים.',body:'EXOSIGNAL\u00a0HAIR הוא הטיפול בקליניקה. דלילות שיער, שיער שביר וחוסר איזון בקרקפת דורשים תמיכה בימים שבין הטיפולים.',tag:'למי מומלץ'},
  {title:'התזה אחת. שלוש משימות.',body:'שומר על סביבה מאוזנת בקרקפת, מזין את השיער ותומך במחזור צמיחת השיער הטבעי — נספג במהירות, ללא שטיפה.',tag:'מה הספריי עושה'},
  {title:'קליל על הקרקפת. ללא שטיפה.',body:'מסייע להקל על יובש ותחושת אי־נוחות; תומך במראה שיער מלא, חזק וחיוני יותר, במריחה נוחה ואחידה באזורים שבהם ניכרת דלילות.',tag:'תמיכה רציפה בקרקפת'},
  {title:'חלוקה. התזה. עיסוי.',body:'לחלק את השיער כדי לחשוף את הקרקפת, להתיז ישירות עליה ולעסות בעדינות – ללא צורך בשטיפה. מדי יום, בין טיפולי EXOSIGNAL\u00a0HAIR ולאחריהם.',tag:'שגרה יומיומית'},
  {title:'15\u00a0מ״ל. יומיומי. ללא שטיפה.',body:'1× EXOSIGNAL\u00a0SPRAY, 15\u00a0מ״ל – ספריי להזנה עמוקה של הקרקפת, לשימוש ביתי. סדרת האקסוזומים הסינתטיים.',tag:'פורמט'},
  {title:'מומחי Mitoderm מוסמכים',body:'כל מומחה כאן מוכשר ומוסמך להעניק פרוטוקולים מקוריים של Mitoderm.',tag:'מצאו מומחה'},
  {title:'תמיכה רציפה בזקיקים בין הביקורים',body:'זמין דרך הקליניקות השותפות של מיטודרם. התייעצו עם המומחה שלכם כיצד EXOSIGNAL\u00a0SPRAY משתלב בתוכנית הטיפול שלכם.',tag:'הצעה'}
 ],
 'mitotech-cell-booster':[
  {title:'MITOTECH CELL BOOSTER',body:'בוסטר תאי בשני בקבוקונים לפרוטוקולים בקליניקה בשילוב עם MITOPEN או MICRO\u00a0BOOST\u00a010%.',tag:'מקצועי'}
 ]
};
