import io
import json
from unittest.mock import MagicMock, patch

SHOWCASE_MANIFEST = {
    "schema": 1,
    "generated_utc": "2026-08-28T21:00:00Z",
    "items": [
        {
            "id": "2026-08-20-canon-cygnus-milky-way",
            "title": "Cygnus and the Northern Cross in Summer",
            "category": "deep-sky",
            "target": "NGC 7000 / Deneb",
            "constellation": "Cygnus",
            "featured": True,
            "date": "2026-08-20",
            "time": "23:15 BST",
            "camera": "canon",
            "night": "2026-08-20",
            "equipment": {
                "optics": "Canon EF 50mm f/1.8 STM",
                "focal_length": "50mm",
                "f_ratio": "f/2.8",
                "sensor": "Canon EOS 2000D",
                "mount": "Fixed Tripod",
                "filter": "UV/IR Cut",
            },
            "exposure": {
                "subs": 40,
                "sub_time": "30s",
                "total_integration": "20m",
                "iso_gain": "ISO 1600",
                "bortle": "Class 6",
            },
            "caption": "A rich widefield view across Cygnus.",
            "processing": "40 sub-exposures aligned with sub-pixel registration.",
            "highlights": [
                "40 x 30s light frames registered with sub-pixel affine transformation",
                "2D polynomial background sky gradient subtraction",
            ],
            "image_key": "showcase/items/2026-08-20-canon-cygnus-milky-way.jpg",
            "thumb_key": "showcase/thumbs/2026-08-20-canon-cygnus-milky-way.jpg",
        },
        {
            "id": "2026-08-22-astrocam-polaris-derotation",
            "title": "Four Hours Around the Celestial Pole",
            "category": "derotated",
            "target": "Polaris",
            "constellation": "Ursa Minor",
            "featured": False,
            "date": "2026-08-22",
            "time": "02:40 BST",
            "camera": "astrocam",
            "night": "2026-08-22",
            "equipment": {
                "optics": "Raspberry Pi Camera Module v2",
                "sensor": "Sony IMX219",
            },
            "exposure": {
                "subs": 240,
                "sub_time": "60s",
                "total_integration": "4h 00m",
            },
            "caption": "A four-hour continuous stack derotated around the pole.",
            "image_key": "showcase/items/2026-08-22-astrocam-polaris-derotation.jpg",
            "thumb_key": "showcase/thumbs/2026-08-22-astrocam-polaris-derotation.jpg",
        },
        {
            "id": "2026-08-12-canon-perseid-fireball",
            "title": "Perseid Fireball",
            "category": "meteors",
            "target": "Perseid Meteor",
            "date": "2026-08-12",
            "camera": "canon",
            "night": "2026-08-12",
            "caption": "A vivid Perseid meteor fireball.",
            "image_key": "showcase/items/2026-08-12-canon-perseid-fireball.jpg",
            "thumb_key": "showcase/thumbs/2026-08-12-canon-perseid-fireball.jpg",
        },
    ],
}


def _client(manifest=SHOWCASE_MANIFEST):
    c = MagicMock()
    if manifest is None:
        c.get_object.side_effect = Exception("NoSuchKey")
    else:
        c.get_object.side_effect = lambda *a, **kw: {
            "Body": io.BytesIO(json.dumps(manifest).encode())
        }
    c.generate_presigned_url.side_effect = (
        lambda *a, **kw: f"https://signed/{kw['Params']['Key']}"
    )
    return c


def _get(mywebsite, make_event, make_context, path, manifest=SHOWCASE_MANIFEST):
    client = _client(manifest)
    mywebsite._S3_CLIENTS.clear()
    with patch.object(mywebsite, "boto3") as fake:
        fake.client.return_value = client
        result = mywebsite.lambda_handler(make_event(path), make_context())
    mywebsite._S3_CLIENTS.clear()
    return result, client


class TestShowcaseCategoryCounts:
    @staticmethod
    def _counts(items):
        from routes.astro_showcase import showcase_category_counts
        return showcase_category_counts(items)

    def test_known_categories_in_order(self, mywebsite):
        counts = self._counts(SHOWCASE_MANIFEST["items"])
        assert [c[0] for c in counts] == ["deep-sky", "derotated", "meteors"]

    def test_custom_category_handling(self, mywebsite):
        counts = self._counts([{"id": "x", "category": "nebula"}])
        assert ("nebula", "Nebula", 1) in counts

    def test_empty_categories_dropped(self, mywebsite):
        counts = self._counts([{"id": "x", "category": "deep-sky"}])
        assert len(counts) == 1
        assert counts[0][0] == "deep-sky"


class TestShowcaseGallery:
    def test_gallery_renders_all_items(self, mywebsite, make_event, make_context):
        result, _ = _get(mywebsite, make_event, make_context, "/astro/photos")
        assert result["statusCode"] == 200
        body = result["body"]
        for item in SHOWCASE_MANIFEST["items"]:
            assert item["title"] in body

    def test_showcase_alias_route(self, mywebsite, make_event, make_context):
        result, _ = _get(mywebsite, make_event, make_context, "/astro/showcase")
        assert result["statusCode"] == 200
        assert "Cygnus and the Northern Cross" in result["body"]

    def test_single_s3_get_for_gallery(self, mywebsite, make_event, make_context):
        _, client = _get(mywebsite, make_event, make_context, "/astro/photos")
        assert client.get_object.call_count == 1
        assert client.list_objects_v2.call_count == 0

    def test_category_filter_renders_matching_subset(self, mywebsite, make_event, make_context):
        result, _ = _get(mywebsite, make_event, make_context, "/astro/photos/derotated")
        assert result["statusCode"] == 200
        body = result["body"]
        assert "Four Hours Around the Celestial Pole" in body
        assert "Cygnus and the Northern Cross" not in body

    def test_unknown_slug_redirects(self, mywebsite, make_event, make_context):
        result, _ = _get(mywebsite, make_event, make_context, "/astro/photos/invalid-slug")
        assert result["statusCode"] == 302
        assert result["headers"]["Location"] == "/astro/photos"

    def test_empty_manifest_graceful(self, mywebsite, make_event, make_context):
        result, _ = _get(mywebsite, make_event, make_context, "/astro/photos", manifest=None)
        assert result["statusCode"] == 200
        assert "astro/bin/add-showcase" in result["body"]


class TestShowcaseDetail:
    def test_photo_detail_page_renders_equipment_and_prose(self, mywebsite, make_event, make_context):
        result, _ = _get(
            mywebsite,
            make_event,
            make_context,
            "/astro/photos/2026-08-20-canon-cygnus-milky-way",
        )
        assert result["statusCode"] == 200
        body = result["body"]
        assert "Cygnus and the Northern Cross in Summer" in body
        assert "Canon EF 50mm f/1.8 STM" in body
        assert "Canon EOS 2000D" in body
        assert "40 frames" in body
        assert "2D polynomial background sky gradient subtraction" in body
        assert "/astro/canon/night/2026-08-20" in body

    def test_navigation_prev_next(self, mywebsite, make_event, make_context):
        result, _ = _get(
            mywebsite,
            make_event,
            make_context,
            "/astro/photos/2026-08-22-astrocam-polaris-derotation",
        )
        assert result["statusCode"] == 200
        body = result["body"]
        assert "Cygnus and the Northern Cross" in body
        assert "Perseid Fireball" in body


class TestHubLinksToShowcase:
    def test_hub_links_to_photos(self, mywebsite, make_event, make_context):
        result = mywebsite.lambda_handler(make_event("/astro"), make_context())
        assert "/astro/photos" in result["body"]
