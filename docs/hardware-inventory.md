# Hardware inventory

Milestone 5 is documentary only. **No installed item is physically verified.** This summary
does not turn historical procurement/design statements into installed values. Detailed
per-item provenance, confidence limits, verification actions and raw-read versus motion
blockers are in the [evidence matrix](evidence-matrix.md#hardware-identity-evidence).

| Item | Current documentary evidence | Still required |
|---|---|---|
| Drive | STEPPERONLINE A6/A6-RS family in historical report and series manuals | Exact nameplate/model, firmware, supply, encoder/communication compatibility |
| Motor | Historical report says 750 W, 2.39 Nm and brake-equipped procurement; bibliography names candidate A6M80-750H2B1-M17 datasheet | Actual nameplate/datasheet, rated speed, encoder, brake voltage/control |
| Adapter | Waveshare USB TO RS232/485/TTL illustration and custom RJ45 cable in report p. 26 | Exact installed model/revision, isolation, direction, VID/PID/identity, pinout and wiring |
| RS485 wiring / termination | Custom cable described, no verified as-built wiring | Qualified isolated A/B/reference, bias and termination review |
| Mechanics | Worm gearbox; 50:1 used in historical calculation; NMRVS50 bibliography | Installed label/ratio, coupling, sign, limits, zero, backlash, load/holding review |
| Pi | Zero 2 W is the design target; supplied generic pinout is not installed-board proof | Actual board, OS/architecture, power/USB topology and service ownership |
| Camera / temperature | HQ camera and DS18B20 intended; historical code uses camera and 1-Wire APIs | Installed sensor identity/wiring; separate monitoring scope |
| E-stop / STO or enable / contactor | Required by current safety design; installed implementation unknown | Exact capabilities, schematic, safe disabled-state/energization review |
| PL / NL | Required independent travel protection | Switch identity, placement, active levels and verified wiring |
| HSW | Required for selected future homing workflow | Switch type, placement, active level and homing compatibility |
| Switch electrical behavior / DI common | Unknown | NO/NC, PNP/NPN/dry-contact truth table and qualified wiring review |
| Encoder Z-phase | Unknown | Exact encoder/drive capability and homing-mode applicability |
| Gravity / brake / holding | Historical counterweight calculations only | Approved restraint and torque-loss behavior; no assumed self-locking |
| Qualified electrical safety review | Not supplied | Signed review before any proposed powered read |
| Pi stable by-id identity | Unknown; no enumeration performed | Later explicitly authorized observation; full value in local config only |
| Motion and monitoring users/groups | Separate least-privilege identities are design requirements only | Actual accounts/permissions in later deployment review |
| PC operating system | Windows is the GUI design target | Actual supported Windows version, no host discovery in this audit |

Do not record credentials, tokens, private network details, or machine-specific serial
paths in this shared file. Until the inventory and safety evidence are complete, the
project remains simulation or documentation only and real enable, homing, and motion are
prohibited.

See [readiness gates and prioritized evidence requests](hardware-readiness.md): A PASS,
B/C/D BLOCKED. Current safety level remains **Simulation**. Exact model-specific
communication documentation and genuine raw Modbus captures are not currently available.
