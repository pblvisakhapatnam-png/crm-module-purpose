# Slice 5B Acceptance - Prototype Handoff / Agent Readiness Pack

## Automated checks

No backend or frontend code is changed by this slice.

Recommended checks:

```powershell
git diff --stat
```

Optional safety regression:

```powershell
docker compose exec backend pytest
```

## Manual documentation acceptance

Confirm these files exist and are readable:

```text
AGENTS.md
PBL's internal working instructions
docs/agent/PLAN.md
docs/agent/AGENT_HANDOFF.md
docs/agent/FUTURE_SLICES.md
docs/agent/DEFERRED_REQUIREMENTS.md
docs/agent/SKILLS_AND_TOOLS.md
docs/agent/UI_UX_CARRY_FORWARD.md
docs/agent/PRODUCTION_UPGRADE_READINESS.md
docs/continuity/NEXT_STEPS.md
```

## Content checks

Confirm the handoff documents clearly state:

```text
- Current foundation chain ends at Work Order shell.
- Account is UI term; business_party is internal/domain/database term.
- Commercial Offer credit/exposure gate is not the initial prospect credit assessment.
- Commercial Offer lines are future attachment points for line-level T&C, WO lines, pricing evidence, GST/site/billing details.
- T&C master and line-level customization are deferred future work.
- Work Order shell is not WO release/posting or Equipment Hiring execution.
- Future agent workstreams are listed in sensible order.
- UI/UX carry-forward is recorded.
- Skills/tools guidance is recorded.
```

## Acceptance result

Slice 5B is accepted when the documentation gives future agents enough guidance to continue without re-reading the whole chat history.
