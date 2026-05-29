"""
VALET — "Be the oracle" interactive demo (Gradio Space).

The trained VALET agent runs in MiniGrid-DoorKey-16x16 with a partial 7x7 view.
Its action space is the 7 MiniGrid actions + 1 `query` action. Whenever the agent
chooses `query`, the simulation pauses and asks YOU (the human oracle) which base
action to take — exactly where the BFS oracle would have been called during training.

Drop this file in a Gradio Space together with:
  - model_partial.py          (your CNNPolicy definition, unchanged)
  - the checkpoint .pt         (set its name below or via the CHECKPOINT env var)
  - requirements.txt
"""

import os
import time
import uuid

import numpy as np
import torch
import gymnasium as gym
import gradio as gr

import minigrid  # noqa: F401  (registers the MiniGrid environments)
from minigrid.wrappers import RGBImgPartialObsWrapper

from model_partial import CNNPolicy

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
CHECKPOINT = os.environ.get(
    "CHECKPOINT",
    "best__oracle_paid_001_16_partial__MiniGrid-DoorKey-16x16-v0.pt",
)
ENV_ID      = os.environ.get("ENV_ID", "MiniGrid-DoorKey-16x16-v0")
TILE_SIZE   = 8
HIDDEN_DIM  = 256
DEVICE      = torch.device("cpu")
DEFAULT_SPEED = 0.45  # seconds between auto-steps (visualisation pacing)

# MiniGrid base actions, indices 0..6. Index 7 == query (the agent asks us).
ACTION_NAMES = [
    "\u21b0 Turn left",     # 0
    "\u21b1 Turn right",    # 1
    "\u2191 Forward",       # 2
    "\u270b Pick up",       # 3
    "\U0001f447 Drop",      # 4
    "\U0001f501 Toggle / open",  # 5
    "\u2713 Done",          # 6
]

# ---------------------------------------------------------------------------
# Build a probe env to read shapes, then load the model once (shared globally)
# ---------------------------------------------------------------------------
def make_env(render=True):
    env = gym.make(ENV_ID, render_mode="rgb_array" if render else None)
    env = RGBImgPartialObsWrapper(env, tile_size=TILE_SIZE)
    return env


_probe = make_env(render=False)
OBS_SHAPE    = _probe.observation_space["image"].shape  # (56, 56, 3)
N_BASE       = _probe.action_space.n                    # 7
N_ACTIONS    = N_BASE + 1                               # +1 for query
QUERY_ACTION = N_BASE                                   # == 7
_probe.close()

MODEL = CNNPolicy(OBS_SHAPE, N_ACTIONS, HIDDEN_DIM).to(DEVICE)
UNTRAINED = not os.path.exists(CHECKPOINT)
if UNTRAINED:
    print(f"[WARN] Checkpoint '{CHECKPOINT}' not found — running with a RANDOM, "
          f"UNTRAINED agent (UI/loop test only).")
else:
    _ckpt = torch.load(CHECKPOINT, map_location=DEVICE, weights_only=False)
    _sd = _ckpt["state_dict"] if isinstance(_ckpt, dict) and "state_dict" in _ckpt else _ckpt
    MODEL.load_state_dict(_sd)
    print(f"[OK] Loaded checkpoint: {CHECKPOINT}")
MODEL.eval()

# ---------------------------------------------------------------------------
# Per-session state. We keep the live gym env in a module-level dict keyed by a
# session id (stored in gr.State) rather than inside gr.State itself, because
# gr.State may deep-copy its value and a live gym env does not copy cleanly.
# ---------------------------------------------------------------------------
SESSIONS = {}


def _policy_action(obs_img, stochastic):
    obs_t = torch.tensor(obs_img[None], dtype=torch.uint8, device=DEVICE)
    with torch.no_grad():
        logits, _ = MODEL(obs_t)
    if stochastic:
        return torch.distributions.Categorical(logits=logits).sample().item()
    return logits.argmax(dim=-1).item()


def _god_view(env):
    return env.render()  # full grid RGB (H, W, 3) uint8


def _agent_view(obs_img, scale=5):
    # nearest-neighbour upscale of the 56x56 partial obs so it's visible
    return np.kron(obs_img, np.ones((scale, scale, 1), dtype=obs_img.dtype))


def _status(s, msg):
    return (
        f"### {msg}\n"
        f"**Step** {s['steps']} &nbsp;·&nbsp; "
        f"**Return** {s['return']:.3f} &nbsp;·&nbsp; "
        f"**Oracle calls** {s['queries']}"
    )


def _panel(visible):
    return gr.update(visible=visible)


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------
def new_episode(sid, seed_str):
    if sid and sid in SESSIONS:
        try:
            SESSIONS[sid]["env"].close()
        except Exception:
            pass
    sid = sid or str(uuid.uuid4())

    env = make_env(render=True)
    try:
        seed = int(seed_str)
    except (TypeError, ValueError):
        seed = int(np.random.randint(0, 1_000_000))
    obs_dict, _ = env.reset(seed=seed)

    SESSIONS[sid] = {
        "env": env,
        "obs": obs_dict["image"],
        "steps": 0,
        "return": 0.0,
        "queries": 0,
        "done": False,
        "speed": DEFAULT_SPEED,
    }
    s = SESSIONS[sid]
    return (
        sid,
        _god_view(env),
        _agent_view(s["obs"]),
        _status(s, f"New episode ready (seed {seed}) — press \u25b6 Run"),
        _panel(False),
    )


def _advance(sid, stochastic):
    """Auto-step with the policy, yielding frames, until a query or terminal state."""
    s = SESSIONS[sid]
    env = s["env"]
    while True:
        action = _policy_action(s["obs"], stochastic)

        if action == QUERY_ACTION:
            yield (
                sid, _god_view(env), _agent_view(s["obs"]),
                _status(s, "\U0001f52e The agent is asking **YOU** — pick an action to suggest"),
                _panel(True),
            )
            return

        obs_dict, reward, term, trunc, _ = env.step(action)
        s["obs"] = obs_dict["image"]
        s["steps"] += 1
        s["return"] += float(reward)
        yield (
            sid, _god_view(env), _agent_view(s["obs"]),
            _status(s, f"Agent acted: {ACTION_NAMES[action]}"),
            _panel(False),
        )

        if term or trunc:
            s["done"] = True
            outcome = "\U0001f3c6 Solved!" if reward > 0 else "\U0001f480 Failed / timed out"
            yield (
                sid, _god_view(env), _agent_view(s["obs"]),
                _status(s, outcome), _panel(False),
            )
            return

        time.sleep(s.get("speed", DEFAULT_SPEED))


def run(sid, stochastic, speed):
    if not sid or sid not in SESSIONS:
        yield (sid, None, None, "### Press \U0001f3b2 New episode first", _panel(False))
        return
    s = SESSIONS[sid]
    s["speed"] = float(speed)
    if s["done"]:
        yield (
            sid, _god_view(s["env"]), _agent_view(s["obs"]),
            _status(s, "Episode finished — press \U0001f3b2 New episode"), _panel(False),
        )
        return
    yield from _advance(sid, stochastic)


def oracle_step(sid, action_idx, stochastic):
    """The human picked an action while the agent was querying. Execute it, then resume."""
    if not sid or sid not in SESSIONS:
        return
    s = SESSIONS[sid]
    env = s["env"]

    obs_dict, reward, term, trunc, _ = env.step(action_idx)
    s["obs"] = obs_dict["image"]
    s["steps"] += 1
    s["return"] += float(reward)
    s["queries"] += 1
    yield (
        sid, _god_view(env), _agent_view(s["obs"]),
        _status(s, f"You guided the agent: {ACTION_NAMES[action_idx]}"),
        _panel(False),
    )

    if term or trunc:
        s["done"] = True
        outcome = "\U0001f3c6 Solved!" if reward > 0 else "\U0001f480 Failed / timed out"
        yield (
            sid, _god_view(env), _agent_view(s["obs"]),
            _status(s, outcome), _panel(False),
        )
        return

    time.sleep(s.get("speed", DEFAULT_SPEED))
    yield from _advance(sid, stochastic)


def make_oracle_handler(idx):
    def handler(sid, stochastic):
        yield from oracle_step(sid, idx, stochastic)
    return handler


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
css = """
#oracle-panel button {
    border: 2px solid #555 !important;
    border-radius: 8px !important;
}
"""

with gr.Blocks(title="VALET — be the oracle", css=css) as demo:
    gr.Markdown(
        "# \U0001f9ed VALET — be the oracle\n"
        "A PPO agent trained with VALET navigates **MiniGrid-DoorKey-16×16** through a "
        "partial 7×7 view. It can spend a small cost to **query an oracle**. Here, *you* are "
        "the oracle: whenever the agent asks for help, the simulation pauses and you choose "
        "the action it takes. Try giving it good advice — or bad advice, and watch what happens."
    )

    if UNTRAINED:
        gr.Markdown(
            "> \u26a0\ufe0f **No checkpoint loaded — this is a RANDOM, untrained agent.** "
            "It moves more or less at random and queries roughly once every few steps, "
            "which is enough to test the interface. Drop your `.pt` next to `app.py` "
            "(or set the `CHECKPOINT` env var) to run the real agent."
        )

    sid = gr.State(None)

    with gr.Row():
        with gr.Column(scale=3):
            god = gr.Image(label="Full environment (your view)", height=420)
        with gr.Column(scale=1):
            partial = gr.Image(label="What the agent sees (7×7 partial)", height=260)
            status = gr.Markdown("### Press \U0001f3b2 New episode to start")

    with gr.Row():
        seed_box = gr.Textbox(label="Seed (blank = random)", value="", scale=1)
        stoch = gr.Checkbox(
            label="Stochastic policy",
            value=True,
            info="Sampling makes the agent query more often (recommended for the demo).",
            scale=1,
        )
        speed = gr.Slider(0.05, 1.0, value=DEFAULT_SPEED, step=0.05,
                          label="Step delay (s)", scale=1)
        new_btn = gr.Button("\U0001f3b2 New episode", variant="secondary", scale=1)
        run_btn = gr.Button("\u25b6 Run", variant="primary", scale=1)

    stop_btn = gr.Button("\u23f9 Stop", variant="stop")

    with gr.Group(visible=False, elem_id="oracle-panel") as oracle_panel:
        gr.Markdown("### \U0001f52e The agent is asking for guidance — choose an action:")
        with gr.Row():
            oracle_btns = [gr.Button(name) for name in ACTION_NAMES]

    outputs = [sid, god, partial, status, oracle_panel]

    run_event = run_btn.click(run, [sid, stoch, speed], outputs)
    oracle_events = []
    for i, b in enumerate(oracle_btns):
        oracle_events.append(b.click(make_oracle_handler(i), [sid, stoch], outputs))
    new_btn.click(new_episode, [sid, seed_box], outputs, cancels=[run_event] + oracle_events)
    stop_btn.click(fn=None, cancels=[run_event] + oracle_events)


if __name__ == "__main__":
    demo.queue().launch()