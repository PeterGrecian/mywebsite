"""Tests for /astro/transients — the curated general collection.

The gallery reads ONE manifest (transients/index.json) and presigns only
what it renders, so the things worth pinning are: the manifest is the only
S3 get, filtering by category is exact, an unknown slug redirects instead
of rendering a dead page, and an absent manifest degrades to an empty
gallery rather than a 500.
"""
import io
import json
from unittest.mock import MagicMock, patch


MANIFEST = {"schema": 1, "items": [
    {"id": "2026-08-12-meteor-perseid", "title": "Perseid fireball",
     "category": "meteor", "date": "2026-08-12", "time": "23:41 BST",
     "camera": "canon", "night": "2026-08-12", "caption": "Burnt out mid-frame.",
     "rationale": "Both ends stop inside the frame and it appears in one sub.",
     "evidence": ["both ends interior", "present in exactly one sub"],
     "confidence": "likely",
     "image_key": "transients/items/a.jpg",
     "thumb_key": "transients/thumbs/a.jpg"},
    {"id": "2026-08-01-daytime-focus", "title": "Focus target at noon",
     "category": "daytime", "date": "2026-08-01", "camera": "canon",
     "confidence": "confirmed",
     "image_key": "transients/items/b.jpg",
     "thumb_key": "transients/thumbs/b.jpg"},
    {"id": "2026-07-04-aurora-glow", "title": "Odd northern glow",
     "category": "aurora", "date": "2026-07-04",
     "image_key": "transients/items/c.jpg",
     "thumb_key": "transients/thumbs/c.jpg"},
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


class TestCategoryCounts:
    @staticmethod
    def _counts(items):
        # Imported lazily: conftest's `mywebsite` fixture is what puts
        # lambda/ on sys.path, and that runs after collection.
        from routes.astro import transient_category_counts
        return transient_category_counts(items)

    def test_known_categories_come_first_in_chip_order(self, mywebsite):
        counts = self._counts(MANIFEST["items"])
        assert [c[0] for c in counts] == ["meteor", "daytime", "aurora"]

    def test_unknown_category_is_titlecased(self, mywebsite):
        counts = self._counts(MANIFEST["items"])
        assert ("aurora", "Aurora", 1) in counts

    def test_missing_category_counts_as_other(self, mywebsite):
        counts = self._counts([{"id": "x"}])
        assert counts == [("other", "Other", 1)]

    def test_empty_categories_are_dropped(self, mywebsite):
        # No chip should offer a filter that leads to an empty gallery.
        counts = self._counts([{"id": "x", "category": "meteor"}])
        assert [c[0] for c in counts] == ["meteor"]


class TestTransientsPage:
    def test_renders_every_item_unfiltered(self, mywebsite, make_event,
                                           make_context):
        result, _ = _get(mywebsite, make_event, make_context,
                         "/astro/transients")
        assert result["statusCode"] == 200
        body = result["body"]
        for item in MANIFEST["items"]:
            assert item["title"] in body

    def test_one_s3_get_for_the_whole_gallery(self, mywebsite, make_event,
                                              make_context):
        _, client = _get(mywebsite, make_event, make_context,
                         "/astro/transients")
        assert client.get_object.call_count == 1
        assert client.list_objects_v2.call_count == 0

    def test_only_rendered_items_are_presigned(self, mywebsite, make_event,
                                               make_context):
        _, client = _get(mywebsite, make_event, make_context,
                         "/astro/transients/meteor")
        keys = {c.kwargs["Params"]["Key"]
                for c in client.generate_presigned_url.call_args_list}
        assert keys == {"transients/items/a.jpg", "transients/thumbs/a.jpg"}

    def test_category_filter_excludes_other_categories(self, mywebsite,
                                                       make_event,
                                                       make_context):
        result, _ = _get(mywebsite, make_event, make_context,
                         "/astro/transients/daytime")
        body = result["body"]
        assert "Focus target at noon" in body
        assert "Perseid fireball" not in body

    def test_chips_keep_full_counts_while_filtered(self, mywebsite,
                                                   make_event, make_context):
        result, _ = _get(mywebsite, make_event, make_context,
                         "/astro/transients/daytime")
        # The meteor chip is still offered even though no meteor is shown.
        assert 'href="/astro/transients/meteor"' in result["body"]

    def test_unknown_category_redirects_to_the_collection(self, mywebsite,
                                                          make_event,
                                                          make_context):
        result, _ = _get(mywebsite, make_event, make_context,
                         "/astro/transients/nonsense")
        assert result["statusCode"] == 302
        assert result["headers"]["Location"] == "/astro/transients"

    def test_missing_manifest_renders_empty_not_error(self, mywebsite,
                                                      make_event,
                                                      make_context):
        result, _ = _get(mywebsite, make_event, make_context,
                         "/astro/transients", manifest=None)
        assert result["statusCode"] == 200
        assert "add-transient" in result["body"]

    def test_night_link_only_for_a_camera_with_night_pages(self, mywebsite,
                                                           make_event,
                                                           make_context):
        result, _ = _get(mywebsite, make_event, make_context,
                         "/astro/transients")
        assert '/astro/canon/night/2026-08-12' in result["body"]
        # The aurora entry has no camera/night, so it gets no night link.
        assert result["body"].count("night page") == 1


class TestReasoning:
    """A streak does not explain itself: the card has to say why it is
    called what it is, and must not present an unestablished label as
    settled."""

    def test_rationale_and_every_evidence_point_are_shown(self, mywebsite,
                                                          make_event,
                                                          make_context):
        result, _ = _get(mywebsite, make_event, make_context,
                         "/astro/transients/meteor")
        body = result["body"]
        assert "Both ends stop inside the frame" in body
        assert "both ends interior" in body
        assert "present in exactly one sub" in body

    def test_confirmed_carries_no_hedge(self, mywebsite, make_event,
                                        make_context):
        result, _ = _get(mywebsite, make_event, make_context,
                         "/astro/transients/daytime")
        # The CSS rule is always present; the span is what must be absent.
        assert 'class="t-conf"' not in result["body"]

    def test_unhedged_label_is_never_implied_by_a_missing_field(
            self, mywebsite, make_event, make_context):
        # The aurora entry has no confidence key at all.
        result, _ = _get(mywebsite, make_event, make_context,
                         "/astro/transients/aurora")
        assert "unclassified" in result["body"]

    def test_item_without_reasoning_gets_no_empty_reason_block(
            self, mywebsite, make_event, make_context):
        result, _ = _get(mywebsite, make_event, make_context,
                         "/astro/transients/daytime")
        assert "why we call it this" not in result["body"]


class TestHubLinksToTransients:
    def test_hub_offers_the_collection(self, mywebsite, make_event,
                                       make_context):
        result = mywebsite.lambda_handler(make_event("/astro"),
                                          make_context())
        assert '/astro/transients' in result["body"]

class TestTransientPicturePage:
    """Dedicated single picture page per transient capture."""

    def test_single_transient_page_renders(self, mywebsite, make_event, make_context):
        result, _ = _get(mywebsite, make_event, make_context,
                         "/astro/transients/2026-08-12-meteor-perseid")
        assert result["statusCode"] == 200
        body = result["body"]
        assert "Perseid fireball" in body
        assert "Both ends stop inside the frame" in body
        assert "both ends interior" in body
        assert "/astro/canon/night/2026-08-12" in body
        assert "media-zoom-trigger" in body
        assert "Breadcrumbs" in body

    def test_single_transient_presigns_only_that_item(self, mywebsite, make_event, make_context):
        _, client = _get(mywebsite, make_event, make_context,
                         "/astro/transients/2026-08-12-meteor-perseid")
        keys = {c.kwargs["Params"]["Key"]
                for c in client.generate_presigned_url.call_args_list}
        assert keys == {"transients/items/a.jpg", "transients/thumbs/a.jpg"}

    def test_single_transient_prev_next_links(self, mywebsite, make_event, make_context):
        result, _ = _get(mywebsite, make_event, make_context,
                         "/astro/transients/2026-08-01-daytime-focus")
        assert result["statusCode"] == 200
        body = result["body"]
        # In MANIFEST, daytime-focus is between perseid and aurora-glow
        assert "Perseid fireball" in body
        assert "Odd northern glow" in body

    def test_gallery_links_to_picture_page(self, mywebsite, make_event, make_context):
        result, _ = _get(mywebsite, make_event, make_context, "/astro/transients")
        assert result["statusCode"] == 200
        body = result["body"]
        assert 'href="/astro/transients/2026-08-12-meteor-perseid"' in body
        assert 'href="/astro/transients/2026-08-01-daytime-focus"' in body
