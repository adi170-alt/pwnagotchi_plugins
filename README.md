# envtune

A self-tuning plugin for the [jayofelony noai pwnagotchi](https://github.com/jayofelony/pwnagotchi). It picks the best `personality.*` settings for whatever environment you're in — different ones at home, in your car, walking through a busy street — and gets better as it runs.

Goal: catch more **unique** handshakes (BSSIDs you've never captured before). Not more handshakes total. Re-capturing the same network ten times doesn't help.

## Why

Jay removed the original A2C neural network because it wrecked Wi-Fi firmware on long sessions and drained the battery faster than you could walk. That was the right call. But it left noai running on **fixed parameters**, which can't react to the fact that:

- a quiet residential street looks nothing like a coffee shop
- 9pm has different traffic than 3am
- handshake yield collapses when you're walking but you don't always remember to flip a config

envtune fixes that without re-introducing the firmware-killing parts. There's no neural net. There's no separate inference thread. There's nothing tweaking the radio at the channel level beyond what pwnagotchi natively does. **By default it does NOT add any radio activity to what stock noai does** — it only adjusts knobs pwnagotchi already supports.

It's a small multi-armed bandit (around 100 lines of actual algorithm). About 2-3% CPU on a Pi Zero 2 W. State is a single JSON file. No extra pip installs.

## Should you use it?

**Yes, if:** you run jayofelony noai, you've been wondering why your capture rate varies so much between locations, you're OK with letting the plugin learn for a few hours before judging.

**No, if:** you're on the original evilsocket fork (envtune assumes noai), you have a custom personality config you've heavily tuned and don't want second-guessed (you can set `prefer_stability=true` and the plugin will respect your config more conservatively, but it still adjusts within your range), you don't have web access to the Pi (most of the value is in the dashboard).

**Maybe, if:** you wardrive — envtune helps when you're stationary, helps less when you're moving fast and don't stay in any one λ-distribution long enough for the bandit to converge. It still won't *hurt* you while moving (mobility is a learned context dimension), but the gains are bigger when stationary.

## Install

Drop the file in:

```
/usr/local/share/pwnagotchi/custom-plugins/envtune.py
```

Then in `/etc/pwnagotchi/config.toml`:

```toml
main.plugins.envtune.enabled = true
```

Reboot. That's it. Defaults are already sensible — the plugin picks a CPU profile from `/proc/cpuinfo`, captures your `personality.channels` as the channel universe, and starts learning.

If you used the stock `auto-tune` plugin, disable it. envtune does the same job and more.

## What you'll see

The dashboard is at `http://<your-pi>:8080/plugins/envtune/`.

First few minutes you'll see:

- **Stability mode: on (noai-aligned)** — the default, see below
- **Channel universe: N channels** — the list of channels envtune is allowed to scan, sourced from your `personality.channels`
- **Pre-captured BSSIDs: N** — handshakes already on disk; these are *not* counted as "new" when re-encountered
- **Channel strategy: auto → adaptive (block 2/...)** — which scheduling strategy is currently being evaluated
- **🤖 Auto-strategy meta-bandit** panel showing how the plugin is benchmarking three different strategies against each other

After ~6 hours of operation, you'll see one strategy emerge as the leader for your environment. After ~150 epochs (a couple hours), you'll start to see the parameter bandit converging on values that work for your contexts.

## Two modes

There's exactly one switch you might want to flip. Stability mode controls whether envtune ever does anything that adds radio activity beyond stock noai's natural loop:

| | `prefer_stability = true` (default) | `prefer_stability = false` |
|---|---|---|
| Proactive `wifi.assoc` attacks | off | on |
| Opportunistic channel pokes when a new client appears | off | on |
| `full` strategy (scan all channels every epoch) when moving | banned | allowed |
| Battery impact | minimal — same as stock noai | slightly higher |
| Firmware stability | same as stock noai | risk increases marginally |
| Capture rate | high | a few % higher |

Default is true because the noai branch exists for stability reasons — sticking to that philosophy is the right default. Flip it if you have AC power, a stationary Pi, and want to squeeze out the last few percent of capture rate.

```toml
main.plugins.envtune.prefer_stability = false
```

## What it actually learns

Two bandits, layered:

1. **Per-context parameter bandit.** For each of 14 personality parameters (`min_rssi`, `recon_time`, `ap_ttl`, `throttle_a`, `throttle_d`, `max_interactions`, …) it picks the value that's been working best for the current context. Context = `(AP density × time of day × mobility)` = 24 cells.

2. **Strategy meta-bandit.** Every ~30 minutes, envtune runs one of three channel-scheduling strategies (`adaptive`, `full`, `capped`), measures the unique-handshake rate during that block, and uses that to decide which strategy to run next. Stationary and moving each have their own strategy bandit — the right answer is often different.

Both use UCB1. The reward signal is **lifetime-new** unique BSSIDs per minute, Hill-saturated against an adaptive target (90th percentile of recent rates). Catching the same network twice doesn't move the needle.

The state is persisted to `/etc/pwnagotchi/envtune_state.json` and survives reboots. The schema is versioned and migrates forward — older saves load cleanly.

## Sharing learning with the community

You can export your learned state for other people to bootstrap from:

```bash
curl -o my_envtune_export.json http://<pi>:8080/plugins/envtune/export
```

The default endpoint **anonymises GPS zones** (their raw keys are reversible to lat/lon at ~150m precision — sharing those would dox you), strips your captured BSSID list (publicly geolocatable via WiGLE), and removes the wpa-sec cracked list. It preserves the actually-useful part: which parameters and channels worked across which contexts.

To use someone else's anonymised export:

```bash
mkdir -p /etc/pwnagotchi/envtune_priors
mv someone_elses_export.json /etc/pwnagotchi/envtune_priors/
# Restart pwnagotchi or reload the plugin
```

On startup envtune merges any `.json` files in that directory into its learning table at low weight (60% community signal, 40% neutral), capped at 5 samples per arm per file. You get a head start; your own real evidence overrides as soon as it accumulates.

For your own backup (don't share): `?full=1` gives you the unredacted JSON.

## Common config

```toml
# Only the most useful overrides — defaults are good for most people.

# Lock in one strategy if you've decided what works for you
main.plugins.envtune.channel_strategy = "adaptive"   # or "full", "capped", "auto" (default)

# More conservative if you want better thermal/battery margins
main.plugins.envtune.prefer_stability = true     # default
main.plugins.envtune.cpu_profile      = "light"  # default auto-detected

# More aggressive if your Pi is stationary on AC and you want max yield
main.plugins.envtune.prefer_stability = false
main.plugins.envtune.cpu_profile      = "aggressive"   # or "beast" on Pi 4/5

# Turn off the meta-bandit and keep the existing channel order untouched
main.plugins.envtune.channel_strategy      = "capped"
main.plugins.envtune.respect_full_channels = true
```

Every value in the plugin's `DEFAULTS` is overridable under `main.plugins.envtune.<key>`. Out-of-range values are clamped with a warning at startup (envtune validates its own config).

## Known limits

Some honest things you should know:

- **The plugin needs data to be useful.** First couple hours look about the same as stock noai. After that, you start to see it pick different parameters in different contexts.
- **It can't fix bad antennas or weak signals.** No amount of parameter tuning beats a better radio location.
- **Strategy convergence takes about 6 hours of operation.** If you reboot every 30 minutes, the strategy bandit never settles. The parameter bandit converges per-context — moving fast through many contexts means each one gets less data.
- **The dashboard auto-refreshes every 30 seconds.** That's a deliberate trade-off — feels live, doesn't hammer the Pi. Add `?norefresh=1` to the URL when you're inspecting a value carefully.
- **By default, opportunistic channel overrides are disabled.** Even with `prefer_stability=false`, this only matters if you've also un-silenced `wifi.client.new` in your `bettercap.silence` list (which noai silences by default). The plugin will log a notice at startup if those events are unavailable.

## When something looks wrong

The plugin logs everything that matters at INFO level. The startup line tells you:

```
[envtune] active and learning (tuning 15 params, STABILITY mode (noai-aligned: ...))
[envtune] handshake dir resolved: /etc/pwnagotchi/handshakes
[envtune] +N BSSIDs adopted from real handshake dir (...)
```

If `handshake dir resolved:` doesn't match your real handshake directory, something's off in your bettercap config. If `+0 BSSIDs adopted` and you have pcaps, the filename format on your fork might be unexpected (envtune extracts BSSIDs from `<ssid>_<bssid>.pcap` filenames; some forks use different conventions).

The dashboard's **Status** panel honestly reports which optional features are active or unavailable:

- "GPS source: off (mobility via AP-turnover heuristic)" — no GPS plugin detected, falling back
- "Battery: not detected (no PiSugar / no UI element)" — battery awareness skipped
- "Cracked (wpa-sec): not configured" — no potfile, the wpa-sec feedback loop is dormant
- "Community priors: 0 file(s) in /etc/pwnagotchi/envtune_priors" — no community exports loaded

None of those make the plugin malfunction. They just mean specific features aren't doing anything because the prerequisites aren't there.

If you want a fresh start: stop pwnagotchi, delete `/etc/pwnagotchi/envtune_state.json`, restart. Captured-BSSID tracking rebuilds from your handshakes directory automatically.

## Endpoints

| URL | What it gives you |
|---|---|
| `/plugins/envtune/` | Dashboard |
| `/plugins/envtune/?ap_filter=uncaptured` | Dashboard with the AP list filtered |
| `/plugins/envtune/?norefresh=1` | Pause auto-refresh |
| `/plugins/envtune/export` | State JSON, anonymised — safe to share |
| `/plugins/envtune/export?full=1` | State JSON, raw — your backup |
| `/plugins/envtune/metrics` | Prometheus metrics |
| `/plugins/envtune/zones` | Per-zone productivity, anonymised |
| `/plugins/envtune/force-save` (POST) | Flush state to disk now |
| `/plugins/envtune/rescan-potfile` (POST) | Re-read wpa-sec.cracked.potfile |
| `/plugins/envtune/reset-stagnation` (POST) | Clear stagnation streak, force exploration |
| `/plugins/envtune/clear-blind` (POST) | Clear blind-panic counter |

POST endpoints use Flask-WTF's CSRF token, the standard pwnagotchi mechanism.

## Credits

- [evilsocket](https://github.com/evilsocket) — original pwnagotchi
- [jayofelony](https://github.com/jayofelony) — noai fork
- [Sniffleupagus](https://github.com/Sniffleupagus) — the `auto_tune` plugin envtune started life copying from
- [AlienMajik](https://github.com/AlienMajik) — TheyLive GPS plugin



