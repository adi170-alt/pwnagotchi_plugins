    #!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
envtune.py  —  Adaptive Environment Tuner for Pwnagotchi
=========================================================
Version   : 2.2.0
License   : MIT
Repository: https://github.com/adi170-alt/envtune

Changelog 2.1.0 → 2.2.0  (NOAI-ALIGNED: stability + battery first)
──────────────────────────────────────────────────────────────────

v2.2 audits every operation envtune performs against natural
pwnagotchi radio behaviour, and DEFAULTS conservative wherever we'd
add load beyond what noai does on its own.

NEW DEFAULTS
 • prefer_stability = True (DEFAULT). When True (the noai-aligned
   default):
     - enable_proactive is FORCED False regardless of CPU profile —
       no extra `wifi.assoc` frames beyond what pwnagotchi's natural
       loop fires. Operators who want max capture rate at the cost
       of slightly more radio load can set prefer_stability=False
       in config.toml.
     - opportunistic_overrides defaults to False. The runtime
       `wifi.recon.channel` poke when bettercap reports a new client
       is silenced (bettercap's silence list disables it by default
       anyway, so this is consistency hygiene rather than a behaviour
       change).
     - When mobility=moving AND prefer_stability=True, the
       channel_strategy meta-bandit is restricted to {capped, adaptive}
       — `full` is dropped from consideration so the Pi doesn't
       hammer the radio with multi-channel sweeps while walking.
       Battery saver.
 • prefer_stability = False restores v2.1 aggressive behaviour for
   operators who want maximum capture rate on a stationary Pi with
   AC power.
 • Startup log now states which mode is active so operators see the
   trade-off at boot.

DOC SWEEP
 • Module docstring rewritten to explicitly call out the noai-aligned
   philosophy. Plugin description updated.

The bandit math, the strategy meta-bandit, the mobility-aware
selection, and all v2.0 / v2.1 fixes are unchanged. v2.2 is purely
about defaulting the right way.

Changelog 2.0.0 → 2.1.0  (verified against noai source + original AI)
─────────────────────────────────────────────────────────────────────
After cross-referencing against the actual noai pwnagotchi source,
the original removed AI module (ai/reward.py, gym.py, epoch.py), and
the auto_tune_new.py predecessor, several fingerprint mismatches were
found and fixed. v2.1 is the version that actually does what v2.0
*claimed* to do.

CRITICAL FIX
 • HANDSHAKE_DIR was hardcoded to '/root/handshakes' in v1.x and v2.0.
   The noai default is '/etc/pwnagotchi/handshakes' (per defaults.toml
   and bettercap config). On every default install since v1.0, the
   lifetime-new-handshake tracking found NOTHING at startup — every
   pre-existing capture looked "new" the first time it was re-seen,
   inflating reward and crediting the bandit for things it never did.
   v2.1 reads the path from agent._config['bettercap']['handshakes']
   in on_ready, with a sane fallback to the noai default. The wpa-sec
   potfile is now resolved next to the real handshakes dir.

ALGORITHMIC ADDITIONS
 • New UCB arm: excited_num_epochs (verified in noai personality
   defaults at value 10). The original AI tuned this; v2.0 missed it.
 • New EMAs tracking: num_peers (mesh peers), mem_usage (Pi memory
   pressure), slept_for_secs (epoch sleep time). All three are first-
   class noai _epoch_data fields that v2.0 ignored. Now available for
   future reward-function refinements and ops dashboards.

OBSERVABILITY
 • Bettercap silence-list detection at on_ready: pwnagotchi defaults
   to silencing wifi.ap.new/lost and wifi.client.new/lost, which
   disables our on_bcap_* handlers (opportunistic-channel override,
   live AP/client tracking). v2.1 logs a WARNING listing the silenced
   tags so operators understand WHY the feature is dormant — and tells
   them how to enable it (remove tags from bettercap.silence in
   config.toml).
 • Handshake-count sanity check: cross-references our BSSID-extracted
   count against pwnagotchi's pcap-file count. If they diverge >2×,
   the operator gets a WARNING — usually means the fork uses an
   unexpected filename convention.

Changelog 1.9.0 → 2.0.0 
─────────────────────────────────────────────
v2.0 is the production-ready, "no-tuning-needed" release. It consolidates
every correctness fix, hardens robustness for bare-bones setups, adds the
observability needed to operate at scale, and ships ONE major algorithmic
upgrade: the strategy meta-bandit is now mobility-aware.

ALGORITHMIC UPGRADE
 • Mobility-aware strategy bandit. v1.9.0 had a single 3-arm bandit
   over (adaptive, full, capped). v2.0 has TWO 3-arm bandits — one for
   `stationary`, one for `moving`. This matters because:
     - When stationary: capped/adaptive consistently win (Pareto λ).
     - When moving: full sweep is often best (entering new λ
       distributions every block, capped lacks discovery time).
   The bandit learns which strategy fits each mobility independently.
   v1.9 state migrates: existing strategy stats are seeded into BOTH
   mobility cells as warm priors so no learning is lost.

CORRECTNESS FIXES (16 total)
 F-01: warmstart_prior_reward fallback default now matches DEFAULTS (0.30).
 F-02: warmstart docstring updated to reflect v1.7 neutral-prior semantics.
 F-03: New PRIOR_NEUTRAL_R class constant; the magic 0.30 is no longer
       duplicated in three places (TOD prior, warmstart-replace check,
       UI prior badge).
 F-04: Strategy meta-bandit reward target is now ADAPTIVE (matches the
       param bandit's _adaptive_hpm_target). Was fixed at 0.5 unique/ep
       — meaningless in sparse environments where no block could ever
       earn a high reward and the bandit couldn't differentiate.
 F-05: auto_strategy_block_secs new option (default 1800s = 30 min).
       Replaces auto_strategy_block_epochs which was epoch-count based
       and silently misbehaved on Pis with non-default epoch periods.
       The epochs-based option is kept for back-compat.
 F-06: Strategy bandit recovers gracefully on location change. The
       block in progress is dropped (its reward would credit the wrong
       environment); the next block starts fresh under the new
       mobility's strategy bandit.
 F-08: Thermal recovery now restores pre-throttle parameter values
       instead of leaving them at the elevated values until the next
       UCB select cycle.
 F-09: _strategy_block_start_ep initialises to None instead of -999
       (the latter was a dead sentinel, the cold-start branch always
       overwrites it).
 F-10: mood_threshold_epochs now in DEFAULTS (was hardcoded 5).
 F-11: Documentation sweep — every "v1.5 schema" reference updated to
       "v4 schema"; stale comments referring to deleted code removed.
 F-12: last_shake initial state includes all fields the UI may read,
       so first-load UI doesn't see partial dict.
 F-13: _chistos session-stats dict is now bounded (cap 200 channels;
       LRU eviction). Was unbounded; over months of operation could
       accumulate stale per-channel counters.
 F-14: proactive_min_rssi documented as deliberately decoupled from
       the bandit's min_rssi arm (different concept: bandit chooses
       FILTER threshold, proactive uses ATTACK threshold).
 F-15: "Long recon cycle" warning fires only when channel_strategy is
       explicitly "full" — not on auto-mode's periodic full sweeps,
       which were generating false-alarm warnings.
 F-16: import copy moved to top of file (was inline in _anonymise_export).

OBSERVABILITY
 • Prometheus /metrics endpoint now exports strategy-bandit telemetry:
     envtune_strategy_blocks_total{strategy,mobility}
     envtune_strategy_mean_reward{strategy,mobility}
     envtune_strategy_current_block_uniques (current block progress)
 • envtune_exception_count{handler} counter — lets ops dashboards
   detect when an event handler is consistently failing.
 • Pwnagotchi version compatibility check at on_loaded: warns if
   running on a version outside the tested range (1.8.x noai).
 • Cfg validation at on_loaded: every value type-checked, out-of-range
   values logged as warnings (not silently used).

ROBUSTNESS
 • /export uses a cached state snapshot refreshed by the save thread
   instead of building a fresh snapshot on the webhook thread (which
   was a 50–200ms operation on Pi Zero 2 W).
 • _chistos cap (see F-13).

DOCS
 • Comprehensive doc sweep — all version-referenced comments updated.
 • Module docstring rewritten as the v2.0 reference.

UPGRADE PATH FROM v1.9
 No config changes required. Existing state loads cleanly. The flat
 strategy_bandit dict in old state is automatically split into the
 new mobility-aware structure (stationary + moving each get the v1.9
 stats as priors). State JSON schema_version stays at 4.

Changelog 1.8.1 → 1.9.0  (true AI behaviour: strategy auto-selection)
─────────────────────────────────────────────────────────────────────
The plugin can now auto-select its own channel scheduling strategy,
in addition to auto-tuning its 14 personality parameters. This makes
envtune genuinely "self-driving" — there is no longer a "right" config
the user has to pick, the plugin learns what's right for THEIR Pi in
THEIR environment.

 • New default `channel_strategy = "auto"` — meta-bandit at the
   strategy level. The plugin runs each strategy (adaptive/full/capped)
   for a block of `auto_strategy_block_epochs` (default 30 ≈ 30 min),
   measures the unique-HS-per-epoch rate, scores it via the same
   Hill-saturated reward function the param bandit uses, and updates
   each strategy's UCB1 stats. After the cold-start phase (each
   strategy run once = ~90 min), pure UCB1 picks the next block:
     score(s) = mean(s) + auto_strategy_c × sqrt(log(N_total) / n_s)
   The leader settles within ~6 hours. Convergence accelerates if
   the environment has clear winners, slows in marginal cases — both
   are correct UCB behaviours.
 • Strategy bandit state is persisted in state JSON, so learning
   survives restarts. Schema-tolerant load (unknown strategies are
   ignored, missing strategies stay cold-start-eligible).
 • New web UI panel "🤖 Auto-strategy meta-bandit" shows per-strategy
   blocks-evaluated, mean reward, recent rewards, current block
   progress, and the leader. Operators see the AI learning live.
 • Subtitle indicator: `channels=auto→adaptive (block 12/30)` so the
   active strategy + block progress are visible at a glance.
 • Block-end log line: `auto-strategy block done: adaptive →
   X unique HS in 30 ep (reward=Y). Next block: full` — operators
   can correlate HS bursts with strategy choices in the system log.

If you prefer to lock in one strategy (e.g. you've verified your
environment and want pure exploitation), set explicitly in config.toml:
  main.plugins.envtune.channel_strategy = "adaptive"   # or full / capped

Changelog 1.8.0 → 1.8.1  (robustness for bare-bones setups)
───────────────────────────────────────────────────────────
EnvTune is designed to work fully even when optional features are
absent. v1.8.1 cleans up several places where the code wasn't quite
honouring that promise.

 • cracked_bssids: state-load now MERGES with the live potfile instead
   of REPLACING. The comment in _load_state explicitly said "safety net
   rather than the source of truth", but on_loaded was overwriting.
   Cases this fixes:
     - User used wpa-sec briefly, then disabled it: state had cracks,
       now they survive.
     - Potfile got rotated/truncated: cracks remembered.
     - Pi without wpa-sec at all: still works (set just stays empty).
   Same fix applied to the periodic rescan in on_epoch and the
   "Rescan potfile" web action.
 • Anonymised export now strips captured_bssids and cracked_bssids.
   These are publicly geolocatable via WiGLE (https://wigle.net) and
   sharing them effectively reveals approximate locations the operator
   has been. Counts are preserved so the receiver knows roughly how
   seasoned the contributing operator is.
 • Anonymised export also redacts ema.speed (GPS-derived mobility
   signal).
 • Community-priors merge ONLY reads ucb_table — defensive against an
   operator accidentally dropping a non-anon export into the priors
   directory. captured_bssids / cracked_bssids / gps_zones / EMA from
   community files are now ignored.
 • Status panel now shows feature availability honestly:
     - "GPS source: off (mobility via AP-turnover heuristic)"
     - "Battery: not detected (no PiSugar / no UI element)"
     - "Cracked (wpa-sec): not configured" when no potfile exists
     - "Channel universe: 11 channels (2.4 GHz)" / "(2.4 + 5 GHz)"
     - "Community priors: 0 file(s) in /etc/pwnagotchi/envtune_priors"
       with hint to drop anon exports there
     - "Channel strategy: adaptive/full/capped"
   So operators of bare-bones setups understand at a glance what's
   active vs unavailable, and never wonder if "0" means broken.

Changelog 1.7.1 → 1.8.0
───────────────────────
 • New `channel_strategy` config option with three modes:
     - "adaptive" (DEFAULT, recommended): top-K productive channels
       most epochs (best HS yield) + full universe sweep every
       channel_full_sweep_every (default 15) epochs (~15 min) so the
       bandit re-checks channels that scored low historically.
     - "full":  legacy v1.7.1 behaviour — every channel every epoch.
     - "capped": legacy v1.5–v1.7.0 — top-K only, no sweeps.
 • The adaptive default is the math-optimal trade-off: in a Pareto
   λ_total distribution (the typical Wi-Fi environment), capped mode
   yields ~32% more handshakes per epoch than full mode because each
   channel gets more time. Adaptive sacrifices ~3% yield to get full
   coverage every 15 epochs — discovering new productive channels
   without paying the per-epoch coverage tax.
 • The legacy `respect_full_channels` flag is now a back-compat alias:
   True → "full", False → "capped". Unset (== None default in the new
   DEFAULTS) → falls through to channel_strategy="adaptive".
 • UI subtitle shows current strategy + countdown to next adaptive
   sweep. Hover for explanation.
 • Adaptive sweep is logged at INFO level when it fires, so operators
   can correlate handshake bursts with sweep epochs.

Changelog 1.7.0 → 1.7.1
───────────────────────
 • respect_full_channels (default True): the user's `personality.channels`
   from config.toml is now the channel universe. The bandit re-orders
   channels by score so the most-productive lead the hop cycle, but
   NEVER returns a smaller list than the user configured. v1.5–v1.7.0
   silently truncated long user-configured lists down to 14 channels
   (the recon-cycle cap). The cap is now legacy-only; set
   respect_full_channels=false in config.toml to restore it.
 • Empty `personality.channels` (= "scan all" in pwnagotchi semantics)
   now expands to the iface's full hardware-supported list, including
   5 GHz channels 36–165, instead of being clamped to 1–11.
 • Opportunistic-channel-override (when bettercap reports a new client)
   no longer pushes channels OUTSIDE the user's universe.
 • Long-recon-cycle warning logged once every 50 epochs when the user's
   universe makes the hop cycle exceed 120 s, so operators see the
   trade-off they're choosing.

Changelog 1.6.0 → 1.7.0  (driven by analysis of community v1.3 exports)
───────────────────────────────────────────────────────────────────────
Algorithmic
 • warmstart_prior_reward default lowered 0.45 → 0.30 (neutral). Real
   community telemetry showed that the 0.45 bias toward the user's
   existing pwnagotchi defaults locked the bandit onto suboptimal arms
   for thousands of epochs (e.g. ap_ttl=120 accumulating 3944 samples
   at mean reward 0.064 — the worst arm — while the truly-best arm
   ap_ttl=60 only got 211). At 0.30 the synthetic sample still satisfies
   UCB's "every arm tried once" property without actively misleading
   selection.
 • Forced-exploration floor: every `forced_explore_every` epochs, if
   the current state has any arm with n < 5 across the active params,
   the bandit overrides UCB and picks the most-starved arm instead.
   Closes the v1.5/v1.6 starvation pattern where arms like
   `min_recon_time=4` (n=35, mean=0.212 — the BEST observed) never got
   enough samples to escape their wide UCB bounds.
 • Location change no longer neutral-credits buffered decisions with
   reward 0.5. Real telemetry showed those neutral credits drift state
   means toward 0.5, hiding both genuinely-bad and genuinely-good arms.
   Buffered decisions are now dropped entirely on location change —
   the new environment gets a clean exploration phase via the existing
   exploration_boost mechanism.
 • Channel-efficiency multiplier strengthened. Was `0.5 + eff*3.0`
   capped 0.5–1.5×; community channel data showed channel 7 with 16.5%
   HS/attack getting essentially 1.0× boost while losing to channel 1
   (8% efficiency, 10× more raw HS) on absolute-score grounds. Now
   `0.5 + eff*5.0` capped 0.4–2.5× — a 16% channel gets 1.32×, a 20%
   channel gets 1.5×.

Robustness
 • EMA denormal floor: any [0,1]-clamped EMA below 1e-6 snaps to 0.
   Telemetry from real users showed `hs_rate=2.4e-15`,
   `missed_rate=2.3e-28` — mathematically valid exponential decay but
   meaningless to the bandit, and dangerous because the next non-zero
   sample creates an enormous EMA jump that the reward function
   misattributes to whichever arm was chosen.
 • Schema migration v3 → v4 verified end-to-end against four real
   community exports (108-state schema → 24-state schema, all 432
   migrated states have valid 3-component keys, mobility correctly
   collapsed walking+mobile → moving).

UI / community
 • Starved-arm warning column in the UCB Learning panel — flags arms
   with mean > 0.30 but n < 5 so operators can see what the bandit is
   missing.
 • New `POST /import-priors` endpoint accepts a community export JSON
   and merges its UCB samples into the local table at low weight (each
   imported reward weighted as 0.4× a real local observation). This
   lets new users bootstrap from collective wisdom instead of running
   ~200 epochs of cold-start.

Changelog 1.5.0 → 1.6.0
───────────────────────
Correctness
 • Hierarchical prior restored — schema-3 length check (was len==4 left
   over from the v1.4 → v1.5 schema collapse, leaving the empirical-Bayes
   shrinkage falling back to flat population mean across all 24 states).
   Neighbour states now actually contribute extra weight again.
 • `reset_history` default now agrees in DEFAULTS and at the call site
   (was True at the .get() fallback, False in DEFAULTS — destructive if
   the key ever went missing).
 • `stagnation_boost_epochs` added to DEFAULTS — was referenced by the
   reset-stagnation web action but never actually overridable.
 • PMF re-evaluation now clears the detection timestamp too, so a second
   detection isn't compared against a stale age.
 • Named module logger ('envtune') instead of mutating the ROOT logger
   level — debug logs no longer flood every other Pwnagotchi component.
 • `_decision_buffer` maxlen now scales with reward_delay, so users with
   sparse-environment configs no longer silently lose attribution.
 • `_save_worker` drain loop preserves the latest snapshot even when a
   shutdown sentinel arrives mid-coalesce.

Performance
 • `_ch_score` memoised per-epoch — was O(channels² · known_aps) per
   epoch, now O(channels · known_aps) once; ~5–10× faster scheduling
   on dense environments.
 • Total-samples counter for shrinkage anneal — `_current_shrinkage_k`
   no longer walks the entire UCB table (~9k cells) every selection.

Concurrency
 • `_unscanned_channels`, `_active_channels`, `_dead_session` now read
   under `_state_lock` consistently — were mutated under lock in
   on_wifi_update but read lockless in `_schedule_channels`.

Algorithmic
 • RSSI weighting in `_ap_priority_score` is now geometric (RSSI is
   logarithmic in dB — strong signals succeed disproportionately).
 • `_recent_hpm` and `_reward_history` persisted across restarts so the
   adaptive HPM target doesn't degrade to the floor for ~10 epochs on
   every reload.

Hygiene
 • Dead code removed: legacy `_sw_ucb_pick` (replaced by with_state
   variant), `_hierarchical_marginal` (subsumed by shrinkage),
   `abort` import, `session_start_wall` (unused), `cracked` channel
   counter (was never written, only read).


A drop-in replacement for the removed pwnagotchi AI, built specifically
for jayofelony/pwnagotchi (noai branch). Uses Sliding-Window UCB1 — a
proven reinforcement learning technique — with a contextual state space
extended by GPS zones, thermal safety, client awareness, and smart
channel scheduling. Gets measurably better every session.

Why this exists
───────────────
Jay removed the A2C neural network because it destabilised the wifi
firmware and drained batteries. The stock pwnagotchi is still strong,
but runs on fixed parameters — it can't adapt to your specific routes,
times, or environments. EnvTune fills that gap using lightweight ML
(≈ 2-3% CPU on a Pi Zero 2 W) that cannot crash the radio.

What it learns per environmental context
─────────────────────────────────────────
14 personality parameters across 24 contexts (density × time × mobility).
UCB1 with a sliding window means the learning adapts as environments
change — a stale memory of "what worked in 2024" does not override
fresh evidence of "what works here now".

Key capabilities
────────────────
 • 14-parameter UCB learning (ALL verified against jayofelony defaults)
 • Hierarchical priors so rare contexts benefit from common ones
 • Proper bettercap sync for wifi.ap.ttl / sta.ttl / min.rssi
 • GPS zone-aware learning (optional, auto-detects TheyLive/stock gps)
 • Stationary vs mobile detection via speed/AP-turnover
 • Heatmap of captures with zone productivity scoring
 • Thermal safety (Pi can crash >80°C — we back off at 70°C)
 • Client-aware targeting (deauth needs clients; PMKID doesn't)
 • PMF detection (stops wasting deauths on protected networks)
 • Per-AP cooldown on persistent non-responders
 • Already-captured detection from /root/handshakes/
 • Free-channel opportunism via on_free_channel callback
 • PiSugar battery awareness (optional, graceful)
 • wpa-sec cracked-feedback loop (if potfile exists)
 • Whitelist respect (doesn't skew learning on skipped APs)
 • Nexmon crash detection + automatic backoff
 • Async state save (no SD-card IO stalls mid-epoch)
 • Version-migrated state (survives plugin upgrades)
 • Full web UI at /plugins/envtune/ with explanatory tooltips
 • Five CPU profiles: minimal, light, balanced, aggressive, beast

Requirements
────────────
 • jayofelony/pwnagotchi (noai branch)     — verified compatible
 • Python 3.7+                             — part of stock image
 • No extra pip packages                   — uses only stdlib + flask

Installation
────────────
 1) Copy this file to /usr/local/share/pwnagotchi/custom-plugins/envtune.py
 2) In /etc/pwnagotchi/config.toml add:

        main.plugins.envtune.enabled = true

 3) (Optional) pick a CPU profile for your hardware:

        main.plugins.envtune.cpu_profile = "balanced"
        # choices: "minimal" "light" "balanced" "aggressive" "beast"
        # default: auto-detects based on /proc/cpuinfo

 4) (Optional) GPS integration — works automatically if TheyLive or
    stock gps plugin is enabled. No config required.

 5) (Optional) PiSugar — automatically detected if pisugarx is enabled.

 6) (Optional) Turn off stock auto_tune if you use it — envtune replaces
    it completely.

 7) Reboot. First 20 epochs = warmup + exploration. After ~200 epochs
    the plugin begins consistently choosing optimal parameters for each
    state you encounter. It gets smarter forever.

Config presets (add to config.toml to override defaults)
─────────────────────────────────────────────────────────
For aggressive wardriving:
    main.plugins.envtune.cpu_profile = "aggressive"
    main.plugins.envtune.temp_critical = 80.0
    main.plugins.envtune.extra_channels = 5

For stealthy home use:
    main.plugins.envtune.cpu_profile = "light"
    main.plugins.envtune.ucb_c = 1.0
    main.plugins.envtune.opportunistic_overrides = false

For max learning on strong hardware (Pi 4/5):
    main.plugins.envtune.cpu_profile = "beast"
    main.plugins.envtune.ucb_window = 80
    main.plugins.envtune.save_every_n_epochs = 10

Web UI
──────
http://<pwnagotchi>:8080/plugins/envtune/
Shows live stats, UCB learning table, channel productivity, AP
intelligence, GPS zones, and thermal status. Hover any value for an
explanation.

Credits
───────
Built on top of prior art by:
  • @evilsocket   — original pwnagotchi
  • @jayofelony   — noai fork
  • @Sniffleupagus — auto_tune plugin
  • @AlienMajik — TheyLive GPS plugin
"""

import copy
import html
import json
import logging
import math
import os
import queue
import random
import tempfile
import threading
import time
from collections import defaultdict, deque

import pwnagotchi.plugins as plugins
import pwnagotchi.utils
from flask import make_response, render_template_string
# Optional: pwnagotchi wraps Flask with CSRFProtect; render_template_string
# exposes csrf_token() automatically. We don't import it directly — it's
# resolved via the Jinja env at template-render time.

# Module-level logger. Using the named logger ('envtune') instead of the
# root logger means setting log_level here does NOT flood every other
# Pwnagotchi component (bettercap-bridge, mesh, other plugins) with
# debug output. v1.6 fix.
log = logging.getLogger('envtune')


# ═══════════════════════════════════════════════════════════════════════════
# Small helpers
# ═══════════════════════════════════════════════════════════════════════════

def _si(v, default=0):
    """Safe int cast — never raises."""
    try:
        return int(v) if v is not None else default
    except (TypeError, ValueError):
        return default


def _sf(v, default=0.0):
    """Safe float cast — never raises."""
    try:
        return float(v) if v is not None else default
    except (TypeError, ValueError):
        return default


def _haversine_m(lat1, lon1, lat2, lon2):
    """Great-circle distance in metres between two (lat, lon) pairs."""
    R = 6371000.0
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2)
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _is_valid_mac(mac):
    """Validate a MAC string of form aa:bb:cc:dd:ee:ff."""
    if not mac or not isinstance(mac, str):
        return False
    parts = mac.split(':')
    if len(parts) != 6:
        return False
    for p in parts:
        if len(p) != 2 or not all(c in '0123456789abcdefABCDEF' for c in p):
            return False
    return True


def _format_mac_colons(mac_n):
    """Convert normalised 12-char MAC to colon-separated form. Returns '' on bad input."""
    if not mac_n or len(mac_n) != 12:
        return ''
    return ':'.join(mac_n[i:i+2] for i in range(0, 12, 2))


def _detect_hardware():
    """
    Detect Pi hardware for CPU profile defaults.
    Returns one of: 'pi_zero', 'pi_zero_2', 'pi_3', 'pi_4', 'pi_5', 'unknown'

    Detection priority (FIX in v1.4.1):
      1. The model string from `/proc/cpuinfo`'s "Model" line — the
         most specific and reliable signal. e.g. "Raspberry Pi 3 Model
         B Rev 1.2" or "Raspberry Pi Zero 2 W Rev 1.0".
      2. SoC chip codes — bcm2710 (Pi 0 2W), bcm2837 (Pi 3), bcm2711
         (Pi 4), bcm2712 (Pi 5).
      3. CPU core (cortex-a53 etc.) is intentionally NOT used as a
         primary signal: both Pi 0 2W and Pi 3 use Cortex-A53, so
         matching on it would cause Pi 3 to be misclassified as Pi 0
         2W (and pick the wrong CPU profile).

    Also reads `/proc/device-tree/model` as a fallback — that file
    contains exactly "Raspberry Pi 3 Model B Plus Rev 1.3" etc. on
    modern kernels and is more deterministic than cpuinfo.
    """
    info = ''
    try:
        with open('/proc/device-tree/model') as f:
            info += f.read().lower() + '\n'
    except Exception:
        pass
    try:
        with open('/proc/cpuinfo') as f:
            info += f.read().lower()
    except Exception:
        pass

    if not info:
        return 'unknown'

    # Most-specific model strings first. The order matters: 'pi zero 2'
    # is checked before 'pi zero' so the 2W isn't matched by both.
    if 'raspberry pi zero 2' in info or 'pi zero 2' in info:
        return 'pi_zero_2'
    if 'raspberry pi 5' in info or 'pi 5' in info:
        return 'pi_5'
    if 'raspberry pi 4' in info or 'pi 4' in info:
        return 'pi_4'
    if 'raspberry pi 3' in info or 'pi 3' in info:
        return 'pi_3'
    if 'raspberry pi zero' in info or 'pi zero' in info:
        return 'pi_zero'

    # SoC fallback. Each chip is unique to one Pi model so this is safe.
    if 'bcm2712' in info:
        return 'pi_5'
    if 'bcm2711' in info:
        return 'pi_4'
    if 'bcm2710' in info:
        return 'pi_zero_2'
    if 'bcm2837' in info:
        return 'pi_3'
    if 'bcm2835' in info:
        return 'pi_zero'

    return 'unknown'


# CPU profile definitions — balance between learning quality and CPU
#
#   ucb_window          — how many recent rewards UCB remembers per arm
#   zone_resolution_m   — GPS zone cell size (smaller = more zones = harder to learn)
#   save_every_n        — how often to persist state to SD card
#   ap_track_max        — hard cap on AP dict size (memory control)
#   extra_channels      — how many non-active channels to include per hop
#   ucb_cache_epochs    — cache UCB selections for N epochs (saves math)
#   enable_proactive    — permit opportunistic wifi.assoc injection
CPU_PROFILES = {
    'minimal': {
        'ucb_window': 20, 'zone_resolution_m': 300, 'save_every_n': 15,
        'ap_track_max': 150, 'extra_channels': 2, 'ucb_cache_epochs': 3,
        'enable_proactive': False,
    },
    'light': {
        'ucb_window': 30, 'zone_resolution_m': 200, 'save_every_n': 10,
        'ap_track_max': 250, 'extra_channels': 3, 'ucb_cache_epochs': 2,
        'enable_proactive': False,
    },
    'balanced': {
        'ucb_window': 40, 'zone_resolution_m': 150, 'save_every_n': 5,
        'ap_track_max': 400, 'extra_channels': 3, 'ucb_cache_epochs': 1,
        'enable_proactive': True,
    },
    'aggressive': {
        'ucb_window': 60, 'zone_resolution_m': 100, 'save_every_n': 5,
        'ap_track_max': 600, 'extra_channels': 4, 'ucb_cache_epochs': 1,
        'enable_proactive': True,
    },
    'beast': {
        'ucb_window': 80, 'zone_resolution_m': 75, 'save_every_n': 5,
        'ap_track_max': 1000, 'extra_channels': 5, 'ucb_cache_epochs': 0,
        'enable_proactive': True,
    },
}

# Hardware → default profile
HW_DEFAULT_PROFILE = {
    'pi_zero':   'light',
    'pi_zero_2': 'balanced',    # that's you — Pi Zero 2 W overclocked
    'pi_3':      'balanced',
    'pi_4':      'aggressive',
    'pi_5':      'beast',
    'unknown':   'balanced',
}


# ═══════════════════════════════════════════════════════════════════════════
# Main Plugin class
# ═══════════════════════════════════════════════════════════════════════════

class EnvTune(plugins.Plugin):
    __author__      = 'adi1708'
    __version__     = '2.2.0'
    __license__     = 'MIT'
    __description__ = ('Adaptive environment tuner — drop-in replacement '
                       'for the removed pwnagotchi AI. Learns optimal '
                       'parameters per context using Sliding-Window UCB1, '
                       'with GPS zones, thermal safety, and smart channel '
                       'scheduling. Maximises unique handshake captures.')

    # ── Paths ─────────────────────────────────────────────────────────────
    STATE_PATH    = '/etc/pwnagotchi/envtune_state.json'
    GPS_TRACK     = '/root/pwnagotchi_gps_track.ndjson'   # TheyLive
    # v2.1.0: HANDSHAKE_DIR is now a FALLBACK only. The real path comes
    # from agent._config['bettercap']['handshakes'] which the noai
    # default sets to '/etc/pwnagotchi/handshakes' — NOT /root/handshakes
    # as v1.x and v2.0 hardcoded. That meant lifetime-new-handshake
    # tracking was silently empty on every noai install since v1.0.
    # The actual path is captured in on_ready into self._hs_dir.
    HANDSHAKE_DIR_FALLBACK = '/etc/pwnagotchi/handshakes'
    # Likewise, the wpa-sec potfile lives next to the handshakes dir
    # (configurable via wpa-sec plugin's path setting). We resolve it
    # in on_ready from the live handshakes dir.
    WPASEC_POT_FALLBACK    = '/etc/pwnagotchi/handshakes/wpa-sec.cracked.potfile'
    # v1.7: community-priors directory. Drop anonymised export.json
    # files here (anything ending .json) and the plugin will merge
    # their UCB samples into the local table at low weight on startup.
    # Lets new users bootstrap from collective wisdom instead of
    # running ~200 epochs of cold-start. Files are scanned once at
    # `on_loaded`; rename or move them to disable.
    COMMUNITY_PRIORS_DIR = '/etc/pwnagotchi/envtune_priors'

    # State schema — bumped on breaking changes, migrate on load.
    #   v1, v2: density_tod_trend (3 dims, no mobility)
    #   v3:     density_tod_trend_mobility (4 dims, 108 states)
    #   v4:     density_tod_mobility (3 dims, 24 states; trend dropped,
    #           walking+mobile collapsed into 'moving'). v2.0 still v4 —
    #           the strategy_bandit shape change is migrated in-place,
    #           no schema bump needed for the param-bandit table.
    STATE_SCHEMA_VERSION = 4

    # v2.0: single source of truth for the cold-start neutral prior R.
    # Used in three places (TOD prior, warmstart-replace check, UI prior
    # badge). Must stay in sync with `warmstart_prior_reward` default —
    # they're conceptually the same number (the "no information" reward
    # level the bandit treats as equivalent to no data).
    PRIOR_NEUTRAL_R = 0.30

    # Pwnagotchi version compatibility — warn if outside this range so
    # operators know the plugin hasn't been verified on their fork.
    PWNAGOTCHI_VERIFIED_VERSIONS = ('1.8.', '1.9.', '2.')

    # ── UCB arms — VERIFIED against jayofelony defaults.toml (noai) ───────
    # Every single parameter here actually exists and affects pwnagotchi
    # behaviour. No fake parameters this time.
    UCB_ARMS = {
        # Core attack tuning
        'min_rssi':                  [-85, -80, -75, -70, -65],
        'hop_recon_time':            [4, 6, 8, 10, 12, 15],
        'min_recon_time':            [2, 3, 5, 7, 10],
        'recon_time':                [15, 20, 25, 30, 35, 45],
        'max_interactions':          [2, 3, 4, 5, 6],

        # AP/client retention in bettercap
        'ap_ttl':                    [60, 120, 180, 300, 600],
        'sta_ttl':                   [120, 300, 600, 900],

        # Recon dynamics (how pwnagotchi reacts to inactivity)
        'max_misses_for_recon':      [3, 5, 7, 10],
        'max_inactive_scale':        [2, 3, 5],
        'recon_inactive_multiplier': [1, 2, 3],

        # Jay's throttles (radio pause between attacks — float seconds)
        'throttle_a':                [0.2, 0.4, 0.6, 0.8, 1.0],
        'throttle_d':                [0.3, 0.5, 0.7, 0.9, 1.2],

        # Mood thresholds (how many epochs before pwnagotchi flips emotion).
        # These influence its decision to take a break / change mode and
        # therefore indirectly affect handshake productivity. The original
        # AI tuned these too — they are safe to learn (no firmware impact).
        # v2.1.0: added excited_num_epochs (verified in noai defaults.toml).
        'excited_num_epochs':        [5, 10, 15, 20],
        'bored_num_epochs':          [10, 15, 20, 25],
        'sad_num_epochs':            [15, 20, 25, 30],
    }

    # Hard bounds for safety clamping during panic/thermal modes
    BOUNDS = {
        'min_rssi':                  (-85,  -65),
        'hop_recon_time':            (4,     15),
        'min_recon_time':            (2,     10),
        'recon_time':                (15,    45),
        'max_interactions':          (2,      6),
        'ap_ttl':                    (60,   600),
        'sta_ttl':                   (120,  900),
        'max_misses_for_recon':      (3,     10),
        'max_inactive_scale':        (2,      5),
        'recon_inactive_multiplier': (1,      3),
        'throttle_a':                (0.2,  1.0),
        'throttle_d':                (0.3,  1.2),
        'excited_num_epochs':        (5,     20),
        'bored_num_epochs':          (10,    30),
        'sad_num_epochs':            (15,    30),
    }

    # Parameters that need explicit bettercap sync (wifi.* namespace).
    # Bettercap since commit 12a11ef applies these in realtime when
    # changed via "set" command. Writing the dict is NOT enough.
    BETTERCAP_SYNC_MAP = {
        'min_rssi': 'wifi.rssi.min',
        'ap_ttl':   'wifi.ap.ttl',
        'sta_ttl':  'wifi.sta.ttl',
    }

    # Non-overlapping channels get a scoring bonus (less interference)
    NON_OVERLAPPING = {1, 6, 11, 36, 40, 44, 48, 149, 153, 157, 161}

    # Mobility categories — v1.5 collapsed from 3-way to 2-way to
    # 4.5× the sample efficiency. Real-world data showed walking and
    # mobile produced near-identical optimal params (short ap_ttl,
    # shorter recon_time); only stationary was meaningfully different.
    MOBILITY_STATIONARY = 'stationary'  # < 0.5 m/s (≈ 1.8 km/h)
    MOBILITY_MOVING     = 'moving'      # ≥ 0.5 m/s (walking, biking, driving)
    # Legacy values — kept as constants for state migration. Code never
    # produces these any more, but old state files use them.
    MOBILITY_WALKING    = 'walking'
    MOBILITY_MOBILE     = 'mobile'

    # ── Default config (all overridable via main.plugins.envtune.*) ───────
    DEFAULTS = {
        # Core
        'cpu_profile':               None,     # auto-detect if None
        'ema_alpha':                 0.30,
        'warmup_epochs':             5,
        'dense_aps':                 25,
        'sparse_aps':                8,

        # UCB
        'ucb_c':                     1.4,
        'reward_delay':              3,
        'ucb_c_floor':               0.6,      # lowest C may decay to
        'ucb_c_anneal_epochs':       500,
        # Empirical-Bayes shrinkage strength (ANNEALED): with n local
        # samples per arm we trust the local mean by n/(n+k). Cold-start
        # we want HEAVY shrinkage (k_max≈5: at n=5 you're 50/50 with the
        # parent). Late-game we want LIGHT shrinkage (k_min≈1: at n=5
        # you're 83% local) so genuinely-better-but-undertested arms
        # aren't pulled back to the mediocre prior forever.
        # k decays linearly with total real samples observed, capped at
        # ucb_shrinkage_anneal_samples. Telemetry showed v1.1's fixed
        # k=5 was holding back arms like min_rssi=-75 (mean=0.40, n=13)
        # whose effective mean was being pulled down to ~0.37.
        'ucb_shrinkage_k_max':       5.0,
        'ucb_shrinkage_k_min':       1.0,
        'ucb_shrinkage_anneal_samples': 500,
        # Back-compat key — if user's config sets `ucb_shrinkage_k`
        # explicitly we keep using that as a fixed override (no anneal).
        'ucb_shrinkage_k':           None,

        # WARM-START strength. Whatever pwnagotchi's `personality.*`
        # values are at startup, the closest UCB arm in every state
        # gets seeded with a synthetic reward at this level.
        #
        # v1.7: lowered 0.45 → 0.30 (== neutral TOD prior). Real
        # community telemetry showed the 0.45 bias was sticky enough
        # to lock the bandit onto suboptimal user-defaults for
        # thousands of epochs (e.g. ap_ttl=120 accumulated 3944 samples
        # at mean reward 0.064 — the WORST arm — while ap_ttl=60, the
        # truly-best, only got 211). At 0.30 the synthetic sample still
        # satisfies UCB's "every arm tried once" property and seeds
        # the n=1 bucket so the bandit doesn't burn a real epoch on
        # cold-start trial — but it stops actively recommending the
        # user's default config when evidence says otherwise.
        # Set to >0.30 to re-enable the old "trust user settings" mode.
        'warmstart_prior_reward':    0.30,

        # Stagnation / exploration
        'stagnation_epochs':         12,
        'exploration_boost_c':       2.5,
        'exploration_boost_epochs':  6,
        # v1.7 forced-exploration floor. Every `forced_explore_every`
        # epochs, override UCB to pick the most-starved arm in the
        # current state for one randomly-chosen active param. Closes
        # the v1.5/v1.6 starvation pattern where promising arms with
        # n<5 never accumulate enough samples to escape their wide
        # UCB bound. Set to 0 to disable; default 8 epochs strikes
        # a balance (≈ 12% of decisions are forced explorations).
        # `forced_explore_starvation_n` is the n threshold below which
        # an arm counts as "starved."
        'forced_explore_every':           8,
        'forced_explore_starvation_n':    5,
        # Boost length when operator manually clicks "Reset stagnation"
        # in the web UI. Larger than the auto-detected boost because a
        # human-driven reset means the operator KNOWS something has
        # changed and we should explore aggressively. Was previously
        # read from cfg with a hardcoded fallback of 30 — now declared
        # so the option is actually honoured if set in config.toml.
        'stagnation_boost_epochs':   30,

        # Blind panic
        'blind_panic_epochs':        3,
        'blind_recovery_steps':      5,

        # AP targeting
        'ap_cooldown_attacks':       12,
        'ap_cooldown_short':         15,
        'ap_cooldown_long':          50,
        'pmf_attack_threshold':      10,
        'client_recency_epochs':     3,
        'missed_cooldown_threshold': 5,  # AP marked missed this many times → cooldown

        # Re-capture policy. The plugin's reward function and channel
        # scoring already favour brand-new BSSIDs (60% reward weight on
        # lifetime-new captures), so we DON'T need a hard exclusion of
        # already-captured APs to stay focused on uniques. Instead we:
        #   - keep already-captured APs in the attack queue with low but
        #     non-zero priority (so opportunistic re-captures still
        #     happen — useful when a fresh client appears, when the AP's
        #     PSK might have rotated, or when an earlier capture was
        #     incomplete);
        #   - only ask bettercap to skip CRACKED BSSIDs by default (we
        #     have the password — no point recapturing).
        # Set bcap_skip_captured=true to restore the old v1.2 behaviour
        # where every captured BSSID is excluded at the bettercap level.
        'bcap_skip_captured':            False,
        'bcap_skip_cracked':             True,
        # Priority score for already-captured-but-not-cracked APs in the
        # in-plugin attack queue. 0.40 keeps them roughly 6× lower than
        # a typical uncaptured AP (~2.5) but well above the 0.0 floor.
        'recapture_priority_base':       0.40,
        # Priority for cracked APs — much lower since we have the PSK.
        'recapture_priority_cracked':    0.05,
        # Bonus per fresh client (≤1 epoch ago) when recapturing —
        # opportunistic capture window. Capped at 3 clients.
        'recapture_client_bonus':        0.5,

        # Channel scheduling
        'priority_channel_weight':   0.70,
        'dead_channel_cooldown':     5,
        'dead_ch_lifetime_weight':   0.01,
        # v1.9.0 channel_strategy:
        #   "auto" (DEFAULT, recommended): runs a meta-bandit at the
        #     strategy level. Each block of `auto_strategy_block_epochs`
        #     (default 30 ≈ 30 min), the plugin chooses one strategy
        #     (adaptive / full / capped) via UCB1 over their observed
        #     unique-HS-per-epoch rates, runs that strategy for the
        #     whole block, scores the result, and updates the strategy
        #     bandit. Within ~6 hours of operation the plugin auto-
        #     converges on whatever strategy genuinely works best in
        #     YOUR specific environment. No tuning needed.
        #   "adaptive" (the v1.8.0 default): top-K productive channels
        #     most epochs + full universe sweep every
        #     channel_full_sweep_every epochs.
        #   "full":   scan whole universe every epoch.
        #   "capped": legacy top-K only, no sweeps.
        'channel_strategy':          'auto',
        # v2.0: block size in SECONDS (preferred). Replaces the old
        # epoch-based default which silently misbehaved on Pis with
        # non-default epoch periods (a 5-second epoch made 30 "epochs"
        # = 2.5 min, way too noisy). Default 1800 = 30 min real time.
        # Smaller = faster convergence, noisier samples. Larger = slower
        # convergence, more reliable per-block reward.
        'auto_strategy_block_secs':   1800,
        # Legacy v1.9 epoch-based block size. If non-zero, OVERRIDES
        # auto_strategy_block_secs (back-compat for users who hand-tuned
        # this in v1.9). Set to 0 to use the seconds-based config.
        'auto_strategy_block_epochs': 0,
        # UCB1 exploration constant for the strategy meta-bandit. Higher
        # = more exploration. 1.4 is the textbook default; lower it to
        # 1.0 if you want the bandit to settle on its current favourite
        # faster.
        'auto_strategy_c':            1.4,
        # How often (epochs) the adaptive strategy does a full universe
        # sweep. With default ~60s epochs, 15 = ~15 minutes between
        # sweeps. Lower → more discovery, slightly less yield. Higher →
        # more yield, slower discovery of new productive channels.
        'channel_full_sweep_every':  15,
        # Legacy v1.7.1 option — kept for back-compat. When
        # channel_strategy is unset (= None / not in user options),
        # respect_full_channels=True maps to "full", False to "capped".
        # If channel_strategy IS set explicitly, this is ignored.
        'respect_full_channels':     None,

        # Thermal safety
        'temp_warn':                 70.0,
        'temp_critical':             78.0,

        # v2.2.0 NOAI-ALIGNED STABILITY MODE
        # When True (default), envtune respects the noai philosophy:
        # don't add radio activity beyond what natural pwnagotchi does.
        # Specifically:
        #   - enable_proactive is FORCED False (no extra wifi.assoc TX)
        #   - opportunistic_overrides defaults False (no runtime
        #     wifi.recon.channel pokes from on_bcap_wifi_client_new)
        #   - When mobility=moving, the strategy meta-bandit drops
        #     'full' from consideration (battery saver while walking)
        # Set to False if you have AC power, a stationary Pi, and want
        # maximum capture rate at the cost of slightly more radio load.
        'prefer_stability':          True,

        # Misc
        # reset_history: when True, on plugin start we wipe pwnagotchi's
        # `_history` (per-AP attack counters), bettercap's recon table
        # (`wifi.recon clear`), bettercap's session state (`wifi.clear`)
        # and force-set the recon channel list. v1.4.1 changed the
        # DEFAULT to False because the old `True` default destroyed
        # useful runtime state on every plugin reload — surprising and
        # destructive for operators who already had a session in flight.
        # Set to True if you want a fresh start every plugin restart.
        'reset_history':             False,
        # Recon-cycle target (seconds) — used by `_schedule_channels` to
        # cap the number of channels so one full hop cycle fits in this
        # budget. Combined with `hop_recon_time` it sets the upper bound
        # on channel-list size.
        'target_recon_cycle_secs':   75,
        'opportunistic_min_gap':     2,
        'opportunistic_overrides':   True,

        # GPS
        'enable_gps':                True,     # auto-disables if no GPS
        'gps_stale_seconds':         90,
        'mobility_walk_threshold':   0.5,      # m/s; >= this = MOVING
        # NOTE: v1.5 collapsed mobility to 2-way (stationary/moving), so
        # there's no longer a separate "walking vs driving" threshold.
        # The old `mobility_mobile_threshold` was removed in v2.2.

        # Proactive attacks (opt-in via prefer_stability=False)
        'proactive_min_rssi':        -68,
        # v2.2: minimum fresh clients on the AP for proactive attack to
        # fire. Strong client presence = more chance the proactive assoc
        # actually catches an EAPOL exchange.
        'proactive_min_clients':     1,
        'proactive_gap_epochs':      5,

        # Battery (pisugar integration)
        'battery_low_threshold':     20.0,
        'battery_critical_threshold': 10.0,

        # wpa-sec feedback
        'enable_wpasec_feedback':    True,
        'potfile_rescan_every_n':    100,    # epochs
        'handshake_rescan_every_n':  200,    # epochs

        # v2.0 (F-10): mood threshold gate — bored/sad penalties only
        # apply when the mood-counter has been elevated for at least
        # this many epochs. Prevents warmup penalties.
        'mood_threshold_epochs':     5,

        # v2.0 (F-13): max distinct channels we keep stats for in the
        # session-only `_chistos` dict. Prevents unbounded growth over
        # very long sessions (months) on systems that hop through many
        # channels. LRU-evicted when exceeded.
        'chistos_max_channels':      200,

        # v2.0 (F-14): proactive_min_rssi is intentionally a separate
        # threshold from the bandit's `min_rssi` arm. The bandit picks
        # the SCAN filter (which APs to track at all). proactive_min_rssi
        # is the ATTACK-aggression threshold (which APs to fire wifi.assoc
        # at proactively). These should NOT be merged — proactive is
        # always more conservative.
        # The default of -68 is well within the bandit's range (-85 to
        # -65), so any min_rssi the bandit picks is a permissive enough
        # filter that proactive targets remain visible.

        # v2.0 (P10): pwnagotchi version compat. Set to false to silence
        # the version-mismatch warning (e.g. when running a custom fork).
        'verify_pwnagotchi_version': True,

        # Logging
        'log_level':                 'INFO',
    }

    # ─────────────────────────────────────────────────────────────────────
    # Initialisation
    # ─────────────────────────────────────────────────────────────────────

    def __init__(self):
        # Config — finalised in on_loaded after options merge
        self.cfg = dict(self.DEFAULTS)
        self._profile = None          # populated in on_loaded

        # EMA-smoothed observation signals
        # v2.1.0: added num_peers, mem_usage, slept_for_secs — verified
        # against noai pwnagotchi/epoch.py _epoch_data fields.
        self.ema = {k: None for k in (
            'aps', 'hs_rate', 'reward', 'missed_rate', 'hs_per_min',
            'active_ratio', 'inactive_ratio', 'hops_per_epoch',
            'temperature', 'cpu_load', 'speed',
            'num_peers', 'mem_usage', 'slept_for_secs',
        )}
        self._prev_reward_ema = None
        self._reward_trend    = 0.0
        self._last_reward_breakdown = {}
        self._prev_aps_ema    = None   # persists between epochs for crash detect

        # Adaptive reward target — learns what "good hs/min" means here
        self._recent_hpm      = deque(maxlen=60)
        self._reward_history  = deque(maxlen=60)   # for rolling-median stagnation

        # Epoch counters / state machine
        self.epochs_seen          = 0
        self.epochs_since_save    = 0
        self._stagnation_count    = 0
        self._exploration_boost   = 0
        self._blind_recovery      = 0
        self._blind_saved_params  = None
        self._crash_suspect       = 0
        self._last_override_ep    = -99
        self._last_proactive_ep   = -99
        self._thermal_throttle    = False
        self._thermal_saved_params = None  # v2.0 (F-08): pre-throttle param snapshot
        self._mood                = 'neutral'
        self._battery_level       = None    # pisugar integration
        self._session_hs_bssids   = set()   # for per-epoch new_unique calc
        self._lifetime_new_count  = 0        # cumulative count of LIFETIME-new captures

        # UCB — initialised in on_loaded
        self.ucb_table        = {}
        # Decision buffer — sized in on_loaded after cfg is finalised so
        # the maxlen scales with reward_delay. v1.5 had hardcoded
        # maxlen=5; with the dense-environment delay tweak that adds +1,
        # any user setting reward_delay >= 5 silently never had rewards
        # attributed (deque saturated below the indexing window).
        self._decision_buffer = deque(maxlen=12)
        self._ucb_cache       = {}    # (param,state) -> (arm, epoch_set)
        self._ucb_cache_epoch = -1
        # Per-epoch _ch_score memoisation. Cleared at the start of each
        # on_epoch and on any state mutation that would change scores.
        # Without it, a single _schedule_channels pass does ~14² ch_score
        # calls × ~400 known_aps = ~78 k ops per epoch on dense terrain.
        self._ch_score_cache  = {}
        self._ch_score_epoch  = -1
        # Running counter of real reward samples across the whole UCB
        # table — drives the shrinkage-k anneal. Was previously
        # recomputed by walking ~9 k cells on every arm pick (14×/epoch).
        self._total_real_samples = 0

        # Which pwnagotchi params this fork actually exposes
        self._active_params = set(self.UCB_ARMS.keys())

        # Best-reward tracking (telemetry)
        self.best_reward   = None
        self.best_settings = None

        # Lifetime stats (persistent)
        self.lifetime_handshakes = 0
        self.session_start_mono  = time.monotonic()
        # Per-session HS counter (incl. duplicates of already-captured
        # BSSIDs). Used by /metrics for envtune_session_duplicates.
        # Distinct from lifetime_handshakes (cross-session) and from
        # len(_session_hs_bssids) which is the *unique* count this session.
        self.session_handshakes  = 0

        # Counters synced after _load_state in on_loaded (prevents inflated
        # diff on first epoch when state has lifetime_new_count > 0).
        self._lifetime_new_count_prev = 0
        self._known_aps_count_prev    = 0
        self._last_loc_change_ep      = -99

        # Bettercap dynamic skip-list — captured BSSIDs we ask bettercap to
        # deprioritise so radio time goes to *new* targets (the whole point).
        self._bcap_skip_macs           = set()
        self._bcap_skip_pushed_count   = 0

        # Channel lifetime dict  ch → stats (persistent).
        # v1.6: removed the dead 'cracked' counter (only ever read in
        # _ch_score, never written anywhere). Channel "cracked
        # productivity" is better expressed via the GPS-zone-level
        # cracked count if we ever need it.
        self._ch_lt = defaultdict(lambda: {
            'hs': 0, 'assocs': 0, 'deauths': 0,
            'clients': 0, 'visits': 0, 'wasted': 0,
            'free_seen': 0, 'passive_hs': 0,
        })
        self._dead_lt = defaultdict(int)

        # Session-only channel state
        self._chistos            = {'_all_actions': {-1: 0}}
        self._active_channels    = []
        self._unscanned_channels = []
        self._dead_session       = defaultdict(int)
        self._free_channels      = deque(maxlen=8)   # recent free-channel reports
        # v1.7.1: user's original `personality.channels` (or the iface's
        # full supported list if the user left it empty). Captured ONCE
        # in on_ready, never modified by envtune. Used as the channel
        # universe — envtune's `next_chs` output never goes below this
        # set when `respect_full_channels=True`. None until on_ready.
        self._user_channels_orig = None
        # v1.8.0: last epoch we did a full universe sweep. Used by the
        # adaptive channel_strategy to schedule sweeps every
        # channel_full_sweep_every epochs. -999 = "do a sweep on first
        # opportunity" so the bandit gets initial coverage even if
        # restarted mid-stable-environment.
        self._last_full_sweep_ep = -999
        # v2.0 (A1): MOBILITY-AWARE meta-bandit. v1.9 had a single 3-arm
        # bandit; v2.0 has TWO 3-arm bandits — one per mobility — because
        # community evidence + math show different strategies are optimal
        # under different mobility regimes (capped wins when stationary;
        # full sweep often wins when moving because the AP λ-distribution
        # changes faster than capped can rediscover).
        # Schema: {mobility: {strategy: {'n': int, 'rewards': deque}}}
        # Persisted in state JSON. v1.9 flat schema migrates: existing
        # stats are seeded into BOTH mobilities as warm priors.
        self._strategy_bandit = {
            mobility: {
                s: {'n': 0, 'rewards': deque(maxlen=20)}
                for s in ('adaptive', 'full', 'capped')
            }
            for mobility in (self.MOBILITY_STATIONARY, self.MOBILITY_MOVING)
        }
        # Block tracking (session-only; recovers cleanly on restart by
        # cold-starting the next block).
        # v2.0 (F-09): None (clean) instead of -999 sentinel.
        self._strategy_current        = None       # strategy in this block
        self._strategy_block_start_ep = None       # epoch the block began
        self._strategy_block_start_mono = None     # wall-clock start (F-05)
        self._strategy_block_mobility = None       # mobility at block start
        self._uniques_at_block_start  = 0          # to compute block reward

        # AP tracking
        self._known_aps        = {}
        self._captured_aps     = set()     # apIDs with HS this session
        self._captured_bssids  = set()     # BSSIDs seen in /root/handshakes/
        self._cracked_bssids   = set()     # BSSIDs with known password (wpa-sec)
        self._whitelist_macs   = set()
        self._whitelist_ssids  = set()

        # GPS
        self._gps_available   = False
        self._gps_source      = None       # 'theylive', 'stock_gps', or None
        self._gps_last_fix    = None       # {'lat', 'lon', 'speed', 'ts_mono'}
        self._gps_zones       = defaultdict(lambda: {
            'hs': 0, 'attacks': 0, 'visits': 0,
            'last_seen': 0.0, 'channels': defaultdict(int),
        })
        self._current_zone    = None
        self._current_mobility = self.MOBILITY_STATIONARY

        # Location-change detection (works with or without GPS)
        self._loc_fp_stored = None
        self._fp_history    = deque(maxlen=12)

        # Thread safety
        self._state_lock = threading.RLock()

        # Async save thread
        self._save_queue   = queue.Queue(maxsize=4)
        self._save_thread  = None
        self._save_stop    = threading.Event()
        # v2.0 (R-01): cached snapshot for /export — updated by the save
        # worker thread when it writes to disk. /export serves this
        # cache instead of building a fresh snapshot on the webhook
        # thread (which was a 50–200ms operation on Pi Zero 2 W).
        # Stale by at most save_every_n epochs, which is fine for an
        # export endpoint (operators don't need millisecond freshness).
        self._cached_snapshot       = None
        self._cached_snapshot_at    = 0.0   # wall-clock time of cache

        # Web-UI action log (rolling, last 20). CSRF protection comes from
        # pwnagotchi's flask_wtf.CSRFProtect middleware — we use the
        # Flask-WTF csrf_token() helper inside our forms.
        self._action_log = deque(maxlen=20)

        # Plugin wiring
        self._agent     = None
        self._ui        = None
        # v2.1.0: resolved at on_ready from agent._config. Fallbacks are
        # the noai-default paths so first-load (before on_ready) doesn't
        # crash on access.
        self._hs_dir         = self.HANDSHAKE_DIR_FALLBACK
        self._wpasec_pot     = self.WPASEC_POT_FALLBACK
        self._bcap_silenced_events = set()  # populated in on_ready from cfg
        # v2.0 (F-12): full schema so UI never sees a partial dict on
        # first render, before any handshake has been recorded.
        self.last_shake = {
            'time': time.time(),
            'ap': None,
            'cl': None,
            'passive': False,
            'lifetime_new': False,
        }
        # v2.0 (P-11): error counters per handler. Exposed via /metrics
        # so ops dashboards can detect when a handler is consistently
        # failing.
        self._error_counts = defaultdict(int)

    # ─────────────────────────────────────────────────────────────────────
    # State-space definition (v4 schema, 24 states)
    # ─────────────────────────────────────────────────────────────────────
    # State key format: "density_tod_mobility"
    #   density:  sparse / medium / dense                 (3)
    #   tod:      night / morning / afternoon / evening   (4)
    #   mobility: stationary / moving                     (2)
    # Total: 3×4×2 = 24 base states.
    #
    # 4.5× sample-efficiency improvement vs the v1.4 108-state schema.
    # `trend` was dropped (redundant with stagnation+saturation logic),
    # walking+mobile merged into 'moving' (empirically same optimal
    # params).
    # ─────────────────────────────────────────────────────────────────────

    def _all_states(self):
        return [
            f'{d}_{t}_{m}'
            for d in ('sparse', 'medium', 'dense')
            for t in ('night', 'morning', 'afternoon', 'evening')
            for m in (self.MOBILITY_STATIONARY, self.MOBILITY_MOVING)
        ]

    def _init_ucb_table(self):
        """Build empty UCB tables for all (param, state, arm) triples."""
        W      = int(self._profile['ucb_window'])
        states = self._all_states()
        self.ucb_table = {
            param: {
                state: {arm: {'n': 0, 'rewards': deque(maxlen=W)} for arm in arms}
                for state in states
            }
            for param, arms in self.UCB_ARMS.items()
        }

    def _ensure_state(self, param, state):
        """Lazy-create UCB entry (handles new states after version bumps)."""
        W = int(self._profile['ucb_window'])
        if param not in self.ucb_table:
            self.ucb_table[param] = {}
        if state not in self.ucb_table[param]:
            self.ucb_table[param][state] = {
                arm: {'n': 0, 'rewards': deque(maxlen=W)}
                for arm in self.UCB_ARMS[param]
            }

    # ─────────────────────────────────────────────────────────────────────
    # UCB serialisation (with version migration)
    # ─────────────────────────────────────────────────────────────────────

    def _serialise_ucb(self):
        out = {}
        for param, states in self.ucb_table.items():
            out[param] = {}
            for state, arms in states.items():
                out[param][state] = {
                    str(arm): {'n': d['n'], 'rewards': list(d['rewards'])}
                    for arm, d in arms.items()
                }
        return out

    def _deserialise_ucb(self, raw, loaded_schema):
        """Load UCB table with on-the-fly state-key migration."""
        W = int(self._profile['ucb_window'])
        for param, states in raw.items():
            if param not in self.ucb_table:
                continue  # param removed in newer version — skip gracefully
            for old_state, arms in states.items():
                # Migration: add missing mobility suffix to old states
                new_state = self._migrate_state_key(old_state, loaded_schema)
                self._ensure_state(param, new_state)
                for arm_s, d in arms.items():
                    try:
                        ref_type = type(self.UCB_ARMS[param][0])
                        arm      = ref_type(arm_s)
                    except (ValueError, TypeError):
                        try:
                            arm = float(arm_s)
                        except (ValueError, TypeError):
                            continue
                    if arm in self.ucb_table[param][new_state]:
                        entry = self.ucb_table[param][new_state][arm]
                        entry['n'] = _si(d.get('n', 0))
                        rews = d.get('rewards', []) or []
                        # If migrating, merge rather than overwrite
                        if len(entry['rewards']) > 0:
                            combined = list(entry['rewards']) + rews
                            entry['rewards'] = deque(combined[-W:], maxlen=W)
                        else:
                            entry['rewards'] = deque(rews, maxlen=W)

    def _migrate_state_key(self, old_key, from_schema):
        """
        Migrate state keys between schema versions.
          v1, v2 → density_tod_trend (3 components, no mobility)
          v3     → density_tod_trend_mobility (4 components, 108 states)
          v4     → density_tod_mobility (3 components, 24 states)

        v4 collapses two dimensions:
          - drop `trend` entirely (rising/stable/falling all merge)
          - merge mobility {walking, mobile} → 'moving'
        Up to 6 old keys map onto each new key. The deserialiser
        concatenates their reward histories (keeping only ucb_window
        most recent), so no learning is lost.
        """
        parts = old_key.split('_')
        # v3 → v4: 4 components → 3 (drop trend at index 2; collapse mobility)
        if from_schema == 3 and len(parts) == 4:
            density, tod, _trend, mobility = parts
            if mobility in (self.MOBILITY_WALKING, self.MOBILITY_MOBILE):
                mobility = self.MOBILITY_MOVING
            elif mobility != self.MOBILITY_STATIONARY:
                mobility = self.MOBILITY_STATIONARY  # safety
            return f'{density}_{tod}_{mobility}'
        # v1/v2 → v4: 3 components without mobility → assume stationary
        if from_schema < 3 and len(parts) == 3:
            density, tod, _trend = parts
            return f'{density}_{tod}_{self.MOBILITY_STATIONARY}'
        # Already v4 (3 components with mobility) — pass through
        if len(parts) == 3:
            density, tod, mobility = parts
            if mobility in (self.MOBILITY_WALKING, self.MOBILITY_MOBILE):
                mobility = self.MOBILITY_MOVING
            return f'{density}_{tod}_{mobility}'
        return old_key

    # ─────────────────────────────────────────────────────────────────────
    # Time-of-day priors + hierarchical marginal priors
    # ─────────────────────────────────────────────────────────────────────

    def _apply_tod_prior(self):
        """
        Seed empty arms with weak synthetic observations so cold start
        is not random. Real data always dominates: n=1 prior vs n=40
        window means real observations win after 3-4 samples.
        """
        tod_priors = {
            'night': {
                'recon_time': 35, 'min_rssi': -80, 'max_interactions': 2,
                'hop_recon_time': 10, 'min_recon_time': 7,
                'throttle_d': 0.9, 'throttle_a': 0.4,
                'ap_ttl': 300, 'sta_ttl': 600,
                'max_misses_for_recon': 7, 'max_inactive_scale': 3,
                'recon_inactive_multiplier': 2,
            },
            'morning': {
                'recon_time': 25, 'min_rssi': -72, 'max_interactions': 3,
                'hop_recon_time': 8, 'min_recon_time': 5,
                'throttle_d': 0.7, 'throttle_a': 0.4,
                'ap_ttl': 180, 'sta_ttl': 300,
                'max_misses_for_recon': 5, 'max_inactive_scale': 2,
                'recon_inactive_multiplier': 2,
            },
            'afternoon': {
                'recon_time': 20, 'min_rssi': -72, 'max_interactions': 4,
                'hop_recon_time': 6, 'min_recon_time': 5,
                'throttle_d': 0.7, 'throttle_a': 0.4,
                'ap_ttl': 120, 'sta_ttl': 300,
                'max_misses_for_recon': 5, 'max_inactive_scale': 2,
                'recon_inactive_multiplier': 2,
            },
            'evening': {
                'recon_time': 20, 'min_rssi': -70, 'max_interactions': 5,
                'hop_recon_time': 6, 'min_recon_time': 3,
                'throttle_d': 0.5, 'throttle_a': 0.2,
                'ap_ttl': 120, 'sta_ttl': 300,
                'max_misses_for_recon': 5, 'max_inactive_scale': 2,
                'recon_inactive_multiplier': 2,
            },
        }
        # Mobility adjustments — v4 schema (2-way only)
        mobility_adjust = {
            self.MOBILITY_STATIONARY: {'ap_ttl': +60, 'sta_ttl': +120, 'recon_time': +5},
            self.MOBILITY_MOVING:     {'ap_ttl': -30, 'sta_ttl': -80,  'recon_time': -5},
        }
        # v2.0 (F-03): single source of truth for the neutral prior.
        PRIOR_R = self.PRIOR_NEUTRAL_R

        # v4 SCHEMA: state = density_tod_mobility (24 states, no trend)
        for density in ('sparse', 'medium', 'dense'):
            for tod, vals in tod_priors.items():
                for mobility in (self.MOBILITY_STATIONARY,
                                 self.MOBILITY_MOVING):
                    state = f'{density}_{tod}_{mobility}'
                    adj   = mobility_adjust.get(mobility, {})
                    for param, preferred in vals.items():
                        if param not in self.UCB_ARMS:
                            continue
                        pref = preferred + adj.get(param, 0)
                        self._ensure_state(param, state)
                        arms    = self.UCB_ARMS[param]
                        nearest = min(arms, key=lambda a: abs(a - pref))
                        entry   = self.ucb_table[param][state][nearest]
                        if entry['n'] == 0:
                            entry['n'] = 1
                            entry['rewards'].append(PRIOR_R)

    def _apply_personality_warmstart(self, agent):
        """Seed the bandit with whatever pwnagotchi's personality is
        configured to right now.

        v2.0 (F-02 docstring update): the synthetic sample is at the
        NEUTRAL prior level (R=0.30 by default, equal to the TOD
        prior). This gives the user-configured arm the same status as
        any seeded arm — it gets to skip the "untried-arm" branch of
        UCB selection without actively biasing the mean toward it.
        Real evidence (n>1 actual rewards) overrides immediately.
        v1.6 had R=0.45 here, which created the "sticky warmstart"
        pattern where suboptimal user defaults locked the bandit for
        thousands of epochs (e.g. ap_ttl=120 at mean 0.064 vs
        ap_ttl=60 at 0.247 in real community telemetry).

        Skipped silently if the agent isn't ready.
        """
        if agent is None:
            return
        try:
            p = agent._config.get('personality') or {}
        except Exception:
            return
        # v2.0 (F-01): fallback default matches DEFAULTS (PRIOR_NEUTRAL_R).
        WARM_R = float(self.cfg.get('warmstart_prior_reward',
                                    self.PRIOR_NEUTRAL_R))
        for param in self.UCB_ARMS:
            if param not in p:
                continue
            try:
                user_val = float(p[param])
            except (TypeError, ValueError):
                continue
            arms    = self.UCB_ARMS[param]
            nearest = min(arms, key=lambda a: abs(a - user_val))
            for state in self._all_states():
                self._ensure_state(param, state)
                entry = self.ucb_table[param][state][nearest]
                # Only warm-start arms that have NO real data yet.
                # Don't overwrite cells already learned during a long
                # session if the user reloads the plugin.
                if entry['n'] == 0:
                    entry['n'] = 1
                    entry['rewards'].append(WARM_R)
                elif (entry['n'] == 1 and entry['rewards']
                      and abs(entry['rewards'][0] - self.PRIOR_NEUTRAL_R) < 1e-6):
                    # n=1 with the seeded NEUTRAL prior — replace
                    # with the warm-start value (still n=1, but a
                    # better starting point).
                    entry['rewards'].clear()
                    entry['rewards'].append(WARM_R)
        log.info(
            f'[envtune] personality warm-start applied '
            f'(prior reward {WARM_R:.2f} on user-configured arms)')

    # NOTE: _hierarchical_marginal was deleted in v1.6 — subsumed by the
    # shrinkage-aware UCB pick (_sw_ucb_pick_with_state + _arm_parent_mean).
    # The shrinkage path pulls each cell's mean toward the parent prior
    # in proportion to how undersampled the cell is, achieving the same
    # "rare contexts borrow from common ones" goal but continuously
    # rather than as a discrete fallback.

    # ─────────────────────────────────────────────────────────────────────
    # Context / state computation
    # ─────────────────────────────────────────────────────────────────────

    def _compute_mobility(self):
        """Infer mobility from GPS speed (if available) or AP turnover.

        v4 schema: 2-way classification only (stationary vs moving).
        Walking/mobile are folded into a single 'moving' state because
        empirically they require similar param adjustments (short
        ap_ttl, faster recon) and merging them gives 50% more samples
        per cell.
        """
        # GPS-based (preferred when available)
        if self._gps_last_fix is not None:
            speed = _sf(self._gps_last_fix.get('speed', 0))
            age   = time.monotonic() - self._gps_last_fix['ts_mono']
            if age <= self.cfg['gps_stale_seconds']:
                if speed >= self.cfg['mobility_walk_threshold']:
                    return self.MOBILITY_MOVING
                return self.MOBILITY_STATIONARY

        # Fallback: AP turnover heuristic
        # If many APs have appeared/disappeared recently, we're moving.
        if len(self._fp_history) >= 3:
            recent = list(self._fp_history)[-3:]
            # Count unique channels across the last 3 fingerprints
            all_chs = set()
            for fp in recent:
                all_chs.update(fp.get('top', []))
            if len(all_chs) >= 5:
                return self.MOBILITY_MOVING
        return self.MOBILITY_STATIONARY

    def _compute_state(self, aps_ema):
        """Map current observations to a discrete state key.

        v4 SCHEMA — 24 states (was 108 in v3).
          density (3) × tod (4) × mobility (2) = 24

        The `trend` dimension was dropped because telemetry showed it
        carried almost no signal: 87% of `*_*_falling_*` cells stayed
        at the seeded prior, and stagnation/saturation detection
        already triggers exploration boost when reward drops.

        Mobility was collapsed from 3-way to 2-way (stationary/moving)
        because walking and driving optimal params are nearly identical
        in practice. Net result: 4.5× more samples per cell, ~3×
        faster convergence.
        """
        # AP density
        if aps_ema >= self.cfg['dense_aps']:
            density = 'dense'
        elif aps_ema <= self.cfg['sparse_aps']:
            density = 'sparse'
        else:
            density = 'medium'

        # Time of day (local time)
        h = time.localtime().tm_hour
        if h < 7:       tod = 'night'
        elif h < 12:    tod = 'morning'
        elif h < 18:    tod = 'afternoon'
        else:           tod = 'evening'

        # Mobility (cached per-epoch) — 2-way only in v1.5
        mobility = self._current_mobility

        return f'{density}_{tod}_{mobility}'

    # ─────────────────────────────────────────────────────────────────────
    # UCB arm selection (Sliding-Window UCB1 with hierarchical fallback)
    # ─────────────────────────────────────────────────────────────────────

    def _ucb_select(self, param, state):
        """
        Pick best arm for (param, state).

        Algorithm:
          1. v1.7 forced-exploration floor: if forced_explore_every is
             active and any arm has n < forced_explore_starvation_n,
             force-pick the most-starved arm to guarantee minimum
             coverage. Closes the UCB1 starvation pattern observed in
             real community telemetry.
          2. If any arm has zero observations (even after priors): try it.
          3. Shrinkage-aware UCB self-handles sparse cells by pulling
             toward the parent group's mean.
        """
        self._ensure_state(param, state)
        arms  = self.UCB_ARMS[param]
        table = self.ucb_table[param][state]

        # 1. Forced exploration. We compute the same trigger condition
        # for every (param, state) call this epoch; it's cheap and
        # avoids needing global state about which params we've forced.
        # Note: forced selections deliberately bypass the UCB cache so
        # successive epochs with cached arms don't lock out the floor.
        every = int(self.cfg.get('forced_explore_every', 0))
        if every > 0 and self.epochs_seen > 0 and self.epochs_seen % every == 0:
            starved_n = int(self.cfg.get('forced_explore_starvation_n', 5))
            starved = [(a, table[a]['n']) for a in arms
                       if table[a]['n'] < starved_n]
            if starved:
                # Tie-break: lowest n wins, random among equally starved.
                min_n = min(n for _, n in starved)
                candidates = [a for a, n in starved if n == min_n]
                return random.choice(candidates)

        # Cache: return cached choice if we computed this recently.
        # Only consulted when forced exploration didn't fire.
        cache_key = (param, state)
        if (self._profile['ucb_cache_epochs'] > 0
                and cache_key in self._ucb_cache
                and self.epochs_seen < self._ucb_cache[cache_key][1]):
            return self._ucb_cache[cache_key][0]

        # 2. Try untried arms first (post-prior)
        untried = [a for a in arms if table[a]['n'] == 0]
        if untried:
            choice = random.choice(untried)
        else:
            # 3. Shrinkage-aware UCB
            choice = self._sw_ucb_pick_with_state(param, state, arms, table)

        # Cache
        if self._profile['ucb_cache_epochs'] > 0:
            self._ucb_cache[cache_key] = (
                choice, self.epochs_seen + self._profile['ucb_cache_epochs'])
        return choice

    def _arm_parent_mean(self, param, state, arm):
        """
        Empirical-Bayes prior for an arm: weighted mean of this arm's
        rewards across (a) states sharing 2+ context dims (preferred),
        falling back to (b) population mean across ALL states.

        v1.6 FIX: schema check is now `len == 3` (density_tod_mobility),
        matching the v1.5 schema collapse. The old `len == 4` check was
        a leftover from v1.4 (density_tod_trend_mobility) and silently
        disabled the dimension-weighted parent prior, leaving shrinkage
        falling back to flat population mean across all 24 states. The
        plugin's headline claim "rare contexts benefit from common ones"
        was effectively false until this fix.

        Weighting: states sharing 2 dims get full weight 1.0 (e.g.
        target=`dense_evening_stationary`, neighbour=`dense_evening_moving`
        is 2 dims shared, very informative). 1 dim shared gets 0.25.
        0 dims shared (entirely different context) is excluded — the
        population fallback handles those.

        Returns float prior, or None if there's no data anywhere.
        """
        target_parts = state.split('_')
        parent_sum = parent_n = 0.0
        pop_sum    = pop_n    = 0.0

        for other_state, arms in self.ucb_table.get(param, {}).items():
            d = arms.get(arm)
            if d is None or d['n'] == 0 or not d['rewards']:
                continue
            m = sum(d['rewards']) / len(d['rewards'])
            n = d['n']
            if other_state == state:
                continue   # we already have local in the caller
            pop_sum += m * n
            pop_n   += n
            op = other_state.split('_')
            if len(op) == 3 and len(target_parts) == 3:
                shared = sum(1 for a, b in zip(target_parts, op) if a == b)
                if shared >= 1:
                    # 2 shared dims = highly relevant neighbour (1.0)
                    # 1 shared dim  = moderately relevant (0.25)
                    w = 1.0 if shared == 2 else 0.25
                    # Use sqrt(n) instead of n so an n=200 distantly-
                    # related state doesn't drown out an n=5 closely-
                    # related state (was a v1.5 weighting bug).
                    sqrt_n = math.sqrt(n)
                    parent_sum += m * w * sqrt_n
                    parent_n   += w * sqrt_n

        if parent_n > 0:
            return parent_sum / parent_n
        if pop_n > 0:
            return pop_sum / pop_n
        return None

    def _current_shrinkage_k(self):
        """
        Annealed shrinkage strength.

        With FIXED k=5 (v1.1) we observed in real telemetry that
        genuinely-better-but-undertested arms (e.g. min_rssi=-75 with
        n=13, local mean=0.40) had their effective mean pulled down to
        ~0.37 by the prior of 0.30 — slowing convergence.

        Solution: k starts heavy (k_max=5) for cold-start, then anneals
        linearly to k_min=1 as the table accumulates real samples. At
        the end of anneal, an arm with n=13 retains 93% of its local
        mean instead of 72%.

        If ucb_shrinkage_k is set explicitly in user config (legacy
        v1.1 behaviour), that fixed value is used and anneal is skipped.

        v1.6 PERF: was walking the entire UCB table (~9 k cells) on
        every arm pick — 14 picks/epoch → 126 k iterations/epoch.
        Now uses `_total_real_samples`, a running counter that's
        incremented in `_ucb_update`. O(1) per call.
        """
        fixed = self.cfg.get('ucb_shrinkage_k')
        if fixed is not None:
            try:
                return max(0.0, float(fixed))
            except (TypeError, ValueError):
                pass
        k_max = float(self.cfg.get('ucb_shrinkage_k_max', 5.0))
        k_min = float(self.cfg.get('ucb_shrinkage_k_min', 1.0))
        anneal = max(1, int(self.cfg.get('ucb_shrinkage_anneal_samples', 500)))
        frac = min(1.0, self._total_real_samples / anneal)
        return k_max - (k_max - k_min) * frac

    def _record_error(self, handler):
        """v2.0 (P-11): increment per-handler exception counter.
        Exposed via /metrics for ops dashboards."""
        try:
            self._error_counts[handler] += 1
        except Exception:
            pass

    def _recompute_total_real_samples(self):
        """Walk the full UCB table once to seed `_total_real_samples`.
        Called after `_load_state` and `_apply_tod_prior` /
        `_apply_personality_warmstart` (which inject synthetic samples
        with n=1)."""
        total = 0
        for states in self.ucb_table.values():
            for arms in states.values():
                for d in arms.values():
                    total += d.get('n', 0)
        self._total_real_samples = total

    def _sw_ucb_pick_with_state(self, param, state, arms, table):
        """
        Sliding-window UCB1 pick with annealed empirical-Bayes shrinkage.

        With 14 params × 108 states × ~6 arms = 9072 cells and a typical
        session of 100-300 epochs, vanilla UCB sees almost every cell as
        "the seeded prior". Shrinkage pulls each cell's mean toward the
        mean of similar states (sharing 2+ context dims) so neighbours
        contribute information. As the local sample count grows, the
        local mean reasserts itself via weight = n/(n+k); k itself
        anneals from heavy to light over the first ~500 real samples.
        """
        # Annealed exploration constant
        if self._exploration_boost > 0:
            C = self.cfg['exploration_boost_c']
        else:
            frac   = min(1.0, self.epochs_seen / self.cfg['ucb_c_anneal_epochs'])
            C_min  = self.cfg['ucb_c_floor']
            C_max  = self.cfg['ucb_c']
            C      = C_max - (C_max - C_min) * frac

        k = self._current_shrinkage_k()
        total_w = sum(len(table[a]['rewards']) for a in arms)
        best_score = -math.inf
        best_arm   = arms[0]
        for arm in arms:
            d      = table[arm]
            w_size = len(d['rewards'])
            local  = sum(d['rewards']) / w_size if w_size > 0 else 0.0
            prior  = self._arm_parent_mean(param, state, arm)
            if prior is None:
                # No information anywhere → cold-start neutral.
                eff = local if w_size > 0 else 0.3
            else:
                w_loc = w_size / (w_size + k)
                eff   = w_loc * local + (1.0 - w_loc) * prior
            expl   = C * math.sqrt(math.log(max(2, total_w)) / max(1, w_size))
            score  = eff + expl
            if score > best_score:
                best_score = score
                best_arm   = arm
        return best_arm

    def _ucb_update(self, param, state, arm, reward):
        """Record a reward observation for (param, state, arm)."""
        if param not in self._active_params:
            return
        self._ensure_state(param, state)
        tbl = self.ucb_table[param][state]
        if arm not in tbl:
            W = int(self._profile['ucb_window'])
            tbl[arm] = {'n': 0, 'rewards': deque(maxlen=W)}
        tbl[arm]['n'] += 1
        tbl[arm]['rewards'].append(float(reward))
        # Maintain the running sample-count for shrinkage anneal — was
        # previously recomputed by walking the full table on every arm
        # pick (v1.5).
        self._total_real_samples += 1
        # Invalidate cache for this (param, state)
        self._ucb_cache.pop((param, state), None)

    # ─────────────────────────────────────────────────────────────────────
    # Custom handshake-focused reward (adaptive, percentile-based target)
    # ─────────────────────────────────────────────────────────────────────

    def _adaptive_hpm_target(self):
        """
        Adaptive reward target for unique handshakes per minute.

        We want a target that scales with what's achievable in the current
        environment, but doesn't move so fast it kills the reward signal.
        Strategy: use 90th percentile of recent hpm — only the very best
        recent epochs raise the bar. Floor at 0.5 unique per minute.
        """
        if len(self._recent_hpm) < 10:
            return 0.5  # default target: 0.5 unique/min ≈ 30/hour
        vals = sorted(self._recent_hpm)
        idx  = int(len(vals) * 0.90)
        p90  = vals[min(idx, len(vals) - 1)]
        # Never drop below a useful threshold; cap upper to prevent runaway
        return max(0.5, min(p90, 5.0))

    def _custom_reward(self, handshakes, hs_rate, missed_rate, native_reward,
                       duration_secs, lifetime_new_this_epoch,
                       active_ratio, inactive_ratio, hops_ratio,
                       new_aps_seen, interactions,
                       blind_ratio=0.0, bored_ratio=0.0, sad_ratio=0.0):
        """
        UNIQUE-handshake-maximising reward (v1.5 — pure unique focus).

        v1.5 deliberately removed weights that were polluting the
        signal:
          - native_reward (was 0.03): pwnagotchi's own reward counts
            TOTAL handshakes including duplicates, contradicting the
            unique-only goal. Removed.
          - work_term (was 0.04): "we attacked, even if we caught
            nothing" — too indirect; the activity floor handles the
            "tried something" case more cleanly. Removed.

        82% of positive reward weight now goes directly to unique-HS
        signals (new_term + eff_term). Penalties unchanged.

        Components (all normalised to [0,1]):
          - lifetime-new HS per minute         (0.70)  PRIMARY GOAL
          - unique-HS-per-attack efficiency    (0.12)  duplicates penalised
          - new APs discovered this epoch      (0.08)  exploration value
          - inverse missed rate                (0.04)  efficiency
          - pwnagotchi active ratio            (0.03)  working signal
          - channel hop diversity              (0.03)  coverage
          - penalty: inactive ratio            (-0.05) stalls
          - penalty: blind ratio               (-0.07) radio sees nothing
          - penalty: sad / bored               (-0.04 / -0.03)

        Floor:
          - 0.01 if there were any interactions, so UCB still
            distinguishes 'tried but failed' from 'did nothing'.
        """
        dur_min        = max(0.01, duration_secs / 60.0)
        hs_per_min     = handshakes / dur_min
        new_per_min    = lifetime_new_this_epoch / dur_min

        # v1.4.1 FIX: compute target BEFORE appending current epoch's
        # value, otherwise the current sample influences its own target.
        target = self._adaptive_hpm_target()
        self._recent_hpm.append(new_per_min)

        # 1) PRIMARY — lifetime-new HS per minute, Hill-saturated.
        #   ratio=0       → 0.00
        #   ratio=0.5     → 0.33
        #   ratio=1.0     → 0.50  (target hit, well above 0.30 prior)
        #   ratio=2.0     → 0.67
        #   ratio=4.0     → 0.80
        if target > 0 and new_per_min > 0:
            ratio = new_per_min / target
            new_term = ratio / (ratio + 1.0)
        else:
            new_term = 0.0

        # 2) UNIQUE-per-attack efficiency. v1.5 uses the same Hill
        # saturation as the primary term so the gradient matches:
        # 1 unique per 10 attempts → 0.5 (target), more is better.
        # This ensures attack budget is spent on UNIQUE captures —
        # a duplicate-only epoch gets near-zero credit here.
        if interactions > 0 and lifetime_new_this_epoch > 0:
            eff_ratio = (lifetime_new_this_epoch * 10.0) / interactions
            eff_term  = eff_ratio / (eff_ratio + 1.0)
        else:
            eff_term  = 0.0

        # 3) Inverse missed rate
        miss_term = max(0.0, 1.0 - missed_rate)

        # 4) New APs discovered (exploration value, even without HS)
        new_aps_term = min(1.0, new_aps_seen / 10.0)

        # 5) Active ratio — pwnagotchi's own working signal
        active_term = min(1.0, active_ratio)

        # 6) Hop diversity
        hops_term = min(1.0, hops_ratio)

        # 7) Inactive penalty
        inactive_pen = min(1.0, inactive_ratio)

        # 8) Blind penalty — radio "sees nothing" → scan params wrong
        blind_pen = min(1.0, max(0.0, blind_ratio))

        # 9) Mood penalties — bored/sad means we were idle long enough
        # to flip emotion. Original AI weighted these at -0.20/-0.10;
        # we soften because blind_pen + active_term overlap signals.
        bored_pen = min(1.0, max(0.0, bored_ratio))
        sad_pen   = min(1.0, max(0.0, sad_ratio))

        r = (
            0.70 * new_term         # PRIMARY GOAL
          + 0.12 * eff_term         # unique-per-attack
          + 0.08 * new_aps_term     # discovery
          + 0.04 * miss_term        # efficiency
          + 0.03 * active_term      # working signal
          + 0.03 * hops_term        # coverage
          - 0.05 * inactive_pen
          - 0.07 * blind_pen
          - 0.04 * sad_pen
          - 0.03 * bored_pen
        )
        # Activity floor: distinguish "tried but failed" from "nothing".
        if interactions > 0 and new_per_min == 0:
            r = max(r, 0.01)

        # Per-component breakdown for the dashboard panel.
        self._last_reward_breakdown = {
            'new':      0.70 * new_term,
            'eff':      0.12 * eff_term,
            'new_aps':  0.08 * new_aps_term,
            'miss':     0.04 * miss_term,
            'active':   0.03 * active_term,
            'hops':     0.03 * hops_term,
            'inact':   -0.05 * inactive_pen,
            'blind':   -0.07 * blind_pen,
            'sad':     -0.04 * sad_pen,
            'bored':   -0.03 * bored_pen,
        }
        return max(0.0, min(1.0, r))

    # ─────────────────────────────────────────────────────────────────────
    # EMA smoothing
    # ─────────────────────────────────────────────────────────────────────

    # Per-key sane clamps. ANY input outside these is treated as a bad
    # sample and the EMA is updated with the clamped value instead. Prevents
    # one rogue epoch (e.g. native pwnagotchi reward returning 1e16) from
    # poisoning the EMA forever — without that clamp we observed the
    # 'reward' EMA get stuck at -8.5e15 across 125 epochs.
    EMA_CLAMP = {
        'aps':            (0.0, 5000.0),
        'hs_rate':        (0.0, 1.0),
        'reward':         (-2.0, 2.0),
        'missed_rate':    (0.0, 1.0),
        'hs_per_min':     (0.0, 600.0),
        'active_ratio':   (0.0, 1.0),
        'inactive_ratio': (0.0, 1.0),
        'hops_per_epoch': (0.0, 200.0),
        'temperature':    (-40.0, 130.0),
        'cpu_load':       (0.0, 1.0),
        'speed':          (0.0, 200.0),
        # v2.1.0 fields verified in noai _epoch_data
        'num_peers':      (0.0, 100.0),
        'mem_usage':      (0.0, 1.0),     # 0.0–1.0 fraction
        'slept_for_secs': (0.0, 600.0),
    }

    def _ema(self, key, value):
        # Reject non-finite (nan/inf) — they would propagate forever.
        v = _sf(value)
        if not math.isfinite(v):
            v = 0.0
        # Per-key clamp to reject pathological inputs.
        lo, hi = self.EMA_CLAMP.get(key, (-1e9, 1e9))
        if v < lo:
            v = lo
        elif v > hi:
            v = hi
        a    = float(self.cfg['ema_alpha'])
        prev = self.ema.get(key)
        # Defensive: if a stored EMA somehow got corrupted (NaN/inf, or far
        # outside the clamp range — e.g. legacy state from before this
        # safeguard), drop it and treat this sample as the first.
        if prev is not None:
            if not math.isfinite(_sf(prev)) or prev < lo - 1e-6 or prev > hi + 1e-6:
                prev = None
        new  = v if prev is None else (a * v + (1.0 - a) * prev)
        # Final defensive clamp on the output too.
        if new < lo:
            new = lo
        elif new > hi:
            new = hi
        # v1.7 DENORMAL FLOOR: when a [0, 1]-clamped EMA decays below
        # 1e-6 from many consecutive zero inputs, snap to exactly 0.
        # Real community telemetry showed values like hs_rate=2.4e-15
        # and missed_rate=2.3e-28 — mathematically valid exponential
        # decay (alpha=0.30 ^ ~100 epochs of zero) but practically
        # meaningless. Worse, the next non-zero sample creates an
        # enormous EMA jump (1e-15 → ~0.15 in one step) that the
        # reward function may credit to whichever arm was chosen at
        # that moment, polluting the bandit. Only applied when the
        # clamp range is [0.0, X] — bipolar signals like 'reward'
        # legitimately spend time near zero.
        if lo == 0.0 and abs(new) < 1e-6:
            new = 0.0
        self.ema[key] = new
        return new

    # ─────────────────────────────────────────────────────────────────────
    # Channel scoring & scheduling
    # ─────────────────────────────────────────────────────────────────────

    def _ch_score(self, ch):
        """
        Score a channel for priority selection.
        Combines persistent lifetime stats with fresh session signals
        AND a critical "uncaptured AP opportunity" boost.

        For UNIQUE handshakes, what matters is not just past success — it's
        whether there are CURRENTLY VISIBLE uncaptured APs on this channel.
        That signal dominates over historical data once we have it.

        v1.6 PERF: results are memoised per-epoch in `_ch_score_cache`.
        `_schedule_channels` calls this O(channels²) (sort + weighted
        pick + filter), and each call iterates `_known_aps` (~400
        entries on dense terrain). Without caching that's ~78 k ops per
        epoch on a Pi Zero 2 W. Cache invalidates automatically on
        epoch boundary; explicitly invalidate via `_ch_score_cache.clear()`
        whenever an event handler does something that meaningfully
        changes scores within the same epoch (handshake, AP visibility
        flip).
        """
        # Per-epoch cache. The (epoch, ch) pair is the cache key — when
        # epoch advances, all entries are stale; we lazy-evict by
        # checking the epoch counter, not by walking the dict.
        if self._ch_score_epoch != self.epochs_seen:
            self._ch_score_cache.clear()
            self._ch_score_epoch = self.epochs_seen
        cached = self._ch_score_cache.get(ch)
        if cached is not None:
            return cached
        # FIX: take a single locked snapshot of all _ch_lt / _free_channels /
        # _gps_zones / _known_aps state we need; concurrent event-handlers
        # mutate these dicts/lists. After this we work on snapshots only.
        live_uncaptured           = 0
        live_uncaptured_w_clients = 0
        live_strong_signals       = 0
        with self._state_lock:
            lt        = dict(self._ch_lt[ch])
            free      = sum(1 for c in self._free_channels if c == ch)
            aps_snap  = list(self._known_aps.values())
            zone_ch_count = 0
            if self._current_zone is not None:
                zc = self._gps_zones.get(self._current_zone, {}).get(
                    'channels', {})
                zone_ch_count = zc.get(ch, 0)
            dead_count = self._dead_lt.get(ch, 0)
        for ap in aps_snap:
            if _si(ap.get('channel', 0)) != ch:
                continue
            if not ap.get('AT_visible', False):
                continue
            if ap.get('AT_already_captured', False):
                continue
            if ap.get('AT_pmf_detected', False):
                continue
            if ap.get('AT_cooldown_until', 0) > self.epochs_seen:
                continue
            live_uncaptured += 1
            if ap.get('AT_clients', 0) > 0:
                live_uncaptured_w_clients += 1
            if _sf(ap.get('rssi', -100)) > -70:
                live_strong_signals += 1

        score = (
            # Historical productivity (lifetime stats)
            lt['hs']         * 4.0
          + lt['passive_hs'] * 5.0       # passive captures are FREE — boost
          - lt['wasted']     * 0.7
          + lt['free_seen']  * 0.3

            # Live opportunity (current uncaptured APs visible) — DOMINANT
          + live_uncaptured            * 6.0
          + live_uncaptured_w_clients  * 4.0   # clients = deauth opportunity
          + live_strong_signals        * 3.0   # strong RSSI = high success rate

            # Channel positioning
          + free             * 2.0
          + (2.0 if ch in self.NON_OVERLAPPING else 0.0)
          + 0.01
        )

        # Zone-specific channel bonus: if this channel has been
        # productive in the current GPS zone specifically
        if zone_ch_count:
            score += zone_ch_count * 1.5

        # Channel-efficiency multiplier.
        #
        # v1.5 telemetry: ch1 5% HS/attack vs ch8 73% over 41 assocs.
        # v1.7 community telemetry: across four users, ch7 dominates at
        #   16.5% HS/attack (97 attempts) but the bandit kept piling
        #   onto ch1 (970 attempts, 8.1% HS/attack). The old
        #   `0.5 + eff*3.0` cap 1.5× gave ch7 only ~1.0×, losing to
        #   ch1's larger absolute base score on raw history.
        #
        # New: `0.5 + eff*5.0`, cap 0.4–2.5×. A 16% efficiency channel
        # now gets 1.30×; a 20% channel gets 1.5×; a 30%+ channel
        # gets the full 2.0–2.5× boost it deserves.
        #
        # Threshold lowered 30 → 20 attempts so genuinely-good but
        # less-visited channels start being rewarded earlier.
        attempts_lt = lt['assocs'] + lt['deauths']
        if attempts_lt >= 20:
            eff = lt['hs'] / max(1, attempts_lt)
            # eff=0.05 → 0.75   (slight punishment)
            # eff=0.10 → 1.00   (break even)
            # eff=0.16 → 1.30   (community ch7-tier — boost)
            # eff=0.20 → 1.50
            # eff=0.30 → 2.00
            # eff=0.50 → 2.50   (capped — best of the best)
            mul = max(0.4, min(2.5, 0.5 + eff * 5.0))
            score *= mul

        score *= max(0.05, 1.0 - float(self.cfg['dead_ch_lifetime_weight'])
                                 * dead_count)
        result = max(0.0, score)
        # Cache for the rest of this epoch.
        self._ch_score_cache[ch] = result
        return result

    def _pick_weighted(self, pool, n):
        """Weighted random draw without replacement, weighted by score."""
        if not pool or n <= 0:
            return []
        candidates = [(c, self._ch_score(c)) for c in pool]
        total      = sum(s for _, s in candidates)
        picks      = []
        while len(picks) < n and candidates and total > 1e-9:
            r   = random.random() * total
            acc = 0.0
            for i, (c, s) in enumerate(candidates):
                acc += s
                if acc >= r:
                    picks.append(c)
                    total -= s
                    candidates.pop(i)
                    break
        return picks

    def _resolve_channel_strategy(self):
        """Return the effective channel strategy string for THIS epoch.

        Modes:
          - "auto" (default): meta-bandit decides per-block. Returns
            whichever strategy is currently active in the block.
          - "adaptive" / "full" / "capped": that exact strategy.
          - Legacy `respect_full_channels` flag is honoured if
            channel_strategy is unset: True→"full", False→"capped".
        """
        strat = self.cfg.get('channel_strategy')
        if strat == 'auto':
            return self._strategy_current or 'adaptive'
        if strat in ('adaptive', 'full', 'capped'):
            return strat
        rfc = self.cfg.get('respect_full_channels')
        if rfc is True:
            return 'full'
        if rfc is False:
            return 'capped'
        return 'auto'

    def _strategy_hill_reward(self, uniques, epochs):
        """Convert (uniques captured in N epochs) → bounded reward [0, 1].

        v2.0 (F-04): target rate is now ADAPTIVE, derived from the
        same 90th-percentile-of-recent-hpm logic the param bandit uses
        in `_adaptive_hpm_target`. This fixes a real bug from v1.9
        where the fixed target=0.5 unique/epoch (≈30/hour) was so
        high in sparse environments that EVERY block scored ≤ 0.10
        reward — meaning the bandit couldn't differentiate strategies.
        Now the target scales with what's achievable in this
        environment, so the bandit can always learn.

        Conversion: target is in unique/MINUTE (HPM scale) but our
        block reward is in unique/EPOCH. Convert by assuming epochs
        approximate to 60s (the pwnagotchi default); deviation up to
        2× is fine — it just shifts the scoring slightly.

        Hill saturation:
          rate=0          → 0.0
          rate=target/2   → 0.33
          rate=target     → 0.50
          rate=2×target   → 0.67
          rate=4×target   → 0.80
        """
        if epochs <= 0:
            return 0.0
        rate_per_epoch = uniques / epochs
        # Translate the param-bandit's adaptive HPM target (per minute)
        # to a per-epoch equivalent. With default ~60s epochs, 1 hpm =
        # 1 unique per epoch. Floor at 0.05/ep so even sparse-env
        # bandits can produce non-trivial rewards.
        adaptive_target_hpm = self._adaptive_hpm_target() or 0.5
        target = max(0.05, adaptive_target_hpm)
        if rate_per_epoch <= 0:
            return 0.0
        ratio = rate_per_epoch / target
        return max(0.0, min(1.0, ratio / (ratio + 1.0)))

    def _strategy_bandit_for(self, mobility=None):
        """Return the per-mobility strategy bandit dict.
        Defaults to the current mobility. Defensive against unknown
        mobility values (e.g. legacy 'walking') — falls back to
        stationary."""
        m = mobility or self._current_mobility or self.MOBILITY_STATIONARY
        if m not in self._strategy_bandit:
            m = self.MOBILITY_STATIONARY
        return self._strategy_bandit[m]

    def _strategy_ucb_pick(self, mobility=None):
        """UCB1 over the three strategies WITHIN the given mobility.

        v2.0 (A1): each mobility has its own bandit. The pick uses
        only that mobility's history.

        v2.2.0: when prefer_stability=True AND mobility=moving, drop
        'full' from consideration. Walking with a long channel list
        means more channel hops per minute than the firmware sees on
        a stationary stock pwnagotchi — exactly the kind of extra
        load the noai branch was designed to avoid. We still allow
        capped + adaptive (which preserve the user's channel universe
        but keep cycle times tight).
        """
        bandit = self._strategy_bandit_for(mobility)
        strats = list(bandit.keys())
        if (bool(self.cfg.get('prefer_stability', True))
                and (mobility or self._current_mobility) == self.MOBILITY_MOVING):
            # Drop 'full' while moving in stability mode — battery + firmware
            strats = [s for s in strats if s != 'full']
        # Cold-start: any untried strategy first.
        untried = [s for s in strats
                   if bandit[s]['n'] == 0
                   or len(bandit[s]['rewards']) == 0]
        if untried:
            return random.choice(untried)
        # UCB1 score: mean + c * sqrt(log(N_total) / n_arm)
        c = float(self.cfg.get('auto_strategy_c', 1.4))
        total_n = sum(d['n'] for d in (bandit[s] for s in strats))
        best_score = -math.inf
        best_strat = strats[0]
        for s in strats:
            d = bandit[s]
            rs = d['rewards']
            if not rs:
                continue
            mean = sum(rs) / len(rs)
            n = d['n']
            expl = c * math.sqrt(math.log(max(2, total_n)) / max(1, n))
            score = mean + expl
            if score > best_score:
                best_score = score
                best_strat = s
        return best_strat

    def _strategy_block_size_check(self):
        """Returns True if the current block should end now.

        v2.0 (F-05): primary trigger is wall-clock seconds. Falls back
        to the legacy epoch-counter if the user explicitly set
        auto_strategy_block_epochs > 0 (back-compat with v1.9 configs).
        """
        epochs_legacy = int(self.cfg.get('auto_strategy_block_epochs', 0) or 0)
        if epochs_legacy > 0:
            if self._strategy_block_start_ep is None:
                return False
            return (self.epochs_seen - self._strategy_block_start_ep) \
                >= max(5, epochs_legacy)
        # Default: wall-clock seconds.
        secs = max(60, int(self.cfg.get('auto_strategy_block_secs', 1800)))
        if self._strategy_block_start_mono is None:
            return False
        return (time.monotonic() - self._strategy_block_start_mono) >= secs

    def _start_strategy_block(self, log_prefix='starting'):
        """Begin a fresh block under the current mobility's bandit."""
        mobility = self._current_mobility or self.MOBILITY_STATIONARY
        next_strat = self._strategy_ucb_pick(mobility)
        self._strategy_current          = next_strat
        self._strategy_block_start_ep   = self.epochs_seen
        self._strategy_block_start_mono = time.monotonic()
        self._strategy_block_mobility   = mobility
        self._uniques_at_block_start    = self._lifetime_new_count
        epochs_legacy = int(self.cfg.get('auto_strategy_block_epochs', 0) or 0)
        if epochs_legacy > 0:
            duration_s = f'{epochs_legacy} epochs'
        else:
            secs = int(self.cfg.get('auto_strategy_block_secs', 1800))
            duration_s = f'{secs}s'
        log.info(f'[envtune] auto-strategy: {log_prefix} block under '
                 f'mobility={mobility} → {next_strat} ({duration_s})')

    def _maybe_advance_strategy_block(self):
        """Called each epoch in `on_epoch`. If channel_strategy='auto'
        and the block has expired, score it under the mobility it ran
        in and pick the next block's strategy under the CURRENT
        mobility (which may have changed)."""
        if self.cfg.get('channel_strategy') != 'auto':
            return
        # First-ever invocation
        if self._strategy_current is None:
            self._start_strategy_block(log_prefix='starting')
            return
        # Block still in progress
        if not self._strategy_block_size_check():
            return
        # Block finished — score under the mobility it ran in.
        block_mobility = (self._strategy_block_mobility
                          or self.MOBILITY_STATIONARY)
        epochs_in_block = max(1,
            self.epochs_seen - (self._strategy_block_start_ep or self.epochs_seen))
        uniques_this_block = max(
            0, self._lifetime_new_count - self._uniques_at_block_start)
        reward = self._strategy_hill_reward(uniques_this_block, epochs_in_block)
        prev_strat = self._strategy_current
        bandit = self._strategy_bandit_for(block_mobility)
        d = bandit.setdefault(
            prev_strat, {'n': 0, 'rewards': deque(maxlen=20)})
        d['n'] += 1
        d['rewards'].append(reward)
        log.info(
            f'[envtune] auto-strategy block done: {prev_strat}@'
            f'{block_mobility} → {uniques_this_block} unique HS in '
            f'{epochs_in_block} ep (reward={reward:.3f})')
        # Start next block under CURRENT mobility (may differ from the
        # block we just scored).
        self._start_strategy_block(log_prefix='next')

    def _abort_strategy_block(self, reason):
        """v2.0 (F-06): drop the in-progress block without scoring it.
        Used on location change — the block ran in a now-stale
        environment, scoring it would credit the wrong mobility's
        bandit. Next epoch will start a clean block."""
        if self._strategy_current is None:
            return
        log.info(
            f'[envtune] auto-strategy: aborting block ({reason}) — '
            f'in-progress {self._strategy_current}@'
            f'{self._strategy_block_mobility}')
        self._strategy_current          = None
        self._strategy_block_start_ep   = None
        self._strategy_block_start_mono = None
        self._strategy_block_mobility   = None

    def _schedule_channels(self, agent):
        """Build the next scan channel list.

        v1.8.0 dispatches by `channel_strategy`:
          - "adaptive" (default): top-K capped most epochs, full sweep
            every channel_full_sweep_every epochs. Best total HS yield.
          - "full":  scan whole universe every epoch.
          - "capped": legacy top-K, no sweeps.

        All modes are bounded by `_user_channels_orig` — channels
        outside the user's config never appear, channels inside it
        are never permanently dropped (full + adaptive guarantee at
        least one full visit per sweep period).
        """
        try:
            n_extra = int(self._profile['extra_channels'])

            # User universe — captured once in on_ready. Falls back if
            # something went sideways during startup capture.
            universe = self._user_channels_orig
            if not universe:
                universe = list(range(1, 12))

            with self._state_lock:
                if not self._unscanned_channels:
                    # Restrict_channels (envtune-specific override) wins
                    # if present, else use the user universe.
                    if 'restrict_channels' in self.cfg:
                        pool = list(self.cfg['restrict_channels'])
                    else:
                        pool = list(universe)
                    self._unscanned_channels = [c for c in pool
                                                if c in universe]
                # Snapshot — work on copies from here on to avoid races
                # with on_wifi_update / on_bcap_wifi_ap_lost.
                unscanned_snap     = [c for c in self._unscanned_channels
                                      if c in universe]
                active_snap        = [c for c in self._active_channels
                                      if c in universe]
                dead_session_snap  = dict(self._dead_session)

            strategy = self._resolve_channel_strategy()

            # Decide if THIS epoch is a full-universe sweep:
            # - "full" mode: every epoch is a sweep
            # - "adaptive" mode: every channel_full_sweep_every epochs
            # - "capped" mode: never
            sweep_every = max(2, int(self.cfg.get(
                'channel_full_sweep_every', 15)))
            is_sweep_epoch = (
                strategy == 'full' or (
                    strategy == 'adaptive'
                    and self.epochs_seen > 0
                    and (self.epochs_seen - self._last_full_sweep_ep)
                        >= sweep_every))

            if is_sweep_epoch:
                ranked = sorted(universe, key=lambda c: -self._ch_score(c))
                if strategy == 'adaptive':
                    self._last_full_sweep_ep = self.epochs_seen
                    log.info(
                        f'[envtune] adaptive full sweep '
                        f'({len(ranked)} channels) '
                        f'— next in {sweep_every} epochs')
                else:
                    # v2.0 (F-15): the long-cycle warning fires only
                    # when the user EXPLICITLY set channel_strategy="full"
                    # — not on auto-mode's periodic full-sweep blocks
                    # (which were generating false-alarm warnings).
                    cfg_mode = self.cfg.get('channel_strategy')
                    if cfg_mode == 'full' and self.epochs_seen % 50 == 1:
                        personality = agent._config.get('personality', {})
                        hrt = max(1.0, _sf(personality.get('hop_recon_time', 8)))
                        cycle_secs = len(ranked) * hrt
                        if cycle_secs > 120:
                            log.info(
                                f'[envtune] strategy=full: scanning all '
                                f'{len(ranked)} channels each epoch '
                                f'(~{cycle_secs:.0f}s recon cycle). '
                                f'Consider channel_strategy="auto" or '
                                f'"adaptive" for higher HS yield.')
                agent._config['personality']['channels'] = ranked
                return

            # CAPPED PATH (also adaptive non-sweep epochs).
            cdl       = int(self.cfg['dead_channel_cooldown'])
            available = [c for c in unscanned_snap
                         if dead_session_snap.get(c, 0) < cdl]
            if not available:
                with self._state_lock:
                    self._dead_session.clear()
                available = list(unscanned_snap)

            pw     = float(self.cfg['priority_channel_weight'])
            n_prio = max(1, int(round(n_extra * pw))) if n_extra > 0 else 0
            n_expl = max(0, n_extra - n_prio)

            prio_pool  = [c for c in available if self._ch_score(c) > 0.05]
            prio_picks = self._pick_weighted(prio_pool, n_prio)

            shortfall  = n_prio - len(prio_picks)
            expl_pool  = [c for c in available if c not in prio_picks]
            n_expl    += shortfall
            expl_picks = (random.sample(expl_pool, min(n_expl, len(expl_pool)))
                          if expl_pool else [])

            # Build score-sorted, deduplicated channel list
            all_candidates = set(active_snap) | set(prio_picks) | set(expl_picks)
            next_chs = sorted(
                all_candidates,
                key=lambda c: -self._ch_score(c),
            )

            # CRITICAL: cap total channels to prevent recon stalls in dense
            # environments. Each channel gets ~hop_recon_time seconds, so
            # one full cycle ≈ N_channels × hop_recon_time. We want a
            # cycle bounded to ~`target_cycle_secs` (default 75 s) so a
            # freshly-arriving client doesn't sit on a channel we haven't
            # visited for minutes. v1.4.1 fix — earlier versions computed
            # `hrt` but never used it, so the cap was static.
            personality = agent._config.get('personality', {})
            hrt = max(1.0, _sf(personality.get('hop_recon_time', 8)))
            target_cycle_secs = float(self.cfg.get('target_recon_cycle_secs', 75))
            hrt_max   = max(3, int(target_cycle_secs / hrt))
            must_have = len(active_snap)
            # v1.7.1: cap can never go BELOW the user's configured
            # channel universe size. If the user explicitly listed 30
            # channels in personality.channels, we honour that (even
            # in legacy capped mode — the cap only applies to bandit
            # ADDITIONS beyond the user's list, not to the user's list
            # itself). The 14-channel hard cap is also lifted to match
            # the user's universe so 5 GHz channel sets aren't truncated.
            user_n = len(universe)
            max_total = max(
                user_n,                                       # honour user
                min(must_have + n_extra,
                    max(must_have, hrt_max),
                    max(14, user_n)))

            # Identify channels with strong, attackable, uncaptured APs.
            # These MUST stay in the list even if score-cap would drop them —
            # losing such a channel = guaranteed missed unique handshake.
            must_keep = set()
            with self._state_lock:
                aps_snap_local = list(self._known_aps.values())
            for ap in aps_snap_local:
                if not ap.get('AT_visible'):
                    continue
                if ap.get('AT_already_captured'):
                    continue
                if ap.get('AT_pmf_detected'):
                    continue
                if ap.get('AT_cooldown_until', 0) > self.epochs_seen:
                    continue
                if _sf(ap.get('rssi', -100)) <= -75:
                    continue
                ch = _si(ap.get('channel', 0))
                if ch:
                    must_keep.add(ch)

            dropped = []
            if len(next_chs) > max_total:
                # Keep top max_total by score, then add must_keep channels
                # that didn't make the cap (force-included)
                top_keep      = next_chs[:max_total]
                forced_extras = [c for c in must_keep if c not in top_keep]
                final         = top_keep + forced_extras
                dropped       = [c for c in next_chs if c not in final]
                next_chs      = final

            # Reconcile unscanned-pool mutations under lock at the end —
            # one write transaction instead of mid-loop list.remove racing
            # with on_wifi_update.
            with self._state_lock:
                for ch in dropped:
                    if (ch not in self._unscanned_channels
                            and ch not in next_chs):
                        self._unscanned_channels.append(ch)
                for ch in prio_picks + expl_picks:
                    if (ch in self._unscanned_channels
                            and ch in next_chs):
                        self._unscanned_channels.remove(ch)

            # In LEGACY "capped" mode we never want to silently drop a
            # user-configured channel. Adaptive non-sweep epochs are
            # explicitly allowed to (their full sweep refreshes the
            # missed channels every channel_full_sweep_every epochs).
            if strategy == 'capped':
                present = set(next_chs)
                for ch in universe:
                    if ch not in present:
                        next_chs.append(ch)

            agent._config['personality']['channels'] = next_chs
            # Note: channel set is applied by pwnagotchi's recon loop
            # via `wifi.recon.channel` — no manual sync needed.
        except Exception as e:
            self._record_error('_schedule_channels')
            log.exception(f'[envtune] _schedule_channels: {e}')

    # ─────────────────────────────────────────────────────────────────────
    # AP tracking (thread-safe via _state_lock on public entry points)
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def _norm(name):
        if not name:
            return 'EMPTY'
        return ''.join(c for c in str(name).lower() if c.isalnum())

    def _ap_id(self, ap):
        """
        Unique AP identifier. For hidden SSIDs we use only the MAC so
        each hidden AP is tracked separately (previous versions merged
        them under a single 'HIDDEN' id, losing data).
        """
        hostname = ap.get('hostname', '')
        mac      = ap.get('mac', '')
        if not hostname or hostname == '<hidden>' or hostname == '':
            return 'hidden-' + self._mac_norm(mac)
        return self._norm(hostname) + '-' + self._mac_norm(mac)

    @staticmethod
    def _mac_norm(mac):
        return str(mac).lower().replace(':', '').replace('-', '').replace(' ', '')

    def _is_whitelisted(self, ap):
        """Check if an AP is in the user's whitelist (SSID or MAC)."""
        mac_n = self._mac_norm(ap.get('mac', ''))
        if mac_n and mac_n in self._whitelist_macs:
            return True
        ssid = ap.get('hostname', '')
        if ssid and ssid in self._whitelist_ssids:
            return True
        # Partial MAC prefix match (pwnagotchi supports this)
        for prefix in self._whitelist_macs:
            if len(prefix) < 12 and mac_n.startswith(prefix):
                return True
        return False

    def _mark_ap_seen(self, ap, context=None):
        try:
            # Skip whitelisted APs entirely — pwnagotchi won't attack them
            # so tracking them would distort channel scores
            if self._is_whitelisted(ap):
                return

            # Enforce AP dict size cap (evict least-recently-seen)
            cap = int(self._profile['ap_track_max'])
            if len(self._known_aps) >= cap:
                self._evict_oldest_ap()

            apID  = self._ap_id(ap)
            ch    = _si(ap.get('channel', 0))
            tag   = 'AT_' + context if context else 'AT_seen'
            mac_n = self._mac_norm(ap.get('mac', ''))

            with self._state_lock:
                if apID not in self._known_aps:
                    entry = dict(ap)
                    entry.update({
                        'AT_seen':             1,
                        'AT_visible':          True,
                        'AT_attacks':          0,
                        'AT_handshake':        0,
                        'AT_clients':          0,
                        'AT_client_epoch':     -99,
                        'AT_lastattack_ep':    -99,
                        'AT_missed':           0,
                        'AT_rssi_hist':        deque([_sf(ap.get('rssi', -80))], maxlen=4),
                        'AT_pmf_detected':     False,
                        'AT_pmkid_success':    False,
                        'AT_cooldown_until':   0,
                        'AT_already_captured': mac_n in self._captured_bssids,
                        'AT_cracked':          mac_n in self._cracked_bssids,
                        'AT_efficiency':       0.0,
                        'AT_lastseen':         time.monotonic(),
                        # First-seen epoch — used by _ap_priority_score to
                        # surface brand-new BSSIDs aggressively. A BSSID
                        # appearing for the first time this session AND
                        # not in our captured set is the highest-EV moment
                        # to attack: clients may still be in connect/roam
                        # phase leaking EAPOL.
                        'AT_first_seen_ep':    self.epochs_seen,
                        tag:                   1,
                    })
                    self._known_aps[apID] = entry
                    self._inc_ch('Unique APs', ch)
                    self._inc_ch('Current APs', ch)
                else:
                    entry = self._known_aps[apID]
                    for k in ('rssi', 'hostname', 'channel', 'encryption', 'clients'):
                        if k in ap:
                            entry[k] = ap[k]
                    if not entry.get('AT_visible', True):
                        entry['AT_visible'] = True
                        entry['AT_seen']    = entry.get('AT_seen', 0) + 1
                        self._inc_ch('Current APs', ch)
                    entry[tag] = entry.get(tag, 0) + 1
                    entry['AT_rssi_hist'].append(_sf(ap.get('rssi', -80)))
                    if mac_n in self._captured_bssids:
                        entry['AT_already_captured'] = True
                    if mac_n in self._cracked_bssids:
                        entry['AT_cracked'] = True

                self._known_aps[apID]['AT_lastseen'] = time.monotonic()

        except Exception as e:
            log.debug(f'[envtune] _mark_ap_seen: {e}')

    def _evict_oldest_ap(self):
        """Remove the lowest-value AP entry to stay under cap.

        Eviction priority (lowest value first):
          1. Already-captured APs (we won't attack them again — only
             retain for the skip-list, which lives in _bcap_skip_macs).
          2. Cracked APs (we have the password — no further value).
          3. APs with zero attack efficiency and many attacks (PMF / hidden /
             unreachable — wasting our attack budget if kept).
          4. Otherwise: oldest AT_lastseen (LRU fallback).

        Never evicts a fresh AP we haven't tried yet, even if it's "old".
        """
        if not self._known_aps:
            return

        def _score(k):
            ap          = self._known_aps[k]
            captured    = ap.get('AT_already_captured', False)
            cracked     = ap.get('AT_cracked', False)
            attacks     = ap.get('AT_attacks', 0)
            handshakes  = ap.get('AT_handshake', 0)
            efficiency  = ap.get('AT_efficiency', 0.0) or 0.0
            lastseen    = ap.get('AT_lastseen', 0)
            # Lower tuple = first to evict.
            # Tier 0: cracked + captured                         (cheapest)
            # Tier 1: captured but not cracked
            # Tier 2: many attacks, zero handshakes (dead target)
            # Tier 3: attacked but low-efficiency
            # Tier 4: never attacked (precious — keep)
            if captured and cracked:
                tier = 0
            elif captured:
                tier = 1
            elif attacks >= 5 and handshakes == 0:
                tier = 2
            elif attacks > 0 and efficiency < 0.05:
                tier = 3
            else:
                tier = 4
            return (tier, lastseen)
        with self._state_lock:
            victim = min(self._known_aps, key=_score)
            self._known_aps.pop(victim, None)

    def _rssi_trend(self, apID):
        """Positive = approaching (RSSI improving)."""
        ap = self._known_aps.get(apID)
        if not ap:
            return 0.0
        hist = list(ap.get('AT_rssi_hist', []))
        if len(hist) < 2:
            return 0.0
        return _sf(hist[-1]) - _sf(hist[0])

    def _ap_priority_score(self, apID):
        """Attack priority — higher = attack this first. 0 = skip."""
        ap = self._known_aps.get(apID)
        if ap is None:
            return 0.0
        if ap.get('AT_cooldown_until', 0) > self.epochs_seen:
            return 0.0
        # Already-captured handling: keep in the queue at LOW but non-zero
        # priority so opportunistic re-captures (fresh clients, rotated
        # PSK, incomplete prior capture) can still happen. The reward
        # function and channel scoring already favour brand-new BSSIDs
        # heavily, so the bandit will still concentrate on uniques.
        if ap.get('AT_already_captured', False):
            if ap.get('AT_cracked', False):
                return _sf(self.cfg.get('recapture_priority_cracked', 0.05))
            base = _sf(self.cfg.get('recapture_priority_base', 0.40))
            # Fresh-client opportunistic boost — if a client just
            # connected on a network we already have, we may catch a
            # different EAPOL exchange (different client → different
            # PMK derivation noise) cheaply.
            clients = ap.get('AT_clients', 0)
            recency = self.epochs_seen - ap.get('AT_client_epoch', -99)
            if clients > 0 and recency <= 1:
                bonus = _sf(self.cfg.get('recapture_client_bonus', 0.5))
                base += bonus * min(clients, 3)
            return base

        score        = 1.0
        attacks      = ap.get('AT_attacks', 0)
        clients      = ap.get('AT_clients', 0)
        recency      = self.epochs_seen - ap.get('AT_client_epoch', -99)
        client_fresh = recency <= int(self.cfg['client_recency_epochs'])
        if clients > 0 and client_fresh:
            score += 4.0 * min(clients, 5)
            # FIX: a freshly-seen client on a still-uncaptured AP is the
            # single highest-value moment — clients leak EAPOL on connect/
            # roam and we want to be hammering deauth right then. Stack
            # an extra bonus when the client signal is *very* fresh.
            if recency <= 1:
                score += 2.0 * min(clients, 3)

        # Untried bonus — UCB-style optimism, encourage exploration of
        # APs we have never attacked. Decays as attacks accumulate.
        if attacks == 0:
            score += 1.0
        elif attacks <= 2:
            score += 0.5

        # Fresh-session bonus — a BSSID that appeared for the first time
        # this session is high-EV for unique captures. Decays linearly
        # over the next 8 epochs so the boost is real but doesn't
        # dominate forever. Skipped if we've already captured it.
        first_seen = ap.get('AT_first_seen_ep', -99)
        if first_seen >= 0:
            age = self.epochs_seen - first_seen
            if 0 <= age < 8:
                score += 1.5 * (1.0 - age / 8.0)

        score += ap.get('AT_efficiency', 0.0) * 3.0
        # v1.6 algorithmic upgrade: RSSI is logarithmic (dB scale), but
        # the v1.5 formula `(rssi + 65)/20` weighted it linearly. Effect:
        # an AP at -50 dBm got weight 0.75; an AP at -65 dBm got weight
        # 0.0. In reality the -50 dBm AP succeeds *vastly* more often
        # than -65 dBm — handshake success roughly doubles every 6 dB.
        # Geometric weighting captures this:
        #   rssi=-85 → ~0.06    (weak — barely worth attacking)
        #   rssi=-75 → ~0.25
        #   rssi=-65 → ~1.00
        #   rssi=-55 → ~4.00    (very strong — prioritise heavily)
        # Capped at 5.0 so a -45 dBm super-strong AP doesn't overwhelm
        # client-presence signals (which are independently scored above).
        rssi   = _sf(ap.get('rssi', -85))
        score += min(5.0, 2 ** ((rssi + 75.0) / 6.0))
        score += self._rssi_trend(apID) * 0.4

        if ap.get('AT_pmf_detected', False) and not ap.get('AT_pmkid_success', False):
            score *= 0.2

        # Cracked networks are lower priority (we have the password)
        if ap.get('AT_cracked', False):
            score *= 0.3

        # Many attacks, zero handshakes → likely PMF/hidden — drop priority
        # before sinking more radio time. Don't go to zero (PMKID may still
        # work after a roam) but mute aggressively.
        if attacks >= 8 and ap.get('AT_handshake', 0) == 0:
            score *= 0.25

        return max(0.0, score)

    def _inc_ch(self, stat, ch, count=1):
        if stat not in self._chistos:
            self._chistos[stat] = {-1: 0}
        self._chistos[stat][ch] = self._chistos[stat].get(ch, 0) + count
        self._chistos[stat][-1] = self._chistos[stat].get(-1, 0) + count
        aa       = self._chistos['_all_actions']
        aa[ch]   = aa.get(ch, 0) + abs(count)
        aa[-1]   = aa.get(-1, 0) + abs(count)
        # v2.0 (F-13): cap _chistos to bound long-session memory growth.
        # Eviction: in '_all_actions' (the union counter), drop the
        # least-active channel(s) and propagate to all sub-stats.
        # Cheap — only fires when over cap, walks _all_actions once.
        max_ch = int(self.cfg.get('chistos_max_channels', 200))
        if max_ch > 0 and len(aa) - 1 > max_ch:  # -1 for the '-1' total key
            # Find the least-active channels (excluding -1 total)
            channels_by_activity = sorted(
                ((c, n) for c, n in aa.items() if c != -1),
                key=lambda kv: kv[1])
            evict_count = (len(aa) - 1) - max_ch
            for c, _n in channels_by_activity[:evict_count]:
                # Drop from _all_actions and every sub-stat
                for sub in self._chistos.values():
                    sub.pop(c, None)

    # ─────────────────────────────────────────────────────────────────────
    # Nexmon crash detection (uses pre-epoch-update EMA)
    # ─────────────────────────────────────────────────────────────────────

    def _check_nexmon_crash(self, aps, interactions):
        """Compare against prev_aps_ema (stored across epochs)."""
        prev = self._prev_aps_ema
        if prev is not None and prev > 5 and aps == 0 and interactions == 0:
            self._crash_suspect += 1
        else:
            self._crash_suspect = 0
        return self._crash_suspect >= 2

    # ─────────────────────────────────────────────────────────────────────
    # Location change detection (works with or without GPS)
    # ─────────────────────────────────────────────────────────────────────

    def _compute_location_fp(self, access_points):
        if not access_points:
            return None
        ctr   = defaultdict(int)
        rssis = []
        for ap in access_points:
            ch = _si(ap.get('channel', 0))
            if ch > 0:
                ctr[ch] += 1
            rssis.append(_sf(ap.get('rssi', -80)))
        top = sorted(ctr.items(), key=lambda x: -x[1])[:5]
        return {
            'top':      [c for c, _ in top],
            'avg_rssi': sum(rssis) / len(rssis) if rssis else -80.0,
            'count':    len(access_points),
        }

    def _check_location_change(self, fp):
        if not fp:
            return False
        self._fp_history.append(fp)
        if self._loc_fp_stored is None:
            self._loc_fp_stored = fp
            return False
        old    = self._loc_fp_stored
        union  = set(fp['top']) | set(old['top'])
        jac    = (len(set(fp['top']) & set(old['top'])) / max(1, len(union))
                  if union else 1.0)
        rdiff  = abs(fp['avg_rssi'] - old['avg_rssi'])
        cratio = abs(fp['count'] - old['count']) / max(1, old['count'])
        moved  = jac < 0.30 or rdiff > 15.0 or cratio > 0.70
        self._loc_fp_stored = fp
        # Debounce: prevents constant retriggering while walking/driving
        # (zone hops every ~30s would otherwise reset the boost forever
        # and UCB would never reach exploit phase).
        if moved and self.epochs_seen - self._last_loc_change_ep < 5:
            return False
        if moved:
            self._last_loc_change_ep = self.epochs_seen
        return moved

    # ─────────────────────────────────────────────────────────────────────
    # GPS integration (TheyLive / stock gps / none)
    # ─────────────────────────────────────────────────────────────────────

    def _detect_gps_source(self, agent):
        """
        Determine how to read GPS. Preference order:
          1. agent.session()['gps'] (works for TheyLive + stock gps)
          2. TheyLive NDJSON track file (last line)
          3. None / disabled
        """
        if not self.cfg.get('enable_gps', True):
            return None
        try:
            session = agent.session() or {}
            if 'gps' in session and session['gps']:
                gps = session['gps']
                # Both TheyLive and stock gps expose lat/lon
                lat = _sf(gps.get('Latitude', gps.get('lat', 0)))
                lon = _sf(gps.get('Longitude', gps.get('lon', 0)))
                if lat != 0.0 or lon != 0.0:
                    return 'session'
        except Exception:
            pass
        if os.path.exists(self.GPS_TRACK):
            return 'theylive_ndjson'
        return None

    def _read_gps(self, agent):
        """
        Return current GPS fix dict or None.
        Dict format: {'lat', 'lon', 'alt', 'speed', 'ts_mono', 'raw'}
        """
        if self._gps_source is None:
            return None

        try:
            if self._gps_source == 'session':
                session = agent.session() or {}
                gps = session.get('gps') or {}
                if not gps:
                    return None
                lat   = _sf(gps.get('Latitude', gps.get('lat', 0)))
                lon   = _sf(gps.get('Longitude', gps.get('lon', 0)))
                if lat == 0.0 and lon == 0.0:
                    return None  # no lock
                alt   = _sf(gps.get('Altitude', gps.get('alt', 0)))
                speed = _sf(gps.get('Speed', gps.get('speed', 0)))
                # TheyLive also exposes 'track', 'hdop' — preserve raw
                return {
                    'lat': lat, 'lon': lon, 'alt': alt, 'speed': speed,
                    'ts_mono': time.monotonic(),
                    'raw': gps,
                }

            if self._gps_source == 'theylive_ndjson':
                # Read last line of NDJSON track file
                try:
                    with open(self.GPS_TRACK, 'rb') as f:
                        f.seek(0, 2)
                        size = f.tell()
                        if size == 0:
                            return None
                        # Read last ~4KB and find last \n
                        read_n = min(4096, size)
                        f.seek(size - read_n)
                        tail = f.read().decode('utf-8', errors='ignore')
                    last_line = tail.strip().split('\n')[-1] if tail.strip() else None
                    if not last_line:
                        return None
                    data = json.loads(last_line)
                    lat = _sf(data.get('lat', 0))
                    lon = _sf(data.get('lon', 0))
                    if lat == 0.0 and lon == 0.0:
                        return None
                    return {
                        'lat': lat, 'lon': lon,
                        'alt': _sf(data.get('alt', 0)),
                        'speed': _sf(data.get('speed', 0)),
                        'ts_mono': time.monotonic(),
                        'raw': data,
                    }
                except (FileNotFoundError, json.JSONDecodeError, ValueError):
                    return None

        except Exception as e:
            log.debug(f'[envtune] _read_gps: {e}')

        return None

    def _zone_key(self, lat, lon):
        """
        Convert (lat, lon) into a string zone ID at configured resolution.
        Uses a simple grid: each cell ≈ resolution_m on a side.
        """
        res_m = float(self._profile['zone_resolution_m'])
        # 1 degree latitude  ≈ 111_000 m
        # 1 degree longitude ≈ 111_000 * cos(lat) m
        lat_cell = res_m / 111000.0
        lon_cell = res_m / max(1.0, 111000.0 * math.cos(math.radians(lat)))
        lat_idx  = int(math.floor(lat / lat_cell))
        lon_idx  = int(math.floor(lon / lon_cell))
        return f'{lat_idx}:{lon_idx}'

    GPS_ZONE_CAP = 500   # LRU cap to keep state file bounded
    # Tier-based zone eviction: zones with many attacks and zero
    # handshakes are confirmed-dead and should be dropped before
    # never-touched zones (which might produce handshakes later).
    # Telemetry showed 12/17 zones in real use with 0 HS, several with
    # 5+ visits and 20+ attacks, accumulating indefinitely.
    ZONE_DEAD_ATTACKS = 50

    def _update_gps_zone(self):
        """Update self._current_zone from current GPS fix."""
        fix = self._gps_last_fix
        if not fix:
            self._current_zone = None
            return
        age = time.monotonic() - fix['ts_mono']
        if age > self.cfg['gps_stale_seconds']:
            self._current_zone = None
            return
        zone = self._zone_key(fix['lat'], fix['lon'])
        self._current_zone = zone
        # FIX: _gps_zones is mutated here AND in on_handshake under lock,
        # AND read by _ch_score / _build_state_snapshot. Lock both writers.
        with self._state_lock:
            self._gps_zones[zone]['visits'] += 1
            self._gps_zones[zone]['last_seen'] = time.time()
            # LRU cap with tier-based eviction. Never evict the current
            # zone or any zone that has produced handshakes.
            #   tier 0: confirmed-dead (>=50 attacks, 0 HS) — evict FIRST
            #   tier 1: low-attack 0-HS zones (visited but not exhausted)
            #
            # Within each tier, oldest last_seen goes first (LRU).
            if len(self._gps_zones) > self.GPS_ZONE_CAP:
                def _zone_evict_key(item):
                    zk, zd = item
                    attacks = zd.get('attacks', 0) or 0
                    tier = 0 if attacks >= self.ZONE_DEAD_ATTACKS else 1
                    return (tier, zd.get('last_seen', 0.0) or 0.0)
                victims = [
                    (zk, zd) for zk, zd in self._gps_zones.items()
                    if zk != zone and zd.get('hs', 0) == 0
                ]
                victims.sort(key=_zone_evict_key)
                evict_n = len(self._gps_zones) - self.GPS_ZONE_CAP
                for zk, _zd in victims[:evict_n]:
                    self._gps_zones.pop(zk, None)

    # ─────────────────────────────────────────────────────────────────────
    # Parameter coupling — extensive sanity rules
    # ─────────────────────────────────────────────────────────────────────

    def _sanity_check(self, params):
        """
        Fix known bad inter-parameter combinations. UCB treats params as
        independent but some combinations are always wrong (e.g. very
        high recon_time with very low hop_recon_time).
        """
        p = dict(params)

        # 1) recon_time must be >= 2 × hop_recon_time
        rt  = _sf(p.get('recon_time', 25))
        hrt = _sf(p.get('hop_recon_time', 8))
        if rt < hrt * 2:
            p['recon_time'] = int(min(self.BOUNDS['recon_time'][1], hrt * 2))

        # 2) min_recon_time <= hop_recon_time
        mrt = _sf(p.get('min_recon_time', 5))
        if mrt > hrt:
            p['min_recon_time'] = int(hrt)

        # 3) sta_ttl >= ap_ttl (clients don't expire before their AP)
        if _sf(p.get('sta_ttl', 300)) < _sf(p.get('ap_ttl', 120)):
            p['sta_ttl'] = int(_sf(p.get('ap_ttl', 120)))

        # 4) Tight min_rssi + high max_interactions is wasteful
        if _sf(p.get('min_rssi', -75)) >= -67 and _si(p.get('max_interactions', 3)) > 5:
            p['max_interactions'] = 5

        # 5) Low throttle_d + high max_interactions risks nexmon crash
        if (_sf(p.get('throttle_d', 0.9)) < 0.5
                and _si(p.get('max_interactions', 3)) > 4):
            p['max_interactions'] = 4

        # 6) When moving, long TTLs waste memory on out-of-range APs.
        # v4 schema: covers walking + driving (mobility 2-way).
        if self._current_mobility == self.MOBILITY_MOVING:
            if _sf(p.get('ap_ttl', 120)) > 180:
                p['ap_ttl'] = 180
            if _sf(p.get('sta_ttl', 300)) > 300:
                p['sta_ttl'] = 300

        # 7) In stationary mode, short TTLs lose context unnecessarily
        if self._current_mobility == self.MOBILITY_STATIONARY:
            if _sf(p.get('ap_ttl', 120)) < 120:
                p['ap_ttl'] = 120

        # 8) max_misses_for_recon must allow for weak environments
        if self.ema.get('aps') is not None and _sf(self.ema.get('aps')) < 3:
            # Sparse environment: don't over-trigger recon on misses
            if _si(p.get('max_misses_for_recon', 5)) < 7:
                p['max_misses_for_recon'] = 7

        # 9) max_inactive_scale with very high recon_inactive_multiplier
        #    creates stalls (multiplier^scale × recon_time seconds)
        scale  = _si(p.get('max_inactive_scale', 2))
        mult   = _si(p.get('recon_inactive_multiplier', 2))
        if scale * mult > 8:
            p['max_inactive_scale'] = min(scale, 3)
            p['recon_inactive_multiplier'] = min(mult, 2)

        # 10) Low throttle_a under thermal pressure is dangerous
        if self._thermal_throttle and _sf(p.get('throttle_a', 0.4)) < 0.4:
            p['throttle_a'] = 0.4

        # 11) Very sparse environments: allow deeper min_rssi
        if self.ema.get('aps') is not None and _sf(self.ema.get('aps')) < 4:
            # Don't let the tuner tighten min_rssi when we barely see anything
            if _sf(p.get('min_rssi', -75)) > -75:
                p['min_rssi'] = -80

        # 12) Very dense environments: allow more aggressive filtering
        if self.ema.get('aps') is not None and _sf(self.ema.get('aps')) > 40:
            # Too many APs — focus on strong signals
            if _sf(p.get('min_rssi', -75)) < -78:
                p['min_rssi'] = -75

        # 13) During location change (exploration boost active) ease up
        if self._exploration_boost > 0:
            if _si(p.get('max_interactions', 3)) > 4:
                p['max_interactions'] = 4

        # 14) Low battery: graduated response.
        # v2.2: battery_low_threshold (default 20%) triggers a milder
        # cap — keep max_interactions <= 4 and slightly slower throttle.
        # battery_critical_threshold (default 10%) triggers the harder
        # cap (max_interactions=2, throttle_d>=0.9).
        if self._battery_level is not None:
            crit = float(self.cfg.get('battery_critical_threshold', 10.0))
            low  = float(self.cfg.get('battery_low_threshold', 20.0))
            if self._battery_level < crit:
                p['max_interactions'] = min(_si(p.get('max_interactions', 3)), 2)
                if 'throttle_d' in self._active_params:
                    p['throttle_d'] = max(_sf(p.get('throttle_d', 0.9)), 0.9)
            elif self._battery_level < low:
                p['max_interactions'] = min(_si(p.get('max_interactions', 3)), 4)
                if 'throttle_d' in self._active_params:
                    p['throttle_d'] = max(_sf(p.get('throttle_d', 0.9)), 0.7)

        # 15) Sad/bored mood: longer TTLs to catch slow activity
        if self._mood in ('sad', 'bored'):
            if _sf(p.get('sta_ttl', 300)) < 400:
                p['sta_ttl'] = 400

        # 16) 5GHz-aware recon_time. 5GHz handshakes complete faster (wider
        # channels, stronger short-range signals) — when 5GHz APs make up
        # a meaningful share of what we see, long recon_time wastes a cycle
        # we could spend hopping. Snapshot _ch_lt under lock to avoid races.
        try:
            with self._state_lock:
                hs_5    = sum(d['hs'] for ch, d in self._ch_lt.items() if ch >= 36)
                hs_24   = sum(d['hs'] for ch, d in self._ch_lt.items() if ch < 36)
                aps_5   = sum(1 for ch in self._ch_lt if ch >= 36
                              and self._ch_lt[ch].get('visits', 0) > 0)
                aps_24  = sum(1 for ch in self._ch_lt if ch < 36
                              and self._ch_lt[ch].get('visits', 0) > 0)
            tot_aps = aps_5 + aps_24
            if tot_aps >= 5 and (aps_5 / tot_aps) > 0.30:
                # Drop recon_time by 5s (clamped to bounds)
                target_rt = max(self.BOUNDS['recon_time'][0],
                                _sf(p.get('recon_time', 25)) - 5)
                if _sf(p.get('recon_time', 25)) > target_rt:
                    p['recon_time'] = int(target_rt)
        except Exception:
            pass

        return p

    # ─────────────────────────────────────────────────────────────────────
    # Stagnation check using rolling median
    # ─────────────────────────────────────────────────────────────────────

    def _check_stagnation(self, custom_rwd):
        self._reward_history.append(custom_rwd)
        if len(self._reward_history) < 10:
            return
        # Rolling median — outliers don't lock us into permanent stagnation
        sorted_r = sorted(self._reward_history)
        median   = sorted_r[len(sorted_r) // 2]
        if custom_rwd < median - 0.08:
            self._stagnation_count += 1
        else:
            self._stagnation_count = 0
        if (self._stagnation_count >= int(self.cfg['stagnation_epochs'])
                and self._exploration_boost <= 0):
            self._exploration_boost = int(self.cfg['exploration_boost_epochs'])
            self._stagnation_count  = 0
            # Also clear cache so UCB recomputes
            self._ucb_cache.clear()
            # FIX: queued decisions were made under the stagnant policy;
            # crediting them with rewards from the boost period would
            # reinforce the very arms we want to escape. Drop the queue.
            self._decision_buffer.clear()
            log.info(f'[envtune] Stagnation → '
                         f'{self._exploration_boost}-ep exploration boost')

    # ─────────────────────────────────────────────────────────────────────
    # Thermal safety
    # ─────────────────────────────────────────────────────────────────────

    def _apply_thermal_throttle(self, agent, temp):
        """Back off radio work when CPU temperature climbs.

        v2.0 (F-08): on RECOVERY (temp drops below temp_warn), restore
        the parameter values that were in effect before throttling
        kicked in. v1.9 left the elevated values (throttle_d=0.9 etc.)
        in place until the next UCB select cycle, leaving the radio
        unnecessarily quiet for several minutes after thermal recovery.
        """
        p = agent._config['personality']
        was_throttled = self._thermal_throttle
        if temp >= self.cfg['temp_critical']:
            if not was_throttled:
                # First time entering throttle — snapshot current params
                # so we can restore them on recovery.
                self._thermal_saved_params = {
                    k: p.get(k) for k in
                    ('throttle_d', 'throttle_a', 'max_interactions')
                    if k in p
                }
            self._thermal_throttle = True
            if 'throttle_d' in self._active_params:
                p['throttle_d'] = min(self.BOUNDS['throttle_d'][1],
                                      _sf(p.get('throttle_d', 0.9)) + 0.3)
            if 'throttle_a' in self._active_params:
                p['throttle_a'] = min(self.BOUNDS['throttle_a'][1],
                                      _sf(p.get('throttle_a', 0.4)) + 0.2)
            p['max_interactions'] = max(2, _si(p.get('max_interactions', 3)) - 1)
            log.warning(f'[envtune] THERMAL CRITICAL {temp:.1f}°C — throttling')
        elif temp >= self.cfg['temp_warn']:
            if not was_throttled:
                self._thermal_saved_params = {
                    k: p.get(k) for k in
                    ('throttle_d', 'throttle_a', 'max_interactions')
                    if k in p
                }
            self._thermal_throttle = True
            if 'throttle_d' in self._active_params:
                p['throttle_d'] = max(_sf(p.get('throttle_d', 0.9)), 0.9)
            log.info(f'[envtune] Thermal warning {temp:.1f}°C')
        else:
            # Temperature has recovered. If we were throttled, restore
            # the params we saved BEFORE the throttle pushed them up.
            # The bandit's next UCB select will then refine from a
            # clean baseline rather than from elevated throttle values.
            if was_throttled and getattr(self, '_thermal_saved_params', None):
                for k, v in self._thermal_saved_params.items():
                    if v is not None:
                        p[k] = v
                self._thermal_saved_params = None
                log.info(f'[envtune] thermal recovery {temp:.1f}°C — '
                         f'restored pre-throttle params')
            self._thermal_throttle = False

    # ─────────────────────────────────────────────────────────────────────
    # Battery integration (pisugar via UI element, if present)
    # ─────────────────────────────────────────────────────────────────────

    def _read_battery(self):
        """Read battery % from pisugar UI element if available."""
        if self._ui is None:
            return None
        try:
            bat = self._ui.get('bat')
            if not bat:
                return None
            # pisugar format: "50%" or similar
            s = str(bat).strip().rstrip('%').strip()
            if s.replace('.', '').isdigit():
                return _sf(s)
        except Exception:
            pass
        return None

    # ─────────────────────────────────────────────────────────────────────
    # wpa-sec cracked potfile feedback
    # ─────────────────────────────────────────────────────────────────────

    def _scan_cracked_potfile(self):
        """
        Read wpa-sec potfile if present. Format: BSSID:CLIENT:SSID:PASSWORD
        Returns a set of cracked BSSIDs (normalised).
        """
        cracked = set()
        if not self.cfg.get('enable_wpasec_feedback', True):
            return cracked
        try:
            if not os.path.exists(self._wpasec_pot):
                return cracked
            with open(self._wpasec_pot, 'r', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if not line or ':' not in line:
                        continue
                    parts = line.split(':')
                    if parts:
                        mac = self._mac_norm(parts[0])
                        if len(mac) == 12 and all(c in '0123456789abcdef' for c in mac):
                            cracked.add(mac)
        except Exception as e:
            log.debug(f'[envtune] potfile scan: {e}')
        return cracked

    # ─────────────────────────────────────────────────────────────────────
    # Whitelist loading from pwnagotchi config
    # ─────────────────────────────────────────────────────────────────────

    def _load_whitelist(self, agent):
        """Load main.whitelist into MAC and SSID sets."""
        try:
            wl = agent._config.get('main', {}).get('whitelist', []) or []
            for item in wl:
                s = str(item).strip()
                if not s:
                    continue
                # MAC heuristic: contains : or - and mostly hex
                if ':' in s or '-' in s:
                    normalised = self._mac_norm(s)
                    # MAC prefix match supported (e.g. "fo:od:ba")
                    if normalised and all(c in '0123456789abcdef'
                                          for c in normalised):
                        self._whitelist_macs.add(normalised)
                        continue
                # Otherwise treat as SSID
                self._whitelist_ssids.add(s)
            if self._whitelist_macs or self._whitelist_ssids:
                log.info(
                    f'[envtune] Whitelist loaded: '
                    f'{len(self._whitelist_macs)} MACs, '
                    f'{len(self._whitelist_ssids)} SSIDs')
        except Exception as e:
            log.debug(f'[envtune] whitelist load: {e}')

    # ─────────────────────────────────────────────────────────────────────
    # Handshake directory scan
    # ─────────────────────────────────────────────────────────────────────

    def _scan_handshake_dir(self):
        """
        Collect normalised BSSIDs with existing captures.
        Pwnagotchi filenames: <ssid>_<bssid>.pcap (bssid = last underscore).
        """
        captured = set()
        try:
            if not os.path.isdir(self._hs_dir):
                return captured
            for fn in os.listdir(self._hs_dir):
                if not fn.endswith(('.pcap', '.pcapng')):
                    continue
                stem  = fn.rsplit('.', 1)[0]
                parts = stem.split('_')
                if not parts:
                    continue
                mac = self._mac_norm(parts[-1])
                if len(mac) == 12 and all(c in '0123456789abcdef' for c in mac):
                    captured.add(mac)
        except Exception as e:
            log.debug(f'[envtune] handshake dir scan: {e}')
        return captured

    # ─────────────────────────────────────────────────────────────────────
    # Bettercap sync (for wifi.* parameters that need realtime update)
    # ─────────────────────────────────────────────────────────────────────

    def _bettercap_sync(self, agent, params_changed):
        """
        Push wifi.* parameter changes to bettercap in realtime.
        Without this, ap_ttl / sta_ttl / min_rssi are silently ignored
        after pwnagotchi startup.
        """
        for param, new_val in params_changed.items():
            bcap_key = self.BETTERCAP_SYNC_MAP.get(param)
            if not bcap_key:
                continue
            try:
                agent.run(f'set {bcap_key} {new_val}')
            except Exception as e:
                log.debug(f'[envtune] bcap sync {bcap_key}={new_val}: {e}')

    def _push_bcap_skip_list(self, agent, force=False):
        """
        Push BSSIDs to bettercap's wifi.assoc.skip / wifi.deauth.skip.

        The set is rebuilt fresh from `_cracked_bssids` and (optionally)
        `_captured_bssids` based on config flags:
          - bcap_skip_cracked  (default True)  — exclude cracked BSSIDs
            from attacks (we have the password, recapture is wasteful)
          - bcap_skip_captured (default False) — exclude every captured
            BSSID, including uncracked ones. v1.2 default behaviour;
            now opt-in because it prevents opportunistic re-captures.

        Coalesces — only re-pushes when the set has changed (or force).
        Best-effort: silently no-ops on bettercap builds that don't
        expose these properties.
        """
        if agent is None:
            return
        skip_captured = bool(self.cfg.get('bcap_skip_captured', False))
        skip_cracked  = bool(self.cfg.get('bcap_skip_cracked',  True))

        new_set = set()
        with self._state_lock:
            if skip_cracked:
                for m in self._cracked_bssids:
                    f = _format_mac_colons(m)
                    if f:
                        new_set.add(f)
            if skip_captured:
                for m in self._captured_bssids:
                    f = _format_mac_colons(m)
                    if f:
                        new_set.add(f)

        # Cache the resolved set for telemetry / UI.
        self._bcap_skip_macs = new_set
        n = len(new_set)
        if not force and n == self._bcap_skip_pushed_count:
            return
        try:
            if new_set:
                skip_list = ','.join(sorted(new_set))
                agent.run(f'set wifi.assoc.skip {skip_list}')
                agent.run(f'set wifi.deauth.skip {skip_list}')
                log.debug(f'[envtune] pushed {n} BSSIDs to bcap skip-list '
                              f'(cracked={skip_cracked}, '
                              f'captured={skip_captured})')
            else:
                # Actively clear stale skip rules from a previous run.
                agent.run('set wifi.assoc.skip ')
                agent.run('set wifi.deauth.skip ')
                log.debug('[envtune] cleared bcap skip-list')
            self._bcap_skip_pushed_count = n
        except Exception as e:
            log.debug(f'[envtune] bcap skip-list push: {e}')

    # ─────────────────────────────────────────────────────────────────────
    # Detect which params this fork exposes (graceful for evilsocket)
    # ─────────────────────────────────────────────────────────────────────

    def _detect_supported_params(self, agent):
        try:
            p = agent._config.get('personality', {}) or {}
            supported = {k for k in self.UCB_ARMS if k in p}
            missing   = set(self.UCB_ARMS.keys()) - supported
            if missing:
                log.info(f'[envtune] Fork missing params: {sorted(missing)} '
                             f'— those UCB arms will be skipped')
            self._active_params = supported
        except Exception as e:
            log.warning(f'[envtune] param detection fallback: {e}')
            self._active_params = set(self.UCB_ARMS.keys())

    # ─────────────────────────────────────────────────────────────────────
    # State persistence (async, atomic, fsync'd)
    # ─────────────────────────────────────────────────────────────────────

    def _load_state(self):
        try:
            if not os.path.exists(self.STATE_PATH):
                return
            with open(self.STATE_PATH) as f:
                st = json.load(f)

            loaded_schema = _si(st.get('schema_version', 1))

            # Sanitize loaded EMAs against EMA_CLAMP. Values from older
            # plugin versions (before the clamp safeguard) could be
            # outside the sane range — e.g. we observed reward=-8.5e15
            # in real telemetry from a one-off bad native_reward sample.
            # Drop those instead of poisoning the new run; _ema() will
            # re-seed on the next epoch.
            loaded_ema = (st.get('ema') or {})
            for k, v in loaded_ema.items():
                if k not in self.ema:
                    continue
                fv = _sf(v, default=None) if v is not None else None
                if fv is None or not math.isfinite(fv):
                    continue
                lo, hi = self.EMA_CLAMP.get(k, (-1e9, 1e9))
                if fv < lo or fv > hi:
                    log.warning(
                        f'[envtune] dropped corrupt EMA {k}={fv} '
                        f'(outside [{lo}, {hi}])')
                    continue
                self.ema[k] = fv
            # Also reset the trend tracker — it depends on prev reward EMA
            # and would carry the corruption forward as a delta.
            self._prev_reward_ema = self.ema.get('reward')
            self._reward_trend    = 0.0
            self.lifetime_handshakes = _si(st.get('lifetime_handshakes', 0))
            self._lifetime_new_count = _si(st.get('lifetime_new_count', 0))

            # v1.6: restore rolling reward/HPM history. Each list is
            # tail-truncated to the deque maxlen (60) and validated as
            # finite floats — a corrupted entry (NaN, str) is dropped
            # rather than poisoning the percentile/median computations.
            for src_key, dest in (
                ('recent_hpm',     self._recent_hpm),
                ('reward_history', self._reward_history),
            ):
                raw = st.get(src_key) or []
                if isinstance(raw, list):
                    for v in raw[-dest.maxlen:]:
                        fv = _sf(v, default=None) if v is not None else None
                        if fv is not None and math.isfinite(fv):
                            dest.append(fv)

            # v2.0 (A1): restore mobility-aware strategy meta-bandit.
            # Migrates from v1.9 flat-schema state automatically.
            # Schema-tolerant: unknown mobilities/strategies are ignored.
            sb_raw = st.get('strategy_bandit') or {}
            sb_schema = st.get('strategy_bandit_schema') or ''
            if isinstance(sb_raw, dict) and sb_raw:
                # Detect format: v1.9 has 'adaptive'/'full'/'capped' as
                # top-level keys; v2.0 has 'stationary'/'moving' as top-
                # level keys (each containing the strategy dict).
                v19_keys = {'adaptive', 'full', 'capped'}
                v20_keys = {self.MOBILITY_STATIONARY, self.MOBILITY_MOVING}
                top_keys = set(sb_raw.keys())
                is_v20 = (sb_schema == 'mobility_aware_v2'
                          or top_keys & v20_keys)
                is_v19 = (top_keys & v19_keys) and not is_v20

                def _ingest_strategy_dict(target_mob, src):
                    """Pull strategy stats from src dict into the
                    target mobility's bandit cells."""
                    for s, d in src.items():
                        if s not in self._strategy_bandit[target_mob]:
                            continue
                        if not isinstance(d, dict):
                            continue
                        n = _si(d.get('n', 0))
                        rs = d.get('rewards') or []
                        if not isinstance(rs, list):
                            continue
                        clean = []
                        for r in rs:
                            fr = _sf(r, default=None) if r is not None else None
                            if fr is not None and math.isfinite(fr):
                                clean.append(max(0.0, min(1.0, fr)))
                        if n > 0 and clean:
                            self._strategy_bandit[target_mob][s]['n'] = n
                            for r in clean[-20:]:
                                self._strategy_bandit[target_mob][s]['rewards'].append(r)

                if is_v20:
                    for mobility, mob_dict in sb_raw.items():
                        if mobility not in self._strategy_bandit:
                            continue
                        if not isinstance(mob_dict, dict):
                            continue
                        _ingest_strategy_dict(mobility, mob_dict)
                elif is_v19:
                    # v1.9 → v2.0 migration: seed BOTH mobilities with
                    # the v1.9 stats. The bandit then differentiates as
                    # new mobility-specific data arrives.
                    log.info(
                        '[envtune] migrating v1.9 strategy bandit '
                        '→ v2.0 mobility-aware schema')
                    for mobility in self._strategy_bandit:
                        _ingest_strategy_dict(mobility, sb_raw)

            # Restore captured-BSSID set. Without this, lifetime_new_count
            # could desync from disk-state (deleted pcaps) and re-counting
            # an already-known BSSID as "new" again would inflate metrics.
            # FIX: validate hex-only — a corrupted JSON entry could otherwise
            # poison the set with garbage that never normalises out (and
            # would inflate counters).
            _hex = set('0123456789abcdef')
            for m in (st.get('captured_bssids') or []):
                m_n = self._mac_norm(m)
                if len(m_n) == 12 and set(m_n).issubset(_hex):
                    self._captured_bssids.add(m_n)

            # FIX: persist cracked-BSSID set so we don't lose this knowledge
            # if the wpa-sec potfile is rotated or corrupted between runs.
            # We re-merge with the live potfile in on_loaded, so this is a
            # safety net rather than the source of truth.
            for m in (st.get('cracked_bssids') or []):
                m_n = self._mac_norm(m)
                if len(m_n) == 12 and set(m_n).issubset(_hex):
                    self._cracked_bssids.add(m_n)

            for k, v in (st.get('ch_lt') or {}).items():
                try:
                    self._ch_lt[int(k)].update(v)
                except (ValueError, TypeError):
                    continue
            for k, v in (st.get('dead_lt') or {}).items():
                try:
                    self._dead_lt[int(k)] = _si(v)
                except (ValueError, TypeError):
                    continue

            for zone_key, zdata in (st.get('gps_zones') or {}).items():
                self._gps_zones[zone_key]['hs']        = _si(zdata.get('hs', 0))
                self._gps_zones[zone_key]['attacks']   = _si(zdata.get('attacks', 0))
                self._gps_zones[zone_key]['visits']    = _si(zdata.get('visits', 0))
                self._gps_zones[zone_key]['last_seen'] = _sf(zdata.get('last_seen', 0))
                for c, n in (zdata.get('channels') or {}).items():
                    try:
                        self._gps_zones[zone_key]['channels'][int(c)] = _si(n)
                    except (ValueError, TypeError):
                        continue

            self.best_reward   = st.get('best_reward')
            self.best_settings = st.get('best_settings')

            raw_ucb = st.get('ucb_table')
            if raw_ucb:
                self._deserialise_ucb(raw_ucb, loaded_schema)

            if loaded_schema < self.STATE_SCHEMA_VERSION:
                log.info(
                    f'[envtune] State migrated from schema v{loaded_schema} '
                    f'to v{self.STATE_SCHEMA_VERSION}')

            log.info(
                f'[envtune] State loaded — lifetime_hs={self.lifetime_handshakes} '
                f'zones={len(self._gps_zones)} best_rwd={self.best_reward}')
        except Exception as e:
            log.warning(f'[envtune] State load failed: {e} — starting fresh')

    # ─────────────────────────────────────────────────────────────────────
    # Community priors — merge anonymised exports from other operators
    # ─────────────────────────────────────────────────────────────────────

    def _merge_community_priors(self):
        """
        Scan COMMUNITY_PRIORS_DIR and merge anonymised export JSON files
        into the local UCB table at low weight.

        For each (param, state, arm) seen across community files we
        append at most `cap` reward samples drawn from that arm's
        community history, capped so a single operator's export can't
        dominate. Schema migration is delegated to `_deserialise_ucb`,
        so v3 (108-state) and v4 (24-state) exports both work.

        v1.8.1 — defensive against accidentally-uploaded non-anon
        exports: we ONLY read `ucb_table`. Even if an export contains
        captured_bssids / cracked_bssids / gps_zones, we ignore those
        — community priors should never ingest someone else's BSSIDs
        (privacy: WiGLE-geolocatable) or zone data (location-revealing).

        Only fired ONCE on plugin load; the merged samples roll out of
        the local sliding window naturally as real data arrives.
        Returns (files_merged, total_samples_merged, errors).
        """
        if not os.path.isdir(self.COMMUNITY_PRIORS_DIR):
            return 0, 0, 0
        cap = 5     # at most 5 imported samples per (state, arm, file)
        files_n     = 0
        samples_n   = 0
        errors_n    = 0
        try:
            entries = sorted(os.listdir(self.COMMUNITY_PRIORS_DIR))
        except OSError:
            return 0, 0, 0
        for fn in entries:
            if not fn.lower().endswith('.json'):
                continue
            path = os.path.join(self.COMMUNITY_PRIORS_DIR, fn)
            try:
                with open(path, encoding='utf-8') as fh:
                    data = json.load(fh)
            except Exception as e:
                log.warning(
                    f'[envtune] community prior {fn} unreadable: {e}')
                errors_n += 1
                continue
            schema = _si(data.get('schema_version', 1))
            ucb    = data.get('ucb_table') or {}
            if not isinstance(ucb, dict) or not ucb:
                continue
            for param, states in ucb.items():
                if param not in self.UCB_ARMS:
                    continue
                if not isinstance(states, dict):
                    continue
                for old_state, arms in states.items():
                    if not isinstance(arms, dict):
                        continue
                    new_state = self._migrate_state_key(old_state, schema)
                    self._ensure_state(param, new_state)
                    for arm_s, info in arms.items():
                        if not isinstance(info, dict):
                            continue
                        try:
                            ref_type = type(self.UCB_ARMS[param][0])
                            arm = ref_type(arm_s)
                        except (ValueError, TypeError):
                            try:
                                arm = float(arm_s)
                            except (ValueError, TypeError):
                                continue
                        if arm not in self.ucb_table[param][new_state]:
                            continue
                        rewards = info.get('rewards') or []
                        if not rewards:
                            continue
                        # Keep only the most-recent `cap` rewards from
                        # this file. Validate finite floats. Then mix
                        # in: 60% community signal, 40% neutral 0.30.
                        # This dampens community pull so it shouldn't
                        # override local learning once real data flows.
                        clean = []
                        for r in rewards[-cap:]:
                            fr = _sf(r, default=None) if r is not None else None
                            if fr is not None and math.isfinite(fr):
                                clean.append(0.6 * max(0.0, min(1.0, fr))
                                             + 0.4 * 0.30)
                        if not clean:
                            continue
                        entry = self.ucb_table[param][new_state][arm]
                        for r in clean:
                            entry['rewards'].append(r)
                        entry['n'] += len(clean)
                        samples_n += len(clean)
            files_n += 1
        return files_n, samples_n, errors_n

    def _build_state_snapshot(self):
        """Build a full state dict under the lock, return it for async write."""
        with self._state_lock:
            return {
                'schema_version':      self.STATE_SCHEMA_VERSION,
                'envtune_version':     self.__version__,
                'ema':                 dict(self.ema),
                'lifetime_handshakes': self.lifetime_handshakes,
                'lifetime_new_count':  self._lifetime_new_count,
                # v1.6: persist rolling reward / HPM history so the
                # adaptive target doesn't reset to the 0.5/min floor for
                # ~10 epochs every restart. Stored as plain lists; the
                # loader puts them back into a deque(maxlen=60).
                'recent_hpm':          list(self._recent_hpm),
                'reward_history':      list(self._reward_history),
                # v2.0 (A1): mobility-aware strategy meta-bandit. Persisted
                # as nested dict: {mobility: {strategy: {n, rewards}}}.
                # v1.9 flat schema is auto-migrated on load. Block
                # progress is session-only — clean restart on reboot.
                'strategy_bandit': {
                    mobility: {
                        s: {'n': d['n'], 'rewards': list(d['rewards'])}
                        for s, d in mob_bandit.items()
                    }
                    for mobility, mob_bandit in self._strategy_bandit.items()
                },
                'strategy_bandit_schema': 'mobility_aware_v2',
                'captured_bssids':     sorted(self._captured_bssids),
                'cracked_bssids':      sorted(self._cracked_bssids),
                'ch_lt':   {str(k): dict(v) for k, v in self._ch_lt.items()},
                'dead_lt': {str(k): v       for k, v in self._dead_lt.items()},
                'gps_zones': {
                    zk: {
                        'hs':        z['hs'],
                        'attacks':   z['attacks'],
                        'visits':    z['visits'],
                        'last_seen': z['last_seen'],
                        'channels':  {str(c): n for c, n in z['channels'].items()},
                    }
                    for zk, z in self._gps_zones.items()
                },
                'best_reward':   self.best_reward,
                'best_settings': self.best_settings,
                'ucb_table':     self._serialise_ucb(),
                'saved_at':      time.time(),
            }

    def _save_worker(self):
        """Background thread: drain save queue, coalesce rapid requests.

        v1.6 fix: a None sentinel arriving DURING coalesce no longer
        causes the latest already-drained snapshot to be lost. We now
        always write the most-recent non-None snapshot before honouring
        the shutdown sentinel.
        """
        while not self._save_stop.is_set():
            try:
                snapshot = self._save_queue.get(timeout=1.0)
            except queue.Empty:
                continue
            if snapshot is None:
                break
            # Drain additional queued snapshots — only keep the latest.
            # If we see a None during drain, remember to stop, but still
            # write the latest real snapshot first.
            stop_after_write = False
            while True:
                try:
                    nxt = self._save_queue.get_nowait()
                except queue.Empty:
                    break
                if nxt is None:
                    stop_after_write = True
                    break
                snapshot = nxt
            try:
                self._atomic_write(snapshot)
                # v2.0 (R-01): refresh the export cache after every
                # successful disk write. Webhook /export now serves this
                # cache instead of paying for a fresh snapshot.
                self._cached_snapshot    = snapshot
                self._cached_snapshot_at = time.time()
            except Exception as e:
                self._record_error('save_worker')
                log.warning(f'[envtune] async save failed: {e}')
            if stop_after_write:
                self._save_stop.set()
                return

    def _atomic_write(self, snapshot):
        """Atomic write with fsync."""
        dir_ = os.path.dirname(self.STATE_PATH) or '.'
        fd, tmp = tempfile.mkstemp(
            prefix='.envtune_', suffix='.json.tmp', dir=dir_)
        try:
            with os.fdopen(fd, 'w') as f:
                json.dump(snapshot, f, separators=(',', ':'))
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, self.STATE_PATH)
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    def _maybe_save(self):
        self.epochs_since_save += 1
        if self.epochs_since_save >= int(self._profile['save_every_n']):
            try:
                snapshot = self._build_state_snapshot()
                # Non-blocking — drop on full queue (stale snapshots
                # matter less than blocking the main loop)
                try:
                    self._save_queue.put_nowait(snapshot)
                except queue.Full:
                    log.debug('[envtune] save queue full — dropping snapshot')
            except Exception as e:
                log.warning(f'[envtune] snapshot build failed: {e}')
            self.epochs_since_save = 0

    def _sync_save_now(self):
        """Force an immediate synchronous save (shutdown path)."""
        try:
            snapshot = self._build_state_snapshot()
            self._atomic_write(snapshot)
        except Exception as e:
            log.warning(f'[envtune] sync save failed: {e}')

    def _enqueue_save(self, reason='manual'):
        """Push a snapshot to the async save queue. Drops on full queue
        (the saver coalesces; one drop is harmless)."""
        try:
            snapshot = self._build_state_snapshot()
            try:
                self._save_queue.put_nowait(snapshot)
                log.debug(f'[envtune] save enqueued ({reason})')
            except queue.Full:
                log.debug(f'[envtune] save queue full — drop ({reason})')
        except Exception as e:
            log.warning(f'[envtune] enqueue save failed ({reason}): {e}')

    # ═════════════════════════════════════════════════════════════════════
    # Plugin lifecycle
    # ═════════════════════════════════════════════════════════════════════

    def _validate_cfg(self):
        """v2.0 (R-05): validate every cfg value against expected type
        and range, log warnings for out-of-bound values, repair where
        safe.

        Doesn't crash on bad config — that would prevent the plugin
        from loading at all. Logs WARNING and falls back to DEFAULTS
        for any malformed value.
        """
        # (key, expected_type, optional_min, optional_max)
        expected = [
            ('ema_alpha',                  float, 0.01,  1.0),
            ('warmup_epochs',               int,   1,    None),
            ('dense_aps',                   int,   1,    None),
            ('sparse_aps',                  int,   1,    None),
            ('ucb_c',                      float, 0.0,   None),
            ('ucb_c_floor',                float, 0.0,   None),
            ('ucb_c_anneal_epochs',         int,   1,    None),
            ('warmstart_prior_reward',     float, 0.0,   1.0),
            ('stagnation_epochs',           int,   1,    None),
            ('exploration_boost_epochs',    int,   1,    None),
            ('forced_explore_every',        int,   0,    None),
            ('forced_explore_starvation_n', int,   1,    None),
            ('reward_delay',                int,   1,    None),
            ('temp_warn',                  float, 0.0,   150.0),
            ('temp_critical',              float, 0.0,   150.0),
            ('auto_strategy_block_secs',    int,  60,    None),
            ('auto_strategy_block_epochs',  int,   0,    None),
            ('auto_strategy_c',            float, 0.0,   None),
            ('channel_full_sweep_every',    int,   2,    None),
            ('chistos_max_channels',        int,  10,    None),
            ('mood_threshold_epochs',       int,   1,    None),
            ('client_recency_epochs',       int,   1,    None),
            ('battery_low_threshold',      float, 0.0,   100.0),
            ('battery_critical_threshold', float, 0.0,   100.0),
        ]
        for key, typ, lo, hi in expected:
            if key not in self.cfg:
                continue
            val = self.cfg[key]
            try:
                # int and float are interchangeable for validation
                # purposes (we accept int values for float configs).
                if typ is float:
                    coerced = float(val)
                else:
                    coerced = int(val)
            except (TypeError, ValueError):
                log.warning(
                    f'[envtune] cfg.{key}={val!r} not a {typ.__name__} '
                    f'— falling back to default {self.DEFAULTS[key]!r}')
                self.cfg[key] = self.DEFAULTS[key]
                continue
            if lo is not None and coerced < lo:
                log.warning(
                    f'[envtune] cfg.{key}={coerced} below min {lo} '
                    f'— clamped to {lo}')
                self.cfg[key] = lo if typ is float else int(lo)
            elif hi is not None and coerced > hi:
                log.warning(
                    f'[envtune] cfg.{key}={coerced} above max {hi} '
                    f'— clamped to {hi}')
                self.cfg[key] = hi if typ is float else int(hi)
        # Strategy enum
        s = self.cfg.get('channel_strategy')
        if s not in ('auto', 'adaptive', 'full', 'capped'):
            log.warning(
                f'[envtune] cfg.channel_strategy={s!r} unknown — '
                f'falling back to "auto"')
            self.cfg['channel_strategy'] = 'auto'
        # v2.2.0: coerce prefer_stability to bool — common typo: "true"/"yes"
        ps = self.cfg.get('prefer_stability', True)
        if isinstance(ps, str):
            self.cfg['prefer_stability'] = ps.lower() in ('1', 'true', 'yes', 'on')
        elif not isinstance(ps, bool):
            self.cfg['prefer_stability'] = bool(ps)
        # Block-config consistency
        if (int(self.cfg.get('auto_strategy_block_epochs', 0) or 0) > 0
                and int(self.cfg.get('auto_strategy_block_secs', 1800)) > 0):
            log.info(
                '[envtune] cfg: both auto_strategy_block_epochs and '
                'auto_strategy_block_secs are set — epochs takes priority '
                '(legacy v1.9 back-compat)')

    def _check_pwnagotchi_compat(self):
        """v2.0 (P-10): warn if running on a pwnagotchi version we
        haven't verified against. Doesn't block load; just informs."""
        if not self.cfg.get('verify_pwnagotchi_version', True):
            return
        try:
            pwn_ver = getattr(__import__('pwnagotchi'), '__version__', None)
        except Exception:
            pwn_ver = None
        if not pwn_ver:
            return
        if not any(pwn_ver.startswith(p)
                   for p in self.PWNAGOTCHI_VERIFIED_VERSIONS):
            log.warning(
                f'[envtune] running on pwnagotchi {pwn_ver} — outside '
                f'verified range {self.PWNAGOTCHI_VERIFIED_VERSIONS}. '
                f'Plugin should still work but is not guaranteed.')

    def on_loaded(self):
        # Merge user options into config
        try:
            user = self.options or {}
            for k, v in user.items():
                if k in self.DEFAULTS:
                    self.cfg[k] = v
        except Exception:
            pass

        # v2.0 (R-05, P-10): validate config + check pwnagotchi version
        # BEFORE we initialise anything that depends on cfg.
        self._validate_cfg()
        self._check_pwnagotchi_compat()

        # Resolve CPU profile
        chosen = self.cfg.get('cpu_profile')
        if not chosen or chosen not in CPU_PROFILES:
            hw = _detect_hardware()
            chosen = HW_DEFAULT_PROFILE.get(hw, 'balanced')
            log.info(f'[envtune] auto-selected CPU profile "{chosen}" '
                     f'for detected hardware: {hw}')
        self._profile = dict(CPU_PROFILES[chosen])
        self._profile_name = chosen

        # Now that cfg is final, size the decision buffer so it can hold
        # `reward_delay` + a generous margin for adaptive sparse delay.
        # Adaptive delay = base + 1 in sparse environments; floor 8 so
        # operators aren't surprised if they tune reward_delay = 5.
        decision_max = max(8, int(self.cfg.get('reward_delay', 3)) + 4)
        self._decision_buffer = deque(maxlen=decision_max)

        # Set log level on the NAMED 'envtune' logger only. v1.5 mutated
        # the ROOT logger which leaked envtune's verbosity into every
        # other Pwnagotchi component (bettercap-bridge, mesh, plugins).
        try:
            level = self.cfg.get('log_level', 'INFO').upper()
            log.setLevel(getattr(logging, level, logging.INFO))
        except Exception:
            pass

        # Initialise UCB tables (cfg/profile must be ready first)
        self._init_ucb_table()

        # Load persistent state (may overwrite UCB entries with real data)
        self._load_state()

        # Apply time-of-day priors (only fills n=0 entries)
        self._apply_tod_prior()

        # v1.7: merge community priors if any exports are present in
        # COMMUNITY_PRIORS_DIR. Runs after _load_state and TOD priors
        # so local data (real samples) and TOD priors (synthetic
        # cold-start) take precedence in the deque.
        try:
            files_n, samples_n, errs = self._merge_community_priors()
            if files_n:
                log.info(
                    f'[envtune] community priors: merged '
                    f'{samples_n} samples from {files_n} file(s)'
                    + (f' ({errs} errors)' if errs else ''))
        except Exception as e:
            log.debug(f'[envtune] community priors merge failed: {e}')

        # Merge state-restored BSSIDs with current handshake-dir scan.
        # State has the authoritative lifetime count; disk has authoritative
        # presence — neither alone is reliable across pcap-deletes / wipes.
        self._captured_bssids |= self._scan_handshake_dir()

        # Scan wpa-sec potfile for cracked networks. v1.8.1: MERGE with
        # the state-restored set instead of REPLACING it. Real-world
        # cases where state has cracked BSSIDs the live potfile doesn't:
        #   - User used wpa-sec briefly, then disabled it.
        #   - Potfile got rotated/truncated between runs.
        #   - User runs envtune on a Pi without wpa-sec at all (this set
        #     stays empty from the potfile, but state may have entries
        #     from a prior wpa-sec-equipped install or from a crack
        #     cracked elsewhere and noted manually).
        # The comment in _load_state explicitly said "safety net rather
        # than the source of truth" — but the code was overwriting.
        self._cracked_bssids |= self._scan_cracked_potfile()

        # First-run init: if no persisted lifetime_new_count yet, seed it
        # from the existing handshake count. Otherwise we'd treat every
        # already-captured AP as "lifetime new" the next time we see it.
        if self._lifetime_new_count == 0 and len(self._captured_bssids) > 0:
            self._lifetime_new_count = len(self._captured_bssids)
            log.info(
                f'[envtune] First run with existing handshakes — '
                f'seeding lifetime_new_count from disk '
                f'({self._lifetime_new_count} unique BSSIDs)')

        # CRITICAL: always sync prev-counters AFTER load+seed so first epoch
        # computes a clean diff. Without this, with stored count=N the
        # first-epoch diff would be N-0=N → reward spike → UCB would
        # incorrectly credit random startup parameters.
        self._lifetime_new_count_prev = self._lifetime_new_count
        self._known_aps_count_prev    = len(self._known_aps)

        # NOTE: _bcap_skip_macs is rebuilt fresh on every push from
        # _captured_bssids and _cracked_bssids according to the
        # bcap_skip_captured / bcap_skip_cracked config flags. The
        # initial push happens in on_ready once the agent is wired up.

        # Seed total-samples counter from the loaded + primed UCB table.
        # From here on, _ucb_update keeps it incrementally up-to-date.
        self._recompute_total_real_samples()

        # Start async save thread
        self._save_thread = threading.Thread(
            target=self._save_worker, name='envtune-save', daemon=True)
        self._save_thread.start()

        log.info(
            f'[envtune] v{self.__version__} loaded | profile={chosen} | '
            f'ucb_window={self._profile["ucb_window"]} | '
            f'samples={self._total_real_samples} | '
            f'lifetime_hs={self.lifetime_handshakes} | '
            f'lifetime_unique={self._lifetime_new_count} | '
            f'pre_captured={len(self._captured_bssids)} | '
            f'cracked={len(self._cracked_bssids)} | '
            f'hpm_hist={len(self._recent_hpm)} | '
            f'best_reward={self.best_reward}')

    def on_ready(self, agent):
        self._agent = agent

        # v2.1.0 CRITICAL FIX: resolve the real handshake dir from
        # bettercap config. v2.0 hardcoded /root/handshakes — but the
        # noai default is /etc/pwnagotchi/handshakes. Without this fix
        # the lifetime-new-handshake tracking finds NO captured BSSIDs
        # at startup → every old AP looks "new" → bandit gets credited
        # for things it didn't do.
        try:
            bcap_cfg = agent._config.get('bettercap', {}) or {}
            hs_path = bcap_cfg.get('handshakes')
            if hs_path:
                self._hs_dir = str(hs_path)
                # wpa-sec potfile lives next to handshakes by convention
                self._wpasec_pot = os.path.join(
                    self._hs_dir, 'wpa-sec.cracked.potfile')
            log.info(f'[envtune] handshake dir resolved: {self._hs_dir}')
        except Exception as e:
            log.warning(
                f'[envtune] could not resolve handshake dir from cfg: {e} '
                f'— falling back to {self._hs_dir}')

        # v2.1.0: detect bettercap event-silence list. By default, noai
        # silences `wifi.ap.new`, `wifi.ap.lost`, `wifi.client.new`,
        # `wifi.client.lost`. Our `on_bcap_*` handlers are dead code if
        # those tags are silenced — we warn so operators understand
        # opportunistic-channel-override and free-channel detection
        # require un-silencing.
        try:
            silence = (agent._config.get('bettercap', {}) or {}).get(
                'silence', []) or []
            self._bcap_silenced_events = set(silence)
            critical = {
                'wifi.ap.new', 'wifi.ap.lost',
                'wifi.client.new', 'wifi.client.lost',
            }
            silenced_critical = critical & self._bcap_silenced_events
            if silenced_critical:
                log.warning(
                    f'[envtune] bettercap silence list includes '
                    f'{sorted(silenced_critical)} — opportunistic-channel '
                    f'override and live AP/client tracking are limited. '
                    f'To enable, remove these from bettercap.silence in '
                    f'config.toml.')
        except Exception as e:
            log.debug(f'[envtune] silence-list inspect: {e}')

        # v2.1.0: re-merge BSSIDs from the now-correct handshake dir
        # (on_loaded scanned the wrong dir before agent was ready).
        new_from_disk = self._scan_handshake_dir()
        with self._state_lock:
            before = len(self._captured_bssids)
            self._captured_bssids |= new_from_disk
            added = len(self._captured_bssids) - before
        if added:
            self._lifetime_new_count = max(
                self._lifetime_new_count, len(self._captured_bssids))
            log.info(
                f'[envtune] +{added} BSSIDs adopted from real handshake dir '
                f'(total captured = {len(self._captured_bssids)}, '
                f'lifetime_new = {self._lifetime_new_count})')
            # Reset the prev counter so we don't credit this on_epoch.
            self._lifetime_new_count_prev = self._lifetime_new_count

        # v2.1.0: cross-check our scan against pwnagotchi's helper. The
        # helper just counts *.pcap files (counts each as unique). If our
        # BSSID-extracted count is significantly LOWER than the file count,
        # something is off (e.g. unexpected filename format on this fork).
        try:
            pwn_count = pwnagotchi.utils.total_unique_handshakes(self._hs_dir)
            our_count = len(self._captured_bssids)
            if pwn_count and our_count < pwn_count * 0.5:
                log.warning(
                    f'[envtune] handshake count sanity-check: pwnagotchi '
                    f'sees {pwn_count} pcap files but we extracted only '
                    f'{our_count} BSSIDs — filename format on this fork '
                    f'may be unexpected. Check /etc/pwnagotchi/handshakes/ '
                    f'manually if lifetime_new tracking looks off.')
        except Exception as e:
            log.debug(f'[envtune] HS count sanity-check failed: {e}')

        # Same for the wpa-sec potfile (now at the correct path).
        new_cracked = self._scan_cracked_potfile()
        if new_cracked:
            with self._state_lock:
                added = len(new_cracked - self._cracked_bssids)
                self._cracked_bssids |= new_cracked
            if added:
                log.info(f'[envtune] +{added} cracked BSSIDs adopted from '
                         f'real wpa-sec potfile')

        self._detect_supported_params(agent)
        self._load_whitelist(agent)

        # v1.7.1: capture user's original channel universe BEFORE we
        # ever touch personality.channels. Empty list (pwnagotchi
        # semantics for "no restriction") expands to the iface's full
        # supported list. Stored as a sorted list for deterministic
        # ordering in logs/UI.
        try:
            orig = list(agent._config.get('personality', {}).get(
                'channels') or [])
            if orig:
                self._user_channels_orig = sorted(set(int(c) for c in orig))
                log.info(f'[envtune] user channel universe (explicit): '
                         f'{len(self._user_channels_orig)} channels '
                         f'{self._user_channels_orig}')
            else:
                # Empty list = "scan all" in pwnagotchi semantics.
                # Resolve via iface_channels (the hardware-supported
                # set). Falls back to 2.4 GHz 1-11 if that fails.
                try:
                    iface = agent._config['main']['iface']
                    full = list(pwnagotchi.utils.iface_channels(iface))
                except Exception:
                    full = list(range(1, 12))
                if hasattr(agent, '_supported_channels') and agent._supported_channels:
                    full = list(set(full) | set(agent._supported_channels))
                self._user_channels_orig = sorted(set(int(c) for c in full))
                log.info(f'[envtune] user channel universe (unrestricted '
                         f'→ all iface-supported): '
                         f'{len(self._user_channels_orig)} channels')
        except Exception as e:
            log.debug(f'[envtune] capture user channels: {e}')
            self._user_channels_orig = list(range(1, 12))
        # Warm-start the UCB tables from whatever personality values
        # the user / previous tuner has set in config.toml. Without
        # this, the bandit treats every arm equally and burns the
        # first ~50 epochs re-discovering settings the user already
        # had right.
        try:
            self._apply_personality_warmstart(agent)
            # Warm-start may have added synthetic n=1 samples — refresh
            # the counter so shrinkage k anneals correctly.
            self._recompute_total_real_samples()
        except Exception as e:
            log.debug(f'[envtune] warm-start failed: {e}')

        # Detect GPS source
        self._gps_source = self._detect_gps_source(agent)
        if self._gps_source:
            self._gps_available = True
            log.info(f'[envtune] GPS active via {self._gps_source}')
        else:
            log.info('[envtune] GPS not detected — '
                         'plugin runs without zone awareness')

        # Initial bettercap sync — push current personality values to bettercap
        try:
            p = agent._config['personality']
            for param in self.BETTERCAP_SYNC_MAP:
                if param in p:
                    self._bettercap_sync(agent, {param: p[param]})
        except Exception as e:
            log.debug(f'[envtune] initial bettercap sync: {e}')

        # Push initial captured-BSSID skip list so bettercap deprioritises
        # duplicates from the very first attack cycle of this session.
        self._push_bcap_skip_list(agent, force=True)

        # reset_history default MUST match DEFAULTS (False). Old code
        # had `True` as the .get() fallback — destructive if the key
        # ever went missing from cfg (e.g. partial state migration).
        if self.cfg.get('reset_history', False):
            try:
                agent._history = {}
                agent.run('wifi.recon clear')
                agent.run('wifi.clear')
                chs = agent._config['personality'].get('channels') or [1, 6, 11]
                agent.run('wifi.recon.channel %s' % ','.join(map(str, chs)))
            except Exception as e:
                log.warning(f'[envtune] history reset: {e}')

        if agent._config.get('ai', {}).get('enabled', False):
            log.info('[envtune] pwnagotchi AI mode is active — '
                         'envtune will be a passive observer')
        else:
            stability = bool(self.cfg.get('prefer_stability', True))
            mode_msg = ('STABILITY mode (noai-aligned: no proactive attacks, '
                        'no opportunistic channel overrides, full strategy '
                        'banned while moving) — set prefer_stability=false '
                        'in config.toml for max-yield mode'
                        if stability else
                        'AGGRESSIVE mode (proactive attacks + opportunistic '
                        'channel overrides enabled) — slightly higher capture '
                        'rate at the cost of more radio activity. Set '
                        'prefer_stability=true to align with noai philosophy')
            log.info(f'[envtune] active and learning '
                     f'(tuning {len(self._active_params)} params, {mode_msg})')

    def on_unload(self, ui):
        self._sync_save_now()
        self._save_stop.set()
        try:
            self._save_queue.put_nowait(None)
        except queue.Full:
            pass
        if self._save_thread and self._save_thread.is_alive():
            self._save_thread.join(timeout=2.0)
        log.info('[envtune] unloaded — final state saved')

    def on_ui_setup(self, ui):
        self._ui = ui

    def on_ui_update(self, ui):
        # Check battery on every UI update (cheap)
        if self._ui is not None:
            self._battery_level = self._read_battery()

    # ── Mood callbacks ────────────────────────────────────────────────────
    def on_bored(self, agent):
        self._mood = 'bored'

    def on_sad(self, agent):
        self._mood = 'sad'
        # Sad pwnagotchi = persistent inactivity. Trigger exploration burst
        # to escape what is probably a stale local-optimum.
        if self._exploration_boost <= 0:
            self._exploration_boost = int(self.cfg['exploration_boost_epochs'])
            self._ucb_cache.clear()

    def on_excited(self, agent):
        self._mood = 'excited'

    def on_grateful(self, agent):
        self._mood = 'grateful'

    def on_angry(self, agent):
        self._mood = 'angry'

    # ── Free channel detection ────────────────────────────────────────────
    def on_free_channel(self, agent, channel):
        try:
            ch = _si(channel)
            if ch:
                with self._state_lock:
                    self._free_channels.append(ch)
                    self._ch_lt[ch]['free_seen'] += 1
        except Exception:
            pass

    # ── Config change callback ────────────────────────────────────────────
    def on_config_changed(self, config):
        # Re-detect supported params (web_cfg may have toggled something)
        if self._agent is not None:
            self._detect_supported_params(self._agent)

    # ═════════════════════════════════════════════════════════════════════
    # Main epoch loop — the brain
    # ═════════════════════════════════════════════════════════════════════

    def on_epoch(self, agent, epoch, epoch_data):
        # Don't fight pwnagotchi's AI if somehow active
        if agent._config.get('ai', {}).get('enabled', False):
            return

        self.epochs_seen += 1
        if self._exploration_boost > 0:
            self._exploration_boost -= 1

        try:
            # ── 1. Read raw observations ──────────────────────────────────
            try:
                raw_aps = agent.get_access_points() or []
                raw_aps = [ap for ap in raw_aps if not self._is_whitelisted(ap)]
                aps     = len(raw_aps)
            except Exception:
                raw_aps = []
                aps     = 0

            # FIX: floor at 10s, not 1s. Very short epochs (e.g. 5s) inflate
            # hs_per_min unrealistically and corrupt _recent_hpm percentiles.
            dur_secs     = max(10.0, _sf(epoch_data.get('duration_secs', 60)))
            deauths      = _si(epoch_data.get('num_deauths',          0))
            assocs       = _si(epoch_data.get('num_associations',     0))
            handshakes   = _si(epoch_data.get('num_handshakes',       0))
            missed       = _si(epoch_data.get('missed_interactions',  0))
            blind_for    = _si(epoch_data.get('blind_for_epochs',     0))
            active_for   = _si(epoch_data.get('active_for_epochs',    0))
            inactive_for = _si(epoch_data.get('inactive_for_epochs',  0))
            num_hops     = _si(epoch_data.get('num_hops',             0))
            temperature  = _sf(epoch_data.get('temperature',          40.0))
            cpu_load     = _sf(epoch_data.get('cpu_load',             0.0))
            # v2.1.0 — verified noai _epoch_data fields
            num_peers    = _si(epoch_data.get('num_peers',            0))
            mem_usage    = _sf(epoch_data.get('mem_usage',            0.0))
            slept_secs   = _sf(epoch_data.get('slept_for_secs',       0.0))
            # native 'reward' field absent in noai (AI removed); pwnagotchi
            # noai never writes this key. We just store 0.0 for back-compat.
            native_rwd   = _sf(epoch_data.get('reward', 0.0))
            ep_total     = max(1, _si(epoch_data.get('epoch', epoch)) or epoch or 1)
            # Mood counters from pwnagotchi's own epoch tracker. Original AI
            # gated these at 5 epochs to avoid penalising warm-up; we keep
            # the same threshold.
            bored_for    = _si(epoch_data.get('bored_for_epochs',     0))
            sad_for      = _si(epoch_data.get('sad_for_epochs',       0))

            interactions = deauths + assocs
            hs_rate      = handshakes / interactions if interactions > 0 else 0.0
            missed_rate  = missed    / interactions if interactions > 0 else 0.0
            hs_per_min   = handshakes / (dur_secs / 60.0)

            # FIX: use pwnagotchi's own epoch counter for ratios
            active_ratio   = active_for   / ep_total
            inactive_ratio = inactive_for / ep_total
            tot_ch         = max(len(self._ch_lt), 14)
            hops_ratio     = min(1.0, num_hops / max(1, tot_ch))

            # FIX: lifetime-new captures (NOT session-new). The whole point
            # of EnvTune is maximising captures of networks we have NEVER
            # seen before across all sessions. We track this via the
            # _captured_bssids set (loaded from /root/handshakes/ + grown
            # in on_handshake). on_handshake increments _lifetime_new_count
            # whenever a brand-new BSSID is captured.
            lifetime_new_this_epoch = (
                self._lifetime_new_count - getattr(
                    self, '_lifetime_new_count_prev', 0))
            lifetime_new_this_epoch = max(0, lifetime_new_this_epoch)
            self._lifetime_new_count_prev = self._lifetime_new_count

            # v1.9.0: advance the auto-strategy block-bandit. Uses the
            # just-updated lifetime_new_count to score the current block
            # if it just expired, then picks the next block's strategy
            # via UCB1. No-op when channel_strategy != 'auto'.
            self._maybe_advance_strategy_block()

            # New APs discovered this epoch (not necessarily captured —
            # exploration value, even when no handshake yet)
            current_ap_count = len(self._known_aps)
            new_aps_seen = max(0, current_ap_count - getattr(
                self, '_known_aps_count_prev', 0))
            self._known_aps_count_prev = current_ap_count

            # FIX: snapshot _known_aps under lock once per epoch. All later
            # iterations in on_epoch use the snapshot, avoiding races with
            # on_wifi_update / on_handshake / on_association mutations.
            with self._state_lock:
                aps_items_snap  = list(self._known_aps.items())
                aps_values_snap = [v for _, v in aps_items_snap]

            # ── 2. Save pre-update aps_ema for nexmon crash check ─────────
            self._prev_aps_ema = self.ema.get('aps')

            # ── 3. Update GPS fix and mobility ────────────────────────────
            if self._gps_available:
                fix = self._read_gps(agent)
                if fix is not None:
                    self._gps_last_fix = fix
                self._update_gps_zone()
            self._current_mobility = self._compute_mobility()

            # ── 4. Update EMAs ────────────────────────────────────────────
            aps_ema  = self._ema('aps',            aps)
            hs_ema   = self._ema('hs_rate',        hs_rate)
            r_ema    = self._ema('reward',         native_rwd)
            mi_ema   = self._ema('missed_rate',    missed_rate)
            _        = self._ema('hs_per_min',     hs_per_min)
            _        = self._ema('active_ratio',   active_ratio)
            _        = self._ema('inactive_ratio', inactive_ratio)
            _        = self._ema('hops_per_epoch', num_hops)
            t_ema    = self._ema('temperature',    temperature)
            _        = self._ema('cpu_load',       cpu_load)
            # v2.1.0 — verified noai _epoch_data fields
            _        = self._ema('num_peers',      num_peers)
            _        = self._ema('mem_usage',      mem_usage)
            _        = self._ema('slept_for_secs', slept_secs)
            if self._gps_last_fix is not None:
                _ = self._ema('speed', self._gps_last_fix.get('speed', 0))

            if self._prev_reward_ema is not None:
                self._reward_trend = r_ema - self._prev_reward_ema
            self._prev_reward_ema = r_ema

            # ── 5. Compute custom reward ──────────────────────────────────
            blind_ratio = blind_for / ep_total
            # v2.0 (F-10): mood_threshold_epochs from DEFAULTS, was hardcoded 5
            mood_thresh = int(self.cfg.get('mood_threshold_epochs', 5))
            bored_ratio = (bored_for / ep_total) if bored_for >= mood_thresh else 0.0
            sad_ratio   = (sad_for   / ep_total) if sad_for   >= mood_thresh else 0.0
            custom_rwd = self._custom_reward(
                handshakes, hs_rate, missed_rate, native_rwd, dur_secs,
                lifetime_new_this_epoch, active_ratio, inactive_ratio, hops_ratio,
                new_aps_seen, interactions,
                blind_ratio=blind_ratio, bored_ratio=bored_ratio,
                sad_ratio=sad_ratio)

            # ── 6. Nexmon crash detection ─────────────────────────────────
            if self._check_nexmon_crash(aps, interactions):
                log.warning('[envtune] nexmon crash suspected — '
                                'aggressive throttle')
                p = agent._config['personality']
                if 'throttle_d' in self._active_params:
                    p['throttle_d'] = min(1.2, _sf(p.get('throttle_d', 0.9)) + 0.3)
                if 'throttle_a' in self._active_params:
                    p['throttle_a'] = min(1.0, _sf(p.get('throttle_a', 0.4)) + 0.2)
                p['max_interactions'] = max(2, _si(p.get('max_interactions', 3)) - 1)
                self._schedule_channels(agent)
                self._reset_decision_buffer()
                self._maybe_save()
                return

            # ── 7. Thermal safety ─────────────────────────────────────────
            if t_ema > 0:
                self._apply_thermal_throttle(agent, t_ema)

            # ── 8. Location change ────────────────────────────────────────
            fp = self._compute_location_fp(raw_aps)
            if self._check_location_change(fp):
                boost = int(self.cfg['exploration_boost_epochs']) * 2
                self._exploration_boost = boost
                self._dead_session.clear()
                self._free_channels.clear()
                self._ucb_cache.clear()
                # v1.7: drop buffered decisions outright. v1.5 credited
                # them with neutral 0.5 so visit counts kept growing,
                # but real community telemetry showed the resulting
                # `n=1, mean=0.5` entries pile up across roving sessions
                # and drift cell means toward 0.5, masking both
                # genuinely-bad arms (mean<0.3) and genuinely-good ones
                # (mean>0.7). The exploration_boost above already widens
                # UCB's bound for the new environment, which is the
                # correct way to handle "we just teleported."
                dropped = len(self._decision_buffer)
                self._reset_decision_buffer()
                # v2.0 (F-06): also abort the strategy bandit's in-progress
                # block. The block ran in a now-stale environment;
                # scoring it would credit the wrong context. Next epoch
                # starts a clean block under the new mobility's bandit.
                self._abort_strategy_block(reason='location change')
                log.info(f'[envtune] location change → '
                         f'{boost}-ep exploration boost '
                         f'(dropped {dropped} buffered decisions)')

            # ── 9. Attribute delayed reward to earlier decision ───────────
            # Adaptive reward_delay: in dense AP environments, parameter
            # changes show in the next 1-2 epochs; in sparse environments,
            # they take longer to manifest (slow scan/handshake cadence).
            base_delay = int(self.cfg['reward_delay'])
            if aps_ema >= 25:
                delay = max(2, base_delay - 1)
            elif aps_ema <= 5:
                delay = base_delay + 1
            else:
                delay = base_delay
            if len(self._decision_buffer) >= delay:
                old_ep, old_state, old_params = list(self._decision_buffer)[-delay]
                for param, val in old_params.items():
                    self._ucb_update(param, old_state, val, custom_rwd)

            # ── 10. Stagnation check ──────────────────────────────────────
            self._check_stagnation(custom_rwd)

            # ── 10b. Saturation-aware exploration boost ───────────────────
            # If we've captured most of the APs visible in this location,
            # there's nothing more to capture without moving — push
            # exploration so we test scan params that might surface the
            # last few hidden / weak APs (deeper min_rssi, longer recon).
            now_mono = time.monotonic()
            with self._state_lock:
                visible = 0
                cap_in_view = 0
                for ap in self._known_aps.values():
                    if ap.get('AT_cracked', False):
                        continue
                    if (now_mono - ap.get('AT_lastseen', 0)) > 90:
                        continue
                    visible += 1
                    if ap.get('AT_already_captured', False):
                        cap_in_view += 1
            if visible >= 8 and cap_in_view / max(1, visible) > 0.80:
                if self._exploration_boost <= 0:
                    self._exploration_boost = int(
                        self.cfg['exploration_boost_epochs'])
                    log.info(
                        f'[envtune] saturation '
                        f'({cap_in_view}/{visible} captured nearby) → '
                        f'{self._exploration_boost}-ep exploration boost')

            # ── 11. Best-settings tracking ────────────────────────────────
            if self.best_reward is None or custom_rwd > self.best_reward + 0.03:
                self.best_reward = custom_rwd
                pdict = agent._config['personality']
                self.best_settings = {k: pdict.get(k) for k in self._active_params}

            # ── 12. Blind-panic handling ──────────────────────────────────
            p = agent._config['personality']
            if blind_for >= int(self.cfg['blind_panic_epochs']):
                if self._blind_recovery == 0:
                    self._blind_saved_params = {
                        k: p.get(k) for k in self._active_params}
                    log.warning(f'[envtune] BLIND PANIC '
                                    f'(blind_for={blind_for})')
                p['min_rssi']         = self.BOUNDS['min_rssi'][0]
                p['recon_time']       = self.BOUNDS['recon_time'][1]
                p['hop_recon_time']   = 8
                # If thermal throttle was already in effect this epoch
                # (step 7 ran before us), keep its lower max_interactions
                # rather than reset to 3 — overheating + blind is the worst
                # combo and we should not loosen the thermal lid.
                if self._thermal_throttle:
                    p['max_interactions'] = min(
                        3, _si(p.get('max_interactions', 3)))
                else:
                    p['max_interactions'] = 3
                if 'throttle_a' in self._active_params:
                    # Slow association attempts to give the radio room to
                    # finish a scan/recover from firmware indigestion.
                    # Keep the more conservative of (blind=0.4, thermal-set).
                    p['throttle_a'] = max(0.4, _sf(p.get('throttle_a', 0.4)))
                if 'throttle_d' in self._active_params:
                    p['throttle_d'] = max(0.9, _sf(p.get('throttle_d', 0.9)))
                self._bettercap_sync(agent, {
                    'min_rssi': p['min_rssi'],
                })
                self._blind_recovery = int(self.cfg['blind_recovery_steps'])
                self._schedule_channels(agent)
                self._reset_decision_buffer()
                self._maybe_save()
                return

            # Gradual recovery from blind panic
            if self._blind_recovery > 0 and self._blind_saved_params:
                self._blind_recovery -= 1
                synced = {}
                for param, saved_val in self._blind_saved_params.items():
                    if saved_val is None or param not in self.UCB_ARMS:
                        continue
                    arms = sorted(self.UCB_ARMS[param])
                    if not arms:
                        continue
                    cur_val = _sf(p.get(param, saved_val))
                    try:
                        ci   = arms.index(min(arms, key=lambda a: abs(a - cur_val)))
                        ti   = arms.index(min(arms, key=lambda a: abs(a - _sf(saved_val))))
                        step = 1 if ti > ci else (-1 if ti < ci else 0)
                        new_val = arms[max(0, min(len(arms) - 1, ci + step))]
                        p[param] = new_val
                        if param in self.BETTERCAP_SYNC_MAP:
                            synced[param] = new_val
                    except (ValueError, IndexError):
                        p[param] = saved_val
                if synced:
                    self._bettercap_sync(agent, synced)
                if self._blind_recovery == 0:
                    self._blind_saved_params = None
                self._schedule_channels(agent)
                self._reset_decision_buffer()
                self._maybe_save()
                return

            # ── 13. Warmup: just observe ──────────────────────────────────
            if self.epochs_seen < int(self.cfg['warmup_epochs']):
                self._schedule_channels(agent)
                self._maybe_save()
                return

            # ── 14. Skip tuning during thermal throttle ───────────────────
            if self._thermal_throttle:
                self._schedule_channels(agent)
                self._reset_decision_buffer()
                self._maybe_save()
                return

            # ── 15. Compute environment state ─────────────────────────────
            state = self._compute_state(aps_ema)

            # ── 16. UCB select arms for active parameters ─────────────────
            chosen = {
                param: self._ucb_select(param, state)
                for param in self.UCB_ARMS
                if param in self._active_params
            }

            # ── 17. Client-aware override ─────────────────────────────────
            recency_limit = int(self.cfg['client_recency_epochs'])
            total_fresh_clients = sum(
                ap.get('AT_clients', 0)
                for ap in aps_values_snap
                if (not ap.get('AT_already_captured', False)
                    and ap.get('AT_cooldown_until', 0) <= self.epochs_seen
                    and (self.epochs_seen - ap.get('AT_client_epoch', -99))
                        <= recency_limit)
            )
            # FIX: also drop max_interactions in genuinely sparse environments
            # (few APs total) — interactions threshold alone misses the "small
            # cafe with 3 strong APs" case where we should still favor PMKID.
            if (total_fresh_clients == 0
                    and (interactions >= 3 or aps_ema < 5)):
                # No clients → focus on PMKID (assoc), reduce deauth aggression
                chosen['max_interactions'] = min(
                    _si(chosen.get('max_interactions', 3)), 2)
            elif total_fresh_clients >= 5:
                chosen['max_interactions'] = max(
                    _si(chosen.get('max_interactions', 3)), 4)

            # ── 18. PMF detection ─────────────────────────────────────────
            # FIX: detection is one-way. Once AT_pmf_detected=True we never
            # try that AP again, but firmware/client-cap can change.
            # Re-evaluate every 200 epochs after detection: if a fresh
            # client appears AND we are well within range, allow one more
            # attempt by clearing the flag (and resetting attack counter).
            pmf_thr = int(self.cfg['pmf_attack_threshold'])
            for apID, ap in aps_items_snap:
                if (ap.get('AT_attacks', 0) >= pmf_thr
                        and ap.get('AT_handshake', 0) == 0
                        and _sf(ap.get('rssi', -85)) > -72):
                    ap['AT_pmf_detected'] = True
                    ap['AT_pmf_detected_ep'] = self.epochs_seen
                elif ap.get('AT_pmf_detected', False):
                    pmf_ep   = ap.get('AT_pmf_detected_ep', 0)
                    age      = self.epochs_seen - pmf_ep
                    has_fresh = (
                        ap.get('AT_clients', 0) > 0
                        and (self.epochs_seen
                             - ap.get('AT_client_epoch', -99))
                            <= recency_limit)
                    if (age >= 200
                            and has_fresh
                            and _sf(ap.get('rssi', -85)) > -65):
                        ap['AT_pmf_detected']    = False
                        ap['AT_pmf_detected_ep'] = 0   # v1.6 fix: was leaking
                        ap['AT_attacks']         = 0
                        ap['AT_missed']          = 0

            # ── 19. Sanity check parameter coupling ───────────────────────
            chosen = self._sanity_check(chosen)

            # ── 20. Apply parameters ──────────────────────────────────────
            sync_needed = {}
            for param, val in chosen.items():
                old = p.get(param)
                p[param] = val
                if param in self.BETTERCAP_SYNC_MAP and old != val:
                    sync_needed[param] = val
            if sync_needed:
                self._bettercap_sync(agent, sync_needed)

            # Record decision for delayed reward attribution
            self._decision_buffer.append((epoch, state, dict(chosen)))

            # ── 21. AP cooldown & efficiency update ───────────────────────
            cd_atk    = int(self.cfg['ap_cooldown_attacks'])
            cd_short  = int(self.cfg['ap_cooldown_short'])
            cd_long   = int(self.cfg['ap_cooldown_long'])
            miss_cd   = int(self.cfg['missed_cooldown_threshold'])
            for apID, ap in aps_items_snap:
                atk = ap.get('AT_attacks', 0)
                hs  = ap.get('AT_handshake', 0)
                ap['AT_efficiency'] = hs / atk if atk > 0 else 0.0

                # ANTI-OVERCAPTURE: if we already have a handshake for this
                # AP (in /root/handshakes/), keep it on permanent rolling
                # cooldown. We can't stop pwnagotchi's main loop from going
                # for it, but we can ensure our channel scoring and
                # proactive logic ignores it. Long cooldown is deliberate:
                # prevents repeat attacks all session.
                if ap.get('AT_already_captured', False):
                    if ap.get('AT_cooldown_until', 0) <= self.epochs_seen:
                        ap['AT_cooldown_until'] = self.epochs_seen + cd_long * 4
                    continue

                # Standard cooldown on attacks-without-HS
                if (atk >= cd_atk and hs == 0
                        and ap.get('AT_cooldown_until', 0) <= self.epochs_seen):
                    cd_dur = cd_long if atk >= cd_atk * 2 else cd_short
                    ap['AT_cooldown_until'] = self.epochs_seen + cd_dur
                    continue

                # Early cooldown on excessive missed-interaction count
                if (ap.get('AT_missed', 0) >= miss_cd
                        and ap.get('AT_cooldown_until', 0) <= self.epochs_seen):
                    ap['AT_cooldown_until'] = self.epochs_seen + cd_short
                    ap['AT_missed'] = 0  # reset counter post-cooldown

            # ── 22. Channel wasted-attack tracking ────────────────────────
            if interactions > 0 and handshakes == 0:
                with self._state_lock:
                    for ch in self._active_channels:
                        self._ch_lt[ch]['wasted'] += 1

            # ── 23. Channel scheduling ────────────────────────────────────
            self._schedule_channels(agent)

            # FIX: push grown skip-list to bettercap so wifi.assoc/deauth
            # don't waste airtime on already-captured BSSIDs.
            self._push_bcap_skip_list(agent)

            # ── 24. Proactive attacks for high-value targets (opt-in) ─────
            # v2.2.0: gate behind prefer_stability — when True (default),
            # NEVER fire extra wifi.assoc frames beyond pwnagotchi's
            # natural loop. The noai branch was created precisely to
            # stop the AI's extra radio TX from destabilising firmware;
            # this plugin honours that.
            stability = bool(self.cfg.get('prefer_stability', True))
            if (not stability
                    and self._profile['enable_proactive']
                    and self.cfg.get('opportunistic_overrides', True)
                    and self.epochs_seen - self._last_proactive_ep
                        >= int(self.cfg['proactive_gap_epochs'])
                    and not self._thermal_throttle):
                self._maybe_proactive_attack(agent)

            # ── 25. GPS zone bookkeeping ──────────────────────────────────
            if self._current_zone is not None:
                if interactions > 0:
                    self._gps_zones[self._current_zone]['attacks'] += interactions

            # ── 26. Compact INFO log line ─────────────────────────────────
            top_ch = sorted(self._ch_lt.items(),
                            key=lambda x: -x[1]['hs'])[:3]
            top_s  = ','.join(f'{c}:{d["hs"]}' for c, d in top_ch) or 'none'
            zone_s = self._current_zone or '-'
            log.info(
                f'[envtune] ep={epoch} st={state} mood={self._mood} '
                f'aps={aps_ema:.0f} hs_rt={hs_ema:.2f} '
                f'hpm={self.ema["hs_per_min"]:.2f} miss={mi_ema:.2f} '
                f'rwd={custom_rwd:.2f} t={t_ema:.0f}C '
                f'unique_lifetime={self._lifetime_new_count} '
                f'(+{lifetime_new_this_epoch} this ep) '
                f'top={top_s} zone={zone_s} mob={self._current_mobility}')

            # ── 27. Verbose DEBUG dump ────────────────────────────────────
            log.debug(f'[envtune] params={chosen} expl={self._exploration_boost} '
                          f'fresh_clients={total_fresh_clients}')
            if self._last_reward_breakdown:
                # Compact one-line component log so operators can see WHY
                # reward landed where it did. Sorted by absolute weight so
                # dominant terms come first.
                items = sorted(
                    self._last_reward_breakdown.items(),
                    key=lambda kv: -abs(kv[1]))
                comps = ' '.join(f'{k}={v:+.3f}' for k, v in items)
                log.debug(f'[envtune] reward_components: {comps}')

            # ── 28. Periodic wpa-sec potfile rescan ───────────────────────
            # External tool (cron / wpa-sec.py) appends to the potfile
            # asynchronously; if we never rescan, freshly cracked networks
            # keep being targeted long after we know the password.
            if (self.cfg.get('enable_wpasec_feedback', True)
                    and self.epochs_seen
                    and self.epochs_seen % int(
                        self.cfg.get('potfile_rescan_every_n', 100)) == 0):
                try:
                    cracked = self._scan_cracked_potfile()
                    if cracked:
                        with self._state_lock:
                            added = len(cracked - self._cracked_bssids)
                            # v1.8.1: MERGE not REPLACE — see notes in
                            # on_loaded and the rescan-potfile webhook.
                            self._cracked_bssids |= cracked
                            if added:
                                for ap in self._known_aps.values():
                                    if self._mac_norm(ap.get('mac', '')) in self._cracked_bssids:
                                        ap['AT_cracked'] = True
                        if added:
                            log.info(f'[envtune] potfile rescan: '
                                     f'+{added} cracked BSSIDs '
                                     f'({len(self._cracked_bssids)} total)')
                except Exception as e:
                    log.debug(f'[envtune] potfile rescan: {e}')

            # ── 29. Handshake-dir rescan watchdog ─────────────────────────
            # If something external (wpa-sec sync, manual copy, another
            # plugin) drops a .pcap into HANDSHAKE_DIR, we won't notice
            # until a restart. Periodically diff the directory against
            # our in-memory _captured_bssids and adopt anything new — so
            # the priority loop and skip-list stay accurate.
            if (self.epochs_seen
                    and self.epochs_seen % int(
                        self.cfg.get('handshake_rescan_every_n', 200)) == 0):
                try:
                    fs_set = self._scan_handshake_dir()
                    with self._state_lock:
                        new_macs = fs_set - self._captured_bssids
                        if new_macs:
                            self._captured_bssids |= new_macs
                            self._lifetime_new_count = max(
                                self._lifetime_new_count,
                                len(self._captured_bssids))
                    if new_macs:
                        log.info(
                            f'[envtune] handshake-dir watchdog: '
                            f'+{len(new_macs)} BSSIDs adopted from disk')
                        # _push_bcap_skip_list rebuilds from the
                        # current _captured_bssids/_cracked_bssids sets
                        # under the config flags — no direct add needed.
                        try:
                            self._push_bcap_skip_list(agent)
                        except Exception:
                            pass
                except Exception as e:
                    log.debug(f'[envtune] handshake-dir watchdog: {e}')

            self._maybe_save()

        except Exception as e:
            self._record_error('on_epoch')
            log.exception(f'[envtune] on_epoch: {e}')

    def _reset_decision_buffer(self):
        """Clear delayed-reward queue when we skip the UCB select path."""
        self._decision_buffer.clear()

    def _maybe_proactive_attack(self, agent):
        """
        Proactively trigger wifi.assoc on a single high-value target.
        Only if profile permits it AND there's a clearly valuable AP.
        Conservative: max 1 per N epochs, opt-in via config flag.

        Strict filters (we only want to attack worthwhile targets):
          - Not already captured (would be wasted reward)
          - Not in cooldown (we already tried recently)
          - Not PMF-detected (waste of breath)
          - Not in wpa-sec cracked set (we know the password)
          - Hidden hostname: only with strict RSSI+clients gate
          - Strong enough RSSI
          - MAC validates as real (not a malformed bcap entry)
        """
        try:
            # FIX: snapshot under lock to avoid race with on_wifi_update.
            with self._state_lock:
                aps_snap     = list(self._known_aps.items())
                cracked_snap = set(self._cracked_bssids)

            best_ap    = None
            best_score = 0.0
            for apID, ap in aps_snap:
                if ap.get('AT_already_captured', False):
                    continue
                if ap.get('AT_cooldown_until', 0) > self.epochs_seen:
                    continue
                if ap.get('AT_pmf_detected', False):
                    continue
                # FIX: skip APs whose password we already cracked via wpa-sec.
                # No reward for re-capturing networks we've already broken.
                mac_n = self._mac_norm(ap.get('mac', ''))
                if mac_n and mac_n in cracked_snap:
                    continue
                rssi    = _sf(ap.get('rssi', -85))
                clients = ap.get('AT_clients', 0)
                # FIX: hidden APs aren't useless for PMKID — bettercap can
                # still elicit an assoc frame. Allow them, but require a
                # stronger gate: very close RSSI AND active clients.
                hostname = str(ap.get('hostname', '')).strip()
                is_hidden = (
                    not hostname
                    or hostname == '<hidden>'
                    or apID.startswith('hidden-'))
                if is_hidden:
                    if rssi < -60 or clients == 0:
                        continue
                if rssi < self.cfg['proactive_min_rssi']:
                    continue
                # v2.2: require minimum client count (was declared in
                # DEFAULTS since v1.x but never actually enforced).
                # Hidden APs already get a stricter clients>=1 gate
                # above; this applies the user-configurable floor to
                # all proactive candidates.
                min_clients = int(self.cfg.get('proactive_min_clients', 1))
                if clients < min_clients:
                    continue
                # FIX: validate MAC syntactically before sending to bcap —
                # malformed entries would cause the agent.run command to
                # silently fail or, worse, parse wrong.
                mac = ap.get('mac', '')
                if not _is_valid_mac(mac):
                    continue
                # Score: rssi + client count
                score = (rssi + 90) + clients * 5
                if score > best_score:
                    best_score = score
                    best_ap = ap

            if best_ap is None:
                return
            mac = best_ap.get('mac')
            # Proactive PMKID grab via wifi.assoc — bettercap sends an
            # association frame, AP may leak PMKID without needing a client.
            # We do NOT do proactive deauth here: deauth requires a client
            # mac and must be timed against a real client connection, which
            # bettercap's main loop handles better than we can.
            agent.run('wifi.assoc %s' % mac)
            self._last_proactive_ep = self.epochs_seen
            with self._state_lock:
                if best_ap is self._known_aps.get(self._ap_id(best_ap)):
                    best_ap['AT_lastattack_ep'] = self.epochs_seen
            log.debug(f'[envtune] proactive assoc → {mac}')
        except Exception as e:
            log.debug(f'[envtune] proactive: {e}')

    # ═════════════════════════════════════════════════════════════════════
    # Event callbacks
    # ═════════════════════════════════════════════════════════════════════

    def on_handshake(self, agent, filename, access_point, client_station):
        """Record a captured handshake — the only thing we truly care about."""
        try:
            ch = 0
            mac_n = ''
            apID = None
            passive = False
            is_lifetime_new = False  # default — overwritten below if applicable

            if isinstance(access_point, dict):
                ch    = _si(access_point.get('channel', 0))
                apID  = self._ap_id(access_point)
                mac_n = self._mac_norm(access_point.get('mac', ''))
                self._mark_ap_seen(access_point, 'handshake')
                with self._state_lock:
                    if apID in self._known_aps:
                        ap = self._known_aps[apID]
                        ap['AT_handshake'] = ap.get('AT_handshake', 0) + 1
                        ap['AT_already_captured'] = True
                        ap['AT_pmkid_success'] = True
                        # Passive capture detection: 0 attacks = pure luck
                        if ap.get('AT_attacks', 0) == 0:
                            passive = True

            with self._state_lock:
                self.lifetime_handshakes += 1
                self.session_handshakes  += 1
                # CRITICAL: distinguish lifetime-new vs. duplicate captures.
                # _captured_bssids is loaded from /root/handshakes/ at start
                # AND maintained across sessions via state save. So if mac_n
                # is NOT in there yet, this is a brand-new capture.
                if mac_n and mac_n not in self._captured_bssids:
                    self._lifetime_new_count += 1
                    is_lifetime_new = True
                else:
                    is_lifetime_new = False
                if mac_n:
                    self._captured_bssids.add(mac_n)
                    self._session_hs_bssids.add(mac_n)
                    # FIX: feed bettercap skip-list so duplicate captures
                    # _push_bcap_skip_list later this epoch will see
                    # mac_n in _captured_bssids and add it to the bcap
                    # skip list IF bcap_skip_captured config is true.
                    # Default is False — captured-not-cracked APs stay
                    # in the attack queue at low priority.
                if apID:
                    self._captured_aps.add(apID)
                if ch:
                    self._inc_ch('Handshakes', ch)
                    self._ch_lt[ch]['hs'] += 1
                    if passive:
                        self._ch_lt[ch]['passive_hs'] += 1

                # GPS zone credit
                if self._current_zone is not None:
                    self._gps_zones[self._current_zone]['hs'] += 1
                    if ch:
                        self._gps_zones[self._current_zone]['channels'][ch] += 1

            # Invalidate per-epoch ch_score cache — capturing this AP
            # changes its channel's score (one fewer uncaptured target).
            self._ch_score_cache.clear()

            self.last_shake = {
                'time': time.time(),
                'ap':   access_point,
                'cl':   client_station,
                'passive': passive,
                'lifetime_new': is_lifetime_new,
            }
            tags = []
            if is_lifetime_new:
                tags.append('🆕NEW')
            else:
                tags.append('dup')
            tags.append('PASSIVE' if passive else 'ACTIVE')
            log.info(f'[envtune] handshake [{" ".join(tags)}] ch={ch} '
                         f'lifetime={self.lifetime_handshakes} '
                         f'unique_lifetime={self._lifetime_new_count}')

            # Refresh bettercap's skip-list. With v1.3 default
            # (bcap_skip_captured=False) this is mostly a no-op for
            # uncracked captures — captured-but-uncracked APs stay
            # attackable so opportunistic re-captures can still happen.
            # If the user opted in to bcap_skip_captured, this push
            # propagates the new BSSID immediately so bettercap doesn't
            # waste a deauth cycle on it.
            if is_lifetime_new and agent is not None:
                try:
                    self._push_bcap_skip_list(agent)
                except Exception as e:
                    log.debug(f'[envtune] immediate skip push: {e}')
        except Exception as e:
            self._record_error('on_handshake')
            log.debug(f'[envtune] on_handshake: {e}')

    def on_association(self, agent, access_point):
        try:
            ch   = _si(access_point.get('channel', 0))
            apID = self._ap_id(access_point)
            self._mark_ap_seen(access_point, 'assoc')
            with self._state_lock:
                self._inc_ch('Associations', ch)
                self._ch_lt[ch]['assocs'] += 1
                if apID in self._known_aps:
                    ap = self._known_aps[apID]
                    ap['AT_attacks'] = ap.get('AT_attacks', 0) + 1
                    ap['AT_lastattack_ep'] = self.epochs_seen
        except Exception as e:
            log.debug(f'[envtune] on_association: {e}')

    def on_deauthentication(self, agent, access_point, client_station):
        try:
            ch   = _si(access_point.get('channel', 0))
            apID = self._ap_id(access_point)
            self._mark_ap_seen(access_point, 'deauth')
            with self._state_lock:
                self._inc_ch('Deauths', ch)
                self._ch_lt[ch]['deauths'] += 1
                if apID in self._known_aps:
                    ap = self._known_aps[apID]
                    ap['AT_attacks'] = ap.get('AT_attacks', 0) + 1
                    ap['AT_lastattack_ep'] = self.epochs_seen
        except Exception as e:
            log.debug(f'[envtune] on_deauthentication: {e}')

    def on_wifi_update(self, agent, access_points):
        try:
            # FIX: 'Current APs' counter must be decremented symmetrically
            # when an AP transitions visible→invisible. Previously we set
            # AT_visible=False without dec'ing the channel counter.
            # FIX: snapshot _known_aps via list() to avoid 'dict changed size'
            # under RLock re-entry from _mark_ap_seen / evict.
            # FIX: all _ch_lt, _unscanned_channels, _dead_session, _dead_lt
            # mutations now under a single lock — these are concurrently
            # read by _schedule_channels and _ch_score from on_epoch.
            with self._state_lock:
                for ap in list(self._known_aps.values()):
                    if ap.get('AT_visible', False):
                        ap_ch = _si(ap.get('channel', 0))
                        if ap_ch:
                            self._inc_ch('Current APs', ap_ch, -1)
                    ap['AT_visible'] = False

                active      = []
                visited_chs = set()
                for ap in access_points:
                    if self._is_whitelisted(ap):
                        continue
                    self._mark_ap_seen(ap, 'wifi_update')
                    ch = _si(ap.get('channel', 0))
                    if ch <= 0:
                        continue
                    if ch not in active:
                        active.append(ch)
                        if ch in self._unscanned_channels:
                            self._unscanned_channels.remove(ch)
                        self._dead_session[ch] = 0
                    if ch not in visited_chs:
                        self._ch_lt[ch]['visits'] += 1
                        visited_chs.add(ch)

                # Dead-channel session counter
                for ch in list(self._dead_session):
                    if ch not in active:
                        self._dead_session[ch] += 1
                        if (self._dead_session[ch]
                                > int(self.cfg['dead_channel_cooldown']) * 4):
                            self._dead_lt[ch] = self._dead_lt.get(ch, 0) + 1

                self._active_channels = active
        except Exception as e:
            self._record_error('on_wifi_update')
            log.exception(f'[envtune] on_wifi_update: {e}')

    def on_bcap_wifi_ap_new(self, agent, event):
        try:
            self._mark_ap_seen(event.get('data', {}))
        except Exception:
            pass

    def on_bcap_wifi_ap_lost(self, agent, event):
        try:
            ap   = event.get('data', {})
            apID = self._ap_id(ap)
            ch   = _si(ap.get('channel', 0))
            with self._state_lock:
                if (apID in self._known_aps
                        and self._known_aps[apID].get('AT_visible', False)):
                    self._known_aps[apID]['AT_visible'] = False
                    self._inc_ch('Current APs', ch, -1)
        except Exception:
            pass

    def on_bcap_wifi_client_new(self, agent, event):
        try:
            data = event.get('data', {}) or {}
            ap   = data.get('AP', {}) or {}
            ch   = _si(ap.get('channel', 0))
            if not ch:
                return
            apID = self._ap_id(ap)
            with self._state_lock:
                self._inc_ch('Clients', ch)
                self._ch_lt[ch]['clients'] += 1
                if apID in self._known_aps:
                    self._known_aps[apID]['AT_clients'] = (
                        self._known_aps[apID].get('AT_clients', 0) + 1)
                    self._known_aps[apID]['AT_client_epoch'] = self.epochs_seen
            # Opportunistic channel override.
            # v1.7.1: ch must be inside the user's channel universe.
            # Users who restricted their config to e.g. [1,6,11] should
            # never see envtune push channel 4 onto bettercap because
            # a client showed up there.
            # v2.2.0: ALSO gated by prefer_stability — the runtime
            # wifi.recon.channel poke is one of the few places we add
            # radio reconfiguration beyond the natural recon loop.
            in_universe = (self._user_channels_orig is None
                           or ch in self._user_channels_orig)
            stability = bool(self.cfg.get('prefer_stability', True))
            if (not stability
                    and in_universe
                    and self.cfg.get('opportunistic_overrides', True)
                    and ch not in self._active_channels
                    and self.epochs_seen - self._last_override_ep
                        >= int(self.cfg['opportunistic_min_gap'])):
                try:
                    current = list(
                        agent._config['personality'].get('channels', []))
                    if ch not in current:
                        current.insert(0, ch)
                    agent.run('wifi.recon.channel %s' %
                              ','.join(map(str, current)))
                    self._last_override_ep = self.epochs_seen
                    log.debug(f'[envtune] opportunistic override → ch {ch}')
                except Exception:
                    pass
        except Exception as e:
            log.debug(f'[envtune] on_bcap_wifi_client_new: {e}')

    def on_bcap_wifi_client_lost(self, agent, event):
        try:
            data = event.get('data', {}) or {}
            ap   = data.get('AP', {}) or {}
            apID = self._ap_id(ap)
            with self._state_lock:
                if apID in self._known_aps:
                    cur = self._known_aps[apID].get('AT_clients', 0)
                    self._known_aps[apID]['AT_clients'] = max(0, cur - 1)
        except Exception:
            pass

    def on_bcap_wifi_assoc(self, agent, event):
        # INTENTIONALLY EMPTY. The bettercap-side `wifi.assoc` event fires
        # on the same attack our `on_association` callback already handles
        # via pwnagotchi's own pipeline. Counting it here would
        # double-increment AT_attacks and `_ch_lt[ch]['assocs']`. Missed
        # interactions are accounted from `epoch_data['missed_interactions']`
        # in `on_epoch`, not here. Keep this stub so plugins.on() doesn't
        # log a "no handler" warning if your bettercap build emits the
        # event under this name.
        return

    # ═════════════════════════════════════════════════════════════════════
    # Web UI (/plugins/envtune/)
    # ═════════════════════════════════════════════════════════════════════

    @staticmethod
    def _html_response(body, status=200):
        # Bypass Jinja: pwnagotchi UI may pass attacker-controlled SSIDs through
        # this method, so we never let `{{ }}` reach a template engine.
        resp = make_response(body, status)
        resp.headers['Content-Type'] = 'text/html; charset=utf-8'
        resp.headers['X-Content-Type-Options'] = 'nosniff'
        resp.headers['Cache-Control'] = 'no-store'
        return resp

    def _plugin_base(self):
        """Absolute URL prefix where this plugin is mounted in pwnagotchi's
        webserver. Pwnagotchi mounts at /plugins/<class_name_lowercase>/.
        Using absolute paths fixes the bug where a relative form action
        like `force-save` resolves against `/plugins/` (instead of
        `/plugins/envtune/`) when the user visits the dashboard URL
        without a trailing slash."""
        return '/plugins/' + type(self).__name__.lower() + '/'

    def on_webhook(self, path, request):
        if not self._agent:
            return self._html_response(
                '<!DOCTYPE html><html><body><h1>EnvTune not ready yet</h1>'
                '</body></html>', status=503)
        try:
            method = (request.method if request is not None else 'GET').upper()

            # POST actions (force-save / reset-stagnation / rescan-potfile)
            if method == 'POST':
                return self._handle_post(path, request)

            # Sub-paths for data export
            if path == 'export':
                return self._endpoint_export(request)
            if path == 'metrics':
                return self._endpoint_metrics()
            if path == 'zones':
                return self._endpoint_zones(request)

            # Main HTML dashboard — every dynamic value goes through html.escape
            # in its helper, and the whole document is returned as a raw HTML
            # response (no Jinja evaluation).
            version = html.escape(str(self.__version__))
            profile = html.escape(str(self._profile_name))
            gps_src = html.escape(str(self._gps_source or 'off'))
            mood = html.escape(str(self._mood))
            mobility = html.escape(str(self._current_mobility))
            base = html.escape(self._plugin_base())
            # Build the zone alias map ONCE per render so Status and
            # the GPS Zone table stay consistent.
            zone_aliases, cur_zone_alias = self._build_zone_alias_map()

            # Auto-refresh — only when no AP filter is active or we're
            # on the main view. Skipped when ?norefresh=1 (operator
            # toggle for when you're inspecting). Default 30 s — long
            # enough not to spam, short enough to feel live.
            refresh_secs = 30
            try:
                if request is not None:
                    nr = request.args.get('norefresh', '')
                    if nr in ('1', 'true', 'yes', 'on'):
                        refresh_secs = 0
                    rs = request.args.get('refresh', '')
                    if rs and rs.isdigit():
                        refresh_secs = max(0, min(600, int(rs)))
            except Exception:
                pass
            refresh_meta = (
                f'<meta http-equiv="refresh" content="{refresh_secs}">'
                if refresh_secs > 0 else '')
            # Read the optional one-shot toast message (set by post-action
            # redirects via ?msg=…). HTML-escape because it's a query
            # param — anyone could craft any URL.
            toast = ''
            try:
                if request is not None:
                    msg = request.args.get('msg', '') or ''
                    ok  = (request.args.get('ok', '1') in ('1', 'true', 'yes'))
                    if msg:
                        cls = 'good' if ok else 'bad'
                        toast = (f'<div class="toast {cls}">'
                                 f'{html.escape(msg[:200])}</div>')
            except Exception:
                pass

            parts = [
                '<!DOCTYPE html><html><head>',
                f'<title>EnvTune v{version}</title>',
                # <base> makes ALL relative URLs (links, forms, redirects)
                # resolve against the plugin mount point, regardless of
                # whether the visitor's URL had a trailing slash.
                f'<base href="{base}">',
                '<meta name="viewport" content="width=device-width, initial-scale=1">',
                refresh_meta,
                f'<style>{self._ui_css()}</style></head><body>',
                toast,
                f'<h1>⚡ EnvTune v{version}</h1>',
                '<p class="subtitle">',
                f'profile=<b>{profile}</b> | gps=<b>{gps_src}</b> | ',
                f'mood=<b>{mood}</b> | mobility=<b>{mobility}</b> | ',
                self._ui_channel_strategy_inline(),
                f'<a href="{base}?norefresh=1" class="muted">'
                f'{"⏸ pause refresh" if refresh_secs > 0 else "▶ resume refresh"}</a>',
                '</p>',
                '<div class="links">',
                f'<a href="{base}export">📥 Export</a> | ',
                f'<a href="{base}metrics">📊 Metrics</a> | ',
                f'<a href="{base}zones">🗺️ Zones</a>',
                '</div>',
                self._ui_summary_cards(current_zone_alias=cur_zone_alias),
                self._ui_actions(),
                self._ui_strategy_bandit(),    # v1.9.0 — auto-strategy panel
                self._ui_reward_breakdown(),
                self._ui_status(current_zone_alias=cur_zone_alias),
                self._ui_current_params(),
                self._ui_bandit_preview(),
                self._ui_ucb_summary(),
                self._ui_channels(),
                self._ui_top_aps(request=request),
            ]
            if self._gps_available and self._gps_zones:
                parts.append(self._ui_gps_zones(aliases=zone_aliases))
            parts.append('</body></html>')
            return self._html_response(''.join(parts))
        except Exception as e:
            self._record_error('webhook')
            log.exception(f'[envtune] webhook: {e}')
            body = ('<!DOCTYPE html><html><body><h1>Error</h1>'
                    f'<pre>{html.escape(repr(e))}</pre></body></html>')
            return self._html_response(body, status=500)

    def _ui_css(self):
        return '''
*{box-sizing:border-box}
body{font-family:"Courier New",monospace;background:#0d0d0d;color:#b0b0b0;
     margin:0;padding:18px;font-size:13px;line-height:1.45}
h1{color:#00ff88;letter-spacing:2px;margin:0 0 4px 0;font-size:1.8em}
h2{color:#00ccff;border-bottom:1px solid #1a3a3a;padding-bottom:4px;
   margin-top:22px}
h3{color:#00ccff;font-size:0.95em;margin:6px 0 4px 0}
p.subtitle{color:#666;margin:0 0 10px 0}
div.links{margin-bottom:20px}
a{color:#00ccff;text-decoration:none}
a:hover{text-decoration:underline}
table{border-collapse:collapse;width:100%;margin-bottom:18px;
      table-layout:auto}
th{background:#0a1a2a;color:#00ff88;padding:5px 8px;
   border:1px solid #1a3a3a;text-align:left;font-size:0.88em;
   white-space:nowrap}
td{padding:3px 8px;border:1px solid #1a1a1a;font-size:0.87em;
   vertical-align:top;word-break:break-word}
tr:hover td{background:#111820}
.good{color:#00ff88;font-weight:bold}
.warn{color:#ffaa00}
.bad{color:#ff4444}
.na{color:#444}
.muted{color:#666}
small{font-size:0.78em;color:#666}
[title]{cursor:help;border-bottom:1px dotted #444}
.actbar{margin:6px 0 12px 0}
.actbtn{font-family:inherit;font-size:0.85em;padding:6px 12px;
        border:1px solid #1a3a3a;background:#101820;color:#00ccff;
        cursor:pointer;border-radius:3px;transition:all 0.15s}
.actbtn.good{color:#00ff88;border-color:#003322}
.actbtn.warn{color:#ffaa00;border-color:#332200}
.actbtn:hover{background:#16242c;border-color:#00ccff}
.actbtn:active{transform:translateY(1px)}
ul.actionlog{list-style:none;padding:0;margin:6px 0 12px 0;
             font-size:0.82em;color:#888}
ul.actionlog li{padding:2px 0;border-bottom:1px dotted #1a1a1a}

/* SUMMARY CARDS */
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));
       gap:10px;margin:14px 0 22px 0}
.card{background:linear-gradient(135deg,#0a1820 0%,#101820 100%);
      border:1px solid #1a3a3a;border-radius:6px;padding:12px 14px;
      position:relative;overflow:hidden}
.card .lbl{font-size:0.78em;color:#666;text-transform:uppercase;
           letter-spacing:1px;margin-bottom:4px}
.card .val{font-size:1.7em;font-weight:bold;color:#00ff88;line-height:1.0}
.card .sub{font-size:0.78em;color:#888;margin-top:3px}
.card.warn{border-color:#332200}
.card.warn .val{color:#ffaa00}
.card.bad{border-color:#3a1a1a}
.card.bad .val{color:#ff4444}
.card.info{border-color:#1a2a3a}
.card.info .val{color:#00ccff}

/* PROGRESS / SPARKLINE */
.bar{display:inline-block;height:8px;background:#1a1a1a;border-radius:2px;
     overflow:hidden;vertical-align:middle;min-width:60px}
.bar > span{display:block;height:100%;background:#00ff88}
.bar.warn > span{background:#ffaa00}
.bar.bad  > span{background:#ff4444}
.bar.info > span{background:#00ccff}
.spark{display:inline-flex;align-items:flex-end;gap:1px;height:14px;
       vertical-align:middle}
.spark span{display:block;width:4px;background:#00ccff;border-radius:1px 1px 0 0}

/* PRIOR + UCB BADGES */
.badge{display:inline-block;font-size:0.72em;padding:1px 5px;border-radius:3px;
       margin-left:5px;font-weight:normal;letter-spacing:0.3px}
.badge.prior{background:#221a00;color:#aa7700;border:1px solid #4a3300}
.badge.cold{background:#001a22;color:#0099aa;border:1px solid #003344}
.badge.hot{background:#002211;color:#00ff88;border:1px solid #003322}
.badge.mood{background:#1a1a2a;color:#aaaacc}

/* REWARD BREAKDOWN */
.rwbd{display:flex;flex-wrap:wrap;gap:6px;margin:6px 0 14px 0}
.rwbd .cmp{background:#101820;border:1px solid #1a3a3a;padding:3px 8px;
           border-radius:3px;font-size:0.82em;display:flex;
           align-items:center;gap:6px}
.rwbd .cmp.pos{border-color:#003322;color:#00ff88}
.rwbd .cmp.neg{border-color:#3a1a1a;color:#ff8888}
.rwbd .cmp .v{font-weight:bold;font-family:inherit}

/* TOAST — one-shot post-action confirmation, top-right corner */
.toast{position:fixed;top:14px;right:14px;z-index:1000;
       padding:10px 16px;border-radius:5px;font-size:0.9em;
       font-weight:bold;box-shadow:0 4px 12px rgba(0,0,0,0.6);
       animation:slidein 0.3s ease-out, fadeout 0.5s ease-in 4.5s forwards;
       max-width:320px}
.toast.good{background:#003322;color:#00ff88;border:1px solid #00aa55}
.toast.bad{background:#3a1a1a;color:#ff8888;border:1px solid #cc4444}
@keyframes slidein{from{transform:translateX(120%);opacity:0}
                   to{transform:translateX(0);opacity:1}}
@keyframes fadeout{to{opacity:0;transform:translateX(120%);
                      pointer-events:none}}

/* AP FILTER PANEL */
.filterbar{margin:6px 0 10px 0;display:flex;gap:6px;flex-wrap:wrap}
.fbtn{background:#101820;color:#888;border:1px solid #1a3a3a;
      padding:3px 10px;border-radius:3px;font-size:0.8em;cursor:pointer;
      font-family:inherit}
.fbtn:hover{background:#16242c;color:#00ccff}
.fbtn.active{background:#003322;color:#00ff88;border-color:#00ff88}

/* MOBILE RESPONSIVE */
@media (max-width:700px){
  body{padding:10px;font-size:12px}
  h1{font-size:1.4em;letter-spacing:1px}
  .cards{grid-template-columns:repeat(2,1fr)}
  .card .val{font-size:1.3em}
  table{font-size:0.78em}
  th,td{padding:3px 4px}
  .actbtn{padding:5px 8px;font-size:0.78em}
}
@media (max-width:400px){
  .cards{grid-template-columns:1fr}
}
'''

    @staticmethod
    def _fmt(v, spec='.3f', na='N/A'):
        if v is None:
            return f'<span class="na">{na}</span>'
        try:
            return format(float(v), spec)
        except (ValueError, TypeError):
            return html.escape(str(v))

    def _ui_channel_strategy_inline(self):
        """Compact strategy indicator for the subtitle line."""
        try:
            cfg_mode = self.cfg.get('channel_strategy', 'auto')
            active = self._resolve_channel_strategy()
            n_universe = len(self._user_channels_orig or [])
            sweep_every = max(2, int(self.cfg.get(
                'channel_full_sweep_every', 15)))

            if cfg_mode == 'auto':
                block_size = max(5, int(self.cfg.get(
                    'auto_strategy_block_epochs', 30)))
                eib = max(0, self.epochs_seen - self._strategy_block_start_ep)
                left = max(0, block_size - eib)
                tip = (f'auto: meta-bandit cycles through adaptive/full/capped '
                       f'in {block_size}-epoch blocks, picks the strategy that '
                       f'captures the most unique HS in YOUR environment')
                return (f'<span title="{html.escape(tip)}">'
                        f'channels=<b>auto→{html.escape(active)}</b> '
                        f'<small>(block {eib}/{block_size})</small></span> | ')
            if active == 'adaptive':
                next_sweep = max(0, sweep_every -
                                 (self.epochs_seen - self._last_full_sweep_ep))
                tip = (f'adaptive: top-K most epochs, full {n_universe}-channel '
                       f'sweep every {sweep_every} epochs')
                return (f'<span title="{html.escape(tip)}">'
                        f'channels=<b>adaptive</b> '
                        f'<small>({n_universe}ch, sweep in {next_sweep})</small>'
                        f'</span> | ')
            if active == 'full':
                tip = f'full sweep every epoch — {n_universe} channels'
                return (f'<span title="{html.escape(tip)}">'
                        f'channels=<b>full</b> '
                        f'<small>({n_universe}ch)</small></span> | ')
            tip = f'capped — top scored channels only, no full sweeps'
            return (f'<span title="{html.escape(tip)}">'
                    f'channels=<b>capped</b> '
                    f'<small>({n_universe}ch universe)</small></span> | ')
        except Exception:
            return ''

    def _ui_strategy_bandit(self):
        """Full panel showing the strategy meta-bandit's stats — only
        rendered when channel_strategy='auto'.

        v2.0: shows BOTH mobility bandits (stationary + moving), so
        operators see how strategy preference differs across mobility.
        """
        try:
            if self.cfg.get('channel_strategy') != 'auto':
                return ''
            # Block-duration display uses whichever mode is active
            epochs_legacy = int(self.cfg.get('auto_strategy_block_epochs', 0) or 0)
            if epochs_legacy > 0:
                block_unit = f'{epochs_legacy}ep'
            else:
                secs = int(self.cfg.get('auto_strategy_block_secs', 1800))
                block_unit = f'{secs}s'
            with self._state_lock:
                snap = {
                    mob: {
                        s: {'n': d['n'], 'rewards': list(d['rewards'])}
                        for s, d in mob_bandit.items()
                    }
                    for mob, mob_bandit in self._strategy_bandit.items()
                }
                current = self._strategy_current
                current_mob = self._strategy_block_mobility
                cur_mobility = self._current_mobility
                if self._strategy_block_start_mono is not None:
                    eib_secs = int(time.monotonic() - self._strategy_block_start_mono)
                else:
                    eib_secs = 0
                uniques_this_block = max(
                    0, self._lifetime_new_count - self._uniques_at_block_start)
            ret = ['<h2>🤖 Auto-strategy meta-bandit '
                   '<small class="muted">(picks the strategy that captures '
                   'the most unique HS in YOUR environment, '
                   'separately for stationary and moving)</small></h2>']
            ret.append(
                f'<p class="muted">Current block: '
                f'<b>{html.escape(str(current or "—"))}</b> '
                f'@ <b>{html.escape(str(current_mob or "—"))}</b> '
                f'(running {eib_secs}s of {block_unit}, '
                f'{uniques_this_block} unique HS so far). '
                f'Active mobility now: <b>{html.escape(cur_mobility)}</b></p>')

            for mobility in (self.MOBILITY_STATIONARY, self.MOBILITY_MOVING):
                mob_snap = snap.get(mobility, {})
                # Find leader within this mobility
                leaders = []
                for s, d in mob_snap.items():
                    rs = d['rewards']
                    if rs:
                        leaders.append((s, sum(rs)/len(rs), d['n']))
                leaders.sort(key=lambda x: -x[1])
                leader_name = leaders[0][0] if leaders else '—'
                ret.append(
                    f'<h3>📊 {html.escape(mobility.title())} '
                    f'<small class="muted">'
                    f'(leader: {html.escape(leader_name)})</small></h3>'
                    '<table>'
                    '<tr><th>Strategy</th><th>Status</th>'
                    '<th>Blocks evaluated</th>'
                    '<th>Mean reward</th>'
                    '<th>Recent rewards</th></tr>')
                for s in ('adaptive', 'full', 'capped'):
                    d = mob_snap.get(s) or {'n': 0, 'rewards': []}
                    rs = d['rewards']
                    n = d['n']
                    mean = (sum(rs) / len(rs)) if rs else 0.0
                    recent_str = ' '.join(f'{r:.2f}' for r in rs[-8:]) or '—'
                    badges = []
                    if s == current and mobility == current_mob:
                        badges.append('<span class="badge hot">RUNNING</span>')
                    if s == leader_name and n > 0:
                        badges.append('<span class="badge prior">★ LEADER</span>')
                    if n == 0:
                        badges.append('<span class="badge cold">untried</span>')
                    status = ' '.join(badges) or '<span class="muted">queued</span>'
                    ret.append(
                        f'<tr><td><b>{html.escape(s)}</b></td>'
                        f'<td>{status}</td>'
                        f'<td>{n}</td>'
                        f'<td>{mean:.3f}</td>'
                        f'<td><small class="muted">'
                        f'{html.escape(recent_str)}</small></td></tr>')
                ret.append('</table>')
            return ''.join(ret)
        except Exception as e:
            log.debug(f'[envtune] _ui_strategy_bandit: {e}')
            return ''

    def _ui_summary_cards(self, current_zone_alias=None):
        """Big-KPI cards at the top of the dashboard. Each card answers
        one question at a glance — no tables to scan."""
        with self._state_lock:
            uniq_lt   = self._lifetime_new_count
            sess_uniq = len(self._session_hs_bssids)
            sess_dup  = max(0, self.session_handshakes - sess_uniq)
            best_rwd  = self.best_reward
            recent    = self._last_reward_breakdown.copy() if hasattr(
                self, '_last_reward_breakdown') else {}
            # Compute UCB convergence percentage — fraction of cells
            # that have at least 3 real samples (vs just the prior 0.30).
            total = pop = 0
            for states in self.ucb_table.values():
                for arms in states.values():
                    for d in arms.values():
                        total += 1
                        if d.get('n', 0) >= 3:
                            pop += 1
            convergence = (100.0 * pop / total) if total else 0.0
            temp        = self.ema.get('temperature') or 0
            thermal_on  = self._thermal_throttle
            blind_left  = self._blind_recovery
            crash_susp  = self._crash_suspect
            mood        = self._mood
            mobility    = self._current_mobility
            elapsed_s   = max(1, int(time.monotonic() - self.session_start_mono))
            hpm         = self.ema.get('hs_per_min') or 0
            target_hpm  = self._adaptive_hpm_target() or 0
        # Health card classification
        if crash_susp >= 1 or thermal_on or blind_left > 0:
            health_cls = 'bad' if crash_susp >= 2 else 'warn'
            if thermal_on:
                health_msg = f'thermal {temp:.0f}°C'
            elif crash_susp >= 1:
                health_msg = f'nexmon? ({crash_susp})'
            else:
                health_msg = f'blind ({blind_left} ep)'
        elif temp >= self.cfg['temp_warn']:
            health_cls = 'warn'
            health_msg = f'{temp:.0f}°C'
        else:
            health_cls = 'good'
            health_msg = 'all green'
        rate_pct = min(100.0, (hpm / max(target_hpm, 0.01)) * 100.0)
        # Recent reward (sum of breakdown if present, else best)
        recent_r = sum(recent.values()) if recent else None
        recent_s = (f'{recent_r:.3f}' if recent_r is not None else '—')

        sess_h = elapsed_s / 3600.0
        sess_str = (f'{int(sess_h)}h{int((sess_h%1)*60):02d}m'
                    if sess_h >= 1 else f'{int(elapsed_s/60)}m{elapsed_s%60:02d}s')

        cards_html = f'''
        <div class="cards">
          <div class="card">
            <div class="lbl">🎯 Unique Lifetime</div>
            <div class="val">{uniq_lt}</div>
            <div class="sub">{sess_uniq} this session ({sess_dup} dup)</div>
          </div>
          <div class="card info">
            <div class="lbl">⚡ Best Reward</div>
            <div class="val">{self._fmt(best_rwd, '.3f')}</div>
            <div class="sub">last epoch: <b>{recent_s}</b></div>
          </div>
          <div class="card info">
            <div class="lbl">📡 Capture rate</div>
            <div class="val">{hpm:.2f}<small>/min</small></div>
            <div class="sub">target {target_hpm:.2f}
              <div class="bar info" style="width:60%">
                <span style="width:{rate_pct:.0f}%"></span>
              </div>
            </div>
          </div>
          <div class="card info">
            <div class="lbl">🧠 Learning</div>
            <div class="val">{convergence:.0f}<small>%</small></div>
            <div class="sub">cells with ≥3 samples
              <div class="bar info" style="width:60%">
                <span style="width:{convergence:.0f}%"></span>
              </div>
            </div>
          </div>
          <div class="card {health_cls}">
            <div class="lbl">🌡️ Health</div>
            <div class="val">{html.escape(health_msg)}</div>
            <div class="sub">{html.escape(mood)} · {html.escape(mobility)}</div>
          </div>
          <div class="card">
            <div class="lbl">⏱ Session</div>
            <div class="val">{sess_str}</div>
            <div class="sub">{html.escape(current_zone_alias or "no GPS zone")}</div>
          </div>
        </div>
        '''
        return cards_html

    def _ui_bandit_preview(self):
        """'What would the bandit pick if it ran right now?' panel.

        Shows side-by-side: the value pwnagotchi is using NOW vs the arm
        UCB would pick at the current context. Lets you SEE the bandit
        reasoning without waiting for the next epoch.
        """
        try:
            aps_ema = self.ema.get('aps') or 0
            state   = self._compute_state(aps_ema)
        except Exception:
            return ''
        # Get current personality values for comparison
        current_vals = {}
        if self._agent is not None:
            try:
                p = self._agent._config.get('personality', {})
                current_vals = {k: p.get(k) for k in self.UCB_ARMS}
            except Exception:
                pass

        ret  = ('<h2>🔮 Bandit preview '
                '<small class="muted">(what would be picked right now in '
                f'state <b style="color:#ff0">{html.escape(state)}</b>)</small></h2>'
                '<table>')
        ret += ('<tr><th>Param</th><th>Current</th>'
                '<th>Bandit pick</th><th>In sync?</th>'
                '<th>Reason</th></tr>')

        with self._state_lock:
            for param in self.UCB_ARMS:
                if param not in self._active_params:
                    continue
                self._ensure_state(param, state)
        for param in self.UCB_ARMS:
            if param not in self._active_params:
                continue
            try:
                pick = self._ucb_select(param, state)
            except Exception:
                pick = None
            current = current_vals.get(param, '?')
            try:
                # Compare numerically when possible
                in_sync = (float(current) == float(pick))
            except (TypeError, ValueError):
                in_sync = (str(current) == str(pick))
            sync_html = ('<span class="good">✓</span>' if in_sync
                         else '<span class="warn">⚠ pending</span>')
            # Reason: show the picked arm's effective mean / n
            reason = ''
            try:
                tbl = self.ucb_table.get(param, {}).get(state, {})
                d   = tbl.get(pick, {})
                rs  = d.get('rewards', [])
                wn  = len(rs)
                if wn > 0:
                    mu = sum(rs) / wn
                    reason = f'mean {mu:.3f} over n={wn}'
                else:
                    reason = 'no data — exploring'
            except Exception:
                reason = '—'
            ret += (f'<tr><td>{html.escape(param)}</td>'
                    f'<td>{html.escape(str(current))}</td>'
                    f'<td class="good"><b>{html.escape(str(pick))}</b></td>'
                    f'<td>{sync_html}</td>'
                    f'<td><small class="muted">{html.escape(reason)}</small></td>'
                    f'</tr>')
        ret += '</table>'
        return ret

    def _ui_reward_breakdown(self):
        """Show the reward function components from the most-recent epoch.
        Demystifies why the bandit picked what it picked."""
        with self._state_lock:
            bd = dict(self._last_reward_breakdown or {})
        if not bd:
            return ('<h2>🧪 Reward components</h2>'
                    '<p class="muted">Waiting for first scored epoch…</p>')
        total = sum(bd.values())
        # Order: positive contributions desc, then negatives asc
        pos = sorted([(k, v) for k, v in bd.items() if v > 0],
                     key=lambda x: -x[1])
        neg = sorted([(k, v) for k, v in bd.items() if v < 0],
                     key=lambda x: x[1])
        ret = ['<h2>🧪 Reward components <small>(last epoch)</small></h2>',
               '<div class="rwbd">']
        for k, v in pos + neg:
            cls = 'pos' if v >= 0 else 'neg'
            sign = '+' if v >= 0 else ''
            ret.append(f'<div class="cmp {cls}">{html.escape(k)}'
                       f'<span class="v">{sign}{v:.3f}</span></div>')
        ret.append('</div>')
        ret.append(f'<p class="muted">Σ = {total:.3f} '
                   f'<small>(clamped to [0, 1])</small></p>')
        return ''.join(ret)

    def _ui_status(self, current_zone_alias=None):
        elapsed_h = max(0.01,
            (time.monotonic() - self.session_start_mono) / 3600.0)
        lt = int(time.time() - self.last_shake.get('time', time.time()))
        lt_s = f'{lt//60}m{lt%60:02d}s' if lt >= 60 else f'{lt}s'
        temp = self.ema.get('temperature') or 0
        temp_cls = 'bad' if temp >= self.cfg['temp_critical'] else (
            'warn' if temp >= self.cfg['temp_warn'] else 'good')
        # PRIVACY: never render the raw zone key (it's a reversible
        # lat/lon grid index). Show an opaque alias instead.
        zone_display = current_zone_alias if current_zone_alias else (
            'in-zone (locating)' if self._current_zone else 'n/a')

        ret = '<h2>📊 Status</h2><table>'
        rows = [
            ('Plugin version',     f'v{self.__version__}',
             'EnvTune release version'),
            ('CPU profile',        self._profile_name,
             'Performance profile (auto-detected or manual)'),
            ('Channel universe',
             (f'{len(self._user_channels_orig)} channels '
              f'<small class="muted">'
              f'({"2.4 GHz" if all(c < 36 for c in self._user_channels_orig) else "2.4 + 5 GHz"})</small>'
              if self._user_channels_orig else '<span class="muted">unknown</span>'),
             'Channels envtune is allowed to scan, sourced from your '
             'config.toml personality.channels (or iface_channels if empty).'),
            ('Channel strategy',
             (f'<b>{html.escape(self._resolve_channel_strategy())}</b>'),
             'How envtune schedules scanning — adaptive (default), '
             'full, or capped. See changelog for trade-offs.'),
            ('Stability mode',
             ('<span class="good">on (noai-aligned)</span>'
              if self.cfg.get('prefer_stability', True)
              else '<span class="warn">off (aggressive: proactive + overrides)</span>'),
             'When on (default), envtune disables features that add '
             'radio activity beyond pwnagotchi\'s natural loop. Aligns '
             'with the noai branch\'s stability + battery-life goals.'),
            ('Community priors',
             (f'<span class="muted">'
              f'{len(os.listdir(self.COMMUNITY_PRIORS_DIR))} file(s) in '
              f'{self.COMMUNITY_PRIORS_DIR}</span>'
              if os.path.isdir(self.COMMUNITY_PRIORS_DIR)
              else f'<span class="muted">none — drop anon exports into '
                   f'{self.COMMUNITY_PRIORS_DIR}/ to bootstrap learning</span>'),
             'Community-shared anonymised exports merged at startup as '
             'low-weight priors. Optional but speeds cold-start convergence.'),
            ('Epochs observed',    self.epochs_seen,
             'Epochs since plugin started'),
            ('🆕 UNIQUE lifetime',
             f'<span class="good" style="font-size:1.2em">'
             f'{self._lifetime_new_count}</span>',
             'Distinct BSSIDs ever captured. THIS IS THE GOAL.'),
            ('Lifetime handshakes (incl. dups)',
             f'{self.lifetime_handshakes}',
             'Total HS events across all sessions, including duplicates'),
            ('Session duration',   f'{elapsed_h:.2f}h',
             'How long this run has been active'),
            ('Time since last HS', lt_s,
             'Wall-clock time since most recent capture'),
            ('Unique pwns (sess)', len(self._captured_aps),
             'Distinct APs handshaked this session'),
            ('Pre-captured BSSIDs', len(self._captured_bssids),
             'BSSIDs already on disk (deprioritized)'),
            ('Cracked (wpa-sec)',
             (f'{len(self._cracked_bssids)}'
              if self._cracked_bssids
              else (f'<span class="muted">0 (potfile present, no cracks yet)</span>'
                    if os.path.exists(self._wpasec_pot)
                    else f'<span class="muted">not configured</span>')),
             'BSSIDs with known password from wpa-sec potfile. '
             'Optional — if you don\'t use wpa-sec, this stays empty. '
             'No effect on capture rate.'),
            ('Whitelisted',
             f'{len(self._whitelist_macs)} MAC + {len(self._whitelist_ssids)} SSID',
             'Networks excluded from tracking'),
            ('Known APs',          len(self._known_aps),
             'In-memory AP intelligence cache'),
            ('Active channels',    self._active_channels,
             'Channels with currently visible APs'),
            ('GPS source',
             (html.escape(self._gps_source)
              if self._gps_source
              else f'<span class="muted">off (mobility via AP-turnover '
                   f'heuristic)</span>'),
             'How GPS data is being read. Optional — without GPS, mobility '
             'is detected from AP turnover (less precise but still works).'),
            ('Current zone',       zone_display,
             'GPS-derived zone (anonymised — raw key never shown). '
             'Empty if GPS is not configured.'),
            ('Battery',            (f'{self._battery_level:.0f}%'
                                    if self._battery_level
                                    else f'<span class="muted">not detected '
                                         f'(no PiSugar / no UI element)</span>'),
             'PiSugar battery level. Optional — without it, battery-aware '
             'aggression scaling is skipped.'),
            ('EMA APs visible',    self._fmt(self.ema.get('aps'), '.1f'),
             'Smoothed AP count'),
            ('EMA HS rate',        self._fmt(self.ema.get('hs_rate')),
             'Handshakes per attack (smoothed)'),
            ('EMA HS/min',         self._fmt(self.ema.get('hs_per_min')),
             'Handshakes per minute (smoothed)'),
            ('Adaptive HPM target',
             self._fmt(self._adaptive_hpm_target()),
             '90th-percentile of recent unique-HS/min — reward target'),
            ('Reward trend',       self._fmt(self._reward_trend),
             'Direction of recent reward EMA'),
            ('Best custom reward', self._fmt(self.best_reward),
             'All-time best epoch reward'),
            ('Temperature',
             f'<span class="{temp_cls}">{self._fmt(temp, ".1f")}°C</span>',
             'CPU temperature EMA'),
            ('Thermal throttle',
             (f'<span class="bad">ACTIVE</span>'
              if self._thermal_throttle else
              f'<span class="good">off</span>'),
             'Whether attack aggression is reduced for thermal safety'),
            ('Exploration boost',  self._exploration_boost,
             'Epochs left of elevated UCB exploration'),
            ('Stagnation streak',  self._stagnation_count,
             'Consecutive epochs below rolling-median reward'),
            ('Blind recovery',     self._blind_recovery,
             'Epochs left of gradual blind-panic recovery'),
            ('Nexmon crash watch', self._crash_suspect,
             'Suspicion counter for radio firmware crash'),
        ]
        for label, val, tip in rows:
            ret += (f'<tr><td><span title="{html.escape(tip)}">{label}</span></td>'
                    f'<td>{val}</td></tr>')
        ret += '</table>'
        return ret

    def _ui_current_params(self):
        # Defensive: agent or its config may be missing during early boot
        # or if a fork relocates personality data.
        try:
            p = (self._agent._config or {}).get('personality', {}) or {}
        except Exception:
            p = {}
        ret = '<h2>🎛️ Current Personality Parameters</h2><table>'
        ret += ('<tr><th>Parameter</th><th>Current</th>'
                '<th>Bounds</th><th>Status</th></tr>')
        for param, (lo, hi) in self.BOUNDS.items():
            tuned    = param in self._active_params
            cls      = '' if tuned else 'na'
            status   = ('<span class="good">tuning</span>' if tuned
                        else '<span class="na">not in fork</span>')
            sync_tag = ' 🔄' if param in self.BETTERCAP_SYNC_MAP else ''
            cur_val  = p.get(param, '?') if isinstance(p, dict) else '?'
            ret += (f'<tr class="{cls}"><td>{html.escape(param)}{sync_tag}</td>'
                    f'<td><b>{html.escape(str(cur_val))}</b></td>'
                    f'<td>[{lo},{hi}]</td><td>{status}</td></tr>')
        ret += '<tr><td colspan=4><small>🔄 = synced to bettercap '
        ret += 'in realtime via "set wifi.* N"</small></td></tr>'
        ret += '</table>'
        return ret

    def _ui_ucb_summary(self):
        aps_ema = self.ema.get('aps') or 0
        state   = self._compute_state(aps_ema)
        # Annealed shrinkage k is informative for the UI: shows whether
        # the bandit is still in cold-start mode or trusting local data.
        try:
            cur_k = self._current_shrinkage_k()
        except Exception:
            cur_k = self.cfg.get('ucb_shrinkage_k_max', 5.0)
        ret  = (f'<h2>🧠 UCB Learning — current state: '
                f'<b style="color:#ff0">{html.escape(str(state))}</b> '
                f'<small class="muted">shrinkage k={cur_k:.2f}</small></h2><table>')
        ret += ('<tr><th>Param</th><th>Best arm</th>'
                '<th>Mean rwd</th><th>n</th>'
                '<th style="width:25%">Convergence</th>'
                '<th>All arms (n:mean)</th></tr>')
        # Snapshot the per-state UCB tables under lock so concurrent updates
        # don't mutate dicts mid-iteration.
        with self._state_lock:
            for param in list(self.UCB_ARMS.keys()):
                if param in self._active_params:
                    self._ensure_state(param, state)
            snap = {}
            for param, arms in self.UCB_ARMS.items():
                if param not in self._active_params:
                    continue
                tbl_state = self.ucb_table.get(param, {}).get(state, {})
                snap[param] = {
                    arm: list(tbl_state.get(arm, {}).get('rewards', []))
                    for arm in arms
                }
        for param, arms in self.UCB_ARMS.items():
            if param not in snap:
                continue
            arm_snap  = snap[param]
            best_arm  = None
            best_mean = -1.0
            best_wn   = 0
            parts     = []
            tot_n     = 0
            starved_promising = []   # (arm, n, mean) — n<5 but mean>=0.30
            starvation_n = int(self.cfg.get('forced_explore_starvation_n', 5))
            for arm in arms:
                rewards = arm_snap.get(arm, [])
                wn      = len(rewards)
                tot_n  += wn
                mean    = (sum(rewards) / wn) if wn > 0 else 0.0
                # Mark cells that are still on the seeded NEUTRAL prior
                # (n=1, single PRIOR_NEUTRAL_R sample) — UCB hasn't
                # really learned this arm yet.
                is_prior = (wn == 1 and abs(mean - self.PRIOR_NEUTRAL_R) < 1e-6)
                # v1.7: starved-but-promising arm — small n but mean
                # above the neutral prior. Flagged so operators can see
                # where forced-exploration is concentrating.
                is_starved_good = (1 <= wn < starvation_n
                                   and mean >= self.PRIOR_NEUTRAL_R
                                   and not is_prior)
                if is_prior:
                    badge = (' <span class="badge prior" '
                             'title="seeded prior — no real data yet">P</span>')
                elif is_starved_good:
                    badge = (' <span class="badge cold" '
                             'title="under-explored but promising — '
                             'forced-exploration will target this">★</span>')
                    starved_promising.append((arm, wn, mean))
                else:
                    badge = ''
                parts.append(f'{arm}({wn}:{mean:.2f}){badge}')
                if wn > 0 and mean > best_mean:
                    best_mean, best_arm, best_wn = mean, arm, wn

            # Convergence visual: progress bar of the BEST arm's local
            # mean vs theoretical max 1.0; tinted by sample count.
            #   < 3 samples → cold (info color)
            #   3-9         → warming (warn)
            #   10+         → hot (good)
            if best_arm is not None and best_wn >= 1:
                pct = max(0.0, min(1.0, best_mean)) * 100.0
                if best_wn >= 10:
                    bcls, badge = 'good', '<span class="badge hot">hot</span>'
                elif best_wn >= 3:
                    bcls, badge = 'warn', '<span class="badge cold">warming</span>'
                else:
                    bcls, badge = 'info', '<span class="badge cold">cold</span>'
                bar_html = (f'<div class="bar {bcls}" '
                            f'style="width:100%"><span style="width:{pct:.0f}%">'
                            f'</span></div> {badge}')
                ret += (f'<tr><td>{html.escape(param)}</td>'
                        f'<td class="good"><b>{html.escape(str(best_arm))}</b></td>'
                        f'<td>{best_mean:.3f}</td><td>{best_wn}</td>'
                        f'<td>{bar_html}</td>'
                        f'<td><small>{" ".join(parts)}</small></td></tr>')
            else:
                ret += (f'<tr><td>{html.escape(param)}</td>'
                        f'<td colspan=3 class="na">exploring…</td>'
                        f'<td><span class="badge cold">no data</span></td>'
                        f'<td><small>{" ".join(parts)}</small></td></tr>')
        ret += '</table>'
        return ret

    def _ui_channels(self):
        # FIX: snapshot under lock — UI reads concurrently with event handlers.
        with self._state_lock:
            ch_lt_snap = {c: dict(v) for c, v in self._ch_lt.items()}
            dead_lt_snap = dict(self._dead_lt)
            dead_session_snap = dict(self._dead_session)
            free_chs = set(self._free_channels)
        chs = sorted(ch_lt_snap.keys(),
                     key=lambda c: -ch_lt_snap[c]['hs'])[:25]
        # Compute the global max HS so the sparkline bars are scaled
        # against the most-productive channel rather than absolute units.
        max_hs = max((ch_lt_snap[c].get('hs', 0) for c in chs), default=0)
        max_hs = max(1, max_hs)
        # Note: 'Dead' column uses _dead_session (responsive — counts
        # epochs the channel has been absent in this session) rather
        # than _dead_lt (which only increments after 20+ epochs of
        # absence and looks "always 0" to short-session users).
        ret  = ('<h2>📡 Channel Productivity '
                '<small class="muted">(lifetime stats, sparklines = HS share)</small>'
                '</h2><table>')
        ret += ('<tr><th>Ch</th><th>HS</th><th>HS share</th>'
                '<th>Passive</th>'
                '<th>Assocs</th><th>Deauths</th><th>Clients</th>'
                '<th>Visits</th><th>Eff</th><th>Wasted</th>'
                '<th>Free</th><th>Dead<small>(sess/lt)</small></th>'
                '<th>Score</th></tr>')
        for ch in chs:
            d   = ch_lt_snap[ch]
            sc  = self._ch_score(ch)
            nol = '🔵' if ch in self.NON_OVERLAPPING else ''
            fr  = '✨' if ch in free_chs else ''
            hs  = d.get('hs', 0)
            attempts = (d.get('assocs', 0) or 0) + (d.get('deauths', 0) or 0)
            eff = (hs / attempts) if attempts else 0
            eff_cls = ('good' if eff >= 0.10 else
                       ('warn' if eff >= 0.03 else
                        ('bad' if attempts >= 20 else 'muted')))
            # Sparkline: percentage of max-channel HS, displayed as a
            # tiny inline bar. ≥80% of max → green, ≥30% → cyan, else dim.
            pct = 100.0 * hs / max_hs
            spark_cls = ('good' if pct >= 80 else
                         ('info' if pct >= 30 else 'na'))
            spark = (f'<div class="bar" style="width:80px"><span '
                     f'class="" style="width:{pct:.0f}%;'
                     f'background:{"#00ff88" if spark_cls=="good" else ("#00ccff" if spark_cls=="info" else "#444")}">'
                     f'</span></div>')
            sess_dead = dead_session_snap.get(ch, 0)
            lt_dead   = dead_lt_snap.get(ch, 0)
            ret += (f'<tr><td>{ch}{nol}{fr}</td>'
                    f'<td class="good"><b>{hs}</b></td>'
                    f'<td>{spark}</td>'
                    f'<td>{d.get("passive_hs", 0)}</td>'
                    f'<td>{d.get("assocs", 0)}</td>'
                    f'<td>{d.get("deauths", 0)}</td>'
                    f'<td>{d.get("clients", 0)}</td>'
                    f'<td>{d.get("visits", 0)}</td>'
                    f'<td class="{eff_cls}">{eff*100:.1f}%</td>'
                    f'<td class="{"bad" if d.get("wasted",0) > 10 else "warn"}">'
                    f'{d.get("wasted", 0)}</td>'
                    f'<td>{d.get("free_seen", 0)}</td>'
                    f'<td><small>'
                    f'<span class="{"warn" if sess_dead > 0 else "muted"}">{sess_dead}</span>'
                    f'/<span class="bad">{lt_dead}</span>'
                    f'</small></td>'
                    f'<td>{sc:.2f}</td></tr>')
        ret += ('<tr><td colspan=13><small>'
                '🔵 = non-overlapping (1/6/11 on 2.4GHz) · '
                '✨ = bettercap reported free this session · '
                'Dead = (session epochs absent / lifetime epochs absent)'
                '</small></td></tr>')
        ret += '</table>'
        return ret

    def _ui_top_aps(self, request=None):
        """AP Intelligence with filter-by-flag support via ?ap_filter=...

        Filters (all optional, set via dashboard URL or ?ap_filter):
          - all          : show everything (default)
          - uncaptured   : only APs we haven't captured yet
          - clients      : only APs with at least one fresh client
          - strong       : only APs with RSSI >= -70
          - captured     : only APs we've captured (recapture targets)
          - pmf          : only PMF-protected APs
        """
        # Parse the filter once. Defaults to 'all' if not specified or
        # if request is unavailable.
        sel = 'all'
        if request is not None:
            try:
                arg = request.args.get('ap_filter', '') or 'all'
                if arg in ('all', 'uncaptured', 'clients',
                           'strong', 'captured', 'pmf'):
                    sel = arg
            except Exception:
                pass

        # Filter buttons: link back to the dashboard with ?ap_filter=X.
        # Using the GET param keeps the bandit/state untouched.
        base = self._plugin_base()
        filters = [
            ('all',         '🌐 All'),
            ('uncaptured',  '🆕 Uncaptured'),
            ('clients',     '👥 With clients'),
            ('strong',      '📶 Strong (≥-70)'),
            ('captured',    '✓ Captured'),
            ('pmf',         '🔒 PMF'),
        ]
        bar_html = '<div class="filterbar">'
        for key, label in filters:
            cls = 'fbtn active' if key == sel else 'fbtn'
            bar_html += (f'<a class="{cls}" '
                         f'href="{base}?ap_filter={key}">{label}</a>')
        bar_html += '</div>'

        # Heading shows current filter.
        sel_label = next((l for k, l in filters if k == sel), 'All')
        ret  = f'<h2>🎯 AP Intelligence <small class="muted">({sel_label})</small></h2>'
        ret += bar_html
        ret += '<table>'
        ret += ('<tr><th>SSID</th><th>BSSID</th><th>OUI</th><th>Ch</th>'
                '<th>RSSI</th><th>Trend</th><th>Clients</th>'
                '<th>HS</th><th>Attacks</th><th>Eff.</th>'
                '<th>Cooldown</th><th>Flags</th></tr>')
        # Snapshot under lock so we don't iterate a dict another thread is
        # mutating (handshake handler / on_wifi_update). Shallow-copy each
        # AP record because helpers below access its fields after release.
        with self._state_lock:
            ap_snap = [(k, dict(v)) for k, v in self._known_aps.items()]
            ep      = self.epochs_seen

        # Apply filter
        def _keep(apID, ap):
            captured = bool(ap.get('AT_already_captured'))
            clients  = ap.get('AT_clients', 0) or 0
            recency  = ep - (ap.get('AT_client_epoch', -99) or -99)
            fresh    = clients > 0 and recency <= int(self.cfg['client_recency_epochs'])
            try:
                rssi = float(ap.get('rssi', -100) or -100)
            except (TypeError, ValueError):
                rssi = -100
            pmf = bool(ap.get('AT_pmf_detected'))
            if sel == 'uncaptured':
                return not captured
            if sel == 'clients':
                return fresh
            if sel == 'strong':
                return rssi >= -70
            if sel == 'captured':
                return captured
            if sel == 'pmf':
                return pmf
            return True

        sorted_aps = sorted(
            (x for x in ap_snap if _keep(*x)),
            key=lambda x: (-x[1].get('AT_handshake', 0),
                           -self._ap_priority_score(x[0]))
        )[:50]

        if not sorted_aps:
            ret += ('<tr><td colspan=12 class="muted" '
                    'style="text-align:center;padding:14px">'
                    'No APs match this filter.</td></tr>')

        for apID, ap in sorted_aps:
            eff     = ap.get('AT_efficiency', 0.0)
            eff_cls = ('good' if eff >= 0.1 else
                      ('warn' if eff > 0 else 'bad'))
            trend   = self._rssi_trend(apID)
            t_str   = (f'<span class="good">▲{trend:+.1f}</span>' if trend > 1
                       else (f'<span class="bad">▼{trend:+.1f}</span>'
                             if trend < -1 else '—'))
            cd_left = max(0, ap.get('AT_cooldown_until', 0) - ep)
            ncl     = ap.get('AT_clients', 0)
            flags   = []
            if ap.get('AT_pmf_detected'):     flags.append('PMF')
            if ap.get('AT_already_captured'): flags.append('✓Cap')
            if ap.get('AT_cracked'):          flags.append('🔓')
            host    = html.escape(str(ap.get('hostname', '?'))[:24])
            mac_raw = str(ap.get('mac', '?'))
            mac     = html.escape(mac_raw)
            chan    = html.escape(str(ap.get('channel', '?')))
            rssi    = html.escape(str(ap.get('rssi', '?')))
            # OUI (first 3 octets) → clickable lookup. Wireshark's
            # public OUI database is the standard reference.
            oui_clean = mac_raw.replace(':', '').replace('-', '')[:6].upper()
            if len(oui_clean) == 6:
                oui_link = (
                    f'<a href="https://www.wireshark.org/tools/oui-lookup.html'
                    f'?oui={oui_clean}" target="_blank" rel="noopener" '
                    f'class="muted" title="Vendor lookup (opens new tab)">'
                    f'{oui_clean[:2]}:{oui_clean[2:4]}:{oui_clean[4:]}</a>')
            else:
                oui_link = '<span class="muted">—</span>'
            ret += (f'<tr>'
                    f'<td>{host}</td>'
                    f'<td><small>{mac}</small></td>'
                    f'<td><small>{oui_link}</small></td>'
                    f'<td>{chan}</td>'
                    f'<td>{rssi}</td>'
                    f'<td>{t_str}</td>'
                    f'<td>{"🧑" * min(ncl, 5)}{ncl}</td>'
                    f'<td class="good"><b>{ap.get("AT_handshake", 0)}</b></td>'
                    f'<td>{ap.get("AT_attacks", 0)}</td>'
                    f'<td class="{eff_cls}">{eff:.2f}</td>'
                    f'<td>{"⏸ " + str(cd_left) + "ep" if cd_left > 0 else ""}</td>'
                    f'<td>{html.escape(" ".join(flags))}</td>'
                    f'</tr>')
        ret += '</table>'
        return ret

    @staticmethod
    def _zone_label(idx):
        """Human-friendly opaque label: A,B,…,Z,AA,AB,…
        Hides reversible lat/lon while keeping rows distinguishable."""
        if idx < 26:
            return f'Zone {chr(65 + idx)}'
        a = (idx // 26) - 1
        b = idx % 26
        return f'Zone {chr(65 + a)}{chr(65 + b)}'

    def _build_zone_alias_map(self):
        """Map raw zone keys → stable aliases for THIS render.

        Sort by HS desc so the most-productive zone is always 'Zone A'.
        The mapping is rebuilt each request (no cache) — that's fine for
        the UI, where a few-millisecond rebuild is negligible.

        Returns the alias dict AND the current-zone alias string so
        callers don't have to look it up twice.
        """
        with self._state_lock:
            ranked = sorted(
                self._gps_zones.items(),
                key=lambda kv: -(kv[1].get('hs', 0) or 0))
            aliases = {zk: self._zone_label(i) for i, (zk, _) in enumerate(ranked)}
            cur     = aliases.get(self._current_zone) if self._current_zone else None
        return aliases, cur

    def _ui_gps_zones(self, aliases=None):
        """Render the GPS Zone Productivity table with anonymised labels.

        Raw lat/lon-reversible zone keys never enter the rendered HTML.
        If you need the raw key for debugging, look at
        `/plugins/envtune/zones?full=1` from the device itself.
        """
        ret  = '<h2>🗺️ GPS Zone Productivity</h2><table>'
        ret += ('<tr><th>Zone</th><th>HS</th><th>Attacks</th>'
                '<th>Visits</th><th>Top channels</th><th>Last seen</th></tr>')
        # Deep-snapshot zones under lock so per-zone channel dicts are stable.
        with self._state_lock:
            zones_snap = [
                (zk, {
                    'hs': z.get('hs', 0),
                    'attacks': z.get('attacks', 0),
                    'visits': z.get('visits', 0),
                    'last_seen': z.get('last_seen', 0),
                    'channels': dict(z.get('channels', {})),
                })
                for zk, z in self._gps_zones.items()
            ]
        zones = sorted(zones_snap, key=lambda kv: -kv[1]['hs'])[:30]
        if aliases is None:
            aliases = {zk: self._zone_label(i)
                       for i, (zk, _) in enumerate(zones)}
        now = time.time()
        for zk, zd in zones:
            top = sorted(zd['channels'].items(),
                         key=lambda x: -x[1])[:3]
            top_s = ', '.join(f'{c}:{n}' for c, n in top) or '—'
            ago = ''
            if zd.get('last_seen', 0):
                secs = int(now - zd['last_seen'])
                ago = (f'{secs//3600}h{(secs%3600)//60}m ago'
                       if secs > 3600 else f'{secs//60}m ago')
            label = aliases.get(zk, self._zone_label(0))
            ret += (f'<tr><td>{html.escape(label)}</td>'
                    f'<td class="good"><b>{zd["hs"]}</b></td>'
                    f'<td>{zd["attacks"]}</td>'
                    f'<td>{zd["visits"]}</td>'
                    f'<td>{html.escape(top_s)}</td>'
                    f'<td><small>{html.escape(ago)}</small></td></tr>')
        ret += '</table>'
        return ret

    # ── Endpoints ─────────────────────────────────────────────────────────

    @staticmethod
    def _anonymise_export(data):
        """Strip location PII from a state-snapshot dict.

        Replaces:
          - gps_zones keys (raw lat_idx:lon_idx, ~150m reversible)
            → opaque tags `zone_001`, `zone_002`, … (sorted by HS desc
            so the order is informative).
          - per-zone `last_seen` (unix timestamp)
            → `days_ago` float, rounded to 0.1 day.

        v1.8.1 — strips:
          - captured_bssids: list of AP MAC addresses you've captured.
            Privacy risk because BSSIDs are publicly geolocatable via
            WiGLE (https://wigle.net), so sharing your captured set
            reveals approximate locations you've been. Useless to other
            users anyway (their environment has different APs).
          - cracked_bssids: same as above, plus reveals which APs you
            have the password for — sensitive info.
          - ema.speed: GPS-derived speed; reveals mobility patterns.
            Replaced with redacted marker if non-null.

        Preserves: hs / attacks / visits / channels per zone — the parts
        that are actually useful when shared as community priors.
        Preserves: ucb_table — the parameter learning, no location data.

        Operates on a deep-ish copy so the live snapshot isn't mutated.
        """
        out = copy.deepcopy(data)

        # Strip BSSID lists — they geolocate via WiGLE
        out['captured_bssids'] = []
        out['cracked_bssids']  = []
        # Replace with counts so the receiver knows roughly how seasoned
        # the contributing operator is, without leaking individual MACs.
        cap_n = len(data.get('captured_bssids') or [])
        crk_n = len(data.get('cracked_bssids')  or [])
        out['_captured_count'] = cap_n
        out['_cracked_count']  = crk_n

        # Redact GPS-derived speed if present
        ema = out.get('ema') or {}
        if ema.get('speed') is not None:
            ema['speed'] = None
            out['ema'] = ema

        # GPS zones: anonymise keys + last_seen
        zones_in = data.get('gps_zones') or {}
        if zones_in:
            ranked = sorted(
                zones_in.items(),
                key=lambda kv: -(kv[1].get('hs', 0) or 0))
            now = time.time()
            anon = {}
            for idx, (_real_key, zd) in enumerate(ranked, start=1):
                ls = _sf(zd.get('last_seen', 0)) or 0.0
                days_ago = round(max(0.0, (now - ls) / 86400.0), 1) if ls else None
                zd_anon = dict(zd)
                zd_anon.pop('last_seen', None)
                zd_anon['days_ago'] = days_ago
                anon[f'zone_{idx:03d}'] = zd_anon
            out['gps_zones'] = anon

        out['_export_mode'] = 'anonymised'
        return out

    def _endpoint_export(self, request=None):
        """State JSON for backup or community-prior sharing.

        DEFAULT (`/export`): GPS zone keys are anonymised to `zone_001`,
        `zone_002` … and per-zone `last_seen` becomes a relative
        `days_ago` float. The reason is concrete: raw zone keys like
        `38472:1921` are reversible to lat/lon at ~150 m precision
        (decoded in real telemetry to a Naaldwijk address), so a user
        innocently sharing their export would be doxxing themselves.
        Channel histograms per zone — the actually-useful part for
        community priors — are preserved.

        FULL (`/export?full=1`): unchanged raw state, including raw zone
        keys. Use this for your own backup; do NOT share it publicly.

        v2.0 (R-01): serves a CACHED snapshot (refreshed by the save
        worker thread). Stale by at most save_every_n epochs (~1-5 min).
        Operators wanting freshness can hit POST /force-save first.
        """
        try:
            # Use the cached snapshot if available; only build fresh on
            # cold-start before any save has fired.
            data = self._cached_snapshot
            if data is None:
                data = self._build_state_snapshot()
            else:
                # The cache is shared with the save worker — operate
                # on a copy so anonymisation can't mutate it.
                data = copy.deepcopy(data)

            # Detect the optional ?full=1 escape hatch. Default = anon.
            want_full = False
            if request is not None:
                try:
                    arg = request.args.get('full', '')
                    want_full = (arg in ('1', 'true', 'yes', 'on'))
                except Exception:
                    want_full = False

            if not want_full:
                data = self._anonymise_export(data)

            resp = make_response(json.dumps(data, indent=2, default=str), 200)
            resp.headers['Content-Type'] = 'application/json; charset=utf-8'
            resp.headers['Cache-Control'] = 'no-store'
            # Make it explicit in the response which mode we used.
            resp.headers['X-Envtune-Export-Mode'] = (
                'full' if want_full else 'anonymised')
            return resp
        except Exception as e:
            resp = make_response(f'Error: {html.escape(str(e))}', 500)
            resp.headers['Content-Type'] = 'text/plain; charset=utf-8'
            return resp

    def _endpoint_metrics(self):
        """Prometheus-compatible metrics — snapshot under lock, no iteration."""
        try:
            with self._state_lock:
                lifetime_hs   = self.lifetime_handshakes
                lifetime_uniq = self._lifetime_new_count
                # Session counts: total handshakes captured this session
                # (incl. duplicates) vs unique BSSIDs this session.
                sess_total    = self.session_handshakes
                sess_uniq     = len(self._session_hs_bssids)
                sess_dups     = max(0, sess_total - sess_uniq)
                pre_cap       = len(self._captured_bssids)
                cracked       = len(self._cracked_bssids)
                known_aps     = len(self._known_aps)
                gps_zones     = len(self._gps_zones)
                free_ch       = len(self._free_channels)
                active_ch     = self._active_channels
                stagnation    = self._stagnation_count
                blind_rec     = self._blind_recovery
                explor_boost  = self._exploration_boost
                crash_susp    = self._crash_suspect
                thermal       = 1 if self._thermal_throttle else 0
                temp_ema      = self.ema.get('temperature') or 0
                hpm           = self.ema.get('hs_per_min') or 0
                aps_ema       = self.ema.get('aps') or 0
                hs_rate       = self.ema.get('hs_rate') or 0
                target_hpm    = self._adaptive_hpm_target() or 0
                trend         = self._reward_trend or 0
                best_rwd      = self.best_reward
                epochs_seen   = self.epochs_seen
                session_mono  = self.session_start_mono
                whitelist     = len(self._whitelist_macs) + len(self._whitelist_ssids)
                save_q        = self._save_queue.qsize() if hasattr(self, '_save_queue') else 0
                # v2.0 (F-07, P-11): strategy bandit + error counters
                strat_snap = {
                    mob: {
                        s: {'n': d['n'],
                            'mean': (sum(d['rewards']) / len(d['rewards']))
                                     if d['rewards'] else 0.0}
                        for s, d in mob_bandit.items()
                    }
                    for mob, mob_bandit in self._strategy_bandit.items()
                }
                strat_cur = self._strategy_current or 'none'
                strat_mob = self._strategy_block_mobility or 'none'
                cur_block_uniques = max(
                    0, self._lifetime_new_count - self._uniques_at_block_start)
                error_snap = dict(self._error_counts)
            uptime_s = max(0.0, time.monotonic() - session_mono)
            lines = [
                '# HELP envtune_lifetime_handshakes Total HS captured ever (incl dups)',
                '# TYPE envtune_lifetime_handshakes counter',
                f'envtune_lifetime_handshakes {lifetime_hs}',
                '# HELP envtune_unique_lifetime_bssids Distinct BSSIDs ever captured (THE GOAL)',
                '# TYPE envtune_unique_lifetime_bssids counter',
                f'envtune_unique_lifetime_bssids {lifetime_uniq}',
                '# HELP envtune_session_unique Distinct BSSIDs captured this session',
                '# TYPE envtune_session_unique gauge',
                f'envtune_session_unique {sess_uniq}',
                '# HELP envtune_session_duplicates Duplicate handshakes this session',
                '# TYPE envtune_session_duplicates gauge',
                f'envtune_session_duplicates {sess_dups}',
                '# HELP envtune_precaptured_bssids Pre-captured BSSIDs from .pcap files',
                '# TYPE envtune_precaptured_bssids gauge',
                f'envtune_precaptured_bssids {pre_cap}',
                '# HELP envtune_cracked_bssids BSSIDs known cracked via wpa-sec potfile',
                '# TYPE envtune_cracked_bssids gauge',
                f'envtune_cracked_bssids {cracked}',
                '# HELP envtune_whitelisted Networks excluded from tracking',
                '# TYPE envtune_whitelisted gauge',
                f'envtune_whitelisted {whitelist}',
                '# HELP envtune_known_aps APs tracked in memory',
                '# TYPE envtune_known_aps gauge',
                f'envtune_known_aps {known_aps}',
                '# HELP envtune_active_channels Channels with currently visible APs',
                '# TYPE envtune_active_channels gauge',
                f'envtune_active_channels {active_ch}',
                '# HELP envtune_free_channels Channels recently reported as free',
                '# TYPE envtune_free_channels gauge',
                f'envtune_free_channels {free_ch}',
                '# HELP envtune_temperature_celsius CPU temperature EMA',
                '# TYPE envtune_temperature_celsius gauge',
                f'envtune_temperature_celsius {temp_ema}',
                '# HELP envtune_hs_per_min Smoothed handshakes per minute',
                '# TYPE envtune_hs_per_min gauge',
                f'envtune_hs_per_min {hpm}',
                '# HELP envtune_target_hpm Adaptive HPM target (90th percentile)',
                '# TYPE envtune_target_hpm gauge',
                f'envtune_target_hpm {target_hpm}',
                '# HELP envtune_aps_visible_ema Smoothed visible-AP count',
                '# TYPE envtune_aps_visible_ema gauge',
                f'envtune_aps_visible_ema {aps_ema}',
                '# HELP envtune_hs_per_attack Smoothed handshakes per attack',
                '# TYPE envtune_hs_per_attack gauge',
                f'envtune_hs_per_attack {hs_rate}',
                '# HELP envtune_reward_trend Direction of recent reward EMA',
                '# TYPE envtune_reward_trend gauge',
                f'envtune_reward_trend {trend}',
                '# HELP envtune_best_reward All-time best epoch reward',
                '# TYPE envtune_best_reward gauge',
                f'envtune_best_reward {best_rwd}',
                '# HELP envtune_epochs_seen Epochs since plugin started',
                '# TYPE envtune_epochs_seen counter',
                f'envtune_epochs_seen {epochs_seen}',
                '# HELP envtune_thermal_throttle 1 if thermal throttle active',
                '# TYPE envtune_thermal_throttle gauge',
                f'envtune_thermal_throttle {thermal}',
                '# HELP envtune_stagnation_streak Consecutive sub-median epochs',
                '# TYPE envtune_stagnation_streak gauge',
                f'envtune_stagnation_streak {stagnation}',
                '# HELP envtune_blind_recovery_left Epochs left of blind-panic recovery',
                '# TYPE envtune_blind_recovery_left gauge',
                f'envtune_blind_recovery_left {blind_rec}',
                '# HELP envtune_exploration_boost_left Epochs left of elevated UCB exploration',
                '# TYPE envtune_exploration_boost_left gauge',
                f'envtune_exploration_boost_left {explor_boost}',
                '# HELP envtune_crash_suspect Suspected nexmon crash counter',
                '# TYPE envtune_crash_suspect gauge',
                f'envtune_crash_suspect {crash_susp}',
                '# HELP envtune_gps_zones Distinct GPS zones learned',
                '# TYPE envtune_gps_zones gauge',
                f'envtune_gps_zones {gps_zones}',
                '# HELP envtune_save_queue_depth Pending state-save tasks',
                '# TYPE envtune_save_queue_depth gauge',
                f'envtune_save_queue_depth {save_q}',
                '# HELP envtune_uptime_seconds Session uptime',
                '# TYPE envtune_uptime_seconds counter',
                f'envtune_uptime_seconds {uptime_s:.1f}',
            ]
            # v2.0 (F-07): strategy bandit metrics — per (mobility, strategy)
            lines.append('# HELP envtune_strategy_blocks Blocks evaluated for (mobility,strategy)')
            lines.append('# TYPE envtune_strategy_blocks counter')
            lines.append('# HELP envtune_strategy_mean_reward Mean reward over recent blocks for (mobility,strategy)')
            lines.append('# TYPE envtune_strategy_mean_reward gauge')
            for mob, mob_d in strat_snap.items():
                for s, vals in mob_d.items():
                    lab = f'{{mobility="{mob}",strategy="{s}"}}'
                    lines.append(f'envtune_strategy_blocks{lab} {vals["n"]}')
                    lines.append(f'envtune_strategy_mean_reward{lab} {vals["mean"]:.4f}')
            lines.append('# HELP envtune_strategy_current_block_uniques Unique HS captured so far in the in-progress strategy block')
            lines.append('# TYPE envtune_strategy_current_block_uniques gauge')
            lines.append(f'envtune_strategy_current_block_uniques {cur_block_uniques}')
            lines.append('# HELP envtune_strategy_active_strategy Strategy currently running (label only)')
            lines.append('# TYPE envtune_strategy_active_strategy gauge')
            lines.append(f'envtune_strategy_active_strategy{{strategy="{strat_cur}",mobility="{strat_mob}"}} 1')
            # v2.0 (P-11): exception counter — operators can detect if a
            # specific handler is consistently failing.
            lines.append('# HELP envtune_exception_count Exceptions caught per handler (cumulative this session)')
            lines.append('# TYPE envtune_exception_count counter')
            for handler, cnt in sorted(error_snap.items()):
                lines.append(f'envtune_exception_count{{handler="{handler}"}} {cnt}')
            resp = make_response('\n'.join(lines) + '\n', 200)
            resp.headers['Content-Type'] = 'text/plain; version=0.0.4; charset=utf-8'
            resp.headers['Cache-Control'] = 'no-store'
            return resp
        except Exception as e:
            resp = make_response(f'Error: {html.escape(str(e))}', 500)
            resp.headers['Content-Type'] = 'text/plain; charset=utf-8'
            return resp

    def _endpoint_zones(self, request=None):
        """GPS zones JSON.

        Anonymised by default (matches /export semantics). Add `?full=1`
        for raw zone keys + timestamps. Channel histograms are always
        included — those are the useful, non-PII bits.
        """
        try:
            want_full = False
            if request is not None:
                try:
                    arg = request.args.get('full', '')
                    want_full = (arg in ('1', 'true', 'yes', 'on'))
                except Exception:
                    want_full = False
            with self._state_lock:
                raw = {
                    zk: {
                        'hs': z.get('hs', 0),
                        'attacks': z.get('attacks', 0),
                        'visits': z.get('visits', 0),
                        'last_seen': z.get('last_seen', 0),
                        'channels': dict(z.get('channels', {})),
                    }
                    for zk, z in self._gps_zones.items()
                }
            if want_full:
                data = raw
            else:
                # Reuse the same anonimiser as /export for consistency.
                data = self._anonymise_export({'gps_zones': raw})['gps_zones']
            resp = make_response(json.dumps(data, indent=2, default=str), 200)
            resp.headers['Content-Type'] = 'application/json; charset=utf-8'
            resp.headers['Cache-Control'] = 'no-store'
            resp.headers['X-Envtune-Export-Mode'] = (
                'full' if want_full else 'anonymised')
            return resp
        except Exception as e:
            resp = make_response(f'Error: {html.escape(str(e))}', 500)
            resp.headers['Content-Type'] = 'text/plain; charset=utf-8'
            return resp

    # ── Actions panel & POST handlers ─────────────────────────────────────

    # Forms use Flask-WTF's csrf_token() helper via render_template_string
    # so pwnagotchi's CSRFProtect middleware accepts the POST. The token
    # name is the Flask-WTF default ("csrf_token"), NOT a custom field.
    _ACTIONS_TEMPLATE = '''
    <h2>🛠 Actions</h2>
    <div class="actbar">
      {% for a in actions %}
        <form method="POST" action="{{ base }}{{ a.path }}"
              style="display:inline-block;margin:2px 6px 2px 0">
          <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
          <button type="submit" class="actbtn {{ a.cls }}"
                  title="{{ a.hint }}">{{ a.label }}</button>
        </form>
      {% endfor %}
    </div>
    {% if log_items %}
      <ul class="actionlog">
      {% for ts, name, ok, msg in log_items %}
        <li><span class="{{ 'good' if ok else 'bad' }}">{{ ts }}</span>
            <b>{{ name }}</b> — {{ msg }}</li>
      {% endfor %}
      </ul>
    {% endif %}
    '''

    _ACTIONS = [
        {'path': 'force-save',       'label': '💾 Force save',
         'hint': 'Flush plugin state JSON to disk now',
         'cls':  'good'},
        {'path': 'rescan-potfile',   'label': '🔓 Rescan wpa-sec',
         'hint': 'Re-read /root/handshakes/wpa-sec.cracked.potfile',
         'cls':  'good'},
        {'path': 'reset-stagnation', 'label': '🔄 Reset stagnation',
         'hint': 'Clear stagnation streak & decision buffer; re-explore',
         'cls':  'warn'},
        {'path': 'reload-whitelist', 'label': '⛔ Reload whitelist',
         'hint': 'Reload main.whitelist + handshake list from config',
         'cls':  'warn'},
        {'path': 'clear-blind',      'label': '👁 Clear blind-panic',
         'hint': 'Drop blind-recovery counter to zero',
         'cls':  'warn'},
    ]

    def _ui_actions(self):
        """HTML form panel for operator-driven actions. CSRF tokens come
        from Flask-WTF's csrf_token() helper, which pwnagotchi's
        webserver wraps via CSRFProtect — using a custom token would be
        rejected by the middleware before reaching _handle_post."""
        with self._state_lock:
            log_raw = list(self._action_log)[-8:][::-1]
        log_items = [
            (time.strftime('%H:%M:%S', time.localtime(ts)),
             name, ok, msg)
            for ts, name, ok, msg in log_raw
        ]
        return render_template_string(
            self._ACTIONS_TEMPLATE,
            base=self._plugin_base(),
            actions=self._ACTIONS,
            log_items=log_items,
        )

    def _record_action(self, name, ok, msg):
        with self._state_lock:
            self._action_log.append((time.time(), name, bool(ok), str(msg)))

    def _post_redirect(self, action, ok, msg, status=303):
        # Redirect (303 See Other) back to dashboard with a toast in the
        # querystring. The dashboard reads ?msg=…&ok=… and renders a
        # transient toast — no full intermediate page, no double-submit
        # if the user reloads.
        self._record_action(action, ok, msg)
        base = self._plugin_base()
        # Truncate + URL-encode the toast text. The dashboard does its
        # own html.escape on render, so we only need to make this safe
        # for inclusion in a URL.
        try:
            from urllib.parse import urlencode
            qs = urlencode({'msg': str(msg)[:200],
                            'ok':  '1' if ok else '0'})
        except Exception:
            qs = ''
        target = f'{base}?{qs}' if qs else base
        resp = make_response('', status)
        resp.headers['Location'] = target
        resp.headers['Cache-Control'] = 'no-store'
        return resp

    def _handle_post(self, path, request):
        # CSRF: pwnagotchi wraps the webserver with flask_wtf.CSRFProtect
        # which validates the `csrf_token` form field BEFORE this handler
        # ever runs. If we reached here, the token was good. The previous
        # custom `_verify_csrf` was redundant and actually broke things,
        # because the middleware uses Flask-WTF's session-bound token,
        # not our per-process token.
        try:
            if path == 'force-save':
                self._enqueue_save(reason='manual')
                return self._post_redirect(
                    'force-save', True,
                    'State save enqueued.')
            if path == 'rescan-potfile':
                cracked = self._scan_cracked_potfile()
                with self._state_lock:
                    added = len(cracked - self._cracked_bssids)
                    # v1.8.1: MERGE not REPLACE — keep prior cracks if
                    # the live potfile got rotated between sessions.
                    self._cracked_bssids |= cracked
                    # Mark already-known APs as cracked so the targeting loop
                    # picks the change up immediately.
                    for k, ap in self._known_aps.items():
                        if self._mac_norm(ap.get('mac', '')) in self._cracked_bssids:
                            ap['AT_cracked'] = True
                self._enqueue_save(reason='potfile-rescan')
                return self._post_redirect(
                    'rescan-potfile', True,
                    f'Potfile rescanned — {len(self._cracked_bssids)} cracked '
                    f'BSSIDs ({added} new).')
            if path == 'reset-stagnation':
                with self._state_lock:
                    self._stagnation_count = 0
                    self._exploration_boost = max(self._exploration_boost,
                                                  self.cfg.get(
                                                      'stagnation_boost_epochs',
                                                      30))
                    if hasattr(self, '_decision_buffer'):
                        try:
                            self._decision_buffer.clear()
                        except Exception:
                            pass
                return self._post_redirect(
                    'reset-stagnation', True,
                    'Stagnation streak reset and exploration boosted.')
            if path == 'reload-whitelist':
                if self._agent is not None:
                    self._load_whitelist(self._agent)
                with self._state_lock:
                    n_mac  = len(self._whitelist_macs)
                    n_ssid = len(self._whitelist_ssids)
                return self._post_redirect(
                    'reload-whitelist', True,
                    f'Whitelist reloaded ({n_mac} MAC, {n_ssid} SSID).')
            if path == 'clear-blind':
                with self._state_lock:
                    prior = self._blind_recovery
                    self._blind_recovery = 0
                    self._crash_suspect = 0
                return self._post_redirect(
                    'clear-blind', True,
                    f'Blind-panic cleared (was {prior}).')
        except Exception as e:
            log.exception(f'[envtune] POST {path}: {e}')
            return self._post_redirect(path, False, repr(e), status=500)
        return self._html_response(
            '<!DOCTYPE html><html><body><h1>404</h1>'
            f'<p>Unknown action: {html.escape(str(path))}</p>'
            '</body></html>',
            status=404)
