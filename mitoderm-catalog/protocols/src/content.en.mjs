// English: translation of the Hebrew protocols (for review by the MITODERM team)
export default {
  lang: 'en',
  dir: 'ltr',
  fonts: ['latin'],
  title: 'MITODERM | Professional In-Clinic Treatment Protocols',
  description: 'MITODERM professional protocols: microneedling and biomicroneedling, EXO-NAD peel, EXOCELL MASK.',
  ui: { skip: 'Skip to content', nav: 'Protocols', langs: 'Language' },
  hero: {
    title: 'Professional In-Clinic Treatment Protocols',
    sub: 'Instructions for professional use',
  },
  families: [
    {
      id: 'microneedling',
      nav: 'MICRONEEDLING',
      title: 'MICRONEEDLING & BIOMICRONEEDLING',
      tile: {
        images: ['micro-boost-10', 'vtech-system', 'mitopen', 'exosignal-hair'],
        links: [
          ['MITOPEN + V-TECH', 'vtech-mitopen'],
          ['BIOSPICULE BOOST 10% + V-TECH', 'biospicule-vtech'],
          ['MITOPEN + MITOTECH CELL BOOSTER', 'cell-booster'],
          ['BIOSPICULE BOOST 10% + MITOTECH CELL BOOSTER', 'cell-booster'],
          ['MITOPEN + EXOSIGNAL HAIR', 'exosignal-hair'],
        ],
      },
      protocols: [
        {
          id: 'vtech-mitopen',
          title: 'V-TECH + MITOPEN',
          images: ['vtech-system', 'mitopen'],
          aside: [
            { title: 'Recommended dosage', body: ['Per treatment area (face, neck or décolleté):', { list: ['V-TECH Serum: up to 2 ml', 'V-TECH Gel Mask: up to 2 ml'] }] },
            { title: 'Storage after opening', body: ["Use the ampoule within one month of opening, following the product's storage instructions."] },
          ],
          steps: [
            { title: 'V-TECH SERUM', body: [
              'Draw V-TECH Serum into a 3 ml syringe with a drawing-up needle.',
              'Apply the serum with MITOPEN, a mesopen or other suitable professional equipment.',
              'Working depth depends on the device, the treatment area, skin thickness and condition, and the professional assessment.',
            ] },
            { title: 'V-TECH GEL MASK', body: [
              'Once the serum work is complete, apply V-TECH Gel Mask to the same area.',
              'Massage gently until fully absorbed. No rinsing needed.',
            ] },
          ],
          after: [
            { title: 'After the serum', body: [{ products: [
              ['Applying EXOCELL MASK is recommended to infuse hyaluronic acid, plant extracts and aloe vera.', 'exocell-mask'],
              ['To finish: DERMA RECOVERY CREAM.', 'derma-recovery'],
              ['Sun protection is mandatory.', null],
            ] }] },
            { title: 'Frequency and treatment course', body: [
              'One treatment every 14 days.',
              'Recommended course: 4-6 treatments, depending on skin condition and the treatment goal.',
              { note: 'Base protocol: 4 consecutive treatments, every two weeks' },
              'After the course, a maintenance treatment every 2-3 months is recommended, depending on skin condition, to preserve and maximise the results of the course.',
            ] },
          ],
        },
        {
          id: 'biospicule-vtech',
          title: 'BIOSPICULE™ MICRO BOOST 10% + V-TECH',
          images: ['micro-boost-10', 'vtech-system'],
          aside: [
            { title: 'Treatment course', body: [
              'A course of 3-4 treatments, 4 weeks apart.',
              "After the course, a maintenance treatment can follow, based on the skin assessment, treatment goals and the patient's response.",
              'For home use, recommend the BIOSPICULE home series for renewal, EXOTECH GEL for optimal hydration and DERMA RECOVERY CREAM for intensive nourishment and hydration.',
            ] },
          ],
          steps: [
            { title: 'Skin cleansing', body: ['Cleanse the skin without rubbing aggressively. After cleansing, dry the skin completely.'] },
            { title: 'Applying MICRO BOOST 10% with controlled massage', body: [
              'Gradually spread MICRO BOOST 10% BIOSPICULE™ over the working areas and massage with even, controlled pressure, following the training technique, until the product is absorbed.',
              { note: 'Massage intensity sets the intensity of stimulation: the more intense the pressure and massage, the stronger the skin reaction may be and the longer the recovery, including peeling.' },
              "Adjust massage intensity, pressure and technique to the skin's condition and type, the professional assessment, the treatment goal and the desired effect.",
              "Work in a controlled way and take the patient's sensations into account throughout the treatment.",
            ] },
            { title: 'Combining active products', body: [
              'Once MICRO BOOST 10% is absorbed, active products can be chosen to match the selected protocol, such as:',
              { list: ['V-TECH Serum + V-TECH Gel Mask', 'MITOTECH CELL BOOST', 'LONGEVITY SERUM'] },
            ] },
          ],
          after: [
            { title: 'Finishing the treatment', body: [{ products: [
              ['EXOCELL MASK as the finishing, restoring mask', 'exocell-mask'],
              ['DERMA RECOVERY CREAM to complete hydration and nourishment and support the skin barrier', 'derma-recovery'],
              ['SPF 30 or higher sunscreen, mandatory', null],
            ] }] },
            { title: 'Expected skin reaction', body: [
              'Because of the high spicule concentration, a characteristic tingling may be felt during the treatment and in the following days, mainly when the skin is touched.',
              { chips: ['Temporary redness', 'Warmth', 'Dryness', 'Tightness', 'Sensitivity to touch', 'Peeling of varying degree'] },
              'The intensity of the reaction varies between patients and is not, on its own, a measure of treatment efficacy. It can depend on skin type, sensitivity, the amount of product and the massage technique.',
              { note: 'Spicules may remain in the outer layers of the skin for up to 72 hours.' },
            ] },
          ],
        },
        {
          id: 'cell-booster',
          title: 'MITOPEN / BIOSPICULE CELL BOOSTER 10%',
          combo: '+ MITOTECH CELL BOOSTER',
          images: ['mitopen', 'micro-boost-10'],
          steps: [
            { body: ['After cleansing the face.'] },
            { body: ['Pour the booster from one vial into the concentrated powder in the second vial. Wait until a clear solution forms. Draw up to 2 ml (face, neck and décolleté).'] },
            { body: ['Then mix the hyaluronic acid ampoule and drip a few drops onto each area of the face while microneedling, using the stamping technique. Alternatively, with the biospicule gel: apply 1.5-2 ml to the face and, immediately after absorption, apply the CELL BOOSTER.'] },
            { body: ['To finish, EXOCELL MASK can be applied.'] },
            { body: ['Apply DERMA RECOVERY CREAM moisturiser.'] },
            { body: ['Over it, apply sunscreen of at least SPF 30.'] },
          ],
          after: [
            { body: [{ note: 'Whatever remains in the falcon tube can be given to the client to take home (priced as a complementary treatment, up to two weeks of use).' }] },
          ],
        },
        {
          id: 'exosignal-hair',
          title: 'EXOSIGNAL HAIR',
          sub: 'Professional scalp treatment protocol',
          combo: 'MITOPEN + EXOSIGNAL HAIR',
          images: ['exosignal-hair', 'mitopen'],
          aside: [
            { title: 'Storage', body: ['After opening, keep the ampoule refrigerated. Shelf life after opening: up to one month.'] },
          ],
          steps: [
            { title: 'Preparing and cleansing the area', figure: 'mitoscan', body: [
              'Thoroughly cleanse the scalp and remove any residue of creams, serums, sebum or other products.',
              "Disinfection can be done with a skin-appropriate antiseptic, following the clinic's professional working protocol.",
              'The MITOSCAN camera can be used to review the scalp, follicle condition, thinning and inflammation.',
            ] },
            { title: 'Drying', body: ['Dry the treatment area completely.'] },
            { title: 'EXOSIGNAL HAIR SERUM', body: [
              'Use about 1.5-2 ml of serum, depending on the size of the area.',
              'The treatment is performed with MITOPEN or a mesopen.',
              'Working depth: up to 0.6 mm, depending on the area, scalp condition and the professional assessment.',
              'Product and device work at the same time. Divide the work into sections: first drip a little product onto a section, then stamp.',
            ] },
            { title: 'Absorbing the serum', body: ['After the procedure, gently massage the scalp with gloved hands until the product is fully absorbed.'] },
          ],
          after: [
            { body: [{ note: 'Indicator: stamping marks and red dots show a successful treatment.' }] },
            { title: 'Frequency and treatment course', body: [
              { list: ['One treatment every 14 days.', 'At least 4 consecutive treatments are recommended.', 'After the course, a maintenance treatment can be done once every two months.'] },
              "Frequency and number of treatments may vary with the degree of hair loss, scalp condition, the professional assessment and the patient's response.",
            ] },
          ],
        },
      ],
    },
    {
      id: 'peeling',
      nav: 'PEELING',
      title: 'PEELING',
      tile: { images: ['exo-nad'], links: [['EXO-NAD PEEL', 'exo-nad']] },
      protocols: [
        {
          id: 'exo-nad',
          layout: 'stages',
          title: 'EXO-NAD SKIN LONGEVITY PEEL',
          sub: 'Protocol and application',
          lead: 'The treatment has three stages: EXO BIPHASIC PEEL | pH NORMALIZER | LONGEVITY SERUM',
          images: ['exo-nad'],
          steps: [
            { title: 'EXO BIPHASIC PEEL', body: [
              'Shake the biphasic solution well before use.',
              { options: [
                ['Option 1. Thin, sensitive or slightly mature skin:', 'Draw 1 ml of the solution and apply it evenly over the treatment area with a gentle massage. Leave on the skin for up to 20 minutes, depending on skin condition and sensitivity.'],
                ['Option 2. Thick or more mature skin:', 'Draw 1 ml of the solution, apply it to the treatment area with massage and leave for 15 minutes. Then draw another 1 ml, spread it over the same area with a gentle massage and leave for up to 15 more minutes. Total exposure time: up to 30 minutes.'],
              ] },
            ] },
            { title: 'pH NORMALIZER', body: [
              'Draw 1.5-2 ml of the neutraliser and apply it evenly over the entire area treated with EXO PEEL.',
              'Leave on the skin for 2-3 minutes. Then rinse thoroughly with water and dry the skin completely.',
            ] },
            { title: 'LONGEVITY SERUM', body: [
              'Draw about 2 ml of Longevity serum and apply it evenly over the treatment area.',
              'Allow the serum to absorb. Do not rinse.',
            ] },
          ],
          after: [
            { title: 'Storage and use after opening', body: [{ list: [
              'After opening, the product can be used for up to one month, stored in a cool place according to the storage instructions.',
              'The kit provides up to 15 treatments, depending on the amount used per treatment.',
              'Change gloves, needles and syringes between stages.',
            ] }] },
          ],
        },
      ],
    },
    {
      id: 'mask',
      nav: 'MASK',
      title: 'MASK',
      tile: { images: ['exocell-mask'], links: [['EXOCELL MASK', 'exocell-mask']] },
      protocols: [
        {
          id: 'exocell-mask',
          layout: 'mask',
          title: 'EXOCELL MASK',
          sub: 'Professional and home-use protocol',
          images: ['exocell-mask'],
          use: { title: 'Use after a professional or invasive treatment', steps: [
            'At the end of in-clinic treatments, apply EXOCELL MASK evenly over the treatment area.',
            'Leave the mask on the skin for up to 30 minutes.',
            'Then remove the mask and gently pat the remaining serum into the skin.',
          ] },
          blocks: [
            { title: 'Within professional protocols', body: [
              'EXOCELL MASK is especially suited as a soothing final step after professional treatments, including:',
              { chips: ['Laser', 'Peeling', 'Injectables and fillers', 'Medical mesotherapy', 'RF microneedling', 'RF', 'Microneedling'] },
            ] },
            { title: 'Package contents', body: ['Each box contains 5 masks, each individually sealed to keep the product optimally stable.'] },
          ],
          home: {
            title: 'Home care after the treatment',
            cards: [
              { title: 'The first 24 hours', body: ['Do not wash or wet the treated area. Avoid sport or any activity that causes heavy sweating. As far as possible, avoid touching or rubbing the area, and avoid make-up.'] },
              { title: 'Hydration and recovery', body: ['Continue at home with suitable hydration and nourishment, as advised by the practitioner. DERMA RECOVERY CREAM is recommended to support hydration and the skin barrier.'] },
              { title: 'Sun protection', body: ['Apply SPF 50 sunscreen every morning and avoid direct sun exposure as much as possible for at least 7 days.'] },
              { title: 'Heat, water and activity', body: ['Avoid saunas, hot showers, swimming and activity that causes heavy sweating for 48 hours.'] },
              { title: 'Active ingredients', body: ['Do not use acids, retinoids, benzoyl peroxide, scrubs or irritating products for 5-7 days, or until the skin has returned to its usual state and feel.', { note: 'Melanin inhibitor as needed.' }] },
              { title: 'Peeling and sensations after the treatment', body: [{ list: [
                'Tingling, redness, warmth, dryness or light peeling may appear after the treatment.',
                'Do not scratch, rub or deliberately remove peeling skin.',
                'In case of significant pain, unusual swelling, blisters, a persistent rash or any unexpected reaction, contact the practitioner and seek medical assessment as needed.',
                'After treatment with spongilla spicules, the needle-like sensation may last up to 72 hours.',
              ] }] },
            ],
            maintain: {
              title: 'Home maintenance protocol',
              images: ['derma-recovery', 'exotech-gel'],
              body: [{ list: [
                'In the evening, the BIOSPICULE biomicroneedling home series, 1.5% or 2.5%, can be used to renew the skin and maintain results, with DERMA RECOVERY CREAM on top for hydration.',
                'EXOTECH GEL can be used to preserve the exosome results immediately after a biomicroneedling course.',
              ] }],
            },
          },
        },
      ],
    },
  ],
  footer: 'MITODERM | WHERE SCIENCE MEETS BEAUTY',
};
