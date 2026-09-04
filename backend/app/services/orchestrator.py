"""Recovery Orchestrator.

Owns every journey and is the only component allowed to start one. Centralising ownership is
what prevents recovery collisions: a customer is claimed by exactly one journey, so two
agents can never contact the same person in parallel.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import RecoveryContext
from app.agents.executor import Executor
from app.agents.learner import Learner
from app.agents.pipeline import RecoveryPipeline
from app.agents.verifier import Verifier
from app.core.clock import after, as_utc, minutes, utcnow
from app.core.config import settings
from app.core.constants import (
    ActionStatus,
    ActionType,
    Actor,
    AuditEvent,
    Cohort,
    EventStatus,
    GatewayStatus,
    JourneyState,
    PolicyRule,
    PolicyVerdict,
)
from app.core.logging import get_logger
from app.core.money import format_inr
from app.data.catalog import intervention
from app.engines import degradation as degradation_engine
from app.engines.decision import DecisionOutcome
from app.engines.degradation import DegradationState
from app.integrations.razorpay import build_request, get_gateway
from app.models.event import RevenueEvent
from app.models.journey import Decision, RecoveryAction, RecoveryJourney
from app.services import audit, idempotency
from app.services import journey as journey_service
from app.services.policy import BudgetState, PolicyEngine, explain, load_engine

log = get_logger(__name__)


#: How a guardrail verdict reads inside a sentence rather than as a key.
VERDICT_PHRASE: dict[PolicyVerdict, str] = {
    PolicyVerdict.ALLOW: "allowed",
    PolicyVerdict.REQUIRE_APPROVAL: "approval needed",
    PolicyVerdict.BLOCK: "blocked",
}


# How long a customer lock is held, generous enough to outlive a journey.
CUSTOMER_LOCK_TTL_SECONDS = 24 * 60 * 60
# Control-cohort events settle organically after this much real-world time.
CONTROL_SETTLE_HOURS = 8.0


@dataclass(slots=True)
class ScanReport:
    scanned: int = 0
    journeys_started: int = 0
    do_nothing: int = 0
    awaiting_approval: int = 0
    blocked: int = 0
    held_out: int = 0
    collisions: int = 0
    expected_recovery_paise: int = 0
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "scanned": self.scanned,
            "journeys_started": self.journeys_started,
            "do_nothing": self.do_nothing,
            "awaiting_approval": self.awaiting_approval,
            "blocked": self.blocked,
            "held_out": self.held_out,
            "collisions": self.collisions,
            "expected_recovery_paise": self.expected_recovery_paise,
            "notes": self.notes,
        }


@dataclass(slots=True)
class TickReport:
    executed: int = 0
    verified: int = 0
    recovered: int = 0
    recovered_paise: int = 0
    blocked: int = 0
    advanced: int = 0
    closed: int = 0
    expired: int = 0
    control_settled: int = 0

    def as_dict(self) -> dict:
        return {
            "executed": self.executed,
            "verified": self.verified,
            "recovered": self.recovered,
            "recovered_paise": self.recovered_paise,
            "blocked": self.blocked,
            "advanced": self.advanced,
            "closed": self.closed,
            "expired": self.expired,
            "control_settled": self.control_settled,
        }


class Orchestrator:
    def __init__(self) -> None:
        self.pipeline = RecoveryPipeline()
        self.executor = Executor()
        self.verifier = Verifier()
        self.learner = Learner()

    # ---------------------------------------------------------------- detection

    async def scan(self, session: AsyncSession, *, limit: int = 40) -> ScanReport:
        report = ScanReport()
        policy = await load_engine(session)
        state = await degradation_engine.detect(session)
        await degradation_engine.reconcile_windows(session, state)

        events = await self._unclaimed_events(session, limit)
        for index, event in enumerate(events):
            report.scanned += 1
            ctx = RecoveryContext(
                session=session,
                event=event,
                customer=event.customer,
                policy=policy,
                degradation=state,
                budget=BudgetState(journey_paused=policy.spec.paused),
                allow_reasoner=index < settings.llm_max_events_per_scan,
            )
            await self.pipeline.plan(ctx)

            if not ctx.worth_pursuing:
                event.status = EventStatus.SUPPRESSED
                report.blocked += 1
                await self._audit_detection(session, ctx, ctx.skip_reason)
                continue

            decision = await self._persist_decision(session, ctx)
            if Cohort(event.cohort) is Cohort.CONTROL:
                # Untouched holdout: needed so incremental recovery can be measured.
                report.held_out += 1
                decision.rationale = [
                    "Assigned to the control holdout, so no intervention is executed",
                    *decision.rationale,
                ]
                continue
            if not ctx.decision.acts:
                event.status = EventStatus.SUPPRESSED
                report.do_nothing += 1
                continue
            if ctx.verdict is PolicyVerdict.BLOCK:
                event.status = EventStatus.SUPPRESSED
                report.blocked += 1
                continue

            if not await idempotency.claim_customer(
                event.customer_id, "pending", CUSTOMER_LOCK_TTL_SECONDS
            ):
                owner = await idempotency.customer_owner(event.customer_id)
                report.collisions += 1
                report.notes.append(f"{event.external_ref} deferred, customer owned by {owner}")
                decision.policy_reasons = [
                    *decision.policy_reasons,
                    str(PolicyRule.COLLISION_DETECTED),
                ]
                continue

            journey = await self._start_journey(session, ctx, decision)
            report.journeys_started += 1
            report.expected_recovery_paise += ctx.decision.chosen.expected_recovery_paise
            if JourneyState(journey.state) is JourneyState.AWAITING_APPROVAL:
                report.awaiting_approval += 1

        await session.flush()
        return report

    async def _unclaimed_events(self, session: AsyncSession, limit: int) -> list[RevenueEvent]:
        claimed = select(RecoveryJourney.event_id).where(
            RecoveryJourney.state.not_in(list(journey_service.TERMINAL_JOURNEY_STATES))
        )
        stmt = (
            select(RevenueEvent)
            .where(
                RevenueEvent.is_training.is_(False),
                RevenueEvent.status == EventStatus.AT_RISK,
                RevenueEvent.id.not_in(claimed),
            )
            .order_by(RevenueEvent.amount_paise.desc())
            .limit(limit)
        )
        return list((await session.execute(stmt)).unique().scalars().all())

    async def _audit_detection(
        self, session: AsyncSession, ctx: RecoveryContext, reason: str
    ) -> None:
        await audit.record(
            session,
            event_type=AuditEvent.EVENT_DETECTED,
            entity_type="revenue_event",
            entity_id=ctx.event.id,
            summary=reason or "Detected revenue at risk",
            payload={"risk_score": ctx.event.risk_score, "amount_paise": ctx.event.amount_paise},
            actor=Actor.AGENT,
            actor_name="sentinel",
        )

    async def _persist_decision(self, session: AsyncSession, ctx: RecoveryContext) -> Decision:
        outcome: DecisionOutcome = ctx.decision
        chosen = outcome.chosen
        decision = Decision(
            event_id=ctx.event.id,
            chosen_action=chosen.action,
            recovery_probability=chosen.probability,
            organic_probability=outcome.organic_probability,
            uplift=chosen.uplift,
            expected_recovery_paise=chosen.expected_recovery_paise,
            expected_value_paise=chosen.expected_value_paise,
            policy_verdict=ctx.verdict,
            policy_reasons=ctx.verdict_reasons,
            alternatives=[option.as_dict() for option in outcome.options],
            rationale=outcome.rationale,
            evidence=outcome.evidence,
            agent_trace=ctx.trace.as_list(),
            model_version=outcome.model_version,
            reasoning_provider=ctx.reasoning_provider,
        )
        session.add(decision)
        await session.flush()
        await audit.record(
            session,
            event_type=AuditEvent.DECISION_MADE,
            entity_type="decision",
            entity_id=decision.id,
            summary=(
                f"{chosen.label} for {format_inr(ctx.event.amount_paise)} "
                f"at {chosen.probability:.0%} recovery, "
                f"{VERDICT_PHRASE.get(ctx.verdict, audit.words(ctx.verdict))}"
            ),
            payload={
                "event_ref": ctx.event.external_ref,
                "action": str(chosen.action),
                "expected_value_paise": chosen.expected_value_paise,
                "verdict": str(ctx.verdict),
                "reasons": ctx.verdict_reasons,
            },
            actor=Actor.AGENT,
            actor_name="optimizer",
        )
        return decision

    async def _start_journey(
        self, session: AsyncSession, ctx: RecoveryContext, decision: Decision
    ) -> RecoveryJourney:
        from app.engines import learning

        event = ctx.event
        journey = RecoveryJourney(
            event_id=event.id,
            customer_id=event.customer_id,
            state=JourneyState.DETECTED,
            strategy_key=learning.context_key(event.kind, event.root_cause, ctx.customer.segment),
            plan=[step.as_dict() for step in ctx.decision.plan],
        )
        session.add(journey)
        await session.flush()
        ctx.journey = journey
        decision.journey_id = journey.id
        event.status = EventStatus.IN_RECOVERY

        # Re-point the customer lock now that a journey id exists.
        await idempotency.release_customer(event.customer_id)
        await idempotency.claim_customer(event.customer_id, journey.id, CUSTOMER_LOCK_TTL_SECONDS)

        journey_service.transition(journey, JourneyState.ANALYZING, reason="Diagnosis complete")
        journey_service.transition(journey, JourneyState.PLANNED, reason="Recovery journey planned")

        await self._schedule_step(session, ctx, journey, decision, step_index=0)
        await audit.record(
            session,
            event_type=AuditEvent.JOURNEY_TRANSITION,
            entity_type="recovery_journey",
            entity_id=journey.id,
            summary=f"Journey opened for {event.external_ref}, now {audit.words(journey.state)}",
            payload={"plan": journey.plan, "strategy_key": journey.strategy_key},
            actor=Actor.SYSTEM,
        )
        return journey

    async def _schedule_step(
        self,
        session: AsyncSession,
        ctx: RecoveryContext,
        journey: RecoveryJourney,
        decision: Decision | None,
        *,
        step_index: int,
    ) -> RecoveryAction | None:
        plan = journey.plan or []
        if step_index >= len(plan):
            return None
        step = plan[step_index]
        action_type = ActionType(step["action"])
        spec = intervention(action_type)
        option = next(
            (o for o in (ctx.decision.options if ctx.decision else []) if o.action is action_type),
            None,
        )
        discount_pct = option.discount_pct if option else 0.0

        verdict = ctx.policy.evaluate(
            action_type,
            event=ctx.event,
            customer=ctx.customer,
            budget=ctx.budget,
            discount_pct=discount_pct,
            degraded_route=ctx.degraded_route,
            now=utcnow(),
        )
        action = RecoveryAction(
            journey_id=journey.id,
            decision_id=decision.id if decision else None,
            sequence=step_index,
            action_type=action_type,
            idempotency_key=idempotency.build_key(journey.id, action_type, step_index),
            scheduled_at=after(minutes(float(step.get("delay_minutes", 0.0)))),
            cost_paise=spec.cost_paise,
            friction_score=spec.friction_score,
            discount_pct=discount_pct,
            status=ActionStatus.PLANNED,
            blocked_reasons=[str(reason) for reason in verdict.reasons],
        )
        journey.step_index = step_index
        journey.next_action_at = action.scheduled_at
        # Flush before auditing: the audit trail needs the generated action id.
        session.add(action)
        await session.flush()

        if verdict.verdict is PolicyVerdict.BLOCK:
            action.status = ActionStatus.BLOCKED
            journey.next_action_at = utcnow()
        elif verdict.verdict is PolicyVerdict.REQUIRE_APPROVAL:
            action.status = ActionStatus.AWAITING_APPROVAL
            journey_service.transition(
                journey, JourneyState.AWAITING_APPROVAL, reason="Human approval required"
            )
            await audit.record(
                session,
                event_type=AuditEvent.APPROVAL_REQUESTED,
                entity_type="recovery_action",
                entity_id=action.id,
                summary=(
                    f"{intervention(action_type).label} on "
                    f"{format_inr(ctx.event.amount_paise)} needs approval"
                ),
                payload={"reasons": action.blocked_reasons},
                actor=Actor.AGENT,
                actor_name="policy_officer",
            )
        await audit.record(
            session,
            event_type=AuditEvent.ACTION_SCHEDULED,
            entity_type="recovery_action",
            entity_id=action.id,
            summary=(
                f"{intervention(action_type).label} scheduled as step "
                f"{step_index + 1} of {len(plan)}"
            ),
            payload={"scheduled_at": action.scheduled_at.isoformat(), "status": str(action.status)},
            actor=Actor.SYSTEM,
        )
        return action

    # ----------------------------------------------------------------- execution

    async def tick(self, session: AsyncSession, *, limit: int | None = None) -> TickReport:
        report = TickReport()
        policy = await load_engine(session)
        if not policy.spec.automation_enabled:
            log.info("orchestrator.kill_switch_active")
            return report

        state = await degradation_engine.detect(session)
        for journey in await self._due_journeys(session, limit or settings.max_actions_per_tick):
            await self._advance(session, journey, policy, state, report)

        report.control_settled = await self._settle_control_cohort(session)
        await self._expire_stale(session, policy, report)
        await session.flush()
        return report

    async def _due_journeys(self, session: AsyncSession, limit: int) -> list[RecoveryJourney]:
        stmt = (
            select(RecoveryJourney)
            .where(
                RecoveryJourney.state.not_in(list(journey_service.TERMINAL_JOURNEY_STATES)),
                RecoveryJourney.next_action_at.is_not(None),
                RecoveryJourney.next_action_at <= utcnow(),
            )
            .order_by(RecoveryJourney.next_action_at)
            .limit(limit)
        )
        return list((await session.execute(stmt)).unique().scalars().all())

    def _context(
        self,
        session: AsyncSession,
        journey: RecoveryJourney,
        policy: PolicyEngine,
        state: DegradationState,
    ) -> RecoveryContext:
        event = journey.event
        last_contact = max(
            (
                as_utc(action.executed_at)
                for action in journey.actions
                if action.executed_at
                and intervention(ActionType(action.action_type)).consumes_contact
            ),
            default=None,
        )
        return RecoveryContext(
            session=session,
            event=event,
            customer=event.customer,
            policy=policy,
            degradation=state,
            journey=journey,
            budget=BudgetState(
                contacts_used=journey.contacts_used,
                retries_used=journey.retries_used,
                discounts_used=journey.discounts_used,
                voice_used=journey.voice_used,
                last_contact_at=last_contact,
                journey_paused=JourneyState(journey.state) is JourneyState.PAUSED
                or policy.spec.paused,
                journey_started_at=as_utc(journey.created_at) if journey.created_at else None,
            ),
        )

    @staticmethod
    def _consume_budget(
        journey: RecoveryJourney, event: RevenueEvent, action_type: ActionType
    ) -> None:
        spec = intervention(action_type)
        if spec.consumes_contact:
            journey.contacts_used += 1
            event.contacts_used += 1
        if action_type is ActionType.RETRY_PAYMENT:
            journey.retries_used += 1
        elif action_type is ActionType.DISCOUNT:
            journey.discounts_used += 1
        elif action_type is ActionType.VOICE:
            journey.voice_used += 1

    async def _advance(
        self,
        session: AsyncSession,
        journey: RecoveryJourney,
        policy: PolicyEngine,
        state: DegradationState,
        report: TickReport,
    ) -> None:
        ctx = self._context(session, journey, policy, state)
        action = journey.actions[-1] if journey.actions else None
        if action is None:
            journey.next_action_at = None
            return

        status = ActionStatus(action.status)
        if status is ActionStatus.AWAITING_APPROVAL:
            journey.next_action_at = None  # waits for a human, not for the clock
            return
        if status is ActionStatus.BLOCKED:
            report.blocked += 1
            await self._next_step_or_close(
                session, ctx, journey, report, reason="Action blocked by policy"
            )
            return

        if status in (ActionStatus.PLANNED, ActionStatus.APPROVED):
            if as_utc(action.scheduled_at) > utcnow():
                journey.next_action_at = as_utc(action.scheduled_at)
                return
            gate_verdict = await self._regate(session, ctx, action, report)
            if gate_verdict is PolicyVerdict.REQUIRE_APPROVAL:
                return  # waits for a human, not for the clock
            if gate_verdict is PolicyVerdict.BLOCK:
                await self._next_step_or_close(
                    session, ctx, journey, report, reason="Blocked on re-check before execution"
                )
                return
            journey_service.transition(
                journey, JourneyState.EXECUTING, reason=str(action.action_type)
            )
            gateway_status = await self.executor.execute(ctx, action)
            self._consume_budget(journey, ctx.event, ActionType(action.action_type))
            journey.cost_paise += action.cost_paise
            ctx.event.recovery_cost_paise += action.cost_paise
            report.executed += 1
            journey_service.transition(journey, JourneyState.VERIFYING, reason="Awaiting outcome")
            if gateway_status is GatewayStatus.PENDING:
                journey.next_action_at = after(
                    timedelta(seconds=float(action.result.get("resolve_after_seconds") or 900))
                )
                return
            status = ActionStatus(action.status)

        if JourneyState(journey.state) is not JourneyState.VERIFYING:
            journey_service.transition(journey, JourneyState.VERIFYING, reason="Awaiting outcome")

        outcome = await self.verifier.run(ctx, action)
        report.verified += 1
        if outcome is GatewayStatus.PENDING:
            journey.next_action_at = after(minutes(10))
            return

        recovered = outcome is GatewayStatus.SUCCEEDED
        await self.learner.run(ctx, action, recovered)
        if recovered:
            report.recovered += 1
            report.recovered_paise += ctx.event.recovered_amount_paise
            journey_service.transition(journey, JourneyState.RECOVERED, reason="Payment confirmed")
            await self._close(session, journey, reason="Recovered", report=report)
            return
        await self._next_step_or_close(
            session, ctx, journey, report, reason="Step did not recover the payment"
        )

    async def _regate(
        self,
        session: AsyncSession,
        ctx: RecoveryContext,
        action: RecoveryAction,
        report: TickReport,
    ) -> PolicyVerdict:
        """Authoritative check immediately before execution. Never overridden."""
        verdict = ctx.policy.evaluate(
            ActionType(action.action_type),
            event=ctx.event,
            customer=ctx.customer,
            budget=ctx.budget,
            discount_pct=action.discount_pct,
            degraded_route=ctx.degraded_route,
            now=utcnow(),
        )
        if verdict.verdict is PolicyVerdict.ALLOW:
            return PolicyVerdict.ALLOW
        action.status = (
            ActionStatus.AWAITING_APPROVAL
            if verdict.verdict is PolicyVerdict.REQUIRE_APPROVAL
            else ActionStatus.BLOCKED
        )
        action.blocked_reasons = [str(reason) for reason in verdict.reasons]
        await audit.record(
            session,
            event_type=AuditEvent.ACTION_BLOCKED,
            entity_type="recovery_action",
            entity_id=action.id,
            summary=(
                f"{intervention(ActionType(action.action_type)).label} stopped at the gate: "
                f"{'; '.join(explain(action.blocked_reasons))}"
            ),
            payload={"verdict": str(verdict.verdict), "reasons": action.blocked_reasons},
            actor=Actor.AGENT,
            actor_name="policy_officer",
        )
        if action.status is ActionStatus.AWAITING_APPROVAL:
            journey_service.transition(
                ctx.journey, JourneyState.AWAITING_APPROVAL, reason="Approval required at execution"
            )
            ctx.journey.next_action_at = None
        report.blocked += 1
        return verdict.verdict

    async def _next_step_or_close(
        self,
        session: AsyncSession,
        ctx: RecoveryContext,
        journey: RecoveryJourney,
        report: TickReport,
        *,
        reason: str,
    ) -> None:
        next_index = journey.step_index + 1
        if next_index < len(journey.plan or []):
            if JourneyState(journey.state) is not JourneyState.PLANNED:
                journey_service.transition(journey, JourneyState.PLANNED, reason=reason)
            scheduled = await self._schedule_step(
                session, ctx, journey, None, step_index=next_index
            )
            if scheduled is not None:
                report.advanced += 1
                return
        journey_service.transition(journey, JourneyState.FAILED, reason=reason)
        ctx.event.status = EventStatus.LOST
        ctx.event.resolved_at = utcnow()
        await self._close(session, journey, reason=reason, report=report)

    async def _close(
        self, session: AsyncSession, journey: RecoveryJourney, *, reason: str, report: TickReport
    ) -> None:
        journey_service.transition(journey, JourneyState.CLOSED, reason=reason)
        await idempotency.release_customer(journey.customer_id)
        report.closed += 1
        await audit.record(
            session,
            event_type=AuditEvent.JOURNEY_CLOSED,
            entity_type="recovery_journey",
            entity_id=journey.id,
            summary=f"Journey closed: {reason}",
            payload={
                "recovered_paise": journey.recovered_amount_paise,
                "cost_paise": journey.cost_paise,
                "contacts_used": journey.contacts_used,
            },
            actor=Actor.SYSTEM,
        )

    async def _expire_stale(
        self, session: AsyncSession, policy: PolicyEngine, report: TickReport
    ) -> None:
        cutoff = utcnow() - timedelta(hours=policy.spec.journey_ttl_hours)
        stmt = select(RecoveryJourney).where(
            RecoveryJourney.state.not_in(list(journey_service.TERMINAL_JOURNEY_STATES)),
            RecoveryJourney.created_at < cutoff,
        )
        for journey in (await session.execute(stmt)).unique().scalars().all():
            journey_service.transition(
                journey, JourneyState.EXPIRED, reason="Journey exceeded its TTL"
            )
            journey.event.status = EventStatus.LOST
            await self._close(session, journey, reason="Expired", report=report)
            report.expired += 1

    async def _settle_control_cohort(self, session: AsyncSession) -> int:
        """Resolve holdout events organically so the control arm has real outcomes."""
        cutoff = utcnow() - timedelta(hours=CONTROL_SETTLE_HOURS / max(settings.clock_speedup, 1.0))
        stmt = select(RevenueEvent).where(
            RevenueEvent.is_training.is_(False),
            RevenueEvent.cohort == Cohort.CONTROL,
            RevenueEvent.status.in_([EventStatus.AT_RISK, EventStatus.SUPPRESSED]),
            RevenueEvent.occurred_at < cutoff,
        )
        events = list((await session.execute(stmt)).unique().scalars().all())
        gateway = get_gateway()
        settled = 0
        for event in events:
            request = build_request(
                event,
                event.customer,
                ActionType.DO_NOTHING,
                idempotency_key=f"control-{event.id}",
                provider_ref=f"organic_{event.id[:12]}",
            )
            result = await gateway.fetch_state(request)
            event.applied_action = ActionType.DO_NOTHING
            event.resolved_at = utcnow()
            if result.status is GatewayStatus.SUCCEEDED:
                event.status = EventStatus.RECOVERED
                event.recovered_amount_paise = event.amount_paise
            else:
                event.status = EventStatus.LOST
            settled += 1
        return settled

    # ------------------------------------------------------------ human controls

    async def approve_action(
        self, session: AsyncSession, action_id: str, *, approver: str, note: str = ""
    ) -> RecoveryAction:
        action = await self._require_action(session, action_id)
        journey = action.journey
        action.status = ActionStatus.APPROVED
        action.scheduled_at = utcnow()
        if JourneyState(journey.state) is JourneyState.AWAITING_APPROVAL:
            journey_service.transition(
                journey, JourneyState.APPROVED, reason=f"Approved by {approver}"
            )
        journey.next_action_at = utcnow()
        await audit.record(
            session,
            event_type=AuditEvent.APPROVAL_GRANTED,
            entity_type="recovery_action",
            entity_id=action.id,
            summary=f"{intervention(ActionType(action.action_type)).label} approved by {approver}",
            payload={"note": note, "reasons": action.blocked_reasons},
            actor=Actor.HUMAN,
            actor_name=approver,
        )
        await session.flush()
        return action

    async def reject_action(
        self, session: AsyncSession, action_id: str, *, approver: str, reason: str = ""
    ) -> RecoveryAction:
        action = await self._require_action(session, action_id)
        journey = action.journey
        action.status = ActionStatus.CANCELLED
        action.error = reason or "Rejected by reviewer"
        journey_service.transition(journey, JourneyState.BLOCKED, reason=f"Rejected by {approver}")
        journey.event.status = EventStatus.SUPPRESSED
        await audit.record(
            session,
            event_type=AuditEvent.APPROVAL_REJECTED,
            entity_type="recovery_action",
            entity_id=action.id,
            summary=f"{intervention(ActionType(action.action_type)).label} rejected by {approver}",
            payload={"reason": reason},
            actor=Actor.HUMAN,
            actor_name=approver,
        )
        await self._close(session, journey, reason="Rejected by reviewer", report=TickReport())
        await session.flush()
        return action

    async def pause_journey(
        self, session: AsyncSession, journey_id: str, *, actor: str
    ) -> RecoveryJourney:
        journey = await self._require_journey(session, journey_id)
        journey_service.transition(journey, JourneyState.PAUSED, reason=f"Paused by {actor}")
        journey.next_action_at = None
        await self._journey_audit(session, journey, f"Journey paused by {actor}")
        await session.flush()
        return journey

    async def resume_journey(
        self, session: AsyncSession, journey_id: str, *, actor: str
    ) -> RecoveryJourney:
        journey = await self._require_journey(session, journey_id)
        target = (
            JourneyState.APPROVED
            if journey.actions and ActionStatus(journey.actions[-1].status) is ActionStatus.APPROVED
            else JourneyState.PLANNED
        )
        journey_service.transition(journey, target, reason=f"Resumed by {actor}")
        journey.next_action_at = utcnow()
        await self._journey_audit(session, journey, f"Journey resumed by {actor}")
        await session.flush()
        return journey

    async def close_journey(
        self, session: AsyncSession, journey_id: str, *, actor: str, reason: str = ""
    ) -> RecoveryJourney:
        journey = await self._require_journey(session, journey_id)
        if not journey_service.is_terminal(journey):
            journey_service.transition(
                journey, JourneyState.BLOCKED, reason=reason or f"Stopped by {actor}"
            )
        await self._close(
            session, journey, reason=reason or f"Stopped by {actor}", report=TickReport()
        )
        await session.flush()
        return journey

    async def set_kill_switch(self, session: AsyncSession, *, enabled: bool, actor: str) -> dict:
        from app.services.policy import get_active_policy

        config = await get_active_policy(session)
        config.automation_enabled = enabled
        if not enabled:
            stmt = select(RecoveryJourney).where(
                RecoveryJourney.state.not_in(list(journey_service.TERMINAL_JOURNEY_STATES))
            )
            for journey in (await session.execute(stmt)).unique().scalars().all():
                journey.next_action_at = None
        await audit.record(
            session,
            event_type=AuditEvent.KILL_SWITCH_TOGGLED,
            entity_type="policy_config",
            entity_id=config.id,
            summary=f"Recovery automation {'enabled' if enabled else 'halted'} by {actor}",
            payload={"automation_enabled": enabled},
            actor=Actor.HUMAN,
            actor_name=actor,
        )
        await session.flush()
        return {"automation_enabled": enabled}

    async def _journey_audit(
        self, session: AsyncSession, journey: RecoveryJourney, summary: str
    ) -> None:
        await audit.record(
            session,
            event_type=AuditEvent.JOURNEY_TRANSITION,
            entity_type="recovery_journey",
            entity_id=journey.id,
            summary=summary,
            payload={"state": str(journey.state)},
            actor=Actor.HUMAN,
        )

    @staticmethod
    async def _require_action(session: AsyncSession, action_id: str) -> RecoveryAction:
        from app.core.errors import NotFoundError

        action = (
            await session.execute(select(RecoveryAction).where(RecoveryAction.id == action_id))
        ).scalar_one_or_none()
        if action is None:
            raise NotFoundError(f"Action {action_id} not found")
        return action

    @staticmethod
    async def _require_journey(session: AsyncSession, journey_id: str) -> RecoveryJourney:
        from app.core.errors import NotFoundError

        journey = (
            (await session.execute(select(RecoveryJourney).where(RecoveryJourney.id == journey_id)))
            .unique()
            .scalar_one_or_none()
        )
        if journey is None:
            raise NotFoundError(f"Journey {journey_id} not found")
        return journey


orchestrator = Orchestrator()
