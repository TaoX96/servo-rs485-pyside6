# Evidence matrix through Milestone 7

Latest audit: 2026-09-03. Current safety level: **Controlled read-only commissioning
preparation**. No device was inspected, enumerated, contacted, read, or written in this
milestone. No legacy code was imported or executed. Nothing here authorizes hardware
access or motion.

## Evidence vocabulary

Levels describe individual claims, not entire documents or devices. Documentary support,
physical verification, and permission to operate are separate dimensions.

| Level | Meaning |
|---|---|
| `PHYSICAL_DEVICE_VERIFIED` | Recorded observation of the identified installed device under an approved procedure. No claim receives this level through Milestone 7. |
| `USER_CONFIRMED` | Identity explicitly reported by the user without physical evidence inspected in this audit; not physical verification. |
| `EXACT_MODEL_MANUAL_CONFIRMED` | Manufacturer statement matched to the exact target model and firmware applicability. No such match is currently established. |
| `SERIES_MANUAL_CONFIRMED` | Statement in supplied manufacturer family/product documentation; exact installed target applicability unconfirmed. |
| `MANUAL_AND_LEGACY_AGREE` | A specifically named field agrees between series documentation and historical code; not proof that the code ran successfully or that the device remains configured that way. |
| `LEGACY_CODE_ONLY` | Historical source assertion or API argument, without matching manufacturer/capture evidence for that claim. |
| `PROJECT_DOCUMENTATION_ONLY` | Historical report or current repository design assertion; the source must distinguish the two. |
| `INFERRED` | Hypothesis derived from evidence, never a confirmed setting or permission. |
| `CONFLICTING` | Sources disagree or a source is internally inconsistent; retain both statements. |
| `MISSING` | Required evidence is absent from the supplied local materials. |
| `HARDWARE_VERIFICATION_REQUIRED` | Open physical verification obligation, which may coexist with documentary support. |

The catalog enum `MANUAL_CONFIRMED` means documentary rather than physical confirmation.
Milestone 7 changes the three U16 diagnostic entries described below; historical sections
remain as an audit trail and do not control the current allowlist.

## Milestone 7 controlling reassessment

| Evidence class | Milestone 7 use and limit |
|---|---|
| Manual evidence | Manufacturer family documents support the three U16/RO mappings, FC03 framing, DI raw-bit layout, and positive-limit mode 18; installed applicability is unverified. |
| Historical LabVIEW evidence | User-confirmed successful control establishes that the drive/RS485 method operated previously; the unavailable VI export does not erase that history. |
| Source-code evidence | Protected legacy Python records RTU/slave/serial assumptions and write-oriented symbols; it was inspected as text only and cannot prove current settings or reads. |
| Synthetic test evidence | Offline frames, faults, cleanup, state phases, and GUI boundaries are deterministic tests; they are not drive observations. |
| Genuine Raspberry Pi raw captures | None exist at completion of Milestone 7. |
| Current installed-hardware verification | None was performed in Milestone 7; all such facts await the supervised observation record. |

The communication manual states that parameters are read with FC03 and constructs the
PDU address from the parameter group and offset bytes. The parameter list identifies
`U40.04`, `U41.08`, and `U41.0A` as U16/read-only parameters. Taken together, these are
sufficiently specific for the fixed first-session diagnostic. The conclusion is
documentary and does not claim installed applicability.

| Symbol | Manual evidence | Diagnostic mapping | Current conclusion |
|---|---|---|---|
| `SERVO_STATUS` | U41.0A, U16, RO; raw states 0 not ready, 1 ready, 2 running, 3 fault | FC03, address `0x410A`, count 1 | Selected first read; confirmed by documentation |
| `PLAN_OPERATION_GROUP` | U41.08, U16, RO | FC03, address `0x4108`, count 1 | Allowlisted optional read; confirmed by documentation |
| `DI_STATUS` | U40.04, U16, RO; DI1-DI8 raw electrical levels; example `0xFFFE` means DI1 low and DI2-DI8 high | FC03, address `0x4004`, count 1 | Allowlisted raw observation; confirmed by documentation; installed DI assignment/polarity unresolved |

The manual's word example supports DI1 at bit 0 through DI8 at bit 7. It exposes raw
electrical levels, not the configured meaning of PL/NL. The tool may identify a selected
raw bit only when the installed DI number is recorded. It reports
`ACTIVE_LEVEL_UNVERIFIED` until polarity is verified and never writes the assignment or
polarity parameters.

Historical successful LabVIEW control is accepted as evidence that this drive/RS485
method worked previously. The historical project report and source support slave 1,
9600/8N1, RTU, MinimalModbus, and a USB-RS485 workflow. This is **supported by historical
operation**, not a current Pi capture, present wiring check, or proof of current settings.
Legacy source was read as text only and contains writes; it was never imported or run.

### Gate B item-by-item status

| Gate B item | Status |
|---|---|
| FC03 parameter read, group/offset address construction, U16 width/access for the three symbols | **Confirmed by documentation** |
| Previous drive/RS485 operation and 9600/8N1/slave-1 baseline | **Supported by historical operation** |
| Installed model/firmware, adapter, wiring, settings, Servo Disabled/restraint condition, DI assignments/polarity, exact Pi by-id path | **Unresolved** |
| Current Raspberry Pi request/response capture | **Unresolved**; no genuine raw capture exists |
| Any installed-hardware fact | **Not verified on current hardware** |
| Joint calibration, homing speeds/distances/offset, motion limits, HSW, encoder index | **Not required for the first read-only test** |

Gate B is therefore **prepared/conditional for Session 1**, rather than globally blocked
by motion-stage questions. Stop Points A/B and explicit authorization for the exact
configured one-shot request remain mandatory. Gates C and D remain blocked.

The position-mode manual documents drive-internal positive-limit homing modes 2 and 18.
Mode 18 uses the PL transition as home and does not search for an encoder Z pulse. This
supports the selected future `POSITIVE_LIMIT_REFERENCE` design at family-manual level;
installed firmware applicability, mode configuration, DI assignment/polarity, speeds,
distances, offset, and completion feedback remain unresolved. It authorizes no motion or
register write.

## Milestone 6 intake and controlling conclusions

The immutable [intake manifest](evidence/intake-manifest.md) records five newly supplied
PDF excerpts. This section supersedes Milestone 5 statements below that the communication
chapter and adapter manual were missing; the older sections remain as an audit trail of
what was known then. The new documents improve **manufacturer-document evidence**, not
installed-device verification or permission to access hardware.

| ID | Document title / revision / scope | Confirmed documentary facts | Remaining limitation / level |
|---|---|---|---|
| N1 | `A6-RS series servo drive manual`, Chapter 9 `Communication Description`, printed pp. 329-336; no displayed revision | Modbus RTU; FC03 for 16/32-bit parameter reads; group/offset C-address construction; high byte then low byte in each word; CRC16 0xA001 with CRC low byte first; >=3.5-character frame boundary; error frame CMD 0x90 and listed errors; 32-bit C0A.06 word ordering | A6-RS family scope; no installed model/firmware or current C0A.06 evidence. C examples only; no explicit U mapping, FC04, maximum read length, broadcast behavior, baud/framing settings, read side-effect statement or disabled-state permission. `SERIES_MANUAL_CONFIRMED` |
| N2 | Same PDF title, Chapter 3 `Electrical Installation`, printed pp. 22-57; no displayed revision | A6-750RS is SIZE B/single-phase 200-240 VAC; CN3 pins 4/5/8 and CN4 pins 12/13/16 are RS485+/RS485-/GND; reference grounds are connected; qualified wiring and residual-voltage warnings | Generic series wiring, not the installed drive/cable; no physical inspection, termination state, firmware or safe-energization approval. `SERIES_MANUAL_CONFIRMED` |
| N3 | Same PDF title, Chapter 1 `Product Information`, printed pp. 9-14; no displayed revision | A6-RS means pulse and 485; family models A6-200RS/400RS/750RS/1000RS and rated data; manual image illustrates an AS-400RS nameplate | Illustration is not installed evidence and is inconsistent in prefix with the A6 model table; installed model, serial, firmware and power remain unknown. `SERIES_MANUAL_CONFIRMED` / `CONFLICTING` illustration |
| N4 | Same PDF title, Chapter 10 `Motor and Options`, printed pp. 337-351; no displayed revision | Model-code legend; A6M80-750H2B1-M17 brake version is 750 W, 220 V, 3000 rpm, 2.39 Nm, 17-bit absolute encoder; table pairs it with A6-750RS; brake table in N2 gives 24 VDC, 3.2 Nm holding, 8.5 W | Tables describe supported products, not the installed motor; no nameplate photograph or current brake/control evidence. `SERIES_MANUAL_CONFIRMED` |
| N5 | Waveshare `USB TO RS232/485/TTL User Manual`, V1.3, 20181108 | FT232RL product; USB-B; A+/B-/GND screw terminals; documented power/signal isolation and automatic direction; Windows OS list; reserved 120-ohm termination pads | No installed-adapter label/revision photo, wiring, solder-pad state, biasing, VID/PID, unique serial or Linux/by-id guarantee. `SERIES_MANUAL_CONFIRMED` for the named product; installed identity remains `HARDWARE_VERIFICATION_REQUIRED` |

### Manual applicability and device identity reassessment

N1-N4 are coherent chapters of an A6-RS series manual and explicitly name A6-750RS and
the candidate 750 W motor combination. They therefore cover the product family and those
listed models. They do **not** identify the installed unit. The correct installed-device
conclusion is **manual compatibility inferred but not proven**: no current drive/motor
nameplate or firmware evidence was supplied. The user's milestone description says the
intake covers exact identity, but it supplies no legible installed model value outside
manual examples; that statement is retained as user context, not promoted to
`PHYSICAL_DEVICE_VERIFIED` or `USER_CONFIRMED` exact model.

The historical report's illustrated Waveshare product resembles N5, but there is still no
current adapter label/photo. N5 confirms capabilities for its named product, not that the
installed adapter is that revision or configured/wired accordingly. The Pi is
`USER_CONFIRMED` as Raspberry Pi Zero 2 W, not physically verified; installed OS,
architecture, power, USB identity and service configuration remain unknown. No optional
web review was used.

### Communication-manual audit

| Topic | N1/N2 finding | Status / limitation |
|---|---|---|
| Protocol / physical interface | N1 sec. 9.1: Modbus RTU; N2 secs. 3.3/3.8: RS485+/RS485-/GND on CN3/CN4 | Family-manual confirmed; installed compatibility/wiring unverified |
| Station | N1 request ADDR 1-247 | Conflicts with earlier parameter-table C0A.00 range 1-255; installed value unknown |
| Baud, data bits, parity, stop bits | Not stated in N1; earlier C0A.01/.02 provides selector/default information but does not explicitly state data bits | Installed settings unknown; legacy 9600/8/N/1 remains historical, defaults remain defaults |
| Frame/timing | Request and response fields; START/END >=3.5-character idle time | No absolute inter-frame time, host timeout or maximum request length stated; earlier C0A.03 response-delay selector is not installed evidence |
| CRC | CRC16 polynomial 0xA001, initialized 0xffff; frame transmits CRC low byte then high | Family-manual confirmed; implementation still future work |
| Read FC | FC03 explicitly for 16/32-bit parameters; FC04 is not listed | Confirmed for documented C-parameter examples only; no arbitrary substitution or FC04 fallback |
| Response representation | Each 16-bit word is high byte then low byte; 32-bit order selected by C0A.06 | Byte-within-word is BIG. Active word order is unknown: setting 0 low-word-first, setting 1 high-word-first |
| Exceptions | CMD 0x90 with 32-bit error value: 0001, 0002, 0003, 0004, 0006, 0008, 0020 | Preserve exact manual behavior; do not replace with generic Modbus exception assumptions |
| Maximum read length / atomicity | Count is a 16-bit request field; a 32-bit parameter uses two words from its smaller offset | Field width is not a documented safe maximum. Coherence beyond a named 32-bit parameter is not established |
| Broadcast behavior | Not stated | Unresolved; broadcast prohibited in future plan |
| Read while disabled / side effects | Error 0x0020 means `Reading disabled`; no state-condition table or blanket no-side-effect statement | Blocker for first physical read until exact field conditions are supported |

### Function-code determination by category

| Category | FC / area / address / maximum | Applicability and remaining issue |
|---|---|---|
| C parameter reads | FC03; address bytes are C group and suffix offset; 32-bit named parameter count 2; maximum safe multi-read length unstated | Explicit A6-RS family evidence. Installed firmware and read conditions still unverified |
| U monitor/status reads | Not separately documented in N1 | U labels are in the parameter-list manual, but extending N1's C-only mapping examples to U is not proven; FC and address area remain unresolved |
| I/O-state reads | U40.04/.05 are read-only labels in the parameter list; N1 gives no category-specific mapping | FC/area/address unresolved; no read authorized |
| Alarm reads | N3 says alarm tracing exists, but N1 supplies no alarm register/FC mapping | Unresolved; do not infer FC03/04 |

### Address mapping and worked examples

N1 explicitly defines C-register PDU bytes as the two hexadecimal components of the
label: group in the high byte, suffix offset in the low byte. This is a direct 16-bit PDU
address construction for the documented C examples, with no one-based register number and
no `-1`/`+1` adjustment. It does not establish a human-facing 4xxxx number or MinimalModbus
argument convention; library behavior must be verified offline before any adapter work.

- C03.00 -> address bytes `03 00`, PDU value `0x0300`, FC03, count 1.
- C03.02 -> address bytes `03 02`, PDU value `0x0302`, FC03, count 2 because it is U32.
- C11.06 -> address bytes `11 06`, PDU value `0x1106`, FC03, count 2 because it is I32.

These are manually worked applications of N1's rule plus the supplied parameter-table
types; no request was sent. N1 itself gives C06.11 -> `06 11` and C05.07 -> `05 07`.
Its separate `C11.12 (1st displacement)`/request `11 12` example conflicts with the
parameter list, which calls C11.06 group 1 displacement and C11.12 group 2 speed. Treat
that example as a blocking manual defect, not a catalog correction. No supported U example
can be provided: U40.16 -> `0x4016` remains a historical/current-project hypothesis, not a
confirmed mapping. Object-style homing notation also remains separate.

### Installed communication settings

| Setting | Current status |
|---|---|
| Station, baud, data bits, parity, stops | Historical code: 1, 9600, 8/N/1. Earlier series defaults/selectors: station 1, baud selector default 115200, no parity/one stop. No current display evidence: **Unknown installed values** |
| Protocol selection | Product family and N1 document Modbus RTU; installed firmware/mode not observed |
| C0A.06 word order | Options documented; current value unknown |
| Response delay / host timeout | C0A.03 options/default and historical 1-second host timeout only; current values unknown |

No setting is `Visible on current drive/keypad evidence` or physically verified. No
parameter change is requested.

### Register reassessment: all 14 current catalog entries

Shared facts: C entries have documentary FC03/C-group mapping; U entries retain unresolved
FC/area/mapping. No entry is physically verified or trusted-interpretation ready. Raw
evidence-ready means the documentary fields needed to design a read are settled; it is
not hardware authorization. All current code still says area `UNRESOLVED`; proposed
metadata corrections must be a later reviewed code milestone.

| Symbol | Label / address | Area, FC | Type / words / sign; unit/scale | Ordering | Manual page(s) / model applicability | Raw evidence-ready / blocker |
|---|---|---|---|---|---|---|
| POSITION_REFERENCE_SELECTION | C03.00 / 0x0300 | C parameter, 03 | U16/1/unsigned; - | word BIG | P 252; N1 329 mapping; A6-RS family | No: RW field lacks explicit no-side-effect/read-state evidence; installed firmware unknown |
| GEAR_1_NUMERATOR | C03.02 / 0x0302 | C parameter, 03 | U32/2/unsigned; - | bytes BIG; C0A.06 active order unknown | P 252; N1 329,334-335; family | No: read conditions/installed applicability unknown; machine-defining engineering field |
| GEAR_1_DENOMINATOR | C03.04 / 0x0304 | C parameter, 03 | U32/2/unsigned; - | same | P 252; N1 329,334-335; family | No: same blockers |
| PLAN_MODE | C11.00 / 0x1100 | C parameter, 03 | U16/1/unsigned; - | word BIG | P 298; N1 329 mapping; family | No: RW motion configuration lacks explicit no-side-effect/read-state evidence |
| GROUP_1_DISPLACEMENT | C11.06 / 0x1106 | C parameter, 03 | I32/2/signed; application unit/1 | bytes BIG; active word order unknown | P 298; N1 mapping; family; N1's C11.12 example conflicts | No: manual conflict/read conditions; not in either code allowlist |
| SPEED_FEEDBACK | U40.01 / hypothesized 0x4001 | U monitor, unknown | I16/1/signed in table vs prose 32-bit; rpm/1 | unresolved | P 311/327; N1 lacks U mapping; family | No: width conflict plus FC/address unknown |
| TORQUE_FEEDBACK | U40.03 / hypothesized 0x4003 | U monitor, unknown | I16/1/signed; % rated torque/0.1 | unresolved | P 312; N1 lacks U mapping; family | No: FC/address/read conditions unknown |
| BUS_VOLTAGE | U40.06 / hypothesized 0x4006 | U monitor, unknown | U16/1/unsigned; V/0.1 | unresolved | P 312; N1 lacks U mapping; family | No: FC/address/read conditions unknown |
| POSITION_DEVIATION | U40.10 / hypothesized 0x4010 | U monitor, unknown | I32/2/signed; encoder pulse/1 | word/byte application unresolved | P 312; N1 lacks U mapping; family | No: FC/address and active order unknown |
| POSITION_FEEDBACK | U40.16 / hypothesized 0x4016 | U monitor, unknown | I32/2/signed; application unit/1 | same | P 312; N1 lacks U mapping; family | No: FC/address/order; application units are not degrees |
| MOTOR_TEMPERATURE | U40.31 / hypothesized 0x4031 | U monitor, unknown | I16/1/signed; deg C/0.1 | unresolved | P 313; N1 lacks U mapping; family | No: FC/address/read conditions unknown |
| ENCODER_TEMPERATURE | U40.32 / hypothesized 0x4032 | U monitor, unknown | I16/1/signed; deg C/0.1 | unresolved | P 313; N1 lacks U mapping; family | No: FC/address/read conditions unknown |
| PLAN_OPERATION_GROUP | U41.08 / hypothesized 0x4108 | U status, unknown | U16/1/unsigned; - | unresolved | P 315; N1 lacks U mapping; family | No: FC/address/read conditions unknown |
| SERVO_STATUS | U41.0A / hypothesized 0x410A | U status, unknown | U16/1/unsigned; raw states | unresolved | P 315; N1 lacks U mapping; family | No: otherwise attractive candidate, but exact FC/area/address/no-side-effect conditions unresolved |

Unknown active word order prevents trusted 32-bit interpretation, not retention of an
otherwise approved two-word raw read. Raw-read blockers in this table are identity,
mapping, width, access/read conditions and authorization, not calibration or layout alone.

### Proposed later catalog review (no code changes now)

Retain all four generic offline codec layouts. A later reviewed metadata change can attach
N1's C-parameter address/FC/high-byte-first documentary evidence without claiming installed
verification. Correct the blanket `historical zero-based runtime address` wording for U
entries, whose mapping remains unsupported. Do not change U numeric values or resolve speed
width by inference. Keep the displacement discrepancy blocking until manufacturer evidence
clarifies it. No production catalog entry was silently corrected in Milestone 6.

### Additional documentary discrepancies

- N1 pp. 6-7 (334-335) calls C11.12 the first displacement, while its later write example
  uses address bytes 11 0C; P p. 58 (298) identifies C11.06 as group 1 displacement. None
  of these conflicting examples establishes a replacement address for the current catalog.
- N3 p. 1 (9) advertises a 17-bit encoder, while p. 5 (13) lists 23/26-bit feedback.
  Exact installed encoder compatibility remains unresolved; do not merge those claims.
- N4 p. 10 (346) has a 750 W table but labels its brake-dimension illustration with a
  400 W motor model. Ratings-table evidence is not authority to use that drawing for assembly.
- N2's CN3/CN4 table labels GND but gives it the description `Data receive-`; preserve the
  pin label and require qualified matched-pinout review rather than reinterpret its function.
- N1's slave-address range, N2's node count and N5's node recommendation are different
  quantities. None proves the installed station, bus loading or current cable topology.

## Milestone 5 source inventory and provenance (historical baseline)

Page numbers below are one-based PDF pages; printed page numbers are given in parentheses.
Links refer only to supplied local files. Bibliographic web links were not visited.

| ID | Actual protected filename / type | Evidence scope |
|---|---|---|
| P | [parameter lists of A6-RS series servo drive manual.pdf](<reference/parameter lists of A6-RS series servo drive manual.pdf>) / PDF, 88 pages | Chapter 8 excerpt, printed pp. 241–328. Series parameter tables, not a complete communication manual. |
| M | [position mode of A6-RS series servo drive manual.pdf](<reference/position mode of A6-RS series servo drive manual.pdf>) / PDF, 68 pages | Chapter 4 excerpt, printed pp. 58–125. Series position/homing descriptions. |
| L | [nonverbose_bestCode.py](reference/nonverbose_bestCode.py) / Python | Historical servo-control source, read as text only. No recorded read responses. |
| D | [TechnikerSchule März2025_Gruppe 1 Dokumentation FINAL.pdf](<reference/TechnikerSchule März2025_Gruppe 1 Dokumentation FINAL.pdf>) / PDF, 39 pages | Historical rig design, procurement narrative, calculations, illustrations and bibliography; not an as-built inspection record. |
| C | [CamTemControlMonitorv3.py](reference/CamTemControlMonitorv3.py) / Python | Historical camera/1-Wire monitoring source; no servo protocol verification. |
| Z | [Raspberry Pi Zero 2 W Pinout _ Pinouts.pdf](<reference/Raspberry Pi Zero 2 W Pinout _ Pinouts.pdf>) / PDF, 3 pages | Third-party generic pinout, not installed-board or OS evidence. |
| R0 | [reference README](reference/README.md) / Markdown | Historical list, not proof that every named file was supplied. |
| R | Current register catalog, register-map, configuration examples and tests | Current design and synthetic offline behavior, not legacy measurements. |

There are seven protected files: two Python, four PDF, one Markdown. R0 names older
`(1)` variants, `Tao_Xiong_Thesis.pdf` and a LabVIEW VI that are not present under those
names. At Milestone 5, no communication chapter or motor tables were supplied; the
Milestone 6 intake above now adds series-level chapters but not installed-device evidence.
The originals and their recorded seven-file SHA-256 baseline remain unchanged.

## Milestone 5 hardware identity evidence (historical baseline)

For each row, the last column distinguishes blockers: **B** = real raw-read gate,
**C** = trusted interpretation gate, **D** = motion gate. `D only` does not waive Gate B's
safe energization, disabled-servo and restraint review. Unknown safety facts relevant to
energization block B even when no motion is requested. All installed identities remain
`HARDWARE_VERIFICATION_REQUIRED`; no photograph in a historical report proves today's rig.
Verification actions below are future evidence requests, not instructions to energize or
open equipment. See the [safe request checklist](hardware-readiness.md#prioritized-user-evidence-request).

### Drive and motor

| Item | Supported value and source / level | Confidence limitation | Required verification | Blocks |
|---|---|---|---|---|
| Drive manufacturer / family | STEPPERONLINE A6 in D pp. 24, 26, 31, 39; A6-RS in P/M and R; `PROJECT_DOCUMENTATION_ONLY` / `SERIES_MANUAL_CONFIRMED` | Family evidence, not exact installed identity | Accessible nameplate and exact compatible manual | B, D |
| Drive exact model / serial | Unknown; `MISSING` | Do not derive a drive model from motor power | Nameplate; retain full serial privately, share redacted identifier | B, D (public full serial not needed) |
| Firmware / communication option and version | Actual values unknown; P p. 76 (316) lists U42.00 ARM, .01 FPGA, .05 internal software, .06 Modbus version; `SERIES_MANUAL_CONFIRMED` labels only | Not runtime addresses or observed version values | Existing version record or separately authorized safe display observation; compatibility assessment | B, C, D |
| Drive rated power / supply voltage | Installed values unknown. P pp. 85–86 (325–326) lists 750RS as 0.75 kW, single-phase 220 V; `SERIES_MANUAL_CONFIRMED` candidate specification only | D's 750 W motor does not identify its drive; never select supply from this table | Drive nameplate and qualified supply review | B, D |
| Drive encoder type / resolution | Unknown; P p. 76 has encoder version/model labels; `MISSING` installed data | No encoder resolution may be decoded from a candidate model name | Matched drive/motor/encoder documents and installed labels | C for encoder units, D; B compatibility review |
| Keypad / commissioning parameter identity | P p. 76 lists U42.10 drive, .11 motor, .12 encoder, .13 power supply model; M p. 68 mentions keypad/Synland; `SERIES_MANUAL_CONFIRMED` | Not confirmation of tool compatibility or current values | Exact manual and existing read-only display records, no software connection now | B, C, D |
| Motor exact model | D p. 39 bibliography names `A6M80-750H2B1-M17_Full_Datasheet.pdf`; `PROJECT_DOCUMENTATION_ONLY` candidate | Datasheet absent; cannot claim installed model from link | Motor nameplate and matching supplied datasheet | B safe setup, C, D |
| Motor rated power / torque | D pp. 24, 26: 750 W; p. 31: 2.39 Nm; `PROJECT_DOCUMENTATION_ONLY` | Historical selection/calculation, not measured or nameplate-confirmed | Nameplate/datasheet, not inferred ratings | C torque interpretation, D; B safe setup |
| Motor rated speed | Unknown; D p. 30 uses 750 rpm in a motion calculation; `MISSING` rating | Calculated operating speed is not rated speed | Nameplate/datasheet | C plausibility, D only |
| Motor encoder | Unknown; `MISSING` | Model-code suffix is not verified encoder information | Matching encoder/motor datasheet and label | C, D only |
| Motor brake presence | D p. 24 says version with brake was ordered because non-brake delivery was delayed; `PROJECT_DOCUMENTATION_ONLY` | Procurement account, not present brake condition | Nameplate and qualified as-built review | B restraint, D |
| Brake voltage / control method | Unknown; `MISSING` | Do not assume brake release/holding behavior on Servo Off or power loss | Brake data and electrical schematic, qualified review | B, D |
| Mounting orientation | D p. 22 describes adapter plate and a gearbox rotated 90 degrees; `PROJECT_DOCUMENTATION_ONLY` | Historical packaging, not installed axes/signs | Isolated rig photos and assembly drawing | B restraint, D |

### Mechanical system

| Item | Supported value and source / level | Confidence limitation | Required verification | Blocks |
|---|---|---|---|---|
| Gearbox type / ratio | Worm gearbox D pp. 15, 22; ratio 50 assumed in p. 30 calculation; p. 39 NMRVS50 / `nmrvs50-g50-d19` bibliography; `PROJECT_DOCUMENTATION_ONLY` | Not as-built gearing or proof of self-locking | Gearbox label/datasheet and assembly evidence | C angle relation, D; B load restraint |
| Coupling / output-shaft relationship | D p. 22 describes lower-shaft `Federverbindung` and adapter mounting; `PROJECT_DOCUMENTATION_ONLY` | No verified motor-to-joint transfer function | Assembly/coupling drawings, isolated inspection | C angle relation, D; B integrity |
| Positive joint direction | Unknown; `MISSING` | Legacy forward/reverse names are not a physical sign convention | Later separately reviewed direction verification | D only |
| Safe travel range | Unknown; D p. 29 uses 0–45 degrees in calculations; `PROJECT_DOCUMENTATION_ONLY` design range | Not approved operating limits or calibration | Mechanical review and measured allowed envelope | D only |
| Mechanical hard stops | Installed details unknown; `MISSING` | No evidenced location/strength | Isolated inspection/drawing and qualified review | D; B if needed for restraint |
| Gravity-loaded behavior | Counterweights and pinch hazards described D pp. 12, 29; `PROJECT_DOCUMENTATION_ONLY` | No proof of static safety with torque removed | Approved load-restraint/energization plan | B, D |
| Holding torque / load | D pp. 29–31 calculates loads and required torque; `PROJECT_DOCUMENTATION_ONLY` | Calculations do not validate holding, brake, gearbox or current assembly | Mechanical safety review, brake behavior evidence | B, D |
| Backlash | Unknown; `MISSING` | Cannot infer from gearbox category | Later approved measurement/design tolerance | C precision, D only |
| Known zero / reference position | Unknown; `MISSING` | Homing descriptions are not a commissioned zero | HSW placement, homing and calibration evidence | D only |

### Adapter and Raspberry Pi

| Item | Supported value and source / level | Confidence limitation | Required verification | Blocks |
|---|---|---|---|---|
| Adapter manufacturer / exact model | Waveshare D p. 26; illustration labelled USB TO RS232/485/TTL; `PROJECT_DOCUMENTATION_ONLY` | Product picture, no installed part/revision | Front/back label and matching datasheet | B, D |
| USB VID/PID / device serial availability | Unknown; `MISSING` | No device enumeration was performed | Existing records first; future authorized Pi observation | B stable identity, D |
| Galvanic isolation / automatic direction | Unknown; `MISSING` | Brand/product resemblance does not prove either feature | Exact adapter manual and qualified review | B, D |
| Biasing / termination | Unknown; `MISSING` | No resistor/topology evidence | Existing schematic, isolated wiring review | B, D |
| Ground/reference terminal | A+, B- and ground symbol appear in D p. 26 illustration; `PROJECT_DOCUMENTATION_ONLY` | Neither installed pinout nor drive-side RJ45 assignment confirmed | Matched adapter/drive pinouts and isolated A/B/reference review | B, D |
| Cable and stable Linux identity | Custom RJ45 cable D p. 26; actual wiring and by-id identity missing | Never copy a generic cable pinout or substitute a transient device path | Continuity review by qualified person while isolated; future explicit by-id observation | B, D |
| Pi exact model | Zero 2 W in R design and Z p. 2 generic pinout; `PROJECT_DOCUMENTATION_ONLY` | Neither identifies the installed board | Accessible board label or existing inventory | B host implementation, D |
| Pi OS / architecture | Unknown; `MISSING` | Generic CPU capability does not establish installed OS architecture | Later authorized local OS/architecture/Python observation | B host implementation, D |
| Pi power supply / USB topology | Unknown; `MISSING` | No safe power/OTG/hub/as-built evidence | Existing supply labels and topology drawing | B, D |
| Network topology | Unknown; future API isolation in R; `PROJECT_DOCUMENTATION_ONLY` design | Not needed for a local first read; no network discovery authorized | Later deployment review using redacted diagram | Not B for local test; required before networked motion |
| Service account / serial permissions | Separate least-privilege motion and monitoring identities in R deployment design; actual users/groups unknown | Policy, not installed permissions | Later authorized permission/sole-owner review, no changes now | B host ownership, D |
| Camera / temperature | HQ camera and DS18B20 intended in R; C camera/1-Wire functions around lines 632–680; `PROJECT_DOCUMENTATION_ONLY` / `LEGACY_CODE_ONLY` | Code use does not prove sensor identity or pin wiring | Later independent monitoring inventory | Neither B nor D motion authorization; outside this commissioning path |

### Safety hardware

All installed values below are `MISSING` and `HARDWARE_VERIFICATION_REQUIRED`. R safety
policy requires them; D p. 12 is a hazard narrative, not a qualified as-built review.

| Item | Evidence limitation / required verification | Raw-read blocker | Motion blocker |
|---|---|---|---|
| E-stop device | Need device identity, independent circuit and qualified review; software stop is not an E-stop | B safe energization | D |
| STO availability / wiring | Exact drive capability and wiring unknown; do not assume STO exists | B inhibition review | D |
| Servo Enable removal | Need actual signal path, active levels and behavior without holding torque | B disabled-state assurance | D |
| Contactor / safety relay | Need part numbers, schematic and validated isolation function | B safe energization | D |
| PL switch | Need identity, independent travel protection and installation evidence | D only unless used for B restraint | D |
| NL switch | Same evidence independently for negative travel | D only unless used for B restraint | D |
| HSW switch | Need identity, unique reference and suitability for selected homing mode | No for a disabled static raw read | D |
| Switch type / NO or NC / PNP, NPN or dry contact | All unknown; obtain each switch datasheet and as-wired truth table | B for enable/safety signals; otherwise D | D |
| DI common wiring | Unknown; qualified schematic/pinout and isolated verification | B if it affects inhibition | D |
| Mechanical switch placement | No as-built dimensions relative to travel/hard stops | D only unless part of B restraint | D |
| Safe stopping distance | No validated speed/load/stop envelope | Not needed for no-motion raw read with approved restraint | D |
| Qualified electrical review | No signed inspection or safe energization record supplied | B | D |

## Milestone 5 communication evidence (superseded where stated above)

`B`/`C` below refer to the [separate readiness gates](hardware-readiness.md). No factory
default is an observed active setting. No Modbus standard or library behavior is filled
in from memory. P p. 36–37 (276–277), section 8.9, is a settings table, not a wire-protocol
specification. Its separate commissioning-software settings C0A.08–0E must not be confused
with C0A.00–06; P p. 85 (325) discusses C0A.09/.0A, not missing Modbus framing details.

| Claim | Available evidence and level | Unresolved consequence / action |
|---|---|---|
| Modbus RTU support | P names Modbus parameters; L line 224 uses `MODE_RTU`; series Modbus support plus `LEGACY_CODE_ONLY` RTU selection | Exact target RTU compatibility/manual required for B |
| Slave address | P C0A.00 range 1–255/default 1; L line 218 selects 1; `MANUAL_AND_LEGACY_AGREE` on default/selection only | Actual station unknown; B, no station scan |
| Baud rate | P C0A.01 supports 2400–115200, selector 3=9600, default 7=115200; L line 219 uses 9600 | Series support confirmed; historical setting differs from factory default, not proof of a current mismatch; B |
| Data bits | L line 220 uses 8; `LEGACY_CODE_ONLY` | No complete framing specification supplied; B |
| Parity / stop bits | P C0A.02 default 0=no parity/one stop; L lines 221–222 match; `MANUAL_AND_LEGACY_AGREE` on selection | Actual format unknown; B |
| Host timeout | L line 223 uses 1 second; `LEGACY_CODE_ONLY` | Not a drive-mandated timeout; future bounded timeout must be approved for B |
| Supported function codes | L explicit `functioncode=6` occurs in writes, not reads; `LEGACY_CODE_ONLY` write API argument | No supported read FC established; no inference of 03/04 or defaults from MinimalModbus; B |
| Parameter-read / monitor-read FC | `MISSING` for both | Need exact communication manual; register labels/RO classification do not identify FC; B |
| Exception responses / maximum registers per request | `MISSING`; fake exceptions/count tests prove offline validation only | Exact framing/exception/count rules needed for B; use one reviewed request, no guessing |
| Inter-frame delay | `MISSING`; L sleeps are motion-action timing | Need protocol timing, not historical sleep values; B |
| Response delay | P C0A.03 range 1–1000 ms, default 1 ms; `SERIES_MANUAL_CONFIRMED` | Active delay and relation to host timeout unknown; B |
| Broadcast behavior | `MISSING` | No broadcast access in proposed test; do not infer behavior from station range |
| CRC behavior | `MISSING` in supplied excerpts; fake checksum failure is synthetic | Exact frame validation/CRC specification required before concrete implementation; B |
| Address notation / area / zero versus one base | P group/index labels; L numeric constants; R preserves numeric map | No deterministic RTU mapping or area known; B, see next section |
| 16-bit byte order | No wire captures or explicit supplied byte-order rule; `MISSING` | Synthetic codec layouts do not prove wire-to-word assembly; B framing, C interpretation |
| 32-bit word order | P C0A.06: 0=low 16 before high 16 (default 0), 1=high before low; `SERIES_MANUAL_CONFIRMED` | Actual setting/compatibility unknown; C for 32-bit fields, not a blocker for an otherwise approved U16 raw read |
| 32-bit byte order / library terminology | L uses `BYTEORDER_LITTLE` for two-register writes; `LEGACY_CODE_ONLY` | Not independent confirmation of byte-within-word order or equivalence to codec names; C |
| Signed representation | P labels I16/I32 and signed ranges; R codec tests two's complement | Series signed types confirmed; exact wire representation remains unverified, C |
| Atomic multi-register reads | `MISSING`; offline snapshots explicitly non-atomic | Need coherent-pair guarantees and supported count before trusted 32-bit telemetry, C; proposed first read is one U16 |
| Read side effects | Monitor tables say read only; no complete access/side-effect specification | RO does not alone prove a harmless protocol transaction; exact first-read safety review required for B |
| Stopped/disabled requirements for parameter reads | P's modification-mode column describes writes, not read permission; `MISSING` read restrictions | Verify exact read conditions. Proposed physical reads require disabled servo regardless; B for selected field |

## Milestone 5 address-notation comparison (superseded for C parameters only)

| Notation | What is actually documented | Mapping / base status |
|---|---|---|
| `C03.00`, `C03.02`, `C11.06` | Human-facing parameter labels, P pp. 12, 58 (252, 298) | Label suffix is not demonstrated to be a PDU offset |
| `U40.16`, `U41.0A` | Monitor labels, P pp. 72, 75 (312, 315) | Not independently a transport address |
| `2003h/C03`, `2011h/C11`, `2040h/U40`, `2041h/U41` | Group identifiers in P section headings | No supplied equation maps these to RTU addresses |
| Group/index pairs | P C03.00 index 01h; C03.02 index 03h; U40.16 index 17h; U41.0A index 0Bh | The differing suffix/index numbering does not authorize adding/subtracting one |
| Historical `0x0300`, `0x410A` | L constants; `0x0300` is passed to a write API, `0x410A` is an unused status constant | API argument evidence, not a captured PDU or confirmed base |
| Current-map `0x4010`, `0x4016`, `0x4108` | R map/catalog, absent as corresponding constants/read calls in supplied L | `PROJECT_DOCUMENTATION_ONLY` numeric assertions, not verified legacy reads |
| MinimalModbus arguments | L passes constants to `write_register`/`write_long` | Library-to-wire conversion unverified; library source was not imported/executed to infer it |
| Modbus PDU address | No genuine request/response capture or explicit supplied mapping | `MISSING`; B blocker |
| Human-facing register number | No separate numbered-register convention established | `MISSING`; no 4xxxx notation or +/-1 conversion introduced |
| Object-style `6040h`, `6064`, `607C`, `60E6` | M p. 68 (125), homing mode 35 discussion, uses control-word/position/home-offset notation | CiA 402-style resemblance is `INFERRED`; supplied text does not establish a CiA 402-to-RTU map. Never use these as transport addresses or trigger commands |

The current `RegisterSpec.address_notation` string calls its stored numeric value a
"historical zero-based runtime address". That is **unverified project wording**, not an
established base convention. The catalog cautions and `UNRESOLVED` area remain controlling;
Milestone 5 changes no source code and approves no offset. Formula generation, automatic
`-1`/`+1` fallback, group arithmetic and address scanning are prohibited.

## Milestone 5 register evidence matrix (superseded by the Milestone 6 table above)

Two joined tables avoid hiding provenance in a very wide table. Symbols identify the same
entry in both tables. Types, word counts and scales below are current documentary codec
metadata, not hardware qualification. `U` = unsigned, `I` = signed; each word is 16 bits.
Dash means no unit/scale in the catalog. RW is documentary access, **not write permission**.
Every entry has area `UNRESOLVED`, **read FC unknown**, real raw reading **NOT READY**, and
trusted physical interpretation **NOT READY**. These shared fields apply to every row.

| Symbol | Manual label | Stored numeric address | Type / bits / words / signed | Unit; scale | Documentary access / offline read policy | P PDF page (printed) |
|---|---|---|---|---|---|---|
| POSITION_REFERENCE_SELECTION | C03.00 | 0x0300 | U16 / 16 / 1 / no | —; — | RW; engineering only | 12 (252) |
| GEAR_1_NUMERATOR | C03.02 | 0x0302 | U32 / 32 / 2 / no | —; — | RW; engineering only | 12 (252) |
| GEAR_1_DENOMINATOR | C03.04 | 0x0304 | U32 / 32 / 2 / no | —; — | RW; engineering only | 12 (252) |
| PLAN_MODE | C11.00 | 0x1100 | U16 / 16 / 1 / no | —; — | RW; engineering only | 58 (298) |
| GROUP_1_DISPLACEMENT | C11.06 | 0x1106 | I32 / 32 / 2 / yes | application_unit; 1 | RW; neither allowlist | 58 (298) |
| SPEED_FEEDBACK | U40.01 | 0x4001 | I16 / 16 / 1 / yes in table; prose says 32-bit | rpm; 1 | RO; operational, ambiguous raw-only result | 71 (311), 87 (327) |
| TORQUE_FEEDBACK | U40.03 | 0x4003 | I16 / 16 / 1 / yes | percent_rated_torque; 1/10 | RO; operational | 72 (312) |
| BUS_VOLTAGE | U40.06 | 0x4006 | U16 / 16 / 1 / no | V; 1/10 | RO; operational | 72 (312) |
| POSITION_DEVIATION | U40.10 | 0x4010 | I32 / 32 / 2 / yes | encoder_pulse (P); 1 | RO; operational | 72 (312) |
| POSITION_FEEDBACK | U40.16 | 0x4016 | I32 / 32 / 2 / yes | application_unit; 1 | RO; operational | 72 (312) |
| MOTOR_TEMPERATURE | U40.31 | 0x4031 | I16 / 16 / 1 / yes | deg_C; 1/10 | RO; operational | 73 (313) |
| ENCODER_TEMPERATURE | U40.32 | 0x4032 | I16 / 16 / 1 / yes | deg_C; 1/10 | RO; operational | 73 (313) |
| PLAN_OPERATION_GROUP | U41.08 | 0x4108 | U16 / 16 / 1 / no | —; — | RO; operational | 75 (315) |
| SERVO_STATUS | U41.0A | 0x410A | U16 / 16 / 1 / no | —; — | RO; operational | 75 (315) |

All non-speed catalog verification states remain `HARDWARE_VERIFICATION_REQUIRED` (HVR
below); speed remains `AMBIGUOUS`. Offline pure decoding supports each listed primitive
with explicit layout, but speed's reader result deliberately has no decoded scalar.
Displacement can be codec-tested, not read through either existing reader allowlist.

Verification action **V** for every row: match model/firmware/manual; confirm harmless read
access, FC, address/base, width/count and wire-to-word assembly; obtain separately approved
raw capture and independent observation; confirm signedness, scale, plausibility,
freshness and repeatability before trusted use. **L32** additionally requires the
[static four-layout comparison](read-only-commissioning.md#32-bit-layout-verification).

| Symbol | Historical-code evidence (L lines) / agreement | Current state; offline support | Required verification beyond V / safety relevance |
|---|---|---|---|
| POSITION_REFERENCE_SELECTION | 53 constant; 235 write of selection 1 agrees with P internal planning option (`MANUAL_AND_LEGACY_AGREE` on option, not address) | HVR; yes | Machine-defining; engineering read disabled by default; no source-selection write |
| GEAR_1_NUMERATOR | 54 constant, 26 assignment 9, 230 two-register write; U32 width agrees, actual value `LEGACY_CODE_ONLY` | HVR; yes | L32; verify active gear separately; never treat 9/16384 as joint calibration |
| GEAR_1_DENOMINATOR | 55 constant, 25 assignment 16384, 232 two-register write; same narrow width agreement | HVR; yes | L32; machine-defining conversion; no parameter change for testing |
| PLAN_MODE | 63 constant; 237 write of 0 agrees with P single-operation option | HVR; yes | Machine-defining motion configuration; engineering only |
| GROUP_1_DISPLACEMENT | 70 constant; 165 signed two-register write agrees with P I32; old angle comments do not establish degrees | HVR; codec yes, reader prohibited | L32; neither read allowlist; application units only; motion configuration |
| SPEED_FEEDBACK | 43 unused numeric constant, no read; P table/prose `CONFLICTING` | AMBIGUOUS; primitive codec yes, reader scalar withheld | Resolve 16/32-bit conflict before selecting real count; never use for safety feedback |
| TORQUE_FEEDBACK | 44 unused numeric constant; type/scale from P (`SERIES_MANUAL_CONFIRMED`), not measured agreement | HVR; yes | Confirm 0.1% convention/reference rated torque; monitoring is not independent torque protection |
| BUS_VOLTAGE | 45 unused numeric constant; type/scale from P | HVR; yes | Confirm 0.1 V and independent reading; not proof supply is isolated or safe to touch |
| POSITION_DEVIATION | No corresponding constant/read in L; numeric address only R (`PROJECT_DOCUMENTATION_ONLY`) | HVR; yes | L32; distinguish encoder pulses from application units/degrees |
| POSITION_FEEDBACK | No corresponding constant/read in L; numeric address only R | HVR; yes | L32; not a calibrated joint angle or verified home; not sole moving layout reference |
| MOTOR_TEMPERATURE | 47 unused numeric constant; type/scale from P | HVR; yes | Validate sensor meaning/availability and 0.1 deg C; not safety-rated protection |
| ENCODER_TEMPERATURE | 48 unused numeric constant; type/scale from P | HVR; yes | Same; do not substitute motor temperature |
| PLAN_OPERATION_GROUP | No corresponding constant/read in L; numeric address only R | HVR; yes | P says 0–16; group alone cannot prove motion completed or authorize the next cycle |
| SERVO_STATUS | 30 unused constant; P states 0 not ready, 1 ready, 2 running, 3 fault | HVR; yes | Independent disabled-state evidence required; status is not an STO or safe-holding indication |

L contains no `read_register` or `read_long` call. Constants in that file are not evidence
of successful reads. Its startup reset/DI/gearing writes and motion functions are unsafe
historical behavior, not an approved workflow. No legacy code was executed. The larger
historical table in register-map.md is not the 14-entry executable catalog; neither is
expanded by this audit. C0A/U42 labels above are evidence targets only, not new entries.

## Genuine capture status

**No genuine raw A6-RS Modbus capture is currently available.**

The repository file inventory, supplied source/documents and offline fixtures contain no
record with a genuine paired request/response and sufficient drive context. Synthetic
words, write-call arguments, prose values, GUI state/event capture and camera image
capture are not wire evidence. No capture was generated during this audit.

A future capture must preserve original request and response bytes, explicit CRC inclusion,
UTC timestamp and acquisition context, exact drive identity/firmware and active settings,
slave, FC, register label/address/base/area/count, adapter/host identity, expected independent
keypad value, observed raw words, errors and the approving procedure/reviewer. Use the
[recording template](read-only-commissioning.md#recording-template); never fabricate missing
fields or store credentials.

## Conflicts and missing evidence

- Speed width remains internally conflicting in P; exact compatible documentation is needed.
- C0A.06 documents selectable word order, not a verified byte/word layout. Legacy
  `BYTEORDER_LITTLE`, default low-word-first and four passing codec layouts are distinct facts.
- P default baud 115200 versus L 9600, and P default gears 131072/10000 versus L 9/16384,
  describe different documentary settings, not proof of present values or safe calibration.
- Object-style homing notation in M p. 68 has no established RTU mapping. No offset or FC
  can be derived from it, the group/index tables, or a successful-looking numeric response.
- D's proposed unattended endurance use (p. 14) is superseded by the current prohibition
  on unattended real-hardware tests. D's Windows-owned RS485 diagram is historical only;
  future ownership belongs exclusively to the Pi motion service.
- Exact installed drive/motor/adapter identity, firmware compatibility, complete U-area
  mapping, as-built wiring/safety review and genuine captures are missing. New series
  manual chapters and historical datasheet
  links, R0's absent files and generic board pinouts do not close those gaps.
- Calibration, HSW/PL/NL installation, homing, direction, limits, brake and load-holding
  behavior remain unverified. Read-only success could not resolve or authorize motion.
