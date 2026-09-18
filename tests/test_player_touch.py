"""The advanced video player's touch/keyboard controls.

Why this file exists rather than relying on the golden master: the golden
sweep in `test_dispatch_golden.py` walks routes with no query string, and
`/skycam/player` needs a `key` or `src` — parameterless it returns 400 with
a 31-byte body. So the ~42 KB player page the sweep appears to cover has in
fact never been pinned by it. Anything asserted about the player has to
render the function directly, as here.
"""

import re
import pytest


@pytest.fixture(scope="module")
def player_html(mywebsite):
    # The `mywebsite` fixture is what puts lambda/ on sys.path; depending on
    # it also gets us the real THEME_CSS_JS the live route passes in.
    from routes.gardencam import _init_theme, render_skycam_player
    _init_theme(mywebsite.THEME_CSS_JS)
    page = render_skycam_player(
        None, src="https://www.petergrecian.co.uk/sky_20260101_00.mp4")
    return page if isinstance(page, str) else page["body"]


def test_has_viewport_meta(player_html):
    """Without this the page lays out at ~980px and the phone scales it
    down — the single largest cause of the player being unusable on a
    phone. Every other gardencam page already had one; the player did not.
    """
    assert re.search(r'<meta name="viewport"[^>]*width=device-width',
                     player_html)


def test_frame_step_is_reachable_without_a_keyboard(player_html):
    """A phone has no arrow keys, so frame stepping needs both an on-screen
    control (precise, discoverable) and a gesture (fast)."""
    assert 'id="stepBack"' in player_html
    assert 'id="stepFwd"' in player_html
    assert 'getElementById("stepBack").onclick = () => stepFrame(-1)' in player_html
    assert 'getElementById("stepFwd").onclick  = () => stepFrame(+1)' in player_html


def test_horizontal_drag_steps_frames(player_html):
    """The gesture itself, and the two things that make it safe: the
    browser keeps the vertical axis (so the page still scrolls) and a
    vertical drag is dropped rather than captured."""
    assert "DRAG_PX_PER_FRAME" in player_html
    assert "touch-action: pan-y" in player_html
    assert 'v.addEventListener("pointercancel", endDrag)' in player_html
    # axis resolves to vertical -> release the drag, do not scroll-jack
    assert "if (Math.abs(dy) >= Math.abs(dx)) { dragId = null; return; }" \
        in player_html


def test_keyboard_stepping_still_wired(player_html):
    """The gesture is additive — the desk path must not regress."""
    assert 'e.code === "ArrowLeft")  { stepFrame(-1); }' in player_html
    assert 'e.code === "ArrowRight") { stepFrame(+1); }' in player_html


def test_phone_layout_enlarges_the_scrub_bar(player_html):
    """8px is not a touch target. The narrow-width rule fattens the bar and
    its fill layers together — they are separate elements that must stay
    geometrically aligned."""
    assert "@media (max-width: 700px)" in player_html
    assert ".bar, .play-region, .clip-band { top: 4px; height: 22px;" \
        in player_html


def test_clip_controls_are_hidden_on_phones_only(player_html):
    """Clip in/out is desk work. The hiding rule lives inside the media
    query, so the class that triggers it is inert on a desktop."""
    assert 'document.body.classList.add("clips-off")' in player_html
    assert 'id="clipsToggle"' in player_html
    # the hiding rule must be inside the media query, not global
    head, _, _tail = player_html.partition("@media (max-width: 700px)")
    assert "body.clips-off #clipsSel" not in head
