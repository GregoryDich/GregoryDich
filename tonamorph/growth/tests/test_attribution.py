"""Campaign attribution: every published link carries UTMs and the content id (§7)."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
import respx
from fastmcp import Client

from mcp_server.attribution import build_landing_url
from mcp_server.config import Settings
from mcp_server.render import RenderResult
from mcp_server.state import Store
from tests.test_publishers import mock_instagram, mock_youtube

ITEM_ID = "1f0e3dad-9999-4c1c-b3c2-000000000042"


@pytest.fixture
def fake_render(monkeypatch: pytest.MonkeyPatch) -> None:
    async def render_item(item, settings, *, work_dir, scene, presenter, avatar_clip, frames=None):
        work_dir.mkdir(parents=True, exist_ok=True)
        out = work_dir / "short.mp4"
        out.write_bytes(b"\0" * 64)
        return RenderResult(
            content_item_id=item.id,
            video_path=str(out),
            renderer="ffmpeg",
            props_path=str(work_dir / "props.json"),
            duration_seconds=15.0,
        )

    monkeypatch.setattr("mcp_server.pipeline.render_item", render_item)


def _params(url: str) -> dict[str, str]:
    return {k: v[0] for k, v in parse_qs(urlsplit(url).query, keep_blank_values=True).items()}


@pytest.mark.parametrize(
    ("platform", "expected"),
    [
        ("instagram", "instagram"),
        ("facebook", "facebook"),
        ("tiktok", "tiktok"),
        ("youtube", "youtube"),
    ],
)
def test_utm_source_is_the_platform(settings: Settings, platform: str, expected: str) -> None:
    url = build_landing_url(settings, platform=platform, content_item_id=ITEM_ID)
    assert _params(url)["utm_source"] == expected


def test_every_parameter_is_present_and_the_content_id_ties_back(settings: Settings) -> None:
    url = build_landing_url(settings, platform="tiktok", content_item_id=ITEM_ID)
    assert url.startswith("https://tonamorph.test/get?")
    assert _params(url) == {
        "utm_source": "tiktok",
        "utm_medium": "social",
        "utm_campaign": "ugc_shorts",
        "utm_content": ITEM_ID,
        "ref": "growth-bot",
    }


def test_referral_code_is_omitted_when_not_configured(settings: Settings) -> None:
    url = build_landing_url(
        settings.model_copy(update={"growth_referral_code": None}),
        platform="youtube",
        content_item_id=ITEM_ID,
    )
    assert "ref" not in _params(url)


def test_every_value_is_percent_encoded(settings: Settings) -> None:
    tricky = settings.model_copy(
        update={
            "growth_landing_url": "https://tonamorph.test/get?src=page one&keep=1",
            "growth_utm_campaign": "spring sale & more/50%",
            "growth_utm_medium": "sociál média",
            "growth_referral_code": "ref#1?x=y",
        }
    )
    url = build_landing_url(
        tricky, platform="instagram", content_item_id="id with space&amp", medium=None
    )
    query = urlsplit(url).query
    assert " " not in query and "#" not in query
    assert "&more" not in query.replace("%26more", "")
    assert "spring%20sale%20%26%20more%2F50%25" in query
    assert "soci%C3%A1l%20m%C3%A9dia" in query
    assert "ref%231%3Fx%3Dy" in query
    assert _params(url) == {
        "src": "page one",
        "keep": "1",
        "utm_source": "instagram",
        "utm_medium": "sociál média",
        "utm_campaign": "spring sale & more/50%",
        "utm_content": "id with space&amp",
        "ref": "ref#1?x=y",
    }


def test_campaign_parameters_replace_ones_already_on_the_landing_url(settings: Settings) -> None:
    url = build_landing_url(
        settings.model_copy(
            update={"growth_landing_url": "https://tonamorph.test/get?utm_source=old&a=b"}
        ),
        platform="facebook",
        content_item_id=ITEM_ID,
        campaign="retarget",
        medium="paid_social",
    )
    params = _params(url)
    assert params["utm_source"] == "facebook"
    assert params["utm_campaign"] == "retarget"
    assert params["utm_medium"] == "paid_social"
    assert params["a"] == "b"


def test_a_relative_landing_url_is_rejected(settings: Settings) -> None:
    with pytest.raises(ValueError, match="absolute http"):
        build_landing_url(
            settings.model_copy(update={"growth_landing_url": "/get"}),
            platform="tiktok",
            content_item_id=ITEM_ID,
        )


async def test_publish_puts_the_tagged_link_in_the_caption_and_on_the_item(
    mcp_client: Client, router: respx.Router, store: Store, fake_render: None
) -> None:
    routes = mock_youtube(router)
    item = store.create_item("licensed_folder", "/clips/a.wav")
    store.update(item.id, assets={"chosen_stem_path": "/clips/a.wav"})
    await mcp_client.call_tool("render_video", {"content_item_id": item.id})
    result = await mcp_client.call_tool(
        "publish_video",
        {
            "content_item_id": item.id,
            "platforms": ["youtube"],
            "caption": "Sample to keys",
            "hashtags": ["tonamorph"],
        },
    )
    entry = result.structured_content["results"][0]
    expected = (
        "https://tonamorph.test/get?utm_source=youtube&utm_medium=social"
        f"&utm_campaign=ugc_shorts&utm_content={item.id}&ref=growth-bot"
    )
    assert entry["link"] == expected
    description = json.loads(routes["session"].calls.last.request.content)["snippet"]["description"]
    assert expected in description
    assert store.require(item.id).publish_record("youtube").link == expected


async def test_each_platform_gets_its_own_utm_source(
    mcp_client: Client, router: respx.Router, store: Store, fake_render: None
) -> None:
    mock_youtube(router)
    mock_instagram(router)
    item = store.create_item("licensed_folder", "/clips/a.wav")
    store.update(item.id, assets={"chosen_stem_path": "/clips/a.wav"})
    await mcp_client.call_tool("render_video", {"content_item_id": item.id})
    result = await mcp_client.call_tool(
        "publish_video",
        {
            "content_item_id": item.id,
            "platforms": ["youtube", "instagram"],
            "caption": "c",
            "hashtags": [],
        },
    )
    links = {r["platform"]: _params(r["link"]) for r in result.structured_content["results"]}
    assert links["youtube"]["utm_source"] == "youtube"
    assert links["instagram"]["utm_source"] == "instagram"
    assert {p["utm_content"] for p in links.values()} == {item.id}


async def test_licence_attribution_is_carried_into_the_caption(
    mcp_client: Client, router: respx.Router, store: Store, fake_render: None, tmp_path: Path
) -> None:
    routes = mock_youtube(router)
    item = store.create_item("free_music_archive", "https://cdn.test/beat.wav")
    store.update(
        item.id,
        assets={"chosen_stem_path": "/clips/a.wav"},
        rights={
            "status": "cleared",
            "license": "Attribution 4.0",
            "attribution": "A — https://fma.test/a",
            "evidence": "free_music_archive license_title",
            "authority": None,
            "reason": None,
        },
    )
    await mcp_client.call_tool("render_video", {"content_item_id": item.id})
    report = (
        await mcp_client.call_tool(
            "publish_video",
            {"content_item_id": item.id, "platforms": ["youtube"], "caption": "c", "hashtags": []},
        )
    ).structured_content
    assert report["attribution_line"] == "Audio: A — https://fma.test/a (Attribution 4.0)"
    description = json.loads(routes["session"].calls.last.request.content)["snippet"]["description"]
    assert "Audio: A — https://fma.test/a (Attribution 4.0)" in description
    assert (
        store.require(item.id).publish_record("youtube").attribution_line
        == "Audio: A — https://fma.test/a (Attribution 4.0)"
    )


async def test_link_survives_a_failed_attempt_and_is_reported(
    mcp_client: Client, router: respx.Router, store: Store, fake_render: None
) -> None:
    mock_instagram(router, upload_ok=False)
    item = store.create_item("licensed_folder", "/clips/a.wav")
    store.update(item.id, assets={"chosen_stem_path": "/clips/a.wav"})
    await mcp_client.call_tool("render_video", {"content_item_id": item.id})
    result = await mcp_client.call_tool(
        "publish_video",
        {"content_item_id": item.id, "platforms": ["instagram"], "caption": "c", "hashtags": []},
    )
    entry = result.structured_content["results"][0]
    assert entry["status"] == "failed"
    assert _params(entry["link"])["utm_content"] == item.id
    assert store.require(item.id).publish_record("instagram").link == entry["link"]
