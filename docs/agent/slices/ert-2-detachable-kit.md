# ERT-2 Detachable kit - design proposal

Status: **Design proposed, 26 September 2026; revised the same day.** The owner answered Q6 to Q11. Crane
makers' documents and the applicable standards were then researched (section 2), and the owner
directed that **where the research contradicts the owner's inputs, the research is more
authoritative**. Q2, Q4, Q5 and Q12 are settled by that research. The owner answered **Q1 and Q3 as
recommended** the same day (section 1.3). A second round of research, on Indian statutory requirements
(section 2, H), raised two small questions, **Q13 and Q14, answered as recommended** (section 1.4).
**Every question is now answered. Built the same day on the owner's word** - section 18 is the
implementation record, with the owner's two requests made while it was built (Fixed Assets; trailer beds)
in section 17.

Hiring lane (Track 2). Worktree `<a separate worktree>`, branch `hiring/ert-2-detachable-kit`,
based on `main` at `6116c4d`. Migration slot `20260908_0043`, parent `20260908_0042` - the single Alembic
head on `main`. No other branch on `origin` holds a `0043` revision (checked 26 September 2026). Foundation
Slice Mode: the shape is built properly, the screens minimally.

ERT-1 brought Plum's machines into the Equipment Reference and fitted each crane's carrier to it by a
dated link. This package records the **detachable kit** the cranes are configured from:

- boom and jib sections;
- counterweight;
- hook blocks;
- the cranes' own lifting tackle.

It also adds the **depth setting** (default 3) that limits how far fitted parts may nest.

In plain words:

- **Kit is shared, not owned by one crane.** Kit is interchangeable between cranes that take the same
  kit, so it belongs to the **crane models it fits**, not to one crane (owner, Q6). A 100 t hook block
  for the SCC1000A is available to every SCC1000A the company holds.
- **Each kind of piece is described once.** The Fleet Admin records it as a model - "SANY SCC1000A
  boom insert, 9 m" - naming the crane models it fits, and then adds the pieces held - "four of them".
- **A crane's page shows the kit held for its model**, and how many cranes share it.
- **8A picks the mobilisation BOM from that shared kit, per trip.**
- **Retiring.** Kit is retired when it is scrapped, lost or sold. When a crane is sold, the buyer
  usually takes a set of kit with it (Q7).
- **Plum does not change.** It lists no kit, so the Fleet Admin enters kit on the platform (ERT-1
  design, comment 5).

"Fleet Admin" means whoever holds `EQUIPMENT_REFERENCE_MANAGE`: **Admin, until a Fleet Admin role
exists** (ERT-1 design, comment 1).

**Reuse, not a second hierarchy** (CODING_STANDARDS.md section 1, DRY first). Kit is carried by ERT-1's
own records:

- a piece of kit is a row of `equipment_asset`;
- its kind is a part class in the structure;
- the kinds a class of machine takes are rows of `equipment_part_fit`;
- each kind of piece is an `equipment_model` with its ratings.

What ERT-1 has no record for is **which crane models a kit model fits**. That is one small new table.
Kit is not put in a crane's dated parts tree: the owner's answer to Q6 makes kit shared, and the reasons
are in section 5.

---

## 1. Owner decisions and questions

### 1.1 Answered by the owner (26 September 2026)

| # | Question | Answer |
| --- | --- | --- |
| Q6 | One crane at a time, or shared by cranes of a model? | **Shared.** "Kit is interchangeable for the same model and the company holds multiple units of the same model." Then: "kit can be associated with a model and shared among multiple units of the same model." **Refined by the research** (section 2, C): some kit fits several models, and some fits only one version of a model, so a kit model names the exact crane models it fits (Q12) |
| Q7 | When a crane is retired, what happens to its kit? | "It is possible that the kit can work with other units of the same model but usually whoever buys will buy the kit too. It does not make too much sense to have multiple kits for each unit unless they are easily breakable." **So nothing is automatic.** The Fleet Admin retires the pieces sold with a crane, reason "sold". The platform shows when a kit model fits no active crane any more |
| Q8 | Retiring a piece | **As recommended**: the Fleet Admin, with a reason (scrapped, lost, sold, recorded by mistake) and a date; history kept; nothing deleted. "Other, with a note" added later the same day (Q14) |
| Q9 | Depth setting | **3 is adequate**, kept with the structure. It applies to fitted parts; kit is recorded flat (section 5) |
| Q10 | How much kit | "Go with 100 cranes and 10 kinds each." PBL's equipment list (section 2, G) gives about 28 crane models carrying kit, so 150 to 350 kit models and some hundreds of pieces. Entry is on screen, with "add several alike". No upload |
| Q11 | Migration slot | **`20260908_0043`** |

The owner also directed, the same day: **"If your research contradicts my inputs, use the research as
more authoritative."**

### 1.2 Settled by the research

Each item below follows from section 2. It is stated so the owner can object, not asked again.

- **Q2. Lifting tackle.**
  - **What goes where.** Tackle that belongs to the cranes is kit: counterweight-handling pendants and
    links, which Manitowoc lists as crane equipment, a crane's own spreader beam and its dedicated
    slings. Slings and shackles held in the store and issued to any job are inventory (Annexure-11(B)),
    which comes later. No maker researched supplies general slings or shackles with a crane.
  - **Why each piece is its own record.** Indian law requires every piece of tackle, kit or store, to
    carry its own identification mark and safe working load, to be entered in a register, and to be
    examined by a competent person the state recognises at least every 12 months. This was first found
    under the Factories Act section 29 and the BOCW rules. Those Acts were repealed by the OSH Code on
    21 November 2025, but the same requirements continue under the rules that survive (section 2, H1).
    So tackle is always recorded one piece at a time.
- **Q4. How a piece is described.** Every piece belongs to a **model**, recorded once for each kind
  of piece. Every maker identifies kit by kind, not by the piece:
  - Liebherr by type number (boom foot 2821.30);
  - SANY by part code (Q320A.595.13);
  - Manitowoc by boom and jib number (No. 44 boom, No. 133 luffing jib).

  The platform's model is that kind. It carries the length, weight or capacity once for every piece of
  it.
- **Q5. A piece's own number.** Optional now, recorded where the piece carries one:
  - Manitowoc lattice sections carry a plate with the boom number, part number and a manufacturing
    code, and its attachments carry serial plates;
  - hook blocks are marked with their rated capacity and weight;
  - Liebherr and SANY data give only kind numbers.

  Where a piece carries no number, the platform's `EQ-` number can be stencilled on it. The **Eligibility
  foundation**, which will keep the examination record, will require a mark on every piece of tackle and
  every hook block. "Details to complete" lists pieces tracked one by one that have no number.
- **Q12 (new). Kit that fits more than one crane model.** A kit model names **one or more exact crane
  models**. Some examples of sharing:
  - Liebherr's LTM 1250-5.1 sections also fit the LTM 1200-5.1 and LTM 1220-5.2;
  - Grove's GMK6300L-1 counterweight slabs fit four other GMK models;
  - the Manitowoc 2250 and M-250 share the No. 44 boom.

  And kit is sometimes not shared even within a model: SANY's SCC1000A and SCC1000A-8 inserts differ in
  weight and height. The platform's models are already exact, since each Plum model name maps to one
  model.
- **Outrigger pads are not kit.** Liebherr's LTM pads are fixed to the outriggers, Grove's are
  self-stowing, and a trade glossary says the pad generally travels with the machine. Mats and timber
  are site or job equipment (OSHA 1926.1402 puts supporting materials on the site). Mats are left to 8A.

### 1.3 Answered after the research (owner, 26 September 2026)

**Q1 and Q3: as recommended.** The owner asked whether four kinds should leave room for a crane that
ships with more. They need not: a kind is a row of the structure, not a slot in a fixed list. A new kind
- an auxiliary hoist, a superlift attachment, an excavator's bucket - is added by a new structure
version, with no change to any table or code. A crane may also have any number of kit models within
those kinds.

Six became four for two reasons. Outrigger pads left, because they travel on the crane. Inserts and jibs
became one kind, "Boom and jib section", with a type for each, following Annexure-11(A)'s "Boom and Jib"
group. Nothing a crane ships with was dropped.

#### Q1. Which kinds of kit?

**Recommendation:** four kinds, for cranes, each with its types. They follow Annexure-11(A)'s groups -
"Boom and Jib", "Counter Weight" - which your record of 24 September called categories of parts. They
also follow what SANY, Liebherr and Manitowoc list (section 2, A).

| Kind | Types | Measured by | Tracked |
| --- | --- | --- | --- |
| Boom and jib section | main boom foot (butt), main boom insert, main boom head (top), luffing jib section, fixed jib section, folding (swing-away) jib, strut or mast | length (m); weight (t), Q13 | one by one |
| Counterweight | upper counterweight (plate or box), counterweight tray, carbody (central) ballast, superlift or derrick ballast | weight (t) | counted (Q3) |
| Hook block | hook block, single-line hook or weight ball | rated capacity (t); weight (t), Q13 | one by one |
| Lifting tackle | counterweight-handling pendant or link, spreader or lifting beam, sling, shackle | rated capacity (t); weight (t), Q13 | one by one (law, Q2) |

The boom foot and head are needed on every job and the inserts only on some. Both are kit, because
all of them are interchangeable pieces the configuration is built from. What stays with one crane -
upperworks, carbody, crawlers, carrier - is that crane's **fitted** part, not kit.

The following are **not** separate kinds:

- pendants, straps and guy rods travel and are sold with their section (Manitowoc), and their lengths
  follow a rigging drawing;
- a removable auxiliary hoist (Grove) can be added as a kind later if PBL uses one;
- kit for machines other than cranes is added when needed.

Please add or remove kinds.

**Answer: as recommended** (26 September 2026).

#### Q3. Counterweight: counted, or one piece at a time?

**Recommendation: counted**, by model - "SCC1000A counterweight block II, 3.9 t: 4 held". Makers and
dealers identify counterweight pieces by weight and crane model:

- SANY's transport lists and a Liebherr used-parts listing give weights only, with no numbers;
- no standard found requires a piece-by-piece record, since counterweight is not lifting tackle;
- rental software offers "bulk" items for exactly this (Wynne, HireHop).

One maker marks them: Grove's instructions show where identification numbers sit on removable
counterweights. **If PBL numbers its counterweight pieces and wants each one's history, say so**, and
counterweight is tracked one by one instead, with "add several alike" keeping entry quick.

**Answer: as recommended - counted** (26 September 2026).

### 1.4 Answered: from the owner's questions on buffers and statutory requirements

**Q13 and Q14: as recommended** (owner, 26 September 2026).

#### Q13. Weight and the maker's part number on each kit model

The statutory research (section 2, H) found two facts about each kind of piece that later work will
need, and that the Fleet Admin has in hand from the maker's data when recording the model:

- **Weight.** Road permits for over-size and over-weight loads record each load's weight and the load
  per axle. IS 13367-1 and OSHA require attachments and hook blocks to be marked with their weight. The
  first proposal measured weight on counterweight only.
- **The maker's part number.** Makers identify kit by it (section 2, B), and certificates cite it.

**Recommendation:**

- weight becomes a measure of **every** kind of kit, beside length or capacity; for counterweight it
  already is;
- a model gains an optional **maker's part number**;
- both are entered once per model, from the maker's transport list.

Transport size, the HSN code and a declared value are left to 8A, with Finance. HSN and value need
PBL's tax adviser (section 2, H3), and size matters only for the largest loads.

#### Q14. "Other, with a note" as a retirement reason

**Recommendation:** add it to the reasons of Q8 (section 5, "Room for change"). With "Other", the note
is required.

### 1.5 Already settled before this package, not asked again

| Point | Settled by |
| --- | --- |
| Admin records kit, as Fleet Admin until that role exists | ERT-1 design, comment 1 |
| Every role that reads Work Orders reads machines, and so kit | ERT-1 design, section 9 |
| Kit is entered on the platform, since Plum lists none | ERT-1 design, comment 5 |
| General tools come from inventory, later | ERT-1 design, comment 5 |
| The BOM is per trip, picked from the kit, never stored in the hierarchy (8A) | Owner, 24 September 2026 (`DEFERRED_REQUIREMENTS.md`, "Asset component hierarchy") |
| Depth is a setting, default 3; build only what Hiring needs | Owner, 24 September 2026 (same record) |

### 1.6 The questions as first put (record)

Q1 to Q11 were put on 26 September 2026 in commit `4e4788e`. The recommendations were:

- **Q1:** six crane kinds, including outrigger pads.
- **Q2:** the crane's own tackle is kit; store tackle is inventory.
- **Q3:** one by one, except outrigger pads.
- **Q4:** a model required per kind.
- **Q5:** the number optional.
- **Q6:** one crane at a time.
- **Q7:** nothing automatic.
- **Q8:** retire with a reason.
- **Q9:** the depth kept with the structure, with nothing at level 3.
- **Q10:** on-screen entry.
- **Q11:** `20260908_0043`.

The owner's answers to Q6 to Q11 and the research changed Q1, Q3 and Q6, and settled Q2, Q4 and Q5. Q12
arose from the research.

---

## 2. What the makers and the standards say (26 September 2026)

Researched from the makers' websites, data sheets and product guides, regulators, and trade and rental
sources. Coverage and its limits:

- **Cranes covered:** SANY SCC1000A, SCC2500A and SCC4000A crawlers and SAC and STC wheeled cranes;
  Liebherr LR 1300 / LR 1300 SX crawlers and LTM 1100-5.2 and LTM 1250-5.1 all-terrain cranes;
  Manitowoc 2250 and MLC300 crawlers and the Grove GMK5250L-1.
- **Standards and law:** EN 13000, ASME B30.5, B30.9, B30.10 and B30.26, OSHA, WorkSafeBC, the
  Factories Act 1948 and the BOCW Central Rules 1998. A second round (section H) checked what is in
  force in India now, after the OSH Code, and added road transport, GST and Indian Standards.
- **Limits:**
  - many makers' PDFs could not be read directly, so some figures come from search-engine extracts of
    them;
  - the standards' own texts are mostly paywalled, so they come from regulators' pages or reputable
    summaries;
  - figures are indicative, not a parts list.

The main sources are given with each finding.

**A. What the kit is.** All three makers split a crane into the same groups.

- **Boom and jib lattice sections:**
  - a boom foot (butt) and head (top), needed on every job;
  - inserts of 3, 6, 9 or 12 m (10, 20 or 40 ft), chosen per job;
  - luffing and fixed jibs, each built from a foot, sections, a head and struts.
- **Counterweight:** a tray with plates or boxes, carbody (central) ballast, and superlift or derrick
  ballast.
- **Hook blocks:** several per crane, of different capacities.
- **Removable crawlers:** always needed, but transported separately.

A 100 t crawler has about 29 detachable pieces. On large crawlers the counterweight alone is 15 to 36
pieces.

Sources:

- SANY SCC1000A:
  `https://www.sanyglobal.com/d/file/product/crane-crawler/2019-11-20/6a0708199807a58dea5ae22430029df6.pdf`
- Liebherr LR 1300: `https://www.manualsdir.com/manuals/520324/liebherr-lr-1300.html?page=3` (and pages
  4-6)
- Manitowoc 2250:
  `https://www.manitowoc.com/sites/default/files/media/divers/file/2020-01/2250-Product-Guide.pdf`
- MLC300: `https://guymturner.com/wp-content/uploads/2017/09/330-ton-Manitowoc-MLC300.pdf`

All-terrain cranes carry their folding jib and part of their counterweight. The rest goes by separate
truck:

- the Liebherr LTM 1100-5.2 carries 11.5 t of its 35 t counterweight;
- none of the Grove GMK5250L-1's 80 t counterweight travels within a 12 t axle load.

Sources: `https://www.manualsdir.com/manuals/520567/liebherr-ltm-1100-52.html?page=13`,
`https://www.manitowoc.com/grove/all-terrain-cranes/gmk5250l-1`.

**B. How pieces are identified.** Two kinds of number exist.

- **Kind numbers**, which identify a kind of piece: Liebherr's type numbers such as 2821.30, SANY's
  part codes such as Q320A.595.13, and Manitowoc's boom and jib numbers. These are what the platform's
  models are.
- **Piece numbers**, which identify one piece:
  - Manitowoc stamps a plate on every lattice section with the boom number, part number and a
    manufacturing code, and puts serial plates on attachments
    (`https://www.manitowoc.com/sites/default/files/media/divers/file/2020-03/Lattice-Inspection-and-Lacing-Replacement-Folio-1316-10-21-15.pdf.pdf`);
  - ASME B30.5, as OSHA quotes it, requires booms, boom sections and jibs to be "clearly identified"
    (`https://www.osha.gov/laws-regs/standardinterpretations/2004-02-23`);
  - OSHA 1926.1433(d)(3) requires hook-and-ball assemblies and load blocks to be marked with rated
    capacity and weight;
  - WorkSafeBC says a unique identifier is what links a piece to its inspection records
    (`https://www.worksafebc.com/en/law-policy/occupational-health-safety/searchable-ohs-regulation/ohs-guidelines/guidelines-part-14`).

  Counterweight pieces are identified by weight and crane model
  (`https://www.wittrock-trading.com/liebherr-counterweight-plates-liebherr-ltm-13001`), except Grove's,
  whose instructions show where identification numbers sit on them.

**C. Sharing between cranes.**

- **Sharing across models is designed in:**
  - Liebherr LTM 1250-5.1 sections and folding-jib extensions fit the LTM 1200-5.1 and LTM 1220-5.2
    (`https://www.liebherr.com/en-me/n/liebherr-presents-the-ltm-1250-5-1-five-axle-mobile-crane-at-bauma-conexpo-india-2016-24070-8141050`);
  - Grove GMK6300L-1 counterweight slabs fit the GMK5180-1, GMK5200-1, GMK5250L and GMK6300L
    (`https://www.manitowoc.com/company/news/manitowoc-launches-gmk6300l-1-successor-groundbreaking-grove-gmk6300l`);
  - Manitowoc's 2250 and M-250 share the No. 44 boom and No. 133 jib;
  - Manitowoc's MLC counterweight boxes are standardised across models;
  - Tadano's ATF 100-4.1 counterweight fits the ATF 120-5.1.
- **Sharing can stop at a version:** SANY's SCC1000A and SCC1000A-8 inserts and counterweight blocks
  differ in weight and size.
- **Rental software keeps the two apart.** DynaRent keeps a crane's fixed serialized parts with the
  crane and holds attachments per crane type (`https://staedean.com/rental/industry/crane-rental-software`).
  Wynne and HireHop offer serialized or bulk items.
- **Kit is traded on its own.** A dealer sells used LR 1300 counterweights as separate stock fitting three
  models (`https://www.bigge.com/crane-parts/attachments/liebherr-lr-1300-counterweights-5-ton-stack/lr1300cw/`).

**D. Nesting.** Kit is assembled from kit:

- a luffing jib from its foot, sections, head and struts;
- a Liebherr derrick from a mast, a ballast tray, a pallet on the tray and plates on both
  (`https://www.liebherr.com/en/usa/products/mobile-and-crawler-cranes/crawler-cranes/lr-crawler-cranes/technologies/derrick-and-counterweight.html`).

For transport, luffing-jib sections travel inside boom sections, so a truckload is not the same thing
as a configuration. Recorded as a tree, the derrick alone would need four levels below the crane. Kit is
therefore recorded flat, and how it is assembled is the configuration's business (8A).

**E. Tackle.**

- **The law in India, as first found.** The Factories Act 1948 and the BOCW Central Rules 1998 have
  since been repealed or superseded; section H1 has the current position, in which the same substance
  continues.
  - Factories Act 1948, section 29 (`https://indiankanoon.org/doc/640593/`): lifting machines and
    every chain, rope sling, hook, shackle, swivel and pulley block are thoroughly examined by a
    competent person at least every 12 months, and each is marked with its safe working load and an
    identification mark;
  - Form 10 (state rule 60): the register gives each item's "distinguishing number or mark";
  - BOCW Central Rules 1998 (`https://indiankanoon.org/doc/49335675/`): Rule 61 requires every lifting
    appliance and piece of loose gear to be marked with its safe working load and identification;
    Rule 70 requires lifting gear to be examined every 12 months and retested every 5 years.
- **Elsewhere:** OSHA 1910.184 and LEEA require each sling to be identified.
- **What makers supply:** Manitowoc lists counterweight-handling pendants and links as crane equipment
  (MLC90A-1). Grove fits counterweight hydraulically. No maker researched supplies general slings or
  shackles.

**F. Outrigger pads and mats.**

- **Pads:**
  - Liebherr LTM 1220-5.2 pads are fixed to the outriggers
    (`http://www.manualsdir.com/manuals/520675/liebherr-ltm-1220-52.html?page=4`);
  - Grove's product guides describe four self-stowing pads as standard;
  - SANY lists pads as optional equipment;
  - a trade glossary says a pad generally travels with the machine, while a mat is sized for a lift
    (`https://dicausa.com/industry-terms/`).
- **Mats:** OSHA 1926.1402 makes supporting materials the site's concern.

**G. PBL's own fleet.** PBL's website equipment list (dated; the owner says it is current to within tens
of units) was read for counts only. It is not kept in the repository.

| Cranes on the list | Units | Models |
| --- | --- | --- |
| Pick-and-carry | 49 | 3 |
| All-terrain | 16 | 14 |
| Truck-mounted | 12 | 6 |
| Crawler | 7 | 7 |
| Mobile tower | 1 | 1 |
| **Total** | **85** | **31** |

- **Pick-and-carry cranes carry practically no detachable kit.** That leaves about 28 models and 36
  units that do.
- **Six of those models have more than one unit** (two to four each). For the others, the model's kit
  is one crane's kit, so sharing by model covers both cases with one rule.
- **Makes:** XCMG, SANY, Liebherr, Demag, TIL, Manitowoc, Tata Hitachi and Kobelco. The research
  covered three of them; its findings on standards and on sharing apply to all.

**H. The statutory position in India (second round, 26 September 2026).** Four further checks were
made, at the owner's request: labour and safety law, road transport, GST, and Indian Standards and BIS.
They record what was found and how certain it is. None of it is legal advice, and three points need
PBL's tax adviser (H3).

**H1. Labour and safety law is changing now.**

- **The Acts are repealed.** The Occupational Safety, Health and Working Conditions Code 2020 came into
  force on 21 November 2025. Its section 143 repeals the Factories Act 1948, the BOCW Act 1996, the Dock
  Workers Act 1986 and the Mines Act 1952. Rules made under them continue until they are replaced.
  Sources: `https://ksandk.com/labour-employment/all-four-labour-codes-enforced-from-21-november-2025/`,
  `https://www.bdo.in/en-gb/insights/alerts-updates/alert-implementation-of-labour-codes-key-provisions-notified-effective-21-november-2025`.
- **Central rules.** The OSH (Central) Rules 2026 (G.S.R. 345(E), 8 May 2026) supersede the BOCW Central
  Rules 1998, the Dock Workers Rules 1990 and the Mines Rules 1955 where the central government is the
  authority (`https://www.taxheal.com/occupational-safety-health-and-working-conditions-central-rules-2026.html`).
- **States differ.**
  - Gujarat's OSH Rules 2025 are in force and replace the Gujarat Factories Rules 1963 and the Gujarat
    BOCW Rules 2003. Its Forms 37 and 38 recognise competent persons
    (`https://www.lawrbit.com/wp-content/uploads/2025/11/gujarat-occupational-safety-health-and-working-conditions-rules-2025.pdf`).
  - Maharashtra has drafts only (April and May 2026), so its old rules, with Form 10, probably continue.
  - The Dock Workers Regulations 1990 probably continue.
- **The substance that survives in every regime found.** The OSH Code itself has no lifting section, and
  the detail is in rules and standards. The rules still standing - BOCW rules 56, 57, 61 and 70 where not
  replaced, and Dock Workers Regulations 41, 42, 48 and 52 - keep the same pattern:
  - each lifting appliance and each piece of gear carries its safe working load and an identification
    mark;
  - a competent person the state recognises tests it before first use, after repair or alteration and
    every 5 years, and examines it thoroughly every 12 months;
  - chains are checked monthly and wire rope every 3 months;
  - certificates and a register are kept for at least 5 years;
  - a crane whose safe load varies with radius has an automatic safe load indicator, or a table of safe
    loads;
  - operators are at least 18, trained for the appliance, and medically examined.
- **Not confirmed:** the lifting text of the OSH Central Rules 2026, Gujarat's examination intervals
  and forms, and Maharashtra's final rules.
- **Consequence for the Eligibility foundation.** The examination rules - intervals, forms, who may
  examine - must be held as data for each jurisdiction (central, each state, ports, mines), not written
  into code, because they are changing now.

**H2. Road transport.**

- **Mobile cranes are "construction equipment vehicles"** (CMVR rule 2(ca)). They need registration,
  insurance, a pollution-under-control certificate and road tax. A fitness certificate and a permit are
  needed only if the crane is registered as a transport vehicle. The documents are carried on the crane,
  and electronic copies are accepted (rule 139). Sources: `https://indiankanoon.org/doc/43734172/`,
  `https://indiankanoon.org/doc/785258/`.
- **Crawler cranes** probably are not motor vehicles.
- **Over-size and over-weight loads** need permission: from MoRTH on national highways
  (`https://morth-owc.nic.in`), from the state on its roads. The permission records each load's size
  and weight, and the load per axle. Axle limits are set by S.O. 3467(E) of 2018; dimensions by rule 93.
- **Unsettled:** which driving-licence class covers a crane (courts and states differ). No Indian rule
  was found on a crane travelling with or without its counterweight.

**H3. GST.**

- **Every trip needs papers.** Moving own equipment or kit to a site needs a delivery challan (CGST rule
  55: description, HSN, quantity, value), and an e-way bill for each consignment over ₹50,000, both ways.
  Source: `https://www.gstcouncil.gov.in/sites/default/files/2024-02/electronic-way-bill-050819.pdf`.
- **No tax is due on the move itself** (Circular 21/21/2017-GST). But a Maharashtra advance ruling
  (Sanghvi Movers, 2018) taxed moving a crane to a branch registered in another state, for that branch
  to hire it out
  (`https://gstcouncil.gov.in/sites/default/files/AAR/mah_aar_43_2017-18_b-50_15.06.2018_sml.pdf`).
- **For PBL's tax adviser:**
  - which value to declare - no circular exists, and practice is book value;
  - whether a crane driven on the road needs an e-way bill;
  - the HSN codes for hook blocks, shackles and counterweight (8431 49, 8425, 7312, 7315 or 7326;
    cranes 8426 41, 8426 49 or 8705 10).

**H4. Indian Standards and BIS.**

- **The standards are voluntary; the intervals come from the labour rules.**
  - IS 4573 (mobile cranes): the safe working load is stamped on hook blocks; a load/radius plate and
    an automatic safe load indicator are required.
  - IS 13367-1 (safe use): major components carry an identification mark, and attachments are marked
    with their safe working load and weight.
  - IS 14473-1: cranes are inspected at least yearly.
  - IS 2762 (wire rope slings): each carries a unique number tied to its certificate, its safe working
    load, and its month and year of manufacture.
  - IS/ISO 2415 (shackles) and IS 15560 (hooks) set their marking.
  - IS 12735: slings are examined at least every 6 months.

  Sources: `https://archive.org/details/gov.in.is.13367.1.1992`,
  `https://archive.org/details/gov.in.is.2762.2009`.
- **One binding certification order.** The wire-rope Quality Control Order 2024 (S.O. 2581(E), in force
  from 1 December 2024) requires ropes to IS 2266 to carry the ISI mark. The BIS Act forbids hiring or
  storing notified goods without it, so replacement ropes must be ISI-marked
  (`https://www.teamleaseregtech.com/updates/article/33255/steel-wires-or-strands-nylon-or-wire-ropes-and-wire-mesh-quality-contr/`).
  Web slings came under a textiles order from April 2025; this is not verified.
- **Customers add their own standards:** NTPC's material-handling standard, and OISD-GDN-192 in IOCL
  tenders. Their texts were not read.

**H5. What this changes in ERT-2.**

- **Nothing in the law needs a new kind of record in ERT-2.** It confirms the ones planned: a piece's
  own mark; tracking one by one where pieces are examined; rated capacity per model.
- **Two small additions, agreed (Q13):** weight on every kind of kit, and the maker's part number on a
  model.
- **Everything else is recorded for the package it belongs to**, in `DEFERRED_REQUIREMENTS.md`,
  "Statutory requirements found with ERT-2".

---

## 3. Authority and required reading

What this design relies on, per PBL's internal working instructions "Reading discipline". Each was read in full unless a section is
named.

- **ERT-1 design:** `docs/agent/slices/ert-1-plum-machines-into-the-equipment-reference.md`, in full -
  the asset table, part classes, links, sections 4, 5, 7, 8, 12 and 15, and refinements 1 to 19.
- **Contracts:**
  - `docs/agent/contracts/equipment-reference-api-contract.md` - in full;
  - `docs/agent/contracts/resource-master-reference-contract.md` (`RMR-001`, APPROVED), with its ADR-032
    and ADR-037 notes - in full;
  - `docs/agent/contracts/resource-planning-assignment-contract.md` (`RPA-001`) and
    `docs/agent/contracts/eligibility-assignment-contract.md` (`ELA-001`) - in full. Neither names kit,
    and ERT-2 changes neither. 8A (the BOM) and the Eligibility foundation (examination of tackle and
    hook blocks) consume what ERT-2 records.
- **Decisions and backlog:**
  - ADR-037 and its refinement of 25 September 2026, in `docs/agent/ARCHITECTURE_DECISIONS.md` - in
    full;
  - the asset hierarchy record of PR #70 (`cd9debe`): `DEFERRED_REQUIREMENTS.md` "Asset component
    hierarchy" (as ERT-1 amended it), and `FUTURE_SLICES.md` 8A and 8E;
  - `FUTURE_SLICES.md`: "Equipment Reference transformer ... ERT-1 and ERT-2", 8A, the Eligibility
    foundation, 8E;
  - `DEFERRED_REQUIREMENTS.md`: "Plum's machines: what ERT-1 left out", "Resource requirements and the
    Equipment Reference", "Equipment documents";
  - `docs/agent/slices/wrr-001-resource-requirement-foundation.md` - "Part classes later".
- **Source and architecture:**
  - `docs/reference/erp-source-extracts/TOOLS_AND_ASSET_ANNEXURES_EXTRACT.md` - in full: FRS 3.1,
    Annexure-11(A) and 11(B), and "Tool Master vs Physical Tool Instance Reconciliation";
  - `MODULE_BOUNDARY_OWNERSHIP_MATRIX.md` - the Equipment Master, Equipment Reference and Resource
    Catalogue rows;
  - `EXTERNAL_DEPENDENCY_REGISTER.md` - the Plum Equipment Master row.
- **The code ERT-1 left:**
  - migrations `20260908_0042` and `20260908_0041` (version 1);
  - `equipment_reference/contract.py`;
  - `services/machines.py`, `services/models.py` and `services/common.py` (`check_can_fit`,
    `write_derived_facts`, `_still_fits`, `rederive_asset`);
  - `plum_report.py` (`_closing_links`, `_pair_proposals`);
  - `repository.py` (`earliest_fitting_date`, `list_unfitted_part_ids`, `sync_part_not_fitted`);
  - the Equipment pages;
  - `backend/tooling/smoke_data/cleanup.py` (equipment provenance and refusals).
- **Outside the repository:** both rounds of research in section 2 - makers and standards; then Indian
  labour, road-transport and GST law, and Indian Standards - and PBL's website equipment list (counts
  only).
- **ADRs:** ADR-013 (source guidance is directional), ADR-023 (a repeated request has one effect),
  ADR-030, ADR-037.

---

## 4. What it builds

1. **Kinds of kit in the structure.** Version 3 adds the kit kinds of Q1 as part classes, used by no
   business line, so none is ever offered where Operations asks for machines. Each is marked **kit** for
   cranes, and **one by one** or **counted** (Q3). Two capabilities are added, length (m) and weight
   (t); rated capacity (t) is reused.
2. **Kit models, each naming the crane models it fits.** They are recorded on the existing Models page,
   in a kit kind, with their ratings (Q4, Q12).
3. **Pieces of kit.** A piece is added from a crane's page: one piece, several alike, or a counted set,
   of a kit model that fits that crane's model. Pieces are changed and retired on their own page.
4. **A crane's page shows its model's kit.** It lists each kit model fitting the crane's model, the
   pieces held, and how many active cranes share them.
5. **Kit that fits no active crane is shown**, so kit left behind when the last crane of a model is sold
   is noticed (Q7).
6. **The depth setting**, default 3, kept with the structure (Q9). A fitted part may carry fitted parts
   where the structure allows it, never deeper than the setting.

---

## 5. The records

```text
Class              a kind of kit is a part class, as Crane carrier is        + tracked one by one or counted
Part fit           which kinds a class of machine takes                      + fitted or kit;
                                                                               + a part class as parent (depth)
Structure version  each version of the structure                             + the depth setting
Model              one kind of piece: maker, name, class, type, ratings      unchanged
Model fit          which crane models a kit model fits                       NEW
Asset              one piece of kit, or one counted set                      + origin; machine number only for
                                                                               Plum's; + quantity; + request key
Link               a fitted part on its machine, dated                       unchanged: kit is not linked
Capability         a piece's own value, with a reason                        unchanged; kit may use it
```

### Why ERT-1's records carry kit

| ERT-1 record | What it already does | What kit needs in addition |
| --- | --- | --- |
| `equipment_asset`, kind `PART` | one physical item of a part class, with the platform's identity (`EQ-`), a model, a serial number, a year of manufacture, versions and events | an origin (the platform, not Plum), no Plum machine number, and a quantity for a counted set |
| `equipment_class`, kind `PART` | a kind of part with its own types, capabilities and ratings, offered to no business line | whether its pieces are tracked one by one or counted |
| `equipment_part_fit` | which part classes a class of machine takes | whether they are fitted or kit; a part class as parent, for the depth rule |
| `equipment_model`, `equipment_model_capability` | a model in any class, with rated values, on the Models page | nothing |
| `equipment_asset_capability` | a machine's own value, with a reason | nothing; a piece may use it where its class has capabilities |
| `equipment_taxonomy_version` | each version of the structure, with its source | the depth setting |

### The one new record, and why nothing existing carries it

`equipment_model_fit`: a kit model and a crane model it fits, one row for each.

- `equipment_part_fit` is a rule between **classes**: hook blocks go on cranes.
- `equipment_model_source_key` maps Plum's names to models.
- Nothing links a **model to a model**: this 100 t block fits the SCC1000A. The fact is many-to-many
  (section 2, C), so it needs a table, not a column.

### Why kit is not linked to a crane

A dated link says "this piece is on that crane". Pieces of shared kit move between the cranes of a model
from job to job (Q6), so that fact would be wrong within weeks, and keeping it right would mean a
Fleet Admin entry after every job. What went where is recorded once, by 8A, per trip, in the BOM, which
the owner decided on 24 September is never stored in the hierarchy.

So:

- kit is held for the crane models it fits;
- **fitted** parts, which stay with one crane - its carrier, and later upperworks and crawlers - keep
  ERT-1's dated links;
- the depth setting governs those links.

This also keeps nesting out of the records. A derrick recorded as a tree would need four levels below
the crane (section 2, D). Recorded flat, it is a set of pieces held for a model, and assembling them is
the configuration's business.

### What a piece of kit carries

- **Identity.** It has the platform's public id and `EQ-` reference, as every asset. It has **no Plum
  machine number**: `origin_code` is `PLATFORM`, and the number is empty. Plum's machines and carriers
  keep `PLUM` and their number, unchanged.
- **Kind, type and ratings** come from its **model**, which is required (Q4). The class is the model's
  class. Every kind is measured by its weight as well as its key measure - length or rated capacity -
  and a model may carry the maker's part number (Q13). Capabilities are read from the model when asked
  for, as for machines. A piece may hold its own
  value, with a reason, where its class has capabilities - a hook block de-rated after an examination,
  say.
- **Its number** (optional, Q5): the maker's serial or plate number, or the number stencilled on it.
  This reuses `serial_number`; year of manufacture reuses `year_of_manufacture`. A counted set has
  neither.
- **Quantity:** 1 for a piece tracked one by one; the count for a counted set (Q3).
- **Where it belongs:** the crane models its model fits. It needs no field of its own.
- **Status:** `ACTIVE` or `RETIRED`. Retirement records a reason and a date (Q8).

### Kit held for a crane model

- **The kit held for crane model M** is every active piece whose model fits M.
- **The cranes sharing it** are the active machines whose model is M.
- **A kit model fits no active crane** when none of the models it fits has an active machine. It is
  shown, not flagged: nothing in Plum is wrong. This is how kit left behind when the last crane of a
  model is sold is noticed (Q7).
- **A crane whose Plum name is not yet mapped to a model** (`MODEL_NOT_MAPPED`) shows no kit, with the
  words "Map its model to see its kit."

### The rules

- **What a kit model may fit.** Its class must be one the structure marks as kit for a class of
  machine. It fits at least one crane model, each of a class that takes its class as kit. Both are held
  by the database, as ERT-1's composite keys are.
- **A kit model is the platform's, never Plum's.**
  - A Plum model name cannot be mapped to a kit model, and no machine can be corrected to one (`422`).
  - If Plum ever lists kit, that comes back for a decision (section 13).
  - A crane model that kit fits cannot change its class while those fits exist, as a model used by
    machines cannot.
- **Kit is not fitted.** A kit class cannot be linked to a machine: fitting takes only classes the
  structure marks as fitted.
  - "Belongs to no machine" (`PART_NOT_FITTED`) is raised only on fitted classes, never on kit.
  - ERT-1's rules for the carrier are unchanged: one fitted part of a class per machine, and dates that
    never overlap.
- **Depth.** A machine is level 1, its fitted parts level 2, their fitted parts level 3.
  - A link is refused when the parent's level plus the depth of what hangs below the child would exceed
    the setting.
  - A part class may be a parent only where the structure has a fitted part fit under it. Version 3 has
    none.
  - The fits contain no loop and no chain longer than the setting. A new version may not lower the depth
    below the deepest chain of open links, and the migration refuses one that does.
- **Counted or one by one.**
  - A quantity above 1 is refused on a class tracked one by one.
  - A number (serial number) is refused on a counted set.
- **Only kit is created on the platform.** Plum's machines and carriers cannot be, and they still retire
  only by report. A piece of kit has no Plum value, so it is never "corrected" (ERT-1 section 5B). Its
  facts are the platform's (ADR-037 refinement, point 1).

### Room for change (owner's question, 26 September 2026)

The owner asked whether the design should leave buffers for future variability. The rule applied: **leave
room only where a later change would be expensive.**

- **Cheap later.** What is data - rows of the structure, lists of models - grows by adding a row. Empty
  slots made in advance would only clutter the screens.
- **Expensive later.** How records relate to each other is expensive to change, so that is where room is
  left now.

| What may vary | How the design takes it | Cost if it comes later |
| --- | --- | --- |
| A new kind of kit (auxiliary hoist, superlift attachment, excavator bucket, axle accessories) | A row of the structure | Small: a new structure version, no table or code change |
| New types or measures within a kind | Rows of the structure | Small, as above |
| How many kit models a crane model has | No limit | None |
| Kit fitting several crane models, across makes | Many-to-many from the start (Q12), though the input was "same model" | None: room left now |
| Deeper nesting of fitted parts | The depth setting | Small: a new structure version |
| Pieces coming from another source than Plum or the platform | `origin_code` is a list | Small: one more code |
| Makers rating kit in feet and US tons (Manitowoc: 10, 20 and 40 ft inserts, a 300 US ton block) | Each measure is stored in one unit, metres or tonnes (WRR-001's rule); the Fleet Admin converts when recording the model | Small: a feet and US tons entry helper on the model form, if it proves error-prone |
| Counted for some makes, one by one for others (Q3) | Tracking is set per kind | Moderate: tracking moves from kind to model (section 13) |
| Recording which crane holds a piece between jobs | Not recorded (Q6) | Moderate: belongs with 8A's BOM (section 13) |
| Adding a kind without a developer | Not possible: the structure changes by migration | A maintenance screen for the structure, already deferred. Worth building if kinds start changing often |

**Agreed (Q14):** **"Other, with a note"** is added to the retirement reasons of Q8. A reason
nobody foresaw - returned to the supplier, transferred within the group - then needs no change. It costs
one code, and the note already exists.

### Authority by phase

| Fact | Phase 1 (now) | Changed on the platform by |
| --- | --- | --- |
| Which kit exists: its model, number, quantity, year of manufacture | **The platform** (Plum lists no kit; ERT-1 comment 5) | the Fleet Admin |
| Which crane models a kit model fits | **The platform** | the Fleet Admin |
| A piece's own ratings | **The platform** | the Fleet Admin, with a reason |
| What went to site with which crane | 8A, per trip | - |
| Examination of tackle and hook blocks, and certificate validity | the Eligibility foundation | - |

---

## 6. How ERT-1's import meets kit

Kit is never in Plum's report and is never linked to a machine, so the report neither creates, changes,
retires nor closes anything of it. Three points need care:

1. **A report cannot reach a kit model.** Mapping a Plum name to a kit model, or correcting a machine's
   model to one, is refused. A report therefore never turns a Plum row into kit.
2. **"Belongs to no machine"** (`list_unfitted_part_ids`, `sync_part_not_fitted`) counts only parts of
   fitted classes. Kit never raises it.
3. **Previews go stale on model changes.** Recording or changing a kit model moves the change count, as
   any model change does, so a waiting preview asks to be refreshed. Nothing a preview shows changes,
   but ERT-1's one rule for models is kept rather than a second one added (DRY). Adding or retiring
   pieces changes nothing a preview is computed from, so it moves nothing.

Pair proposals, closing links and every other step of the import are unchanged.

---

## 7. Screens

No new page and no new URL. Kit lives on the pages ERT-1 built (`/equipment`,
`/equipment/machines/:assetId`, `/equipment/models`), and `routes.tsx` is unchanged. Messages sit beside
the button that caused them, and styling uses `globals.css` classes (CODING_STANDARDS.md section 7).

- **A crane's page** gains a section **"Kit for SANY SCC1000A"**, headed by its model's name.
  - It lists each kit model that fits the crane's model: kind and type, model, key rating (9 m, 3.9 t,
    100 t), pieces held, and a link to them.
  - It says how many active cranes of the model share the kit - "shared by 2 cranes" - and any other
    crane models the kit also fits.
  - For the Fleet Admin, **Add kit**:
    - choose a kit model that fits this crane's model;
    - give how many;
    - give its number and year of manufacture, when adding one piece.

    The words make clear the kit is added to the model's kit, not to this crane.
- **A piece's page** - the machine page for a part, headed "Equipment - kit".
  - It shows its model and ratings, the crane models it fits, its number, year, quantity, status and
    events.
  - For the Fleet Admin: **Details** (number, year, quantity for a counted set, model within the same
    kind); **Own ratings**, where the kind has any; **Retire** (reason, date, note; the note is required
    for "Other").
- **Models page.**
  - The kit kinds are offered as classes, marked "(kit)".
  - A kit model's form asks for the crane models it fits: a choice among the models whose class takes
    that kind.
  - Every model's form gains an optional maker's part number (Q13). A kit model's ratings include its
    weight.
  - The list shows, for each kit model, the models it fits and the pieces held, marking any that fits no
    active crane. For each crane model, it shows its active cranes.
- **Machines list.**
  - The kind filter reads "Machines" or "Parts and kit" (today "Fitted parts").
  - Two filters are added: one kit model's pieces, and the kit for one crane model.
  - "Details to complete" includes pieces tracked one by one that have no number (Q5).

**A screen check fits in twenty minutes**, on a seeded crane model with two cranes:

1. Record a boom insert model and a counterweight model fitting that crane model.
2. From one crane, add four inserts alike and a counted set of six counterweight blocks.
3. See the same kit on the second crane's page.
4. Retire one insert as scrapped.
5. As a read-only user, see the kit with no buttons.

---

## 8. Permissions

No new permission and no new role.

| Permission | Granted to | Allows |
| --- | --- | --- |
| `EQUIPMENT_REFERENCE_READ` (exists) | the six current roles | kit, its models, fits and history |
| `EQUIPMENT_REFERENCE_MANAGE` (exists) | **Admin** (ERT-1 comment 1) | every kit write: kit models and fits, pieces, details, own ratings, retirement |
| `EQUIPMENT_IDENTITY_READ` (exists) | Admin | unchanged: kit has no engine or chassis number |

A piece's own number is shown to every read role, as a machine's serial number is. The screen check and
E2E use `admin1`, and a read-only user for the refusals.

---

## 9. Routes

All routes are under `/api/equipment-reference`. The two new ones are pinned in
`POST_BASELINE_NEW_ROUTES`. `equipment-reference-api-contract.md` is updated with every change.

**New:**

```text
POST /kit                            add pieces of a kit model              201
     {create_request_key, kit_model_public_id, count, serial_number, year_of_manufacture}
POST /machines/{public_id}/retire    retire a piece of kit                  200
     {expected_asset_version, reason_code, note, retired_on}
```

As built, `POST /kit` also names the machine page it is sent from and the versions of that machine and of the
kit model, and `retire` takes a `count` for a counted set (section 18: refinement 2, review round 1).

- **Add pieces.**
  - The model must be a live kit model.
  - For a class tracked one by one, `count` pieces are created, each its own record, and
    `serial_number` is accepted only when `count` is 1. For a counted class, one record of quantity
    `count` is created.
  - `count` is 1 to 50.
  - The same `create_request_key` again returns what the first request made, with `event: null`
    (ADR-023).
    **Reconciled 8 October 2026 (TB-1 TB1-102 part b):** only the very same request is answered so; the key with
    any other request is `409` (`equipment-reference-api-contract.md`, Conventions).
- **Retire.**
  - Kit only: a Plum machine or carrier is refused (`422`, "Plum retires this machine; correct its
    status if Plum is wrong").
  - The reason is one of `SCRAPPED`, `LOST`, `SOLD`, `RECORDED_BY_MISTAKE` or `OTHER` (Q14). The note is
    free text, and required with `OTHER`.
  - `retired_on` may not be in the future.
  - Retiring a retired piece returns it unchanged.

**Changed, backward compatible:**

```text
POST /models, PUT /models/{public_id}     a kit model: fits_model_public_ids[] (one or more; refused
                                          on any other model); any model: maker_part_number (optional,
                                          Q13)
GET  /models                              a kit model's fits, pieces held, fits_no_active_crane;
                                          a crane model's active cranes
PUT  /model-mappings                      refuses a kit model
POST /machines/{public_id}/corrections    refuses MODEL corrected to a kit model
GET  /machines/{public_id}                a crane: kit[] - each kit model fitting its model, with pieces
                                          held - and the number of active cranes sharing it;
                                          a piece: origin_code, quantity, the models it fits
GET  /machines                            machine_number null for kit; origin_code; quantity; filters
                                          kit_model_public_id and fits_model_public_id
PUT  /machines/{public_id}/details        a piece: also quantity (counted) and model (same class)
PUT  /machines/{public_id}/capabilities   also a piece whose class has capabilities
POST /machines/{public_id}/fitted-parts   refuses a kit class; a part may be the parent where the
                                          structure has a fitted part fit and the depth permits
GET  /structure                           the depth setting; each class's tracking; each fit's kind
```

Writes take the version they were made against and refuse a stale one (`409`), as every ERT-1 write does.

---

## 10. Events

No new event name. ERT-1's events carry kit, with a few added fields.

| Event | For kit |
| --- | --- |
| `EQUIPMENT_ASSET_REGISTERED` | each piece added; adds `origin_code: PLATFORM`, `class_code`, `model_public_id`, `quantity` |
| `EQUIPMENT_ASSET_RETIRED` | adds `reason_code`; the note is the event's reason, not its payload |
| `EQUIPMENT_MACHINE_DETAILS_SET` | changed fields by name, `quantity` and `model` among them |
| `EQUIPMENT_MACHINE_CAPABILITY_SET` | as for machines |
| `EQUIPMENT_MODEL_RECORDED`, `EQUIPMENT_MODEL_CHANGED` | a kit model's fits: the crane models' public ids, added and removed |

As in ERT-1, payloads carry public ids, references, codes, versions, counts and dates only. They never
carry a piece's number, a Plum value or free text.

---

## 11. Data, module and migration

All in `backend/app/modules/equipment_reference/`. No other module's table is read or written, and
nothing takes a `crm_` prefix. The migration is **`20260908_0043_equipment_detachable_kit`**, parent
`20260908_0042` (Q11). It follows the 0033 to 0042 convention: the version-3 rows are spelled out, not
imported, so the revision stays a frozen snapshot.

**Structure, version 3:**

- `equipment_taxonomy_version.component_depth`, not null. Each version records the depth it allowed: 1
  for version 1, 2 for version 2, 3 for version 3. The setting in force is the current version's.
- `equipment_class.tracking_code`: `SINGLE` (default) or `COUNTED`. A machine class is always `SINGLE`.
- `equipment_part_fit.fit_kind_code`: `FITTED` (default, so the carrier's row stays as it is) or `KIT`.
  `ck_equipment_part_fit_parent_kind` is widened to `MACHINE` or `PART`, so a part class may be the
  parent of a fitted part fit. A kit fit's parent is always a machine class.
- Capabilities `LENGTH` (m) and `WEIGHT` (t) are added; `RATED_CAPACITY` (t) is reused. `WEIGHT`
  applies to every kit class, as a measure beside its key one (Q13).
- `equipment_model.maker_part_number`, optional, for any model (Q13).
- The kit classes of Q1 - their types, capabilities, tracking, and fits to `CRANE` as `KIT` - as
  answered.

**Models:**

- `equipment_model_fit` (kit model, crane model), unique together. Composite keys hold three things:
  - the kit model's class fits the crane model's class as `KIT`;
  - the crane model's class is a machine class;
  - neither model can change class while the row exists.

**Assets:**

- `equipment_asset.origin_code`: `PLUM` (default, every existing row) or `PLATFORM`.
- `machine_number` becomes nullable. A CASE check requires it for `PLUM` and forbids it for `PLATFORM`.
  A `PLATFORM` asset must also be a `PART` of a kit class, have no `registered_by_import_id`, and have a
  request key.
- `equipment_asset.quantity`: not null, default 1, at least 1. It may be above 1 only on a `COUNTED`
  class, and a serial number is allowed only on a `SINGLE` one. The database holds both rules, not only
  the service.
- `equipment_asset.create_request_key` and `create_request_position` (1 to `count`), unique together, so
  "add several alike" is one request with one effect.
- `equipment_asset_link` is unchanged: `FITTED` only.

The composite-key, NULL-safe CHECK and trigger rules of WRR-001 and ERT-1 apply unchanged. A kit model's
capabilities pass the same capability trigger.

**Code**, each change beside the rule it extends (DRY):

- `services/kit.py`, a new concern module (CODING_STANDARDS.md, "When a service outgrows one file"),
  adds and retires pieces and builds a model's kit. It imports `common` and nothing else under
  `services/`.
- `services/models.py`: a kit model's fits. Mappings and corrections refuse kit models, and a class
  change is refused while fits exist.
- `check_can_fit`, `_still_fits` and `earliest_fitting_date` read the part fit: fitted classes only, a
  part as parent where a fit allows, and the depth check beside them.
- `list_unfitted_part_ids` and `sync_part_not_fitted` count fitted classes only.
- `services/machines.py`: the kit section of a crane, and a piece's facts, in the existing serializer.
- `contract.py` gains the origin, tracking, fit-kind and retirement-reason codes.

**Consumers are unchanged.** `CanonicalMachine` does not carry kit: 8A adds the read it needs from the
service when it builds the BOM.

---

## 12. Not in this package

| Left out | Where it goes |
| --- | --- |
| The mobilisation BOM - what went to site with which crane, per trip - and checking it back at demobilisation | 8A and 8E |
| Which pieces a configuration needs, and which go on every job (boom foot and head) versus only some (inserts) | 8A, from the types recorded here |
| How kit is loaded for transport: sections nest inside sections (section 2, D) | 8A |
| Outrigger mats, timber and cribbing: site or job equipment | 8A |
| Store-held slings and shackles, and general tools | the inventory integration. Store-held tackle also needs its own identification and examination (section 2, E) |
| The examination register for tackle and hook blocks, and certificate validity | the Eligibility foundation, which will require the mark on each piece (Q5) |
| Fitted parts other than Plum's carriers - upperworks, carbody, crawlers, a boom-foot winch | when Hiring or Maintenance needs them; ERT-1's links carry them, within the depth setting |
| A removable auxiliary hoist as a kind of kit (Grove); kit for machines other than cranes | a later structure version, when needed |
| Pendants, straps and guy rods as separate records | not planned: they go with their section |
| Load charts for configurations, and other equipment documents | "Equipment documents" (`DEFERRED_REQUIREMENTS.md`): a kit model and a piece are a model and an asset, so they attach the same way |
| Which crane a piece came with | not planned: pieces are shared (Q6, Q7) |
| Bringing back a retired piece (Q8) | re-record it; a route if needed |
| A spreadsheet upload of kit (Q10) | not needed at PBL's size |
| Whether a piece came with the machine or was bought separately (FRS 3.1 tags tools "OEM or General") | Fixed Assets and the inventory integration: "build only what Hiring needs" (owner, 24 September 2026) |
| Each part's share of the machine's value, maintenance by part, cost roll-up, tyres, batteries | Fixed Assets, Maintenance, Inventory (owner, 24 September 2026) |
| A maintenance screen for the structure and the depth setting | with the structure's own screen |
| Transportation's hydraulic-axle accessories - spacer beams, bolsters, stands, beams - which are shared across makes and counted | Transportation; the same records carry them (kit kinds that fit axle classes) |
| Plum listing kit | section 13 |
| The statutory requirements of section 2, H: the examination register and its rules per jurisdiction; a crane's road-vehicle documents; operators' age, training and medicals; each trip's delivery challan, e-way bill and over-size permit, with HSN codes, declared values and transport sizes; ISI-marked wire rope | the Eligibility foundation, 8A, Transportation, Finance and the inventory integration, as listed in `DEFERRED_REQUIREMENTS.md`, "Statutory requirements found with ERT-2" |

Requirements (WRR-001), the Work Orders module and the frozen Slice 6D.1 handoff contract do not change.

---

## 13. What would stop implementation and come back to the owner

- **Plum's report, or its vehicle type master, arriving with kit rows.** Binding them to kit already
  recorded, and deciding which source then wins, is a new decision (ADR-037 refinement, point 1).
- **A kind that must be counted for some makes and tracked piece by piece for others** - counterweight,
  if some pieces are numbered (Q3). Tracking would then move from the class to the model.
- **A need to record which crane holds which piece between jobs.** That would reverse Q6, and belongs
  with 8A's BOM rather than in the hierarchy.

---

## 14. Differences from earlier records (recorded per ADR-013)

| Earlier record | ERT-2 | Why |
| --- | --- | --- |
| Hierarchy record (24 September): fitted parts and detachable kit "both recorded as the machine's children"; "an insert left at the yard still belongs to its crane" | Kit is held for the crane models it fits, not by a crane; the machine's children are its fitted parts | Owner, 26 September (Q6, Q7); the research (section 2, C) |
| Owner, Q6: kit is shared "for the same model" | For the exact crane models it fits, one or more | The research, which the owner made authoritative: sharing crosses models, and can stop at a version |
| Hierarchy record: "two kinds of child: a part tracked on its own ... and a counted accessory" | One asset table; a counted set is one record with a quantity; the class decides (Q3) | One column, not a second structure |
| Hierarchy record: "numbered counterweight" as tracked on its own | Counterweight counted (Q3, answered as recommended) | Makers and dealers identify counterweight by weight and model (section 2, B) |
| Hierarchy record: kit includes "tackles and lifting accessories"; Annexure-11(B) lists shackles and slings as tools | The crane's own tackle is kit, store-held tackle is inventory, and both are identified piece by piece | Q2; the lifting rules, first found under the Factories Act and Form 10, now under the OSH Code and the rules that survive it (section 2, E and H1) |
| First proposal: outrigger pads as counted kit | Not kit | Pads are fixed or self-stowing and travel with the crane (section 2, F) |
| First proposal: kit linked to a crane, taken off and added | No link; shared by model | Q6 |
| ERT-1 section 4: "ERT-2 adds detachable kit, counted accessories and the depth setting" | All three; the depth setting governs fitted parts | Kit recorded flat (section 5) |
| ERT-1 section 15: "creating a machine Plum does not hold" is out | Still out: kit is not a machine. Platform-origin assets are kit only | ERT-1 comment 5 |
| ERT-1: a part has no own capability values | A piece of kit may, where its class has capabilities | A de-rated hook block |
| ERT-1: every asset has a Plum machine number | Only Plum's; kit has none (`origin_code`) | The machine number is the key Plum and the platform share |
| Owner: depth "a setting" | Kept with the structure's version, changed with it | The depth matters only with a fit at that level, itself a structure change |
| FRS 3.1: major assemblies tracked as child assets | Crawlers, upperworks and carbody are fitted parts, left for when needed | "Build only what Hiring needs" |
| FRS 3.1: tools tagged OEM or General | Not recorded for kit now | Directional (ADR-013); "build only what Hiring needs" |
| FRS extract, "Tool Master vs Physical Tool Instance" | The model is the type, and a record is one piece or one counted set | Consistent with the directional guidance |

---

## 15. Tests and checks

- **Structure:**
  - version 3 loads, with a depth of 3;
  - every kit class is a `PART` class of no business line, fitting `CRANE` as `KIT`, and measured by
    weight (Q13);
  - the carrier's fit stays `FITTED`;
  - the fits hold no loop and no chain deeper than the setting;
  - the empty-database migration reaches the single head, and downgrade removes version 3 cleanly.
- **Kit models and fits:**
  - a kit model needs at least one crane model, each of a class that takes its kind as kit; others are
    refused, by the service and by the database;
  - fits on any other model are refused;
  - a crane model with fits cannot change class;
  - mapping a Plum name to a kit model, and correcting a machine's model to one, are refused;
  - a maker's part number is kept on any model, and is optional (Q13).
- **Adding pieces:**
  - several alike make that many records; a counted set makes one of that quantity;
  - a serial number is refused on a counted set, or with a count above 1;
  - a quantity above 1 is refused on a one-by-one class, by the service and by the database;
  - a retired kit model is refused;
  - the same request key twice has one effect;
  - no Plum machine or carrier can be created.
- **The shared kit:**
  - two cranes of one model show the same kit, and the same count of cranes sharing it;
  - a kit model fitting two crane models shows on both;
  - retiring the last active crane of a model marks its kit models "fits no active crane", and
    reactivating the crane clears the mark.
- **Retirement:**
  - kit only;
  - the reason is in the event;
  - `OTHER` without a note is refused (Q14);
  - a date in the future is refused;
  - retiring twice has one effect;
  - a retired piece is not counted as held.
- **Fitted parts and depth:**
  - a kit class cannot be fitted;
  - ERT-1's carrier rules are unchanged;
  - with a test fit under a part class, level 3 is allowed and level 4 refused;
  - "belongs to no machine" is never raised on kit.
- **With the import:**
  - kit is never new, changed, missing or retired by a report;
  - a kit model's change makes a waiting preview stale; adding or retiring pieces does not.
- **Reads:**
  - kit shows `origin_code`, a null machine number and its quantity;
  - a crane's `kit[]` follows its model;
  - responses for Plum's machines and carriers are otherwise unchanged.
- **Permissions:** kit is read by every read role; every kit write is refused to every role but Admin.
- **Events:** payloads carry no piece number and no free text.
- **Smoke data and cleanup:**
  - `equipment-plum-import` and the core bundle's seventh record set gain a kit model fitting an
    invented crane model, and pieces of it;
  - cleanup takes the run's kit models by the manifest, as ERT-1's models are taken, and pieces by the
    run's kit models;
  - it deletes their fits;
  - it refuses, deleting nothing, when a kit model the run did not make fits one of the run's crane
    models.
- **E2E:** Admin records a kit model fitting a crane model, adds several alike and a counted set from one
  crane, sees them on a second crane of the model, and retires one. A read-only user sees kit and no
  buttons.
- **Full gate:**
  - full backend regression, the frontend gate and E2E;
  - the migration from an empty database;
  - the frozen handoff contract's hash, before and after;
  - independent review;
  - your screen check, with the steps in the chat.

---

## 16. Shared files this package touches

- `backend/tests/fixtures/post_baseline_tightened_routes.py`: two new routes. Read it by eye after any
  merge.
- `backend/tooling/smoke_data/`: scenario, builders, cleanup and status.
- `e2e/tests/equipment-import.spec.ts`, or a sibling spec.

Not touched:

- `backend/app/main.py`: the router is already registered;
- `frontend/src/routes.tsx`: no new URL;
- `backend/app/modules/authorization/contract.py`: no new permission.

Documents updated when it is built:

- `equipment-reference-api-contract.md`;
- this design's implementation record, and an acceptance record;
- `FUTURE_SLICES.md` (ERT-2, 8A) and `DEFERRED_REQUIREMENTS.md` ("Asset component hierarchy", "Plum's
  machines: what ERT-1 left out");
- the Equipment Reference row of `MODULE_BOUNDARY_OWNERSHIP_MATRIX.md` ("and the detachable kit held for
  each crane model");
- `NEXT_STEPS.md` and a continuity note.

ADR-037 needs no new text: kit is a fact Plum does not hold, which its refinement's point 1 already
gives to the platform.

---

## 17. The owner's requests during implementation (26 September 2026)

### Fixed Assets, for machines and kit alike

> Build it in a way that it can be part of the fixed asset module too, either with links or any other
> appropriate way, when we get to that, which won't be any time soon. Equipment as well as kits.

The Fixed Assets module will own value, capitalisation, depreciation and disposal. It will link its own
records to the Equipment Reference's by public id. So nothing Fixed-Assets-specific is stored here. What
this package guarantees, so those links hold:

- **Identity is permanent.** A machine's, a part's and a piece's public id and `EQ-` reference never change
  and are never reused. Nothing is deleted: pieces are retired, Plum's machines retire by report.
- **Every change of state is an event**, with its day and, for a retirement, its reason: registered,
  changed, retired. Fixed Assets can replay them.
- **Each "add kit" is one lot**, recorded together under one request key and one event per record, with
  `records_in_lot`: pieces bought together stay identifiable as one acquisition.
- **A counted set shrinks only by retirement.** "Retire 2 of these 6 plates: lost" leaves 4, and the event
  says how many left, when and why. A set's count may be raised in its details, to correct a count recorded
  too low, but never lowered there. So every disposal Fixed Assets must account for is dated and explained.

Which crane a piece was capitalised with is Fixed Assets' own fact, for its own link records - kit is shared
by model here (Q6, Q7). Recorded in `DEFERRED_REQUIREMENTS.md`, "Fixed Assets: what the Equipment Reference
keeps for it".

### Trailer beds on prime movers

> Also, think about how beds attached to trailers will be treated.

A bed (Plum's "TRAILER BED", the platform's Trailer class) is **its own machine**, not a part or kit of the
prime mover: it is registered on its own, carries its own statutory documents, and Plum already lists beds
as separate machines. Attaching one to a prime mover is a dated **coupling between two machines**:

- one prime mover pulls at most one bed at a time, and a bed is coupled to one prime mover at a time;
- neither machine's identity changes, and retiring either ends the coupling;
- the coupling is a new link kind, `COUPLED`, in ERT-1's dated link table beside `FITTED`, with history
  kept as for a carrier;
- Plum's `BedNo` on each prime mover - already kept in its source binding (ERT-1, Q7) - lets the Plum import
  propose couplings the way it proposes carrier pairs, for the Fleet Admin to confirm.

It is Transportation's (WRR-001, Q15; ERT-1, Q7), so nothing is built now. Nothing in ERT-2 stands in its
way: the link kind is a list, and the fitting rules judge `FITTED` links only. Recorded in
`DEFERRED_REQUIREMENTS.md`, "Trailer beds and prime movers".

---

## 18. Implementation record (26 September 2026)

Built on `hiring/ert-2-detachable-kit` in worktree `<a separate worktree>`, from the design commits on
`main` at `6116c4d`. Migration `20260908_0043`, parent `20260908_0042`.

### What exists now

```text
backend/alembic/versions/20260908_0043_equipment_detachable_kit.py
        structure version 3 (depth, tracking, fit kind, LENGTH and WEIGHT, four kinds of kit);
        equipment_model_fit; maker_part_number; kit columns on equipment_asset; the tracking trigger;
        the structure check (no loop, no chain deeper than the setting)
backend/app/modules/equipment_reference/
        services/machines.py   add_kit, retire_piece; kit details and own ratings; a machine's kit section
        services/models.py     kit models' fits; no mapping or correction to a kit model
        services/common.py     check_can_fit and _still_fits read the part fits, with the depth check
        plum_report.py         a closing link judged by the part fits, as _still_fits judges it
        service.py, repository.py, schemas.py, contract.py, routes.py (POST /kit, POST /machines/{id}/retire)
backend/tooling/smoke_data/            a second crane model, two cranes, and kit held for it, in
                                       equipment-plum-import and the core bundle; cleanup of kit by its model
frontend/src/pages/equipment/          kit on a machine's page, a piece's page, retire; kit models on the
                                       Models page; the list's kit filters; equipmentState.ts's kit rules, tested
frontend/src/styles/globals.css        one class, .choice-list (a kit model's crane models)
e2e/tests/equipment-kit.spec.ts        add kit, see it on both cranes, retire a piece; read-only view
docs/agent/contracts/equipment-reference-api-contract.md, resource-requirement-api-contract.md
```

### Refinements made while building (recorded per ADR-013)

None changes an answer of the owner's. Refinement 2 follows the owner's Fixed Assets request of the same
day (section 17).

| # | Design said | Built | Why |
| --- | --- | --- | --- |
| 1 | A new concern module, `services/kit.py` | Kit writes in `services/machines.py`; kit models' fits in `services/models.py` | Every kit write returns the machine page and reuses its serializer and guards; a separate module would have to import `machines`, which the services rule forbids (CODING_STANDARDS.md, "When a service outgrows one file") |
| 2 | A counted set's quantity changes in its details | Raised only there; lowered only by retiring pieces (`count` on the retire route), with the reason and the day | Section 17: every piece that leaves is dated and explained for Fixed Assets |
| 3 | Retiring a retired piece returns it unchanged | Whatever version is sent | A second click, or a stale page, should not be told someone changed it |
| 4 | "Details to complete" includes pieces tracked one by one with no number | And the filter now says exactly what each summary's `details_missing` says: a machine without its serial number or year, a piece without its number | ERT-1's filter listed Plum parts missing a serial number while their summaries said nothing was missing; the two now agree, and a Plum carrier is no longer listed |
| 5 | - | The list's search also matches a piece's own number | A piece is found by what is painted on it |
| 6 | A crane's page names "any other crane models the kit also fits" | `KitHeldResponse.fits_models` carries every crane model; the page leaves out its own | One simple response; the page decides what to show |
| 7 | A part may carry fitted parts where the structure allows | `check_can_fit`, `_still_fits` and the transformer's closing-link projection all judge a link by the part fits, whatever kind the parent is | One rule in three places; every link ERT-1 can make is judged exactly as before |
| 8 | - | A model's class cannot change while any record uses it - machine, part or piece - and the message says "records" | Pieces are records of their kit model |
| 9 | - | A piece's own values do not move the change count, so waiting previews stay current | A piece is in no report |
| 10 | Smoke data: a kit model fitting an invented crane model | A second invented crane model with two cranes, in both invented reports, with two inserts, a counted set of four blocks, and a hook block model with none held | Two cranes show the sharing; its own crane model keeps ERT-1's carrier pair proposal unambiguous |
| 11 | - | The Retire section stays after a retirement, saying there is nothing more to do | Found by the E2E run: the section vanished with its success message |
| 12 | - | The Models page's "Map a Plum model name" and a machine's model correction offer no kit model | The backend refuses both; the screens do not offer what will be refused |
| 13 | The same request key returns what the first request made | Unless it was used for another kit model: then `409` | As WRR-001 refuses a requirement's key on another line; a reused key must not answer with a lot the user did not ask for. **Superseded 8 October 2026** (TB-1 TB1-102 part b): the key with any other request - another count, number or year too - is `409`, by the request's fingerprint |

### Tests and checks

Recorded in `docs/agent/acceptance/ert-2-detachable-kit-acceptance.md` and the continuity note
`docs/continuity/ERT_2_DETACHABLE_KIT.md`, with the tree each was measured on.

### Independent review

the independent reviewer, bounded packets; the owner's cap is three rounds. Results are recorded here round by
round.

**Round 1** (packet `c6102515...`, tree `df53e31`, commit `0adda07`): `CORRECTION_REQUIRED`, six material
findings, none blocking. All six corrected, each with a test that fails when the correction is undone:

| Finding | What was wrong | Corrected |
| --- | --- | --- |
| ERT2-R1-001 | "Add kit" was not tied to the page it was made on: a kit model whose fits changed, or a crane corrected to another model, since the page was read, still took the pieces | `POST /kit` names the machine page and the versions of that machine and of the kit model it showed; under the write lock a changed one is `409`, and a kit model that does not fit the machine's current model is `422`. The request-key replay is unchanged |
| ERT2-R1-002 | Kit changes the crane's page without changing its version, and the page let any answer of an equal version replace the one shown - an older kit list could replace a newer one | Every request for the page's view - loads, saves, the reading again after kit is added - takes a place in one order when it is sent; between two answers of one version, only one asked for later replaces the one shown |
| ERT2-R1-003 | The kit section, with its crane wording and Add kit, showed on every machine's page | Shown only for a kind of machine the structure gives kit to (today, cranes), in that kind's own word |
| ERT2-R1-004 | Retiring some pieces of a counted set said "Retired." though the set stays, smaller | The message is read from the record returned: "2 pieces retired from the set; 4 left in it." |
| ERT2-R1-005 | The migration's check of open fitted links started only from assets with nothing above them, so a loop - which has no top - was never walked | The walk starts from every asset and carries its path; a loop is refused by name, and a chain deeper than the setting as before |
| ERT2-R1-006 | The Models page offered a new kind for a model the server always refuses it for | The Kind box is disabled, with the reason beside it, while records use the model or kit is recorded as fitting it |

Found with the round-1 corrections, outside the findings: the ERT-1 and ERT-2 API tests took "today" from the
container's clock, which runs on UTC, while the service judges the day in Asia/Kolkata - so between midnight and
05:30 in India a test comparing a date the service set with "today" failed. Both now take the day in
Asia/Kolkata.

**Round 2** (packet `a9540a26...`, tree `6212ec6`, commit `7e02753`): `CORRECTION_REQUIRED`, one material
finding; the reviewer judged round 1's six corrections right.

| Finding | What was wrong | Corrected |
| --- | --- | --- |
| ERT2-R2-001 | A repeated "add kit" was judged against the model its first piece carries now - which its details may change - so after a piece moved to model B, the old key was accepted for B and refused for the model it first asked for | Each record keeps the kit model its request asked for (`create_request_model_id`), and a repeat is judged against that. The database refuses any change to the request that made a record - key, place in the lot, model. The harness's cleanup finds a run's pieces by either model (narrowed in round 3) |

**Round 3** (packet `347b452e...`, tree `3fee2db`, commit `605f8ee`): `CORRECTION_REQUIRED`, three material
findings. All three corrected; the first two each with a test that fails when the correction is undone. Round
3 was the last within the owner's cap of three.

| Finding | What was wrong | Corrected |
| --- | --- | --- |
| ERT2-R3-001 | A machine model with a Plum name mapped to it, and no record yet, could be changed into a kind of kit - leaving a mapping to a kit model, which the design forbids, and a downgrade that could stop on it | A class change into a kind of kit is refused while Plum names are mapped to the model (`422`), and the Models page does not offer the kinds of kit to such a model. The downgrade removes any mapping to a kit model with the model rather than stop on it |
| ERT2-R3-002 | The harness's cleanup still took a piece's current model as provenance, so a piece someone else added and moved onto a run's model would have been deleted | A piece is the run's by the model its request asked for only. The run's piece moved to an outside model goes with the run; an outside piece moved onto a run's model makes cleanup refuse, and is kept |
| ERT2-R3-003 | The records said the full regression of the reviewed tree was "recorded" while it was still running | The result is recorded once the run ends, and a run still going is called pending |

**Round 4** (packet `e425f8f6...`, tree `bb90f79`, commit `8c33874`), authorized by the owner beyond the cap:
`CORRECTION_REQUIRED`, five material findings. All five corrected, each with a test that fails when the
correction is undone. **The owner then directed no fifth round** (27 September 2026): round 4's corrections
are not independently reviewed, and the owner's screen check comes next.

| Finding | What was wrong | Corrected |
| --- | --- | --- |
| ERT2-R4-001 | The retirement CHECK let a retired piece through with no reason: an `IN` on NULL is NULL, which a CHECK passes | The reason is tested NOT NULL before its `IN` |
| ERT2-R4-002 | The database let a Plum record be of a kind of kit | The trigger refuses it, as it refuses a platform record that is not kit; the migration's structure check also finds any record whose origin disagrees with its kind, for a later structure version that makes a kind kit or stops it being kit |
| ERT2-R4-003 | An open model form kept the model as it was when opened: a name mapped to it since, which does not change its version, left the kinds of kit on offer | A reload hands the open form the model as it is now, keeping the draft; a kind the server would now refuse is named beside Save, and Save is not offered |
| ERT2-R4-004 | The machine page loaded the structure and models on their own, so an older answer could replace a newer one after moving to another machine | They are loaded with the machine by its loader, and shown only for the latest load |
| ERT2-R4-005 | A retired piece's details still offered its model and a counted set's count, which the server refuses | Only while it is active; a retired piece offers its own number (one tracked one by one) and year |

### The owner's screen check (27 September 2026)

On scenario run `te1-9c925f54`: every step passed apart from the notes below ("Rest all ok"). Each note was
resolved the same day, and checked by eye in the browser at the owner's screen width on run `te1-0d69afe5`:

| Note | Resolved |
| --- | --- |
| Step 8: Change did not bring the model's form into view | Opening a form on the Models page scrolls it into view |
| Step 9: from a kit model's "N held" link there was no way back | The kit links on the Models page and a crane's page carry where they came from; the filtered Machines list shows "Back to models" or "Back to <machine>" (the shared `hrefWithReturnTarget` and `readSafeReturnTarget`) |
| The disabled Kind box and its reason sat out of line, the other boxes in the row stretched tall | One stylesheet rule: a `.field-stack` keeps its own height at the top of its row, in every form |
| A piece (EQ-000508) could not be found with Status "All": Show was "Machines" | Show adds "Machines, parts and kit" |
| A year of manufacture a year ahead was accepted | Not later than the current year (Asia/Kolkata); ERT-1's next-year allowance had no recorded reason. Plum's commenced year, a correction of Plum's own field, keeps ERT-1's rule |

Step 9's "Map a Plum model name" list offered the crane, crane carrier and aerial work platform models, and
no kit model, as intended.

## 19. Update, 4 October 2026: a counted set may not shrink below its trips (TB-1 finding TB1-307)

TB-1's Pass 3 found that retiring pieces of a counted set did not look at the allocations listing it (retirement takes
only the Equipment Reference's lock; listing kit takes Resource Assignments' and Eligibility's), so a set could be left
holding fewer pieces than its trips list, with no warning on either page - against 8A's "never more at once than it
holds". The owner decided it was an emergency under the TB-1 plan's section 12 and chose a fix as its own package.

- **The rule.** Retiring `count` pieces of a counted set is refused (`422`, nothing changed) when fewer would remain
  than its trips list at once on any day from today on; the message names that number and the allocations. Retiring
  a whole set or piece is unchanged: its allocations show it as retired and need replacing or freeing (8A design,
  from RMR-001).
- **The port.** `equipment_reference/ports.py` gains `KitListingSource` (`hold`, `listed_from`), which Resource
  Assignments registers when it is loaded - as it registers its ports with Eligibility and Resource Requirements - so
  this module never imports it. `listed_from` reuses the query and the count that refuse an over-listed set
  (`list_listed_kit_overlaps`, `most_in_use`).
- **Locks.** Retirement takes Resource Assignments' lock first, then its own, then the piece's row - the order
  Eligibility's "seen" marks already take (allocations, then equipment). Listing kit takes Resource Assignments' lock
  and then, through its foreign key, a share lock on the piece's row, so that is the only order that cannot deadlock
  with it. (The first version took this module's lock first; its own test below caught the inversion before the pull
  request.)
- **Tests.** `test_a_counted_set_cannot_shrink_below_what_its_trips_list_from_today` and
  `test_retiring_kit_takes_the_allocation_lock_before_the_equipment_lock` (8A tests); the second fails, on a lock
  timeout, with the locks taken the other way round.
- No migration, no new route, no new field. See `docs/continuity/TB1_307_KIT_RETIRE_CHECKS_TRIPS.md`.
