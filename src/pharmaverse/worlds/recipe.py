"""Load Phase 2 Marble recipes and expand them into generation jobs."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

import yaml

PlanMode = Literal["primary", "variants", "family"]


@dataclass(frozen=True)
class WorldJob:
    recipe_id: str
    prompt_id: str
    text_prompt: str
    display_name: str
    model: str
    seed: int
    tags: list[str]
    permission: dict[str, Any]
    experiment: str | None = None

    @property
    def job_id(self) -> str:
        return f"{self.recipe_id}__{self.prompt_id}__seed{self.seed}"

    def generate_request(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "display_name": self.display_name[:64],
            "model": self.model,
            "tags": self.tags[:10],
            "seed": self.seed,
            "permission": self.permission or {"public": False},
            "world_prompt": {
                "type": "text",
                "text_prompt": self.text_prompt,
            },
        }
        return body

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["job_id"] = self.job_id
        payload["generate_request"] = self.generate_request()
        return payload


def load_recipe(path: str | Path) -> dict[str, Any]:
    recipe_path = Path(path)
    with recipe_path.open(encoding="utf-8") as handle:
        recipe = yaml.safe_load(handle)
    if not isinstance(recipe, dict) or not recipe.get("id"):
        raise ValueError(f"Recipe {recipe_path} must be a mapping with an id")
    if not recipe.get("primary_prompt"):
        raise ValueError(f"Recipe {recipe_path} is missing primary_prompt")
    return recipe


def _prompts(recipe: dict[str, Any], mode: PlanMode) -> list[tuple[str, str]]:
    primary = " ".join(str(recipe["primary_prompt"]).split())
    items = [("primary", primary)]
    if mode == "primary":
        return items
    for variant in recipe.get("variant_prompts") or []:
        items.append((str(variant["id"]), " ".join(str(variant["text"]).split())))
    return items


def _seeds(recipe: dict[str, Any], mode: PlanMode, seed: int | None) -> list[int]:
    recipe_seeds = [int(value) for value in recipe.get("seeds") or [1]]
    if seed is not None:
        return [int(seed)]
    if mode == "family":
        return recipe_seeds
    return [recipe_seeds[0]]


def _display_name(recipe: dict[str, Any], prompt_id: str, seed: int) -> str:
    base = str(recipe.get("display_name") or recipe["id"])
    suffix = f"{prompt_id} s{seed}"
    name = f"{base} / {suffix}" if prompt_id != "primary" else f"{base} s{seed}"
    return name[:64]


def plan_jobs(
    recipe: dict[str, Any],
    mode: PlanMode = "primary",
    seed: int | None = None,
    draft: bool = False,
    prompt_id: str | None = None,
) -> list[WorldJob]:
    model = str(recipe["draft_model"] if draft else recipe.get("model") or "marble-1.1")
    prompts = _prompts(recipe, mode)
    if prompt_id:
        prompts = [item for item in prompts if item[0] == prompt_id]
        if not prompts:
            available = ", ".join(item[0] for item in _prompts(recipe, "family"))
            raise ValueError(f"Unknown prompt_id {prompt_id!r}. Available: {available}")
    jobs: list[WorldJob] = []
    for prompt_name, text in prompts:
        for job_seed in _seeds(recipe, mode, seed):
            jobs.append(
                WorldJob(
                    recipe_id=str(recipe["id"]),
                    prompt_id=prompt_name,
                    text_prompt=text,
                    display_name=_display_name(recipe, prompt_name, job_seed),
                    model=model,
                    seed=job_seed,
                    tags=list(recipe.get("tags") or []),
                    permission=dict(recipe.get("permission") or {"public": False}),
                    experiment=recipe.get("experiment"),
                )
            )
    return jobs
