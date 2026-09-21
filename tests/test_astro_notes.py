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
