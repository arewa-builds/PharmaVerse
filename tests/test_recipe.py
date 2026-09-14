from __future__ import annotations

from pathlib import Path

import pytest

from pharmaverse.worlds.recipe import load_recipe, plan_jobs

RECIPE = Path(__file__).resolve().parents[1] / "config" / "marble" / "packaging_suite_v1.yaml"


@pytest.fixture
def recipe() -> dict:
    return load_recipe(RECIPE)


def test_primary_plan_is_one_keeper(recipe: dict) -> None:
    jobs = plan_jobs(recipe, mode="primary")
    assert len(jobs) == 1
    job = jobs[0]
    assert job.prompt_id == "primary"
    assert job.seed == 1
    assert job.model == "marble-1.1"
    assert "stainless-steel equipment" in job.text_prompt
    body = job.generate_request()
    assert body["world_prompt"]["type"] == "text"
    assert body["model"] == "marble-1.1"
    assert len(body["display_name"]) <= 64
    assert body["permission"]["public"] is False


def test_variants_plan_covers_prompt_family(recipe: dict) -> None:
    jobs = plan_jobs(recipe, mode="variants")
    ids = [job.prompt_id for job in jobs]
    assert ids == ["primary", "cooler_lighting", "warmer_shift", "tighter_room"]
    assert {job.seed for job in jobs} == {1}


def test_family_plan_crosses_prompts_and_seeds(recipe: dict) -> None:
    jobs = plan_jobs(recipe, mode="family")
    assert len(jobs) == 4 * 3
    assert {job.seed for job in jobs} == {1, 2, 3}


def test_draft_uses_draft_model(recipe: dict) -> None:
    jobs = plan_jobs(recipe, mode="primary", draft=True)
    assert jobs[0].model == "marble-1.0-draft"


def test_prompt_id_filter(recipe: dict) -> None:
    jobs = plan_jobs(recipe, mode="family", prompt_id="tighter_room", seed=2)
    assert len(jobs) == 1
    assert jobs[0].job_id == "packaging_suite_v1__tighter_room__seed2"
