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

-- Running upgrade 0030 -> 0031

CREATE TABLE workspace_billing (
            workspace_id            uuid PRIMARY KEY REFERENCES workspaces(id) ON DELETE CASCADE,
            stripe_customer_id      text UNIQUE,
            stripe_subscription_id  text UNIQUE,
            plan                    text NOT NULL DEFAULT 'none',
            status                  text NOT NULL DEFAULT 'inactive',
            current_period_end      timestamptz,
            cancel_at_period_end    boolean NOT NULL DEFAULT false,
            created_at              timestamptz NOT NULL DEFAULT now(),
            updated_at              timestamptz NOT NULL DEFAULT now(),
            version                 integer NOT NULL DEFAULT 1,
            CONSTRAINT workspace_billing_plan_chk
                CHECK (plan IN ('none', 'pro')),
            CONSTRAINT workspace_billing_status_chk
                CHECK (status IN (
                    'inactive', 'incomplete', 'trialing', 'active',
                    'past_due', 'canceled', 'unpaid'
                ))
        );;

CREATE TRIGGER trg_workspace_billing_version BEFORE UPDATE ON workspace_billing FOR EACH ROW EXECUTE FUNCTION set_version_and_updated_at();;

ALTER TABLE workspace_billing ENABLE ROW LEVEL SECURITY;;

ALTER TABLE workspace_billing FORCE ROW LEVEL SECURITY;;

GRANT SELECT, INSERT, UPDATE ON workspace_billing TO app_runtime;;

CREATE POLICY workspace_billing_select_member ON workspace_billing FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]));;

CREATE POLICY workspace_billing_insert_roles ON workspace_billing FOR INSERT WITH CHECK (app_user_has_workspace_role(workspace_id, ARRAY['admin']::workspace_role[]));;

CREATE POLICY workspace_billing_update_roles ON workspace_billing FOR UPDATE USING (app_user_has_workspace_role(workspace_id, ARRAY['admin']::workspace_role[]));;

CREATE TABLE billing_webhook_events (
            id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            stripe_event_id  text NOT NULL UNIQUE,
            event_type       text NOT NULL,
            workspace_id     uuid REFERENCES workspaces(id) ON DELETE SET NULL,
            processed_at     timestamptz NOT NULL DEFAULT now(),
            payload          jsonb NOT NULL DEFAULT '{}'::jsonb
        );;

CREATE INDEX ix_billing_webhook_events_workspace ON billing_webhook_events (workspace_id);;

ALTER TABLE billing_webhook_events ENABLE ROW LEVEL SECURITY;;

ALTER TABLE billing_webhook_events FORCE ROW LEVEL SECURITY;;

INSERT INTO alembic_version (version_num) VALUES ('0031') RETURNING alembic_version.version_num;

-- Running upgrade 0031, 0031_fk, 0031_spend_precision -> 0032_merge_p1

DELETE FROM alembic_version WHERE alembic_version.version_num = '0031';

DELETE FROM alembic_version WHERE alembic_version.version_num = '0031_fk';

UPDATE alembic_version SET version_num='0032_merge_p1' WHERE alembic_version.version_num = '0031_spend_precision';

-- Running upgrade 0032_merge_p1 -> 0033

WITH ranked AS (
            SELECT id,
                   row_number() OVER (
                       PARTITION BY pipeline_run_id, stage
                       ORDER BY created_at DESC, id DESC
                   ) AS rn
            FROM spend_reservations
            WHERE status = 'reserved'
              AND pipeline_run_id IS NOT NULL
              AND stage IS NOT NULL
        )
        UPDATE spend_reservations sr
        SET status = 'released',
            updated_at = now(),
            version = sr.version + 1
        FROM ranked
        WHERE sr.id = ranked.id
          AND ranked.rn > 1;;

CREATE UNIQUE INDEX ux_spend_reservations_open_run_stage
        ON spend_reservations (pipeline_run_id, stage)
        WHERE status = 'reserved'
          AND pipeline_run_id IS NOT NULL
          AND stage IS NOT NULL;;

UPDATE alembic_version SET version_num='0033' WHERE alembic_version.version_num = '0032_merge_p1';

-- Running upgrade 0033 -> 0034

CREATE TABLE leads (
            id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id    uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            name            text NOT NULL,
            company         text,
            email           text NOT NULL,
            source          text NOT NULL DEFAULT 'manual',
            status          text NOT NULL DEFAULT 'new',
            notes           text,
            follow_up_date  date,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            version         integer NOT NULL DEFAULT 1,
            CONSTRAINT leads_status_chk CHECK (status IN (
                'new', 'contacted', 'qualified', 'negotiation',
                'won', 'lost', 'nurturing'
            )),
            CONSTRAINT leads_email_chk CHECK (position('@' in email) > 1)
        );;

CREATE INDEX ix_leads_workspace_status ON leads (workspace_id, status);;

CREATE INDEX ix_leads_workspace_follow_up ON leads (workspace_id, follow_up_date);;

CREATE INDEX ix_leads_workspace_email ON leads (workspace_id, email);;

CREATE TRIGGER trg_leads_version BEFORE UPDATE ON leads FOR EACH ROW EXECUTE FUNCTION set_version_and_updated_at();;

ALTER TABLE leads ENABLE ROW LEVEL SECURITY;;

ALTER TABLE leads FORCE ROW LEVEL SECURITY;;

GRANT SELECT, INSERT, UPDATE, DELETE ON leads TO app_runtime;;

CREATE POLICY leads_select_member ON leads FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]));;

CREATE POLICY leads_insert_roles ON leads FOR INSERT WITH CHECK (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

CREATE POLICY leads_update_roles ON leads FOR UPDATE USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

CREATE POLICY leads_delete_roles ON leads FOR DELETE
        USING (app_user_has_workspace_role(workspace_id, ARRAY['admin']::workspace_role[]));;

UPDATE alembic_version SET version_num='0034' WHERE alembic_version.version_num = '0033';

-- Running upgrade 0034 -> 0035

CREATE TABLE worker_logs (
            id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id    uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            worker_id       uuid NOT NULL REFERENCES worker_registry(id) ON DELETE RESTRICT,
            pipeline_run_id uuid REFERENCES pipeline_runs(id) ON DELETE RESTRICT,
            assignment_id   uuid REFERENCES stage_assignments(id) ON DELETE RESTRICT,
            severity        text NOT NULL,
            message         text NOT NULL,
            context         jsonb NOT NULL DEFAULT '{}'::jsonb,
            occurred_at     timestamptz NOT NULL DEFAULT now(),
            received_at     timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT worker_logs_severity_chk
                CHECK (severity IN ('debug', 'info', 'warning', 'error', 'critical'))
        );;

CREATE INDEX ix_worker_logs_workspace_time ON worker_logs (workspace_id, occurred_at DESC);;

CREATE INDEX ix_worker_logs_worker_time ON worker_logs (worker_id, occurred_at DESC);;

CREATE INDEX ix_worker_logs_pipeline_time ON worker_logs (pipeline_run_id, occurred_at DESC) WHERE pipeline_run_id IS NOT NULL;;

CREATE INDEX ix_worker_logs_assignment_time ON worker_logs (assignment_id, occurred_at DESC) WHERE assignment_id IS NOT NULL;;

CREATE TRIGGER trg_worker_logs_immutable BEFORE UPDATE ON worker_logs FOR EACH ROW EXECUTE FUNCTION prevent_update();;

CREATE TRIGGER trg_worker_logs_immutable_delete BEFORE DELETE ON worker_logs FOR EACH ROW EXECUTE FUNCTION prevent_delete();;

ALTER TABLE worker_logs ENABLE ROW LEVEL SECURITY;;

ALTER TABLE worker_logs FORCE ROW LEVEL SECURITY;;

GRANT SELECT ON worker_logs TO app_runtime;;

CREATE POLICY worker_logs_select_member ON worker_logs FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin']::workspace_role[]));;

UPDATE alembic_version SET version_num='0035' WHERE alembic_version.version_num = '0034';

-- Running upgrade 0035 -> 0036

ALTER TABLE local_auth_credentials ADD COLUMN failed_attempts INTEGER DEFAULT 0 NOT NULL;

ALTER TABLE local_auth_credentials ADD COLUMN last_failed_at TIMESTAMP WITH TIME ZONE;

ALTER TABLE local_auth_credentials ADD COLUMN locked_until TIMESTAMP WITH TIME ZONE;

UPDATE alembic_version SET version_num='0036' WHERE alembic_version.version_num = '0035';

-- Running upgrade 0036 -> 0037

CREATE TABLE publication_eligibility (
            id                        uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id              uuid NOT NULL
                                      REFERENCES workspaces(id) ON DELETE CASCADE,
            content_item_id           uuid NOT NULL
                                      REFERENCES content_items(id) ON DELETE CASCADE,
            platform                  text NOT NULL,
            generated_by              text,
            synthetic_media_disclosed boolean NOT NULL DEFAULT false,
            rights_confirmed_by       uuid REFERENCES profiles(id) ON DELETE SET NULL,
            rights_confirmed_at       timestamptz,
            originality_fingerprint   text,
            review_gate_id            uuid REFERENCES review_gates(id) ON DELETE SET NULL,
            policy_notes              jsonb,
            created_at                timestamptz NOT NULL DEFAULT now(),
            updated_at                timestamptz NOT NULL DEFAULT now(),
            version                   integer NOT NULL DEFAULT 1,
            CONSTRAINT uq_publication_eligibility_item_platform
                UNIQUE (content_item_id, platform),
            CONSTRAINT publication_eligibility_platform_chk CHECK (
                platform IN ('youtube', 'tiktok', 'instagram')
            ),
            -- A rights attestation is either complete (who + when) or absent;
            -- a half-recorded attestation must never satisfy the gate.
            CONSTRAINT publication_eligibility_rights_chk CHECK (
                (rights_confirmed_by IS NULL AND rights_confirmed_at IS NULL)
                OR (rights_confirmed_by IS NOT NULL AND rights_confirmed_at IS NOT NULL)
            )
        );;

CREATE INDEX ix_publication_eligibility_workspace ON publication_eligibility (workspace_id);;

CREATE INDEX ix_publication_eligibility_fingerprint ON publication_eligibility (workspace_id, platform, originality_fingerprint);;

CREATE INDEX ix_publication_eligibility_review_gate ON publication_eligibility (review_gate_id);;

CREATE INDEX ix_publication_eligibility_rights_confirmed_by ON publication_eligibility (rights_confirmed_by);;

CREATE TRIGGER trg_publication_eligibility_version BEFORE UPDATE ON publication_eligibility FOR EACH ROW EXECUTE FUNCTION set_version_and_updated_at();;

ALTER TABLE publication_eligibility ENABLE ROW LEVEL SECURITY;;

ALTER TABLE publication_eligibility FORCE ROW LEVEL SECURITY;;

GRANT SELECT, INSERT, UPDATE, DELETE ON publication_eligibility TO app_runtime;;

CREATE POLICY publication_eligibility_select_member ON publication_eligibility FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]));;

CREATE POLICY publication_eligibility_insert_roles ON publication_eligibility FOR INSERT WITH CHECK (app_user_has_workspace_role(workspace_id, ARRAY['admin','reviewer']::workspace_role[]));;

CREATE POLICY publication_eligibility_update_roles ON publication_eligibility FOR UPDATE USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','reviewer']::workspace_role[]));;

CREATE POLICY publication_eligibility_delete_roles ON publication_eligibility FOR DELETE USING (app_user_has_workspace_role(workspace_id, ARRAY['admin']::workspace_role[]));;

UPDATE alembic_version SET version_num='0037' WHERE alembic_version.version_num = '0036';

-- Running upgrade 0037 -> 0038

DROP POLICY IF EXISTS content_items_select_member ON content_items;;

CREATE POLICY content_items_select_member ON content_items FOR SELECT USING (  (deleted_at IS NULL    AND app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]))   OR (deleted_at IS NOT NULL       AND app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[])));;

DROP POLICY IF EXISTS content_items_update_roles ON content_items;;

CREATE POLICY content_items_update_roles ON content_items FOR UPDATE USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[])) WITH CHECK (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

DROP POLICY IF EXISTS assets_select_member ON assets;;

CREATE POLICY assets_select_member ON assets FOR SELECT USING (  (deleted_at IS NULL    AND app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]))   OR (deleted_at IS NOT NULL       AND app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[])));;

DROP POLICY IF EXISTS assets_update_roles ON assets;;

CREATE POLICY assets_update_roles ON assets FOR UPDATE USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[])) WITH CHECK (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

DROP POLICY IF EXISTS publish_jobs_select_member ON publish_jobs;;

CREATE POLICY publish_jobs_select_member ON publish_jobs FOR SELECT USING (  (deleted_at IS NULL    AND app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]))   OR (deleted_at IS NOT NULL       AND app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[])));;

DROP POLICY IF EXISTS publish_jobs_update_roles ON publish_jobs;;

CREATE POLICY publish_jobs_update_roles ON publish_jobs FOR UPDATE USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[])) WITH CHECK (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

DROP POLICY IF EXISTS content_pillars_select_member ON content_pillars;;

CREATE POLICY content_pillars_select_member ON content_pillars FOR SELECT USING (  (deleted_at IS NULL    AND app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]))   OR (deleted_at IS NOT NULL       AND app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[])));;

DROP POLICY IF EXISTS content_pillars_update_roles ON content_pillars;;

CREATE POLICY content_pillars_update_roles ON content_pillars FOR UPDATE USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[])) WITH CHECK (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

UPDATE alembic_version SET version_num='0038' WHERE alembic_version.version_num = '0037';

-- Running upgrade 0038 -> 0039

REVOKE ALL PRIVILEGES ON TABLE local_auth_credentials FROM app_runtime;;

UPDATE alembic_version SET version_num='0039' WHERE alembic_version.version_num = '0038';

-- Running upgrade 0039 -> 0040

ALTER TABLE review_gates ADD COLUMN content_version_id UUID;

ALTER TABLE review_gates ADD CONSTRAINT fk_review_gates_content_version FOREIGN KEY(content_version_id) REFERENCES content_versions (id);

CREATE INDEX ix_review_gates_content_version ON review_gates (content_version_id);

UPDATE alembic_version SET version_num='0040' WHERE alembic_version.version_num = '0039';

