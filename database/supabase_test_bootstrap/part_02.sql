-- Running upgrade 0009 -> 0010

CREATE TABLE spend_logs (
            id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id    uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            content_item_id uuid REFERENCES content_items(id),
            provider        text NOT NULL,
            stage           content_stage,
            units           numeric,
            cost_usd        numeric(10,4) NOT NULL CHECK (cost_usd >= 0),
            occurred_at     timestamptz NOT NULL DEFAULT now(),
            created_at      timestamptz NOT NULL DEFAULT now()
        );;

CREATE INDEX ix_spend_logs_workspace_time ON spend_logs (workspace_id, occurred_at DESC);;

CREATE INDEX ix_spend_logs_workspace_provider_time ON spend_logs (workspace_id, provider, occurred_at DESC);;

CREATE TRIGGER trg_spend_logs_immutable BEFORE UPDATE ON spend_logs FOR EACH ROW EXECUTE FUNCTION prevent_update();;

ALTER TABLE spend_logs ENABLE ROW LEVEL SECURITY;;

ALTER TABLE spend_logs FORCE ROW LEVEL SECURITY;;

GRANT SELECT, INSERT ON spend_logs TO app_runtime;;

CREATE POLICY spend_logs_select_member ON spend_logs FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]));;

CREATE TYPE reservation_status AS ENUM ('reserved','committed','released');;

CREATE TABLE spend_reservations (
            id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id       uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            content_item_id    uuid REFERENCES content_items(id),
            provider           text NOT NULL,
            stage              content_stage,
            estimated_cost_usd numeric(10,4) NOT NULL CHECK (estimated_cost_usd >= 0),
            status             reservation_status NOT NULL DEFAULT 'reserved',
            created_at         timestamptz NOT NULL DEFAULT now(),
            updated_at         timestamptz NOT NULL DEFAULT now(),
            version            integer NOT NULL DEFAULT 1
        );;

CREATE INDEX ix_spend_reservations_workspace_status ON spend_reservations (workspace_id, status) WHERE status = 'reserved';;

CREATE TRIGGER trg_spend_reservations_version BEFORE UPDATE ON spend_reservations FOR EACH ROW EXECUTE FUNCTION set_version_and_updated_at();;

ALTER TABLE spend_reservations ENABLE ROW LEVEL SECURITY;;

ALTER TABLE spend_reservations FORCE ROW LEVEL SECURITY;;

GRANT SELECT, INSERT, UPDATE, DELETE ON spend_reservations TO app_runtime;;

CREATE POLICY spend_reservations_select_member ON spend_reservations FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]));;

UPDATE alembic_version SET version_num='0010' WHERE alembic_version.version_num = '0009';

-- Running upgrade 0010 -> 0011

CREATE TABLE provider_usage (
            id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id          uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            content_item_id       uuid REFERENCES content_items(id),
            pipeline_stage_run_id uuid REFERENCES pipeline_stage_runs(id),
            provider              text NOT NULL,
            operation             text,
            quantity              numeric NOT NULL,
            unit_type             text NOT NULL,
            occurred_at           timestamptz NOT NULL,
            created_at            timestamptz NOT NULL DEFAULT now()
        );;

CREATE INDEX ix_provider_usage_workspace_provider_time ON provider_usage (workspace_id, provider, occurred_at DESC);;

CREATE INDEX ix_provider_usage_item ON provider_usage (content_item_id) WHERE content_item_id IS NOT NULL;;

CREATE TRIGGER trg_provider_usage_immutable BEFORE UPDATE ON provider_usage FOR EACH ROW EXECUTE FUNCTION prevent_update();;

ALTER TABLE provider_usage ENABLE ROW LEVEL SECURITY;;

ALTER TABLE provider_usage FORCE ROW LEVEL SECURITY;;

GRANT SELECT, INSERT ON provider_usage TO app_runtime;;

CREATE POLICY provider_usage_select_member ON provider_usage FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]));;

UPDATE alembic_version SET version_num='0011' WHERE alembic_version.version_num = '0010';

-- Running upgrade 0011 -> 0012

CREATE TYPE webhook_status AS ENUM ('received','processed','failed','duplicate');;

CREATE TABLE webhook_events (
            id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id       uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            source             text NOT NULL,
            external_event_id  text NOT NULL,
            signature_verified boolean NOT NULL,
            payload            jsonb NOT NULL,
            status             webhook_status NOT NULL DEFAULT 'received',
            received_at        timestamptz,
            processed_at       timestamptz,
            created_at         timestamptz NOT NULL DEFAULT now(),
            updated_at         timestamptz NOT NULL DEFAULT now(),
            version            integer NOT NULL DEFAULT 1,
            CONSTRAINT uq_webhook_source_event UNIQUE (source, external_event_id)
        );;

CREATE INDEX ix_webhook_events_status ON webhook_events (status) WHERE status IN ('received','failed');;

CREATE INDEX ix_webhook_events_workspace ON webhook_events (workspace_id);;

CREATE TRIGGER trg_webhook_events_version BEFORE UPDATE ON webhook_events FOR EACH ROW EXECUTE FUNCTION set_version_and_updated_at();;

ALTER TABLE webhook_events ENABLE ROW LEVEL SECURITY;;

ALTER TABLE webhook_events FORCE ROW LEVEL SECURITY;;

GRANT SELECT ON webhook_events TO app_runtime;;

CREATE POLICY webhook_events_select_member ON webhook_events FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

CREATE TYPE dead_letter_status AS ENUM ('pending','resolved','discarded');;

CREATE TABLE dead_letter_jobs (
            id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id    uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            related_table   text NOT NULL,
            related_id      uuid NOT NULL,
            job_type        text NOT NULL,
            payload         jsonb,
            failure_reason  text NOT NULL,
            attempt_count   integer NOT NULL CHECK (attempt_count >= 1),
            first_failed_at timestamptz NOT NULL,
            last_failed_at  timestamptz NOT NULL,
            status          dead_letter_status NOT NULL DEFAULT 'pending',
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            version         integer NOT NULL DEFAULT 1
        );;

CREATE INDEX ix_dead_letter_workspace_status ON dead_letter_jobs (workspace_id, status) WHERE status = 'pending';;

CREATE INDEX ix_dead_letter_related ON dead_letter_jobs (related_table, related_id);;

CREATE TRIGGER trg_dead_letter_jobs_version BEFORE UPDATE ON dead_letter_jobs FOR EACH ROW EXECUTE FUNCTION set_version_and_updated_at();;

ALTER TABLE dead_letter_jobs ENABLE ROW LEVEL SECURITY;;

ALTER TABLE dead_letter_jobs FORCE ROW LEVEL SECURITY;;

GRANT SELECT ON dead_letter_jobs TO app_runtime;;

CREATE POLICY dead_letter_jobs_select_member ON dead_letter_jobs FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

UPDATE alembic_version SET version_num='0012' WHERE alembic_version.version_num = '0011';

-- Running upgrade 0012 -> 0013

ALTER TABLE pipeline_runs ADD COLUMN idempotency_key text;;

CREATE UNIQUE INDEX uq_pipeline_runs_workspace_idem ON pipeline_runs (workspace_id, idempotency_key) WHERE idempotency_key IS NOT NULL;;

ALTER TABLE publish_jobs ADD COLUMN idempotency_key text;;

CREATE UNIQUE INDEX uq_publish_jobs_workspace_idem ON publish_jobs (workspace_id, idempotency_key) WHERE idempotency_key IS NOT NULL;;

ALTER TABLE webhook_events ADD COLUMN idempotency_key text;;

CREATE UNIQUE INDEX uq_webhook_events_workspace_idem ON webhook_events (workspace_id, idempotency_key) WHERE idempotency_key IS NOT NULL;;

ALTER TABLE assets
            ADD COLUMN storage_provider   text,
            ADD COLUMN storage_bucket     text,
            ADD COLUMN storage_object_key text,
            ADD COLUMN checksum           text,
            ADD COLUMN checksum_algorithm text,
            ADD COLUMN mime_type          text,
            ADD COLUMN size_bytes         bigint CHECK (size_bytes IS NULL OR size_bytes >= 0);;

ALTER TABLE pipeline_stage_runs ADD COLUMN provider_metadata jsonb;;

ALTER TABLE provider_usage ADD COLUMN provider_metadata jsonb;;

ALTER TABLE spend_logs ADD COLUMN provider_metadata jsonb;;

ALTER TABLE assets ADD COLUMN provider_metadata jsonb;;

CREATE TYPE content_lineage_relationship AS ENUM ('translated','remixed','clipped','derived');;

CREATE TABLE content_lineage (
            id                     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id           uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            parent_content_item_id uuid NOT NULL REFERENCES content_items(id) ON DELETE CASCADE,
            child_content_item_id  uuid NOT NULL REFERENCES content_items(id) ON DELETE CASCADE,
            relationship_type      content_lineage_relationship NOT NULL,
            notes                  text,
            created_at             timestamptz NOT NULL DEFAULT now(),
            created_by             uuid REFERENCES profiles(id),
            CONSTRAINT uq_content_lineage_edge
                UNIQUE (parent_content_item_id, child_content_item_id, relationship_type),
            CONSTRAINT ck_content_lineage_no_self
                CHECK (parent_content_item_id <> child_content_item_id)
        );;

CREATE INDEX ix_content_lineage_parent ON content_lineage (parent_content_item_id);;

CREATE INDEX ix_content_lineage_child ON content_lineage (child_content_item_id);;

CREATE INDEX ix_content_lineage_workspace ON content_lineage (workspace_id);;

CREATE TRIGGER trg_content_lineage_immutable BEFORE UPDATE ON content_lineage FOR EACH ROW EXECUTE FUNCTION prevent_update();;

ALTER TABLE content_lineage ENABLE ROW LEVEL SECURITY;;

ALTER TABLE content_lineage FORCE ROW LEVEL SECURITY;;

GRANT SELECT, INSERT ON content_lineage TO app_runtime;;

CREATE POLICY content_lineage_select_member ON content_lineage FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]));;

CREATE POLICY content_lineage_insert_roles ON content_lineage FOR INSERT WITH CHECK (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

UPDATE alembic_version SET version_num='0013' WHERE alembic_version.version_num = '0012';

-- Running upgrade 0013 -> 0014

ALTER TYPE pipeline_run_status ADD VALUE IF NOT EXISTS 'created';;

ALTER TYPE pipeline_run_status ADD VALUE IF NOT EXISTS 'paused';;

ALTER TYPE pipeline_run_status ADD VALUE IF NOT EXISTS 'compensating';;

ALTER TABLE pipeline_runs
            ADD COLUMN pause_reason text,
            ADD COLUMN definition_id uuid,
            ADD COLUMN correlation_id uuid,
            ADD COLUMN trace_id text;;

CREATE TYPE workflow_transition_trigger AS ENUM ('on_success','on_failure','on_review_approved','on_review_rejected');;

CREATE TABLE workflow_definitions (
            id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            name         text NOT NULL,
            version      integer NOT NULL,
            is_active    boolean NOT NULL DEFAULT true,
            created_at   timestamptz NOT NULL DEFAULT now(),
            created_by   uuid REFERENCES profiles(id),
            CONSTRAINT uq_workflow_definition_version UNIQUE (workspace_id, name, version)
        );;

CREATE INDEX ix_workflow_definitions_active ON workflow_definitions (workspace_id, name) WHERE is_active;;

CREATE TRIGGER trg_workflow_definitions_immutable BEFORE UPDATE ON workflow_definitions FOR EACH ROW EXECUTE FUNCTION prevent_update();;

ALTER TABLE workflow_definitions ENABLE ROW LEVEL SECURITY;;

ALTER TABLE workflow_definitions FORCE ROW LEVEL SECURITY;;

GRANT SELECT, INSERT ON workflow_definitions TO app_runtime;;

CREATE POLICY workflow_definitions_select_member ON workflow_definitions FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]));;

CREATE POLICY workflow_definitions_insert_roles ON workflow_definitions FOR INSERT WITH CHECK (app_user_has_workspace_role(workspace_id, ARRAY['admin']::workspace_role[]));;

CREATE TABLE workflow_stages (
            id                     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id           uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            definition_id          uuid NOT NULL REFERENCES workflow_definitions(id) ON DELETE CASCADE,
            stage_key              content_stage NOT NULL,
            ordinal                integer NOT NULL,
            max_attempts           integer NOT NULL DEFAULT 3,
            backoff_base_seconds   integer NOT NULL DEFAULT 5,
            backoff_multiplier     integer NOT NULL DEFAULT 2,
            backoff_max_seconds    integer NOT NULL DEFAULT 300,
            timeout_seconds        integer NOT NULL DEFAULT 600,
            is_review_gate         boolean NOT NULL DEFAULT false,
            is_terminal            boolean NOT NULL DEFAULT false,
            compensation_stage_key content_stage,
            created_at             timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT uq_workflow_stage_per_definition UNIQUE (definition_id, stage_key)
        );;

CREATE INDEX ix_workflow_stages_definition ON workflow_stages (definition_id, ordinal);;

CREATE TRIGGER trg_workflow_stages_immutable BEFORE UPDATE ON workflow_stages FOR EACH ROW EXECUTE FUNCTION prevent_update();;

ALTER TABLE workflow_stages ENABLE ROW LEVEL SECURITY;;

ALTER TABLE workflow_stages FORCE ROW LEVEL SECURITY;;

GRANT SELECT, INSERT ON workflow_stages TO app_runtime;;

CREATE POLICY workflow_stages_select_member ON workflow_stages FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]));;

CREATE POLICY workflow_stages_insert_roles ON workflow_stages FOR INSERT WITH CHECK (app_user_has_workspace_role(workspace_id, ARRAY['admin']::workspace_role[]));;

CREATE TABLE workflow_transitions (
            id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id   uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            definition_id  uuid NOT NULL REFERENCES workflow_definitions(id) ON DELETE CASCADE,
            from_stage     content_stage NOT NULL,
            to_stage       content_stage NOT NULL,
            trigger        workflow_transition_trigger NOT NULL,
            condition      jsonb,
            priority       integer NOT NULL DEFAULT 0,
            created_at     timestamptz NOT NULL DEFAULT now()
        );;

CREATE INDEX ix_workflow_transitions_lookup ON workflow_transitions (definition_id, from_stage, trigger);;

CREATE TRIGGER trg_workflow_transitions_immutable BEFORE UPDATE ON workflow_transitions FOR EACH ROW EXECUTE FUNCTION prevent_update();;

ALTER TABLE workflow_transitions ENABLE ROW LEVEL SECURITY;;

ALTER TABLE workflow_transitions FORCE ROW LEVEL SECURITY;;

GRANT SELECT, INSERT ON workflow_transitions TO app_runtime;;

CREATE POLICY workflow_transitions_select_member ON workflow_transitions FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]));;

CREATE POLICY workflow_transitions_insert_roles ON workflow_transitions FOR INSERT WITH CHECK (app_user_has_workspace_role(workspace_id, ARRAY['admin']::workspace_role[]));;

ALTER TABLE pipeline_runs ADD CONSTRAINT fk_pipeline_runs_definition FOREIGN KEY (definition_id) REFERENCES workflow_definitions(id);;

UPDATE alembic_version SET version_num='0014' WHERE alembic_version.version_num = '0013';

-- Running upgrade 0014 -> 0015

CREATE TYPE outbox_event_status AS ENUM ('pending','dispatched','poison');;

CREATE TABLE outbox_events (
            event_id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id      uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            event_type        text NOT NULL,
            event_version     integer NOT NULL DEFAULT 1,
            aggregate_type    text NOT NULL,
            aggregate_id      uuid NOT NULL,
            correlation_id    uuid NOT NULL,
            causation_id      uuid,
            trace_id          text,
            span_id           text,
            sequence          bigint NOT NULL,
            payload           jsonb NOT NULL,
            status            outbox_event_status NOT NULL DEFAULT 'pending',
            delivery_attempts integer NOT NULL DEFAULT 0,
            occurred_at       timestamptz NOT NULL DEFAULT now(),
            produced_by       text NOT NULL,
            version           integer NOT NULL DEFAULT 1,
            updated_at        timestamptz NOT NULL DEFAULT now()
        );;

CREATE INDEX ix_outbox_events_status_time ON outbox_events (status, occurred_at) WHERE status = 'pending';;

CREATE UNIQUE INDEX uq_outbox_events_aggregate_sequence ON outbox_events (aggregate_type, aggregate_id, sequence);;

CREATE INDEX ix_outbox_events_workspace ON outbox_events (workspace_id);;

CREATE INDEX ix_outbox_events_correlation ON outbox_events (correlation_id);;

CREATE TRIGGER trg_outbox_events_version BEFORE UPDATE ON outbox_events FOR EACH ROW EXECUTE FUNCTION set_version_and_updated_at();;

ALTER TABLE outbox_events ENABLE ROW LEVEL SECURITY;;

ALTER TABLE outbox_events FORCE ROW LEVEL SECURITY;;

GRANT SELECT, INSERT, UPDATE, DELETE ON outbox_events TO app_runtime;;

CREATE POLICY outbox_events_select_member ON outbox_events FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

CREATE TABLE event_consumers (
            id                     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            name                   text NOT NULL UNIQUE,
            max_event_version      integer NOT NULL DEFAULT 1,
            max_delivery_attempts  integer NOT NULL DEFAULT 10,
            created_at             timestamptz NOT NULL DEFAULT now(),
            updated_at             timestamptz NOT NULL DEFAULT now(),
            version                integer NOT NULL DEFAULT 1
        );;

CREATE TRIGGER trg_event_consumers_version BEFORE UPDATE ON event_consumers FOR EACH ROW EXECUTE FUNCTION set_version_and_updated_at();;

GRANT SELECT ON event_consumers TO app_runtime;;

CREATE TABLE consumer_checkpoints (
            id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            consumer_id     uuid NOT NULL REFERENCES event_consumers(id) ON DELETE CASCADE,
            aggregate_type  text NOT NULL,
            partition_key   text NOT NULL,
            last_sequence   bigint NOT NULL DEFAULT 0,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            version         integer NOT NULL DEFAULT 1,
            CONSTRAINT uq_consumer_checkpoint UNIQUE (consumer_id, aggregate_type, partition_key)
        );;

CREATE TRIGGER trg_consumer_checkpoints_version BEFORE UPDATE ON consumer_checkpoints FOR EACH ROW EXECUTE FUNCTION set_version_and_updated_at();;

GRANT SELECT, INSERT, UPDATE ON consumer_checkpoints TO app_runtime;;

UPDATE alembic_version SET version_num='0015' WHERE alembic_version.version_num = '0014';

-- Running upgrade 0015 -> 0016

CREATE TYPE job_type AS ENUM ('stage','retry','stage_timeout','review_timeout','recurring','compensation');;

CREATE TYPE job_schedule_status AS ENUM ('pending','leased','done','cancelled');;

CREATE TABLE job_schedule (
            id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id     uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            job_type         job_type NOT NULL,
            ref_table        text NOT NULL,
            ref_id           uuid NOT NULL,
            run_after        timestamptz NOT NULL,
            status           job_schedule_status NOT NULL DEFAULT 'pending',
            lease_owner      text,
            lease_expires_at timestamptz,
            attempt          integer NOT NULL DEFAULT 0,
            priority         integer NOT NULL DEFAULT 0,
            correlation_id   uuid,
            trace_id         text,
            created_at       timestamptz NOT NULL DEFAULT now(),
            updated_at       timestamptz NOT NULL DEFAULT now(),
            version          integer NOT NULL DEFAULT 1
        );;

CREATE INDEX ix_job_schedule_due ON job_schedule (status, run_after) WHERE status = 'pending';;

CREATE INDEX ix_job_schedule_lease_expiry ON job_schedule (lease_expires_at) WHERE status = 'leased';;

CREATE INDEX ix_job_schedule_workspace_due ON job_schedule (workspace_id, run_after) WHERE status = 'pending';;

CREATE TRIGGER trg_job_schedule_version BEFORE UPDATE ON job_schedule FOR EACH ROW EXECUTE FUNCTION set_version_and_updated_at();;

ALTER TABLE job_schedule ENABLE ROW LEVEL SECURITY;;

ALTER TABLE job_schedule FORCE ROW LEVEL SECURITY;;

GRANT SELECT, INSERT, UPDATE, DELETE ON job_schedule TO app_runtime;;

CREATE POLICY job_schedule_select_member ON job_schedule FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

CREATE TABLE workspace_concurrency_limits (
            id                        uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id              uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            max_concurrent_assignments integer NOT NULL DEFAULT 10,
            max_per_scheduler_tick    integer NOT NULL DEFAULT 5,
            created_at                timestamptz NOT NULL DEFAULT now(),
            updated_at                timestamptz NOT NULL DEFAULT now(),
            version                   integer NOT NULL DEFAULT 1,
            CONSTRAINT uq_workspace_concurrency_limit UNIQUE (workspace_id)
        );;

CREATE TRIGGER trg_workspace_concurrency_limits_version BEFORE UPDATE ON workspace_concurrency_limits FOR EACH ROW EXECUTE FUNCTION set_version_and_updated_at();;

ALTER TABLE workspace_concurrency_limits ENABLE ROW LEVEL SECURITY;;

ALTER TABLE workspace_concurrency_limits FORCE ROW LEVEL SECURITY;;

GRANT SELECT, INSERT, UPDATE, DELETE ON workspace_concurrency_limits TO app_runtime;;

CREATE POLICY workspace_concurrency_limits_select_member ON workspace_concurrency_limits FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

CREATE POLICY workspace_concurrency_limits_insert_roles ON workspace_concurrency_limits FOR INSERT WITH CHECK (app_user_has_workspace_role(workspace_id, ARRAY['admin']::workspace_role[]));;

CREATE POLICY workspace_concurrency_limits_update_roles ON workspace_concurrency_limits FOR UPDATE USING (app_user_has_workspace_role(workspace_id, ARRAY['admin']::workspace_role[]));;

UPDATE alembic_version SET version_num='0016' WHERE alembic_version.version_num = '0015';

-- Running upgrade 0016 -> 0017

CREATE TYPE worker_status AS ENUM ('online','busy','draining','offline');;

CREATE TABLE worker_registry (
            id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id      uuid REFERENCES workspaces(id) ON DELETE CASCADE,
            name              text NOT NULL,
            supported_stages  text[] NOT NULL DEFAULT '{}',
            capabilities      jsonb,
            status            worker_status NOT NULL DEFAULT 'offline',
            max_concurrency   integer NOT NULL DEFAULT 1,
            current_load      integer NOT NULL DEFAULT 0,
            health_score      integer NOT NULL DEFAULT 100 CHECK (health_score BETWEEN 0 AND 100),
            last_heartbeat_at timestamptz,
            registered_at     timestamptz NOT NULL DEFAULT now(),
            created_at        timestamptz NOT NULL DEFAULT now(),
            updated_at        timestamptz NOT NULL DEFAULT now(),
            version           integer NOT NULL DEFAULT 1
        );;

CREATE INDEX ix_worker_registry_status ON worker_registry (status) WHERE status IN ('online','busy');;

CREATE INDEX ix_worker_registry_stages ON worker_registry USING GIN (supported_stages);;

CREATE TRIGGER trg_worker_registry_version BEFORE UPDATE ON worker_registry FOR EACH ROW EXECUTE FUNCTION set_version_and_updated_at();;

GRANT SELECT, INSERT, UPDATE ON worker_registry TO app_runtime;;

CREATE TABLE worker_heartbeats (
            id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            worker_id     uuid NOT NULL REFERENCES worker_registry(id) ON DELETE CASCADE,
            status        worker_status NOT NULL,
            current_load  integer NOT NULL DEFAULT 0,
            heartbeat_at  timestamptz NOT NULL DEFAULT now()
        );;

CREATE INDEX ix_worker_heartbeats_worker_time ON worker_heartbeats (worker_id, heartbeat_at DESC);;

GRANT SELECT, INSERT ON worker_heartbeats TO app_runtime;;

UPDATE alembic_version SET version_num='0017' WHERE alembic_version.version_num = '0016';

