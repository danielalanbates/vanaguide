# Install on Mac (HorizonXI-on-Mac)

## Preferred (local LSB only)

1. Keep this repo at `~/Library/Mobile Documents/com~apple~CloudDocs/Code/Vanaguide` (addon root: `Vanaguide/Vanaguide` with `Vanaguide.lua`).
2. In **FFXI on Mac / HorizonXI-on-Mac**, choose **Local server (LandSandBoat)**.
3. Open **Setup & Diagnostics** → enable **Quest guide (Vanaguide, local LSB only)**.
4. Press Play. Log should show `==> vanaguide: on …`. In-game: `/vg`.

The launcher copies the addon into the world `addons/Vanaguide` folder and adds `/addon load vanaguide` **outside** the managed AddonSuite markers.

**Never** enable on HorizonXI / CatsEyeXI / FFEra or other allowlist / hosted servers — the launcher greys the toggle out and scrubs leftovers.

Manual fallback: `tools/install.sh` (LSB only). See also `VANASTACK_PLAN_POINTER.md` and HorizonXI `docs/FUTURE_AI_VANASTACK_PLAN.md` / `docs/VANAGUIDE.md`.
