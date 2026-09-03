# Hardware inventory

Milestone 6 is documentary only. **No installed item is physically verified.** This summary
does not turn historical procurement/design statements into installed values. Detailed
per-item provenance, confidence limits, verification actions and raw-read versus motion
blockers are in the [evidence matrix](evidence-matrix.md#hardware-identity-evidence).

| Item | Current documentary evidence | Still required |
|---|---|---|
| Drive | New A6-RS chapters list A6-200RS/400RS/750RS/1000RS; RS means pulse and 485; sample nameplate is illustrative | Installed nameplate/model and firmware; match exact manual revision/applicability |
| Motor | New tables document A6M80-750H2B1-M17: 750 W, 220 V, 3000 rpm, 2.39 Nm, 17-bit absolute encoder, brake; not installed evidence | Actual nameplate and current brake/control evidence |
| Adapter | Waveshare V1.3 manual documents FT232RL, USB-B, isolated A+/B-/GND and automatic direction | Installed label/revision, VID/PID/serial/by-id behavior, bias/termination state and wiring |
| RS485 wiring / termination | Custom cable described, no verified as-built wiring | Qualified isolated A/B/reference, bias and termination review |
| Mechanics | Worm gearbox; 50:1 used in historical calculation; NMRVS50 bibliography | Installed label/ratio, coupling, sign, limits, zero, backlash, load/holding review |
| Pi | Raspberry Pi Zero 2 W is `USER_CONFIRMED`, not physically verified; generic pinout is not installed evidence | OS/architecture, power/USB topology and service ownership |
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
B/C/D BLOCKED. Current safety level remains **Simulation**. A6-RS family communication
documentation is available; installed applicability, U-area mapping and genuine raw
Modbus captures remain unavailable.
