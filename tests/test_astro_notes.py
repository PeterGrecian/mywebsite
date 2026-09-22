"""Tests for /astro/notes — the Field Notes logbook and its instrument pages.

Same contract the transients gallery is held to, because it is the same
shape: ONE manifest read (notes/index.json), presign only what is drawn,
filtering by instrument is exact, an unknown slug redirects rather than
rendering a dead page, and an absent manifest degrades to an empty logbook
rather than a 500.

The two things specific to notes: an entry id and an instrument slug share
one path segment, so the id must win; and an instrument page must still
render when the manifest is missing, because the instrument facts do not
come from it.
"""
import io
import json
from unittest.mock import MagicMock, patch


MANIFEST = {"schema": 1, "items": [
    {"id": "2026-09-20-firstscope-derotation",
     "title": "De-rotation recovers 88 percent of a perfect stack",
     "instrument": "firstscope", "date": "2026-09-20", "night": "2026-09-20",
     "tags": ["de-rotation", "pole"],
     "summary": "A 76 mm scope lands within 12 percent of ideal.",
     "body": "The pole is 4.32 degrees from the field centre.",
     "numbers": ["19.2x noise reduction", "pole offset 4.32 degrees"],
     "figures": [{"key": "notes/figures/a-1.jpg", "caption": "coadd",
                  "width": 811, "height": 328},
                 {"key": "notes/figures/a-2.jpg", "caption": "strip",
                  "width": 2820, "height": 202}],
     "thumb_key": "notes/thumbs/a.jpg"},
    {"id": "2026-09-12-astrocam-seeing",
     "title": "A night of steady seeing on Polecam",
     "instrument": "astrocam", "date": "2026-09-12", "night": "2026-09-12",
     "summary": "Steady all night.",
     "figures": [{"key": "notes/figures/b-1.jpg", "caption": "trails"}],
     "thumb_key": "notes/thumbs/b.jpg"},
    {"id": "2026-08-30-spectroscope-first-light",
     "title": "First light on something new",
     "instrument": "spectroscope", "date": "2026-08-30",
     "summary": "It works.", "figures": [], "thumb_key": None},
]}


def _client(manifest=MANIFEST):
    c = MagicMock()
    if manifest is None:
        c.get_object.side_effect = Exception("NoSuchKey")
    else:
        c.get_object.side_effect = lambda *a, **kw: {
            "Body": io.BytesIO(json.dumps(manifest).encode())}
    c.generate_presigned_url.side_effect = \
        lambda *a, **kw: f"https://signed/{kw['Params']['Key']}"
    return c


def _get(mywebsite, make_event, make_context, path, manifest=MANIFEST):
    client = _client(manifest)
    mywebsite._S3_CLIENTS.clear()
    with patch.object(mywebsite, "boto3") as fake:
        fake.client.return_value = client
        result = mywebsite.lambda_handler(make_event(path), make_context())
    mywebsite._S3_CLIENTS.clear()
    return result, client


class TestInstrumentCounts:
    @staticmethod
    def _counts(items):
        # Imported lazily: conftest's `mywebsite` fixture is what puts
        # lambda/ on sys.path, and that runs after collection.
        from routes.astro import note_instrument_counts
        return note_instrument_counts(items)

    def test_known_instruments_come_first_in_chip_order(self, mywebsite):
        counts = self._counts(MANIFEST["items"])
        assert [c[0] for c in counts] == ["firstscope", "astrocam",
                                          "spectroscope"]

    def test_unknown_instrument_is_titlecased(self, mywebsite):
        assert ("spectroscope", "Spectroscope", 1) in \
            self._counts(MANIFEST["items"])

    def test_missing_instrument_counts_as_other(self, mywebsite):
        assert self._counts([{"id": "x"}]) == [("other", "Other", 1)]

    def test_empty_instruments_are_dropped(self, mywebsite):
        counts = self._counts([{"id": "x", "instrument": "firstscope"}])
        assert [c[0] for c in counts] == ["firstscope"]


class TestNotesIndex:
    def test_renders_every_entry_unfiltered(self, mywebsite, make_event,
                                            make_context):
        result, _ = _get(mywebsite, make_event, make_context, "/astro/notes")
        assert result["statusCode"] == 200
        for item in MANIFEST["items"]:
            assert item["title"] in result["body"]

    def test_one_s3_get_for_the_whole_logbook(self, mywebsite, make_event,
                                              make_context):
        _, client = _get(mywebsite, make_event, make_context, "/astro/notes")
        assert client.get_object.call_count == 1
        assert client.list_objects_v2.call_count == 0

    def test_index_presigns_thumbnails_only(self, mywebsite, make_event,
                                            make_context):
        # The index draws thumbnails; presigning full figures there would be
        # work for pixels nobody sees.
        _, client = _get(mywebsite, make_event, make_context,
                         "/astro/notes/firstscope")
        keys = {c.kwargs["Params"]["Key"]
                for c in client.generate_presigned_url.call_args_list}
        assert keys == {"notes/thumbs/a.jpg"}

    def test_instrument_filter_excludes_others(self, mywebsite, make_event,
                                               make_context):
        result, _ = _get(mywebsite, make_event, make_context,
                         "/astro/notes/astrocam")
        body = result["body"]
        assert "A night of steady seeing on Polecam" in body
        assert "De-rotation recovers" not in body

    def test_unknown_slug_redirects(self, mywebsite, make_event, make_context):
        result, _ = _get(mywebsite, make_event, make_context,
                         "/astro/notes/telescope-that-does-not-exist")
        assert result["statusCode"] == 302
        assert result["headers"]["Location"] == "/astro/notes"

    def test_absent_manifest_is_an_empty_logbook_not_a_500(
            self, mywebsite, make_event, make_context):
        result, _ = _get(mywebsite, make_event, make_context, "/astro/notes",
                         manifest=None)
        assert result["statusCode"] == 200
        assert "logbook is empty" in result["body"]


class TestNoteDetail:
    def test_entry_id_wins_over_instrument_slug(self, mywebsite, make_event,
                                                make_context):
        # Both live in the same path segment; an id must not be read as an
        # instrument filter and redirected away.
        result, _ = _get(mywebsite, make_event, make_context,
                         "/astro/notes/2026-09-20-firstscope-derotation")
        assert result["statusCode"] == 200
        assert "19.2x noise reduction" in result["body"]

    def test_detail_presigns_every_figure(self, mywebsite, make_event,
                                          make_context):
        _, client = _get(mywebsite, make_event, make_context,
                         "/astro/notes/2026-09-20-firstscope-derotation")
        keys = {c.kwargs["Params"]["Key"]
                for c in client.generate_presigned_url.call_args_list}
        assert keys == {"notes/figures/a-1.jpg", "notes/figures/a-2.jpg"}

    def test_detail_links_to_the_instrument_page(self, mywebsite, make_event,
                                                 make_context):
        result, _ = _get(mywebsite, make_event, make_context,
                         "/astro/notes/2026-09-20-firstscope-derotation")
        assert '/astro/firstscope' in result["body"]

    def test_night_link_only_for_cameras_with_night_pages(
            self, mywebsite, make_event, make_context):
        # The FirstScope has no night pages; Polecam does.
        scope, _ = _get(mywebsite, make_event, make_context,
                        "/astro/notes/2026-09-20-firstscope-derotation")
        assert "/astro/firstscope/night/" not in scope["body"]
        polecam, _ = _get(mywebsite, make_event, make_context,
                          "/astro/notes/2026-09-12-astrocam-seeing")
        assert "/astro/astrocam/night/2026-09-12" in polecam["body"]


class TestInstrumentPage:
    def test_renders_the_measured_specs(self, mywebsite, make_event,
                                        make_context):
        result, _ = _get(mywebsite, make_event, make_context,
                         "/astro/firstscope")
        assert result["statusCode"] == 200
        body = result["body"]
        assert "f/3.95" in body
        assert "1.925 arcsec per pixel" in body

    def test_lists_only_its_own_notes(self, mywebsite, make_event,
                                      make_context):
        result, _ = _get(mywebsite, make_event, make_context,
                         "/astro/firstscope")
        body = result["body"]
        assert "De-rotation recovers" in body
        assert "A night of steady seeing on Polecam" not in body

    def test_renders_without_a_manifest(self, mywebsite, make_event,
                                        make_context):
        # The instrument facts are in the code, not the manifest, so a
        # missing manifest costs the notes list and nothing else.
        result, _ = _get(mywebsite, make_event, make_context,
                         "/astro/firstscope", manifest=None)
        assert result["statusCode"] == 200
        assert "f/3.95" in result["body"]
        assert "No field notes" in result["body"]


class TestHub:
    def test_hub_offers_both_new_destinations(self, mywebsite, make_event,
                                              make_context):
        result, _ = _get(mywebsite, make_event, make_context, "/astro")
        body = result["body"]
        assert "/astro/notes" in body
        assert "/astro/firstscope" in body


class TestMarkdownSubset:
    """The section renderer. A logbook entry argues with tables, so the
    failure that matters is a table rendering as a row of pipe characters."""

    @staticmethod
    def _md(text):
        from routes.astro import _md
        return _md(text)

    def test_table_becomes_a_table(self, mywebsite):
        html = self._md("| night | stops |\n|---|---|\n| 2026-09-21 | 4.987 |")
        assert "<table" in html and "<th>night</th>" in html
        assert "<td>4.987</td>" in html
        assert "|" not in html

    def test_alignment_rule_is_not_a_row(self, mywebsite):
        html = self._md("| a | b |\n|:--|--:|\n| 1 | 2 |")
        assert html.count("<tr>") == 2          # header + one body row
        assert "---" not in html

    def test_table_scrolls_rather_than_breaking_the_page(self, mywebsite):
        # Ten-column tables exist; the page must not scroll horizontally.
        assert 'class="md-tw"' in self._md("| a | b |\n|---|---|\n| 1 | 2 |")

    def test_bullets_become_a_list(self, mywebsite):
        html = self._md("- first thing\n- second thing")
        assert html.count("<li>") == 2 and "<ul" in html

    def test_indented_block_is_preformatted(self, mywebsite):
        html = self._md("    mu_G = ZP + 2.5 * log10(4 * p^2 / S_sky)")
        assert "<pre" in html and "mu_G = ZP" in html

    def test_bold_and_code_inline(self, mywebsite):
        html = self._md("the **darkest** frame at `02:26`")
        assert "<strong>darkest</strong>" in html and "<code>02:26</code>" in html

    def test_paragraphs_survive(self, mywebsite):
        html = self._md("one line\n\nanother line")
        assert html.count("<p") == 2

    def test_markup_in_a_card_is_escaped(self, mywebsite):
        # Card text is ours, but it goes through a manifest; only tags this
        # renderer writes itself should reach the page.
        html = self._md("a <script>alert(1)</script> line")
        assert "<script>" not in html and "&lt;script&gt;" in html

    def test_table_cell_markup_is_escaped(self, mywebsite):
        html = self._md("| a |\n|---|\n| <b>x</b> |")
        assert "<b>" not in html and "&lt;b&gt;" in html


class TestSectionedEntry:
    """Entries carry ordered sections; older ones carry body/numbers. Both
    must render, because a schema change must not blank an old entry."""

    SECTIONED = {"schema": 1, "items": [{
        "id": "2026-09-21-astrocam-sky-brightness",
        "title": "What our sky actually measures",
        "instrument": "astrocam", "date": "2026-09-21",
        "summary": "We measured it instead of reading a map.",
        "sections": [
            {"heading": "The night", "md": "| hour | mean |\n|---|---|\n| 02 | 81.8 |"},
            {"heading": "Results", "md": "**18.1 mag/arcsec^2**, which is Bortle 7."},
        ],
        "figures": [], "thumb_key": None}]}

    def test_sections_render_in_order_with_headings(self, mywebsite,
                                                    make_event, make_context):
        result, _ = _get(mywebsite, make_event, make_context,
                         "/astro/notes/2026-09-21-astrocam-sky-brightness",
                         manifest=self.SECTIONED)
        body = result["body"]
        assert body.index("The night") < body.index("Results")
        assert "<th>hour</th>" in body
        assert "<strong>18.1 mag/arcsec^2</strong>" in body

    def test_legacy_body_and_numbers_still_render(self, mywebsite,
                                                  make_event, make_context):
        result, _ = _get(mywebsite, make_event, make_context,
                         "/astro/notes/2026-09-20-firstscope-derotation")
        body = result["body"]
        assert "The pole is 4.32 degrees" in body
        assert "19.2x noise reduction" in body


class TestMarkdownLinks:
    """Entries cross-reference each other — a result in one note is the
    method in another — so internal links are supported and external ones
    are deliberately not."""

    @staticmethod
    def _md(text):
        from routes.astro import _md
        return _md(text)

    def test_internal_link_renders(self, mywebsite):
        html = self._md("see [the sky note](/astro/notes/2026-09-21-x)")
        assert '<a href="/astro/notes/2026-09-21-x">the sky note</a>' in html

    def test_external_link_is_left_as_text(self, mywebsite):
        html = self._md("see [evil](https://example.com/x)")
        assert "<a " not in html and "example.com" in html

    def test_javascript_href_is_left_as_text(self, mywebsite):
        html = self._md("see [x](javascript:alert(1))")
        assert "<a " not in html and "javascript" in html

    def test_protocol_relative_href_is_left_as_text(self, mywebsite):
        # "//evil.com" starts with a slash but is not an internal path.
        html = self._md("see [x](//evil.com/y)")
        assert "<a " not in html
