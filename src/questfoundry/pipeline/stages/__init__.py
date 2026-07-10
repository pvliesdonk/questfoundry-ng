from questfoundry.models.base import Stage
from questfoundry.pipeline.research import with_research
from questfoundry.pipeline.stages.brainstorm import BRAINSTORM_STAGE
from questfoundry.pipeline.stages.dream import DREAM_STAGE
from questfoundry.pipeline.stages.dress import DRESS_STAGE
from questfoundry.pipeline.stages.fill import FILL_STAGE
from questfoundry.pipeline.stages.grow import GROW_STAGE
from questfoundry.pipeline.stages.polish import POLISH_STAGE
from questfoundry.pipeline.stages.seed import SEED_STAGE
from questfoundry.pipeline.types import StageImpl

# Every stage runs behind a research head pass (design doc 02 §1); the
# pass skips itself on corpus-less projects, so wrapping here is free
# for them and keeps stage modules unaware of M6.
IMPLS: dict[Stage, StageImpl] = {
    stage: with_research(impl)
    for stage, impl in {
        Stage.DREAM: DREAM_STAGE,
        Stage.BRAINSTORM: BRAINSTORM_STAGE,
        Stage.SEED: SEED_STAGE,
        Stage.GROW: GROW_STAGE,
        Stage.POLISH: POLISH_STAGE,
        Stage.FILL: FILL_STAGE,
        Stage.DRESS: DRESS_STAGE,
    }.items()
}

__all__ = ["IMPLS"]
