from __future__ import annotations

import random
from dataclasses import dataclass
from itertools import islice, product
from typing import Any, Iterator, Mapping

from tradingbotsuite.optimization.candidate import CandidateConfig


@dataclass(frozen=True, slots=True)
class SearchSpace:
    strategy_id: str
    parameters: Mapping[str, tuple[Any, ...]]
    feature_set_id: str = "features_full_context_no_wt"
    holding_window: str = "24h"
    exit_policy_id: str = "fixed_holding_window"
    exit_policy_params: Mapping[str, Any] | None = None

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "SearchSpace":
        raw_parameters = dict(payload.get("parameters") or payload.get("parameter_space") or {})
        parameters: dict[str, tuple[Any, ...]] = {}
        for key, value in raw_parameters.items():
            values = tuple(value) if isinstance(value, (list, tuple)) else (value,)
            if not values:
                raise ValueError(f"empty search-space values for parameter: {key}")
            parameters[str(key)] = values
        exit_policy_params = dict(payload.get("exit_policy_params") or {})
        if payload.get("target_return") is not None:
            exit_policy_params.setdefault("target_return", payload.get("target_return"))
        if payload.get("stop_return") is not None:
            exit_policy_params.setdefault("stop_return", payload.get("stop_return"))
        return cls(
            strategy_id=str(payload["strategy_id"]),
            parameters=parameters,
            feature_set_id=str(payload.get("feature_set_id", "features_full_context_no_wt")),
            holding_window=str(payload.get("holding_window", "24h")),
            exit_policy_id=str(payload.get("exit_policy_id", "fixed_holding_window")),
            exit_policy_params=exit_policy_params,
        )

    def expand(self, *, method: str = "grid", max_candidates: int = 64, random_seed: int = 17) -> list[CandidateConfig]:
        method = method.lower()
        keys = sorted(self.parameters)
        if not keys:
            return [self._candidate({})]
        max_candidates = max(1, int(max_candidates))
        if method == "grid":
            return list(islice(self.iter_grid(), max_candidates))
        if method == "random":
            rng = random.Random(random_seed)
            return [
                self._candidate({key: rng.choice(tuple(self.parameters[key])) for key in keys})
                for _ in range(max_candidates)
            ]
        if method in {"latin_hypercube", "coarse_lhs", "sobol"}:
            return [
                self._candidate(
                    {
                        key: tuple(self.parameters[key])[(index + key_index) % len(tuple(self.parameters[key]))]
                        for key_index, key in enumerate(keys)
                    }
                )
                for index in range(max_candidates)
            ]
        raise ValueError("method must be one of: grid, random, latin_hypercube, coarse_lhs, sobol")

    def grid_size(self) -> int:
        if not self.parameters:
            return 1
        total = 1
        for values in self.parameters.values():
            total *= len(tuple(values))
        return int(total)

    def iter_grid(self) -> Iterator[CandidateConfig]:
        keys = sorted(self.parameters)
        if not keys:
            yield self._candidate({})
            return
        for values in product(*(self.parameters[key] for key in keys)):
            yield self._candidate(dict(zip(keys, values, strict=True)))

    def local_neighbors(self, center: CandidateConfig, *, radius_steps: int = 1, max_candidates: int = 64) -> list[CandidateConfig]:
        keys = sorted(self.parameters)
        if not keys:
            return [self._candidate({})]
        choices: list[tuple[Any, ...]] = []
        for key in keys:
            values = tuple(self.parameters[key])
            current = center.parameters.get(key)
            if current not in values:
                choices.append((current,) if current is not None else values[:1])
                continue
            index = values.index(current)
            start = max(0, index - max(1, int(radius_steps)))
            end = min(len(values), index + max(1, int(radius_steps)) + 1)
            choices.append(values[start:end])
        return [
            self._candidate(dict(zip(keys, values, strict=True)))
            for values in islice(product(*choices), max(1, int(max_candidates)))
        ]

    def _candidate(self, parameters: Mapping[str, Any]) -> CandidateConfig:
        return CandidateConfig(
            strategy_id=self.strategy_id,
            parameters=dict(parameters),
            feature_set_id=self.feature_set_id,
            holding_window=self.holding_window,
            exit_policy_id=self.exit_policy_id,
            exit_policy_params=dict(self.exit_policy_params or {}),
        )
