from questfoundry.models.base import Stage
from questfoundry.pipeline.stages.brainstorm import BRAINSTORM_STAGE
from questfoundry.pipeline.stages.dream import DREAM_STAGE
from questfoundry.pipeline.stages.seed import SEED_STAGE
from questfoundry.pipeline.types import StageImpl

IMPLS: dict[Stage, StageImpl] = {
    Stage.DREAM: DREAM_STAGE,
    Stage.BRAINSTORM: BRAINSTORM_STAGE,
    Stage.SEED: SEED_STAGE,
}

__all__ = ["IMPLS"]
