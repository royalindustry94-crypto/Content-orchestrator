-- Running upgrade 0017 -> 0018

CREATE TYPE stage_assignment_status AS ENUM ('pending','dispatched','acknowledged','completed','failed','cancelled');;

CREATE TABLE stage_assignments (
            id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id     uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            pipeline_run_id  uuid NOT NULL REFERENCES pipeline_runs(id) ON DELETE CASCADE,
            stage            content_stage NOT NULL,
            attempt_number   integer NOT NULL DEFAULT 1,
            worker_id        uuid REFERENCES worker_registry(id),
            status           stage_assignment_status NOT NULL DEFAULT 'pending',
            idempotency_key  text,
            lease_expires_at timestamptz,
            dispatched_at    timestamptz,
            acknowledged_at  timestamptz,
            completed_at     timestamptz,
            result           jsonb,
            correlation_id   uuid,
            trace_id         text,
            created_at       timestamptz NOT NULL DEFAULT now(),
            updated_at       timestamptz NOT NULL DEFAULT now(),
            version          integer NOT NULL DEFAULT 1
        );;

CREATE UNIQUE INDEX uq_stage_assignments_workspace_idem ON stage_assignments (workspace_id, idempotency_key) WHERE idempotency_key IS NOT NULL;;

CREATE INDEX ix_stage_assignments_lease ON stage_assignments (lease_expires_at) WHERE status IN ('dispatched','acknowledged');;

CREATE INDEX ix_stage_assignments_pending_stage ON stage_assignments (stage, created_at) WHERE status = 'pending';;

CREATE INDEX ix_stage_assignments_run ON stage_assignments (pipeline_run_id);;

CREATE INDEX ix_stage_assignments_worker ON stage_assignments (worker_id) WHERE worker_id IS NOT NULL;;

CREATE TRIGGER trg_stage_assignments_version BEFORE UPDATE ON stage_assignments FOR EACH ROW EXECUTE FUNCTION set_version_and_updated_at();;

ALTER TABLE stage_assignments ENABLE ROW LEVEL SECURITY;;

ALTER TABLE stage_assignments FORCE ROW LEVEL SECURITY;;

GRANT SELECT, INSERT, UPDATE, DELETE ON stage_assignments TO app_runtime;;

CREATE POLICY stage_assignments_select_member ON stage_assignments FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]));;

UPDATE alembic_version SET version_num='0018' WHERE alembic_version.version_num = '0017';

-- Running upgrade 0018 -> 0019

CREATE TYPE review_gate_status AS ENUM ('awaiting','approved','rejected','timed_out','escalated');;

CREATE TABLE review_gates (
            id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id     uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            pipeline_run_id  uuid NOT NULL REFERENCES pipeline_runs(id) ON DELETE CASCADE,
            stage            content_stage NOT NULL,
            status           review_gate_status NOT NULL DEFAULT 'awaiting',
            requested_at     timestamptz NOT NULL DEFAULT now(),
            timeout_at       timestamptz,
            decided_at       timestamptz,
            decided_by       uuid REFERENCES profiles(id),
            escalation_level integer NOT NULL DEFAULT 0,
            created_at       timestamptz NOT NULL DEFAULT now(),
            updated_at       timestamptz NOT NULL DEFAULT now(),
            version          integer NOT NULL DEFAULT 1
        );;

CREATE INDEX ix_review_gates_run ON review_gates (pipeline_run_id);;

CREATE INDEX ix_review_gates_awaiting_timeout ON review_gates (timeout_at) WHERE status = 'awaiting';;

CREATE INDEX ix_review_gates_workspace_status ON review_gates (workspace_id, status);;

CREATE TRIGGER trg_review_gates_version BEFORE UPDATE ON review_gates FOR EACH ROW EXECUTE FUNCTION set_version_and_updated_at();;

ALTER TABLE review_gates ENABLE ROW LEVEL SECURITY;;

ALTER TABLE review_gates FORCE ROW LEVEL SECURITY;;

GRANT SELECT, INSERT, UPDATE, DELETE ON review_gates TO app_runtime;;

CREATE POLICY review_gates_select_member ON review_gates FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]));;

CREATE POLICY review_gates_insert_roles ON review_gates FOR INSERT WITH CHECK (app_user_has_workspace_role(workspace_id, ARRAY['admin','reviewer']::workspace_role[]));;

UPDATE alembic_version SET version_num='0019' WHERE alembic_version.version_num = '0018';

-- Running upgrade 0019 -> 0020

ALTER TABLE spend_reservations ADD COLUMN pipeline_run_id uuid REFERENCES pipeline_runs(id) ON DELETE CASCADE;;

CREATE INDEX ix_spend_reservations_run ON spend_reservations (pipeline_run_id) WHERE pipeline_run_id IS NOT NULL;;

UPDATE alembic_version SET version_num='0020' WHERE alembic_version.version_num = '0019';

-- Running upgrade 0020 -> 0021

CREATE OR REPLACE FUNCTION is_workspace_member(wsid uuid, uid uuid)
        RETURNS boolean
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = public
        AS $$
            SELECT EXISTS (
                SELECT 1 FROM workspace_memberships
                WHERE workspace_id = wsid AND user_id = uid
            );
        $$;;

CREATE OR REPLACE FUNCTION is_workspace_admin(wsid uuid, uid uuid)
        RETURNS boolean
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = public
        AS $$
            SELECT EXISTS (
                SELECT 1 FROM workspace_memberships
                WHERE workspace_id = wsid
                  AND user_id = uid
                  AND role = 'admin'
            );
        $$;;

DROP POLICY IF EXISTS memberships_select_same_workspace ON workspace_memberships;;

CREATE POLICY memberships_select_same_workspace ON workspace_memberships
            FOR SELECT USING (
                is_workspace_member(workspace_id, app_current_user_id())
            );;

DROP POLICY IF EXISTS memberships_write_admin_only ON workspace_memberships;;

CREATE POLICY memberships_write_admin_only ON workspace_memberships
            FOR ALL USING (
                is_workspace_admin(workspace_id, app_current_user_id())
            );;

DROP POLICY IF EXISTS workspaces_select_member ON workspaces;;

CREATE POLICY workspaces_select_member ON workspaces
            FOR SELECT USING (
                is_workspace_member(id, app_current_user_id())
            );;

DROP POLICY IF EXISTS workspaces_update_admin ON workspaces;;

CREATE POLICY workspaces_update_admin ON workspaces
            FOR UPDATE USING (
                is_workspace_admin(id, app_current_user_id())
            );;

UPDATE alembic_version SET version_num='0021' WHERE alembic_version.version_num = '0020';

-- Running upgrade 0021 -> 0022

DROP POLICY IF EXISTS memberships_write_admin_only ON workspace_memberships;;

CREATE POLICY memberships_insert ON workspace_memberships
            FOR INSERT
            WITH CHECK (
                is_workspace_admin(workspace_id, app_current_user_id())
                OR (
                    user_id = app_current_user_id()
                    AND role = 'admin'
                    AND EXISTS (
                        SELECT 1 FROM workspaces
                        WHERE id = workspace_id
                          AND created_by = app_current_user_id()
                    )
                    AND NOT EXISTS (
                        SELECT 1 FROM workspace_memberships existing
                        WHERE existing.workspace_id = workspace_memberships.workspace_id
                    )
                )
            );;

CREATE POLICY memberships_update ON workspace_memberships
            FOR UPDATE
            USING (is_workspace_admin(workspace_id, app_current_user_id()));;

CREATE POLICY memberships_delete ON workspace_memberships
            FOR DELETE
            USING (is_workspace_admin(workspace_id, app_current_user_id()));;

UPDATE alembic_version SET version_num='0022' WHERE alembic_version.version_num = '0021';

-- Running upgrade 0022 -> 0023

CREATE OR REPLACE FUNCTION is_workspace_creator(wsid uuid, uid uuid)
        RETURNS boolean
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = public
        AS $$
            SELECT EXISTS (
                SELECT 1 FROM workspaces
                WHERE id = wsid AND created_by = uid
            );
        $$;;

DROP POLICY IF EXISTS memberships_insert ON workspace_memberships;;

CREATE POLICY memberships_insert ON workspace_memberships
            FOR INSERT
            WITH CHECK (
                is_workspace_admin(workspace_id, app_current_user_id())
                OR (
                    user_id = app_current_user_id()
                    AND role = 'admin'
                    AND is_workspace_creator(workspace_id, app_current_user_id())
                    AND NOT EXISTS (
                        SELECT 1 FROM workspace_memberships existing
                        WHERE existing.workspace_id = workspace_memberships.workspace_id
                    )
                )
            );;

UPDATE alembic_version SET version_num='0023' WHERE alembic_version.version_num = '0022';

-- Running upgrade 0023 -> 0024

DROP POLICY IF EXISTS memberships_delete ON workspace_memberships;;

CREATE POLICY memberships_delete ON workspace_memberships
            FOR DELETE
            USING (
                is_workspace_admin(workspace_id, app_current_user_id())
                OR user_id = app_current_user_id()
            );;

UPDATE alembic_version SET version_num='0024' WHERE alembic_version.version_num = '0023';

-- Running upgrade 0024 -> 0025

ALTER TABLE worker_registry
            ADD COLUMN instance_key    text NOT NULL DEFAULT gen_random_uuid()::text,
            ADD COLUMN worker_version  text,
            ADD COLUMN drain           boolean NOT NULL DEFAULT false,
            ADD COLUMN deregistered_at timestamptz;;

CREATE UNIQUE INDEX uq_worker_registry_name_instance ON worker_registry (name, instance_key);;

ALTER TABLE worker_registry
            ADD CONSTRAINT ck_worker_registry_load_nonneg CHECK (current_load >= 0),
            ADD CONSTRAINT ck_worker_registry_load_capacity CHECK (current_load <= max_concurrency),
            ADD CONSTRAINT ck_worker_registry_max_concurrency CHECK (max_concurrency >= 1),
            ADD CONSTRAINT ck_worker_registry_deregistered_offline CHECK (
                deregistered_at IS NULL
                OR (status = 'offline' AND current_load = 0)
            );;

CREATE INDEX ix_worker_registry_live ON worker_registry (last_heartbeat_at) WHERE deregistered_at IS NULL AND drain = false;;

CREATE TYPE worker_credential_status AS ENUM ('active','revoked');;

CREATE TABLE worker_credentials (
            id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            worker_id    uuid NOT NULL REFERENCES worker_registry(id) ON DELETE CASCADE,
            workspace_id uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            secret_hash  text NOT NULL,
            status       worker_credential_status NOT NULL DEFAULT 'active',
            created_at   timestamptz NOT NULL DEFAULT now(),
            rotated_at   timestamptz,
            expires_at   timestamptz
        );;

CREATE INDEX ix_worker_credentials_worker_active ON worker_credentials (worker_id) WHERE status = 'active';;

ALTER TABLE worker_credentials ENABLE ROW LEVEL SECURITY;;

ALTER TABLE worker_credentials FORCE ROW LEVEL SECURITY;;

ALTER TABLE worker_registry ENABLE ROW LEVEL SECURITY;;

ALTER TABLE worker_registry FORCE ROW LEVEL SECURITY;;

CREATE POLICY workers_select ON worker_registry
            FOR SELECT
            USING (
                workspace_id IS NULL
                OR is_workspace_member(workspace_id, app_current_user_id())
            );;

ALTER TABLE worker_heartbeats ENABLE ROW LEVEL SECURITY;;

ALTER TABLE worker_heartbeats FORCE ROW LEVEL SECURITY;;

CREATE POLICY worker_heartbeats_admin_select ON worker_heartbeats
            FOR SELECT
            USING (
                EXISTS (
                    SELECT 1 FROM worker_registry wr
                    WHERE wr.id = worker_heartbeats.worker_id
                      AND wr.workspace_id IS NOT NULL
                      AND is_workspace_admin(wr.workspace_id, app_current_user_id())
                )
            );;

UPDATE alembic_version SET version_num='0025' WHERE alembic_version.version_num = '0024';

-- Running upgrade 0025 -> 0026

ALTER TABLE stage_assignments
            ADD COLUMN claimed_at  timestamptz,
            ADD COLUMN claimed_by  uuid REFERENCES worker_registry(id),
            ADD COLUMN claim_count integer NOT NULL DEFAULT 0,
            ADD COLUMN claim_token uuid;;

ALTER TABLE stage_assignments ADD CONSTRAINT ck_stage_assignments_claimed_by_matches CHECK (claimed_by IS NULL OR claimed_by = worker_id);;

CREATE INDEX ix_stage_assignments_claim ON stage_assignments (workspace_id, stage, created_at) WHERE status = 'pending';;

CREATE TYPE claim_outcome AS ENUM ('granted','no_work','capacity','ineligible');;

CREATE TABLE stage_claim_audit (
            id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id   uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            assignment_id  uuid REFERENCES stage_assignments(id) ON DELETE SET NULL,
            worker_id      uuid NOT NULL REFERENCES worker_registry(id),
            outcome        claim_outcome NOT NULL,
            stage          content_stage,
            detail         text,
            correlation_id uuid,
            created_at     timestamptz NOT NULL DEFAULT now()
        );;

CREATE INDEX ix_stage_claim_audit_ws_created ON stage_claim_audit (workspace_id, created_at);;

CREATE INDEX ix_stage_claim_audit_worker ON stage_claim_audit (worker_id, created_at);;

ALTER TABLE stage_claim_audit ENABLE ROW LEVEL SECURITY;;

ALTER TABLE stage_claim_audit FORCE ROW LEVEL SECURITY;;

GRANT SELECT ON stage_claim_audit TO app_runtime;;

CREATE POLICY stage_claim_audit_select_member ON stage_claim_audit FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]));;

UPDATE alembic_version SET version_num='0026' WHERE alembic_version.version_num = '0025';

-- Running upgrade 0026 -> 0027

ALTER TABLE stage_assignments
            ADD COLUMN lease_started_at timestamptz,
            ADD COLUMN lease_extension_count integer NOT NULL DEFAULT 0;;

CREATE INDEX ix_stage_assignments_worker_active
        ON stage_assignments (worker_id)
        WHERE status = ANY (ARRAY[
            'dispatched'::stage_assignment_status,
            'acknowledged'::stage_assignment_status
        ])
        AND worker_id IS NOT NULL;;

CREATE TYPE recovery_reason AS ENUM ('lease_expired','worker_offline','worker_deregistered','worker_revoked','worker_restart','max_lease_exceeded');;

CREATE TYPE recovery_outcome AS ENUM ('requeued','dead_lettered','skipped');;

CREATE TABLE stage_recovery_audit (
            id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id        uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            assignment_id       uuid NOT NULL,
            previous_worker_id  uuid,
            reason              recovery_reason NOT NULL,
            previous_status     text NOT NULL,
            previous_attempt    integer NOT NULL,
            new_attempt         integer,
            outcome             recovery_outcome NOT NULL,
            detail              text,
            correlation_id      uuid,
            created_at          timestamptz NOT NULL DEFAULT now()
        );;

CREATE INDEX ix_stage_recovery_audit_ws_created ON stage_recovery_audit (workspace_id, created_at);;

CREATE INDEX ix_stage_recovery_audit_assignment ON stage_recovery_audit (assignment_id, created_at);;

ALTER TABLE stage_recovery_audit ENABLE ROW LEVEL SECURITY;;

ALTER TABLE stage_recovery_audit FORCE ROW LEVEL SECURITY;;

GRANT SELECT ON stage_recovery_audit TO app_runtime;;

CREATE POLICY stage_recovery_audit_select_member ON stage_recovery_audit FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]));;

CREATE TRIGGER trg_stage_recovery_audit_immutable BEFORE UPDATE ON stage_recovery_audit FOR EACH ROW EXECUTE FUNCTION prevent_update();;

CREATE TABLE provider_effect_keys (
            id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id     uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            assignment_id    uuid NOT NULL,
            attempt_number   integer NOT NULL,
            effect_key       text NOT NULL,
            effect_kind      text NOT NULL,
            created_at       timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT uq_provider_effect_keys_ws_key UNIQUE (workspace_id, effect_key)
        );;

CREATE INDEX ix_provider_effect_keys_assignment ON provider_effect_keys (assignment_id, attempt_number);;

ALTER TABLE provider_effect_keys ENABLE ROW LEVEL SECURITY;;

ALTER TABLE provider_effect_keys FORCE ROW LEVEL SECURITY;;

GRANT SELECT ON provider_effect_keys TO app_runtime;;

CREATE POLICY provider_effect_keys_select_member ON provider_effect_keys FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]));;

CREATE TRIGGER trg_provider_effect_keys_immutable BEFORE UPDATE ON provider_effect_keys FOR EACH ROW EXECUTE FUNCTION prevent_update();;

UPDATE alembic_version SET version_num='0027' WHERE alembic_version.version_num = '0026';

-- Running upgrade 0027 -> 0028

CREATE OR REPLACE FUNCTION prevent_delete() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'table % is immutable; row deletes are not permitted', TG_TABLE_NAME
                USING ERRCODE = 'restrict_violation';
        END;
        $$ LANGUAGE plpgsql;;

CREATE TRIGGER trg_stage_recovery_audit_immutable_delete BEFORE DELETE ON stage_recovery_audit FOR EACH ROW EXECUTE FUNCTION prevent_delete();;

CREATE TRIGGER trg_provider_effect_keys_immutable_delete BEFORE DELETE ON provider_effect_keys FOR EACH ROW EXECUTE FUNCTION prevent_delete();;

UPDATE alembic_version SET version_num='0028' WHERE alembic_version.version_num = '0027';

-- Running upgrade 0028 -> 0029

ALTER TABLE workspaces
            ADD COLUMN priority_tier smallint NOT NULL DEFAULT 0;;

ALTER TABLE workspaces ADD CONSTRAINT ck_workspaces_priority_tier CHECK (priority_tier >= 0 AND priority_tier <= 10);;

ALTER TABLE stage_assignments
            ADD COLUMN priority integer NOT NULL DEFAULT 0,
            ADD COLUMN provider text;;

CREATE INDEX ix_stage_assignments_claim_priority
        ON stage_assignments (workspace_id, priority DESC, created_at ASC)
        WHERE status = 'pending'::stage_assignment_status;;

CREATE INDEX ix_stage_assignments_provider_inflight
        ON stage_assignments (workspace_id, provider)
        WHERE status = ANY (ARRAY[
            'dispatched'::stage_assignment_status,
            'acknowledged'::stage_assignment_status
        ])
        AND provider IS NOT NULL;;

ALTER TABLE workspace_concurrency_limits
            ADD COLUMN queue_soft_limit integer NOT NULL DEFAULT 50,
            ADD COLUMN queue_hard_limit integer NOT NULL DEFAULT 200;;

ALTER TABLE workspace_concurrency_limits ADD CONSTRAINT ck_workspace_concurrency_queue_limits CHECK (queue_soft_limit > 0 AND queue_hard_limit >= queue_soft_limit);;

CREATE TYPE backpressure_state AS ENUM ('normal','pressured','throttled');;

CREATE TABLE workspace_backpressure_state (
            workspace_id   uuid PRIMARY KEY REFERENCES workspaces(id) ON DELETE CASCADE,
            state          backpressure_state NOT NULL DEFAULT 'normal',
            pending_depth  integer NOT NULL DEFAULT 0,
            entered_at     timestamptz,
            updated_at     timestamptz NOT NULL DEFAULT now(),
            version        integer NOT NULL DEFAULT 1
        );;

CREATE TRIGGER trg_workspace_backpressure_state_version BEFORE UPDATE ON workspace_backpressure_state FOR EACH ROW EXECUTE FUNCTION set_version_and_updated_at();;

ALTER TABLE workspace_backpressure_state ENABLE ROW LEVEL SECURITY;;

ALTER TABLE workspace_backpressure_state FORCE ROW LEVEL SECURITY;;

GRANT SELECT ON workspace_backpressure_state TO app_runtime;;

CREATE POLICY workspace_backpressure_state_select_member ON workspace_backpressure_state FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]));;

CREATE TABLE provider_concurrency_budgets (
            id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id    uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            provider        text NOT NULL,
            max_concurrent  integer NOT NULL,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            version         integer NOT NULL DEFAULT 1,
            CONSTRAINT uq_provider_concurrency_budgets_ws_provider
                UNIQUE (workspace_id, provider),
            CONSTRAINT ck_provider_concurrency_budgets_max
                CHECK (max_concurrent > 0)
        );;

CREATE TRIGGER trg_provider_concurrency_budgets_version BEFORE UPDATE ON provider_concurrency_budgets FOR EACH ROW EXECUTE FUNCTION set_version_and_updated_at();;

ALTER TABLE provider_concurrency_budgets ENABLE ROW LEVEL SECURITY;;

ALTER TABLE provider_concurrency_budgets FORCE ROW LEVEL SECURITY;;

GRANT SELECT ON provider_concurrency_budgets TO app_runtime;;

CREATE POLICY provider_concurrency_budgets_select_member ON provider_concurrency_budgets FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]));;

CREATE INDEX ix_provider_concurrency_budgets_ws ON provider_concurrency_budgets (workspace_id);;

UPDATE alembic_version SET version_num='0029' WHERE alembic_version.version_num = '0028';

-- Running upgrade 0029 -> 0030

CREATE TABLE local_auth_credentials (
    user_id UUID NOT NULL, 
    email VARCHAR NOT NULL, 
    password_hash TEXT NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (user_id), 
    CONSTRAINT uq_local_auth_credentials_email UNIQUE (email), 
    FOREIGN KEY(user_id) REFERENCES profiles (id) ON DELETE CASCADE
);

GRANT SELECT, INSERT, UPDATE ON local_auth_credentials TO app_runtime;;

UPDATE alembic_version SET version_num='0030' WHERE alembic_version.version_num = '0029';

-- Running upgrade 0030 -> 0031_spend_precision

ALTER TABLE spend_caps
            ALTER COLUMN daily_cap_usd TYPE numeric(12,4)
                USING daily_cap_usd::numeric(12,4),
            ALTER COLUMN monthly_cap_usd TYPE numeric(12,4)
                USING monthly_cap_usd::numeric(12,4);;

UPDATE alembic_version SET version_num='0031_spend_precision' WHERE alembic_version.version_num = '0030';

-- Running upgrade 0030 -> 0031_fk

CREATE INDEX IF NOT EXISTS ix_workspaces_created_by ON workspaces (created_by);;

CREATE INDEX IF NOT EXISTS ix_workspace_memberships_user_id ON workspace_memberships (user_id);;

CREATE INDEX IF NOT EXISTS ix_content_pillars_created_by ON content_pillars (created_by);;

CREATE INDEX IF NOT EXISTS ix_content_pillars_updated_by ON content_pillars (updated_by);;

CREATE INDEX IF NOT EXISTS ix_spend_caps_created_by ON spend_caps (created_by);;

CREATE INDEX IF NOT EXISTS ix_spend_caps_updated_by ON spend_caps (updated_by);;

CREATE INDEX IF NOT EXISTS ix_provider_credentials_created_by ON provider_credentials (created_by);;

CREATE INDEX IF NOT EXISTS ix_provider_credentials_updated_by ON provider_credentials (updated_by);;

CREATE INDEX IF NOT EXISTS ix_content_items_created_by ON content_items (created_by);;

CREATE INDEX IF NOT EXISTS ix_content_items_updated_by ON content_items (updated_by);;

CREATE INDEX IF NOT EXISTS ix_content_items_pillar_id ON content_items (pillar_id);;

CREATE INDEX IF NOT EXISTS ix_content_items_current_pipeline_run_id ON content_items (current_pipeline_run_id);;

CREATE INDEX IF NOT EXISTS ix_content_items_current_version_id ON content_items (current_version_id);;

CREATE INDEX IF NOT EXISTS ix_content_versions_created_by ON content_versions (created_by);;

CREATE INDEX IF NOT EXISTS ix_pipeline_runs_definition_id ON pipeline_runs (definition_id);;

CREATE INDEX IF NOT EXISTS ix_pipeline_stage_runs_content_item_id ON pipeline_stage_runs (content_item_id);;

CREATE INDEX IF NOT EXISTS ix_assets_content_version_id ON assets (content_version_id);;

CREATE INDEX IF NOT EXISTS ix_assets_created_by ON assets (created_by);;

CREATE INDEX IF NOT EXISTS ix_assets_updated_by ON assets (updated_by);;

CREATE INDEX IF NOT EXISTS ix_publish_jobs_created_by ON publish_jobs (created_by);;

CREATE INDEX IF NOT EXISTS ix_publish_jobs_updated_by ON publish_jobs (updated_by);;

CREATE INDEX IF NOT EXISTS ix_review_decisions_content_version_id ON review_decisions (content_version_id);;

CREATE INDEX IF NOT EXISTS ix_review_decisions_reviewer_id ON review_decisions (reviewer_id);;

CREATE INDEX IF NOT EXISTS ix_spend_logs_content_item_id ON spend_logs (content_item_id);;

CREATE INDEX IF NOT EXISTS ix_spend_reservations_content_item_id ON spend_reservations (content_item_id);;

CREATE INDEX IF NOT EXISTS ix_provider_usage_pipeline_stage_run_id ON provider_usage (pipeline_stage_run_id);;

CREATE INDEX IF NOT EXISTS ix_content_lineage_created_by ON content_lineage (created_by);;

CREATE INDEX IF NOT EXISTS ix_workflow_definitions_created_by ON workflow_definitions (created_by);;

CREATE INDEX IF NOT EXISTS ix_workflow_stages_workspace_id ON workflow_stages (workspace_id);;

CREATE INDEX IF NOT EXISTS ix_workflow_transitions_workspace_id ON workflow_transitions (workspace_id);;

CREATE INDEX IF NOT EXISTS ix_worker_registry_workspace_id ON worker_registry (workspace_id);;

CREATE INDEX IF NOT EXISTS ix_stage_assignments_claimed_by ON stage_assignments (claimed_by);;

CREATE INDEX IF NOT EXISTS ix_review_gates_decided_by ON review_gates (decided_by);;

CREATE INDEX IF NOT EXISTS ix_worker_credentials_workspace_id ON worker_credentials (workspace_id);;

CREATE INDEX IF NOT EXISTS ix_stage_claim_audit_assignment_id ON stage_claim_audit (assignment_id);;

INSERT INTO alembic_version (version_num) VALUES ('0031_fk') RETURNING alembic_version.version_num;

