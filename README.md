# Pong Wars

It's the eternal battle between day and night, good and bad. Written in JavaScript with some HTML & CSS in one index.html. Feel free to reuse the code and create your own version.

https://github.com/vnglst/pong-wars/assets/3457693/4eae12fa-bdc1-49ee-8b39-c94deb7cb2c8

## Python version in this repository

This repository now includes a modular Python (pygame) implementation focused on collision handling with an event queue.

Key features:
- Queue-based disruption events (`BALL_BOUNDARY_COLLISION`, `BALL_WALL_COLLISION`, `BALL_BALL_COLLISION`, `BALL_DAMAGE`, `BALL_ELIMINATION_CHECK`)
- Cache-first motion loop (`predict -> reuse -> invalidate -> recompute`)
- OOP-friendly architecture split into package modules (`pongwars/`)
- Lightweight broad-phase with spatial hashing and candidate cache
- Neutral wall blocks that disappear on hit while balls reflect
- Ball-vs-ball reflection + damage with configurable elimination policy
- Runtime random wall spawning with safe placement (avoids overlap with alive balls)

### Cache-first architecture (predictive update)

The runtime is split into systems:
- **Intent/Input System**: updates movement intent/actions
- **Motion System**: fast path reuses cached motion plan when valid
- **Collision System**: broad-phase spatial hash + narrow-phase checks
- **Event System**: resolves disruptions and invalidates caches
- **Rules System**: applies gameplay end conditions

Each ball has runtime motion cache state containing:
- normalized movement direction
- speed
- predicted next position
- cache validity steps
- dirty flag + version counter
- cached nearby candidates (short-lived)

Motion is recomputed only when invalidated by collisions, velocity changes,
or relevant environment changes.

## Module structure

- `pongwars/config.py`: typed config loading
- `pongwars/entities.py`: domain entities and actions
- `pongwars/runtime.py`: motion cache + invalidation helpers
- `pongwars/spatial.py`: broad-phase spatial hash
- `pongwars/physics.py`: reflection + geometric collisions
- `pongwars/events.py`: event types/payload
- `pongwars/walls.py`: wall generation/spawn policy
- `pongwars/spawn.py`: initial ball spawning
- `pongwars/game.py`: orchestration of systems
- `pongwars/runner.py`: CLI entrypoint


### Run Python version (uv)

```sh
uv sync
source .venv/Scripts/activate
python pong_wars.py --config game_config.json
```

You can also run:

```sh
python main.py --config game_config.json
```

### Config

Main config is `game_config.json`.

`elimination_policy` behavior:
- `"hp_only"` (default): only remove balls when HP <= 0
- `"lower_hp"`: after each ball collision, remove the one with lower HP

Relevant random wall spawn settings:

```json
"random_wall_spawn": {
  "enabled": true,
  "interval_sec": 2.5,
  "blocks_per_spawn": 3,
  "max_walls": 220,
  "max_attempts_per_block": 80,
  "avoid_ball_margin": 2.0
}
```

## Development

Run:

```sh
npx serve
```

Open up the link and you're ready to start.

## Credits

I saw this first [here](https://twitter.com/nicolasdnl/status/1749715070928433161), but it appears to be a much older idea. There's some more information on the history in the [Hacknernews discussion](https://news.ycombinator.com/item?id=39159418).

The colors are based on the Mindful Palette by [Alex Cristache](https://twitter.com/AlexCristache/status/1738610343499157872).

## Submitting PRs

I love getting feedback and PRs with improvements for this, but I also want to keep this simple and the code minimal. If you want to extend the game, feel free to create your own. If you found a way to improve the collision detection (or a better way to add some randomness), feel free to open a PR.

## Links

- Original post on Mastodon: https://hachyderm.io/@vnglst/111828811496422610
- On Twitter: https://twitter.com/vnglst/status/1751278052154179770

## Alternate version

If you've created an alternate version of Pong Wars and want to share, feel free to create a PR to add the link here:

- [BBC Micro Bot](https://mastodon.me.uk/@bbcmicrobot/111829277042377169)
- [Earlier version with padels](https://twitter.com/CasualEffects/status/1390290306206216196)
- [Pico8](https://www.pico-8-edu.com/?c=AHB4YQHaAT3vsH558QbF5cXZxd3F_Uedc010zTVJ_gCnN3F6-RNE_SuEUXRRUa8tpK9wzE3nZMedcvntx9y1MpRnV4Xp0v3ZTrm0EUzMSQTsOWBuJL5-8C2Cl0gG0vK2sXTtKYyQN81iujMXPUN03Vq0FGXNajPzGtHOXUGgE3zegFI4hIIzoYCyC7ITgzcogmTuIaba7Nqzz48mh5JFxYFgKllpExWB7ZVnKAaH5qvd3SzqTLA0aZrR1Wy0GFywwsjUQhgOznQ3jtx6QCkisOCWvA9ngqFsZXMnFyKJhkynGFYEyZmCBcaIkk5BMF3YVRBX7RcFcZtGQbRQEN9GU_uMVEkSiRNn_aR55AmGqmBbiigfGuqybCXz5QnZI3W_Lutw2Ph4FOMn6Scn0lBgoSsFi3KlgIGpya1iYRY=&g=w-w-w-w1HQHw-w2Xw-w3Xw-w2HQH)
- [C version](https://github.com/BrunoLevy/TinyPrograms)
- [Ying Yang](https://twitter.com/a__islam/status/1751485227787034863)
- [C++](https://invent.kde.org/carlschwan/pongwars/-/blob/master/src/scene.cpp?ref_type=heads)
- [Scratch](https://scratch.mit.edu/projects/957461584)
- [Pygame version](https://github.com/BjoernSchilberg/py-pong-wars)
- [Python](https://github.com/vocdex/pong-wars-python)
- [Seasons Pong](https://github.com/hmak-dev/seasons-pong)
- [Processing](https://github.com/riktov/processing-pong-wars)
- [Flutter](https://github.com/flikkr/flutter_pong_wars)
- [Rust/Wasm](https://github.com/wasmhub-dev/pong_wars.rs)
- [Kotlin/Wasm](https://github.com/wasmhub-dev/pong_wars.kt)
- [Atari 2600](https://forums.atariage.com/topic/360475-pong-wars-atari-2600)
- [Eternal Bounce Battle (GDevelop)](https://gd.games/victrisgames/eternal-bounce-battle)
- [Swift (SpriteKit)](https://github.com/frederik-jacques/ios-pongwars)
- [React Native](https://github.com/Nodonisko/react-native-skia-pong-wars)
