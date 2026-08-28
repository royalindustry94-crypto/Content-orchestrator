CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 0001

CREATE EXTENSION IF NOT EXISTS pgcrypto;;

CREATE SCHEMA IF NOT EXISTS auth;;

CREATE TABLE IF NOT EXISTS auth.users (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            email text
        );;

DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_runtime') THEN
                CREATE ROLE app_runtime NOLOGIN NOBYPASSRLS NOCREATEROLE NOCREATEDB;
            END IF;
        END
        $$;;

CREATE TYPE workspace_role AS ENUM ('admin', 'editor', 'reviewer');

CREATE TABLE profiles (
    id UUID NOT NULL, 
    email VARCHAR NOT NULL, 
    full_name VARCHAR, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id)
);

CREATE TABLE workspaces (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    name VARCHAR NOT NULL, 
    created_by UUID NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(created_by) REFERENCES profiles (id)
);

CREATE TABLE workspace_memberships (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    workspace_id UUID NOT NULL, 
    user_id UUID NOT NULL, 
    role workspace_role NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_workspace_user UNIQUE (workspace_id, user_id), 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE, 
    FOREIGN KEY(user_id) REFERENCES profiles (id) ON DELETE CASCADE
);

CREATE INDEX ix_workspace_memberships_workspace_id ON workspace_memberships (workspace_id);

GRANT SELECT, INSERT, UPDATE, DELETE ON profiles, workspaces, workspace_memberships TO app_runtime;;

GRANT USAGE ON SCHEMA public TO app_runtime;;

CREATE OR REPLACE FUNCTION app_current_user_id() RETURNS uuid AS $$
          SELECT NULLIF(current_setting('request.jwt.claim.sub', true), '')::uuid
        $$ LANGUAGE sql STABLE;;

ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;;

ALTER TABLE profiles FORCE ROW LEVEL SECURITY;;

CREATE POLICY profiles_select_authenticated ON profiles FOR SELECT USING (app_current_user_id() IS NOT NULL);;

CREATE POLICY profiles_insert_own ON profiles FOR INSERT WITH CHECK (id = app_current_user_id());;

CREATE POLICY profiles_update_own ON profiles FOR UPDATE USING (id = app_current_user_id());;

ALTER TABLE workspaces ENABLE ROW LEVEL SECURITY;;

ALTER TABLE workspaces FORCE ROW LEVEL SECURITY;;

CREATE POLICY workspaces_select_member ON workspaces
            FOR SELECT USING (
                EXISTS (SELECT 1 FROM workspace_memberships m
                        WHERE m.workspace_id = workspaces.id
                          AND m.user_id = app_current_user_id())
            );;

CREATE POLICY workspaces_insert_any_authenticated ON workspaces FOR INSERT WITH CHECK (created_by = app_current_user_id());;

CREATE POLICY workspaces_update_admin ON workspaces
            FOR UPDATE USING (
                EXISTS (SELECT 1 FROM workspace_memberships m
                        WHERE m.workspace_id = workspaces.id
                          AND m.user_id = app_current_user_id()
                          AND m.role = 'admin')
            );;

ALTER TABLE workspace_memberships ENABLE ROW LEVEL SECURITY;;

ALTER TABLE workspace_memberships FORCE ROW LEVEL SECURITY;;

CREATE POLICY memberships_select_same_workspace ON workspace_memberships
            FOR SELECT USING (
                EXISTS (SELECT 1 FROM workspace_memberships m
                        WHERE m.workspace_id = workspace_memberships.workspace_id
                          AND m.user_id = app_current_user_id())
            );;

CREATE POLICY memberships_write_admin_only ON workspace_memberships
            FOR ALL USING (
                EXISTS (SELECT 1 FROM workspace_memberships m
                        WHERE m.workspace_id = workspace_memberships.workspace_id
                          AND m.user_id = app_current_user_id()
                          AND m.role = 'admin')
            );;

CREATE OR REPLACE FUNCTION handle_new_auth_user() RETURNS trigger AS $$
        BEGIN
            INSERT INTO profiles (id, email)
            VALUES (NEW.id, COALESCE(NEW.email, ''))
            ON CONFLICT (id) DO NOTHING;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;;

CREATE TRIGGER on_auth_user_created
            AFTER INSERT ON auth.users
            FOR EACH ROW EXECUTE FUNCTION handle_new_auth_user();;

INSERT INTO alembic_version (version_num) VALUES ('0001') RETURNING alembic_version.version_num;

-- Running upgrade 0001 -> 0002

CREATE OR REPLACE FUNCTION set_version_and_updated_at() RETURNS trigger AS $$
        BEGIN
            NEW.version := OLD.version + 1;
            NEW.updated_at := now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;;

CREATE OR REPLACE FUNCTION prevent_update() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'table % is immutable; row updates are not permitted', TG_TABLE_NAME
                USING ERRCODE = 'restrict_violation';
        END;
        $$ LANGUAGE plpgsql;;

CREATE OR REPLACE FUNCTION app_user_has_workspace_role(
            p_workspace_id uuid, p_roles workspace_role[]
        ) RETURNS boolean AS $$
            SELECT EXISTS (
                SELECT 1 FROM workspace_memberships m
                WHERE m.workspace_id = p_workspace_id
                  AND m.user_id = app_current_user_id()
                  AND m.role = ANY(p_roles)
            )
        $$ LANGUAGE sql STABLE;;

GRANT EXECUTE ON FUNCTION app_user_has_workspace_role(uuid, workspace_role[]) TO app_runtime;;

UPDATE alembic_version SET version_num='0002' WHERE alembic_version.version_num = '0001';

-- Running upgrade 0002 -> 0003

CREATE TABLE content_pillars (
            id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            name         text NOT NULL,
            created_at   timestamptz NOT NULL DEFAULT now(),
            updated_at   timestamptz NOT NULL DEFAULT now(),
            created_by   uuid REFERENCES profiles(id),
            updated_by   uuid REFERENCES profiles(id),
            version      integer NOT NULL DEFAULT 1,
            deleted_at   timestamptz
        );;

CREATE UNIQUE INDEX uq_content_pillars_workspace_name ON content_pillars (workspace_id, name) WHERE deleted_at IS NULL;;

CREATE INDEX ix_content_pillars_workspace ON content_pillars (workspace_id);;

CREATE TRIGGER trg_content_pillars_version BEFORE UPDATE ON content_pillars FOR EACH ROW EXECUTE FUNCTION set_version_and_updated_at();;

ALTER TABLE content_pillars ENABLE ROW LEVEL SECURITY;;

ALTER TABLE content_pillars FORCE ROW LEVEL SECURITY;;

GRANT SELECT, INSERT, UPDATE, DELETE ON content_pillars TO app_runtime;;

CREATE POLICY content_pillars_select_member ON content_pillars FOR SELECT USING (deleted_at IS NULL AND app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]));;

CREATE POLICY content_pillars_insert_roles ON content_pillars FOR INSERT WITH CHECK (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

CREATE POLICY content_pillars_update_roles ON content_pillars FOR UPDATE USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

CREATE TABLE spend_caps (
            id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id    uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            provider        text,
            daily_cap_usd   numeric(10,2) NOT NULL CHECK (daily_cap_usd >= 0),
            monthly_cap_usd numeric(10,2) NOT NULL CHECK (monthly_cap_usd >= 0),
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            created_by      uuid REFERENCES profiles(id),
            updated_by      uuid REFERENCES profiles(id),
            version         integer NOT NULL DEFAULT 1
        );;

CREATE UNIQUE INDEX uq_spend_caps_workspace_provider ON spend_caps (workspace_id, COALESCE(provider, ''));;

CREATE TRIGGER trg_spend_caps_version BEFORE UPDATE ON spend_caps FOR EACH ROW EXECUTE FUNCTION set_version_and_updated_at();;

ALTER TABLE spend_caps ENABLE ROW LEVEL SECURITY;;

ALTER TABLE spend_caps FORCE ROW LEVEL SECURITY;;

GRANT SELECT, INSERT, UPDATE, DELETE ON spend_caps TO app_runtime;;

CREATE POLICY spend_caps_select_member ON spend_caps FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]));;

CREATE POLICY spend_caps_insert_roles ON spend_caps FOR INSERT WITH CHECK (app_user_has_workspace_role(workspace_id, ARRAY['admin']::workspace_role[]));;

CREATE POLICY spend_caps_update_roles ON spend_caps FOR UPDATE USING (app_user_has_workspace_role(workspace_id, ARRAY['admin']::workspace_role[]));;

CREATE TYPE provider_credential_status AS ENUM ('active', 'revoked');;

CREATE TABLE provider_credentials (
            id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id      uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            provider          text NOT NULL,
            label             text NOT NULL,
            encrypted_secret  text NOT NULL,
            encryption_key_id text NOT NULL,
            status            provider_credential_status NOT NULL DEFAULT 'active',
            created_at        timestamptz NOT NULL DEFAULT now(),
            updated_at        timestamptz NOT NULL DEFAULT now(),
            created_by        uuid REFERENCES profiles(id),
            updated_by        uuid REFERENCES profiles(id),
            version           integer NOT NULL DEFAULT 1,
            deleted_at        timestamptz
        );;

CREATE UNIQUE INDEX uq_provider_credentials_workspace_provider_label ON provider_credentials (workspace_id, provider, label) WHERE deleted_at IS NULL;;

CREATE INDEX ix_provider_credentials_workspace ON provider_credentials (workspace_id);;

CREATE TRIGGER trg_provider_credentials_version BEFORE UPDATE ON provider_credentials FOR EACH ROW EXECUTE FUNCTION set_version_and_updated_at();;

ALTER TABLE provider_credentials ENABLE ROW LEVEL SECURITY;;

ALTER TABLE provider_credentials FORCE ROW LEVEL SECURITY;;

GRANT SELECT, INSERT, UPDATE, DELETE ON provider_credentials TO app_runtime;;

CREATE POLICY provider_credentials_admin_only ON provider_credentials FOR ALL USING (app_user_has_workspace_role(workspace_id, ARRAY['admin']::workspace_role[]));;

UPDATE alembic_version SET version_num='0003' WHERE alembic_version.version_num = '0002';

-- Running upgrade 0003 -> 0004

CREATE TYPE content_stage AS ENUM ('idea','scripting','voiceover','visuals','rendering','seo','review','scheduled','published');;

CREATE TYPE content_status AS ENUM ('active','failed','archived');;

CREATE TABLE content_items (
            id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id            uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            pillar_id               uuid REFERENCES content_pillars(id),
            topic                   text NOT NULL,
            target_length_seconds   integer CHECK (target_length_seconds > 0),
            current_stage           content_stage NOT NULL DEFAULT 'idea',
            status                  content_status NOT NULL DEFAULT 'active',
            current_version_id      uuid,
            current_pipeline_run_id uuid,
            created_at              timestamptz NOT NULL DEFAULT now(),
            updated_at              timestamptz NOT NULL DEFAULT now(),
            created_by              uuid REFERENCES profiles(id),
            updated_by              uuid REFERENCES profiles(id),
            version                 integer NOT NULL DEFAULT 1,
            deleted_at              timestamptz
        );;

CREATE INDEX ix_content_items_workspace_stage ON content_items (workspace_id, current_stage) WHERE deleted_at IS NULL;;

CREATE INDEX ix_content_items_workspace_pillar ON content_items (workspace_id, pillar_id) WHERE deleted_at IS NULL;;

CREATE INDEX ix_content_items_workspace_status ON content_items (workspace_id, status) WHERE deleted_at IS NULL;;

CREATE TRIGGER trg_content_items_version BEFORE UPDATE ON content_items FOR EACH ROW EXECUTE FUNCTION set_version_and_updated_at();;

ALTER TABLE content_items ENABLE ROW LEVEL SECURITY;;

ALTER TABLE content_items FORCE ROW LEVEL SECURITY;;

GRANT SELECT, INSERT, UPDATE, DELETE ON content_items TO app_runtime;;

CREATE POLICY content_items_select_member ON content_items FOR SELECT USING (deleted_at IS NULL AND app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]));;

CREATE POLICY content_items_insert_roles ON content_items FOR INSERT WITH CHECK (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

CREATE POLICY content_items_update_roles ON content_items FOR UPDATE USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

CREATE TABLE content_versions (
            id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id    uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            content_item_id uuid NOT NULL REFERENCES content_items(id) ON DELETE CASCADE,
            script_hook     text,
            script_body     text,
            script_cta      text,
            prompt_used     text,
            generated_by    text,
            created_at      timestamptz NOT NULL DEFAULT now(),
            created_by      uuid REFERENCES profiles(id)
        );;

CREATE INDEX ix_content_versions_item ON content_versions (content_item_id, created_at DESC);;

CREATE INDEX ix_content_versions_workspace ON content_versions (workspace_id);;

CREATE TRIGGER trg_content_versions_immutable BEFORE UPDATE ON content_versions FOR EACH ROW EXECUTE FUNCTION prevent_update();;

ALTER TABLE content_versions ENABLE ROW LEVEL SECURITY;;

ALTER TABLE content_versions FORCE ROW LEVEL SECURITY;;

GRANT SELECT, INSERT ON content_versions TO app_runtime;;

CREATE POLICY content_versions_select_member ON content_versions FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]));;

CREATE POLICY content_versions_insert_roles ON content_versions FOR INSERT WITH CHECK (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

ALTER TABLE content_items ADD CONSTRAINT fk_content_items_current_version FOREIGN KEY (current_version_id) REFERENCES content_versions(id);;

UPDATE alembic_version SET version_num='0004' WHERE alembic_version.version_num = '0003';

-- Running upgrade 0004 -> 0005

CREATE TYPE pipeline_run_status AS ENUM ('running','succeeded','failed','cancelled');;

CREATE TYPE stage_run_status AS ENUM ('succeeded','failed');;

CREATE TABLE pipeline_runs (
            id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id    uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            content_item_id uuid NOT NULL REFERENCES content_items(id) ON DELETE CASCADE,
            current_stage   content_stage NOT NULL DEFAULT 'idea',
            status          pipeline_run_status NOT NULL DEFAULT 'running',
            started_at      timestamptz,
            completed_at    timestamptz,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            version         integer NOT NULL DEFAULT 1
        );;

CREATE INDEX ix_pipeline_runs_item ON pipeline_runs (content_item_id, created_at DESC);;

CREATE INDEX ix_pipeline_runs_workspace_running ON pipeline_runs (workspace_id, status) WHERE status = 'running';;

CREATE TRIGGER trg_pipeline_runs_version BEFORE UPDATE ON pipeline_runs FOR EACH ROW EXECUTE FUNCTION set_version_and_updated_at();;

ALTER TABLE pipeline_runs ENABLE ROW LEVEL SECURITY;;

ALTER TABLE pipeline_runs FORCE ROW LEVEL SECURITY;;

GRANT SELECT, INSERT, UPDATE, DELETE ON pipeline_runs TO app_runtime;;

CREATE POLICY pipeline_runs_select_member ON pipeline_runs FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]));;

CREATE TABLE pipeline_stage_runs (
            id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id    uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            pipeline_run_id uuid NOT NULL REFERENCES pipeline_runs(id) ON DELETE CASCADE,
            content_item_id uuid NOT NULL REFERENCES content_items(id) ON DELETE CASCADE,
            stage           content_stage NOT NULL,
            attempt_number  integer NOT NULL CHECK (attempt_number >= 1),
            status          stage_run_status NOT NULL,
            provider        text,
            cost_usd        numeric(10,4) CHECK (cost_usd >= 0),
            error_message   text,
            started_at      timestamptz,
            completed_at    timestamptz,
            created_at      timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT uq_stage_run_attempt UNIQUE (pipeline_run_id, stage, attempt_number)
        );;

CREATE INDEX ix_stage_runs_run_stage ON pipeline_stage_runs (pipeline_run_id, stage);;

CREATE INDEX ix_stage_runs_workspace_status ON pipeline_stage_runs (workspace_id, status);;

CREATE TRIGGER trg_pipeline_stage_runs_immutable BEFORE UPDATE ON pipeline_stage_runs FOR EACH ROW EXECUTE FUNCTION prevent_update();;

ALTER TABLE pipeline_stage_runs ENABLE ROW LEVEL SECURITY;;

ALTER TABLE pipeline_stage_runs FORCE ROW LEVEL SECURITY;;

GRANT SELECT, INSERT ON pipeline_stage_runs TO app_runtime;;

CREATE POLICY pipeline_stage_runs_select_member ON pipeline_stage_runs FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]));;

ALTER TABLE content_items ADD CONSTRAINT fk_content_items_current_run FOREIGN KEY (current_pipeline_run_id) REFERENCES pipeline_runs(id);;

UPDATE alembic_version SET version_num='0005' WHERE alembic_version.version_num = '0004';

-- Running upgrade 0005 -> 0006

CREATE TYPE asset_type AS ENUM ('script','audio','visual','render');;

CREATE TYPE asset_source AS ENUM ('ai_generated','uploaded');;

CREATE TYPE asset_status AS ENUM ('pending','ready','failed');;

CREATE TABLE assets (
            id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id       uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            content_item_id    uuid NOT NULL REFERENCES content_items(id) ON DELETE CASCADE,
            content_version_id uuid REFERENCES content_versions(id),
            type               asset_type NOT NULL,
            source             asset_source NOT NULL,
            status             asset_status NOT NULL DEFAULT 'pending',
            url                text,
            sequence_index     integer,
            created_at         timestamptz NOT NULL DEFAULT now(),
            updated_at         timestamptz NOT NULL DEFAULT now(),
            created_by         uuid REFERENCES profiles(id),
            updated_by         uuid REFERENCES profiles(id),
            version            integer NOT NULL DEFAULT 1,
            deleted_at         timestamptz
        );;

CREATE INDEX ix_assets_item_type ON assets (content_item_id, type) WHERE deleted_at IS NULL;;

CREATE INDEX ix_assets_workspace ON assets (workspace_id);;

CREATE TRIGGER trg_assets_version BEFORE UPDATE ON assets FOR EACH ROW EXECUTE FUNCTION set_version_and_updated_at();;

ALTER TABLE assets ENABLE ROW LEVEL SECURITY;;

ALTER TABLE assets FORCE ROW LEVEL SECURITY;;

GRANT SELECT, INSERT, UPDATE, DELETE ON assets TO app_runtime;;

CREATE POLICY assets_select_member ON assets FOR SELECT USING (deleted_at IS NULL AND app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]));;

CREATE POLICY assets_insert_roles ON assets FOR INSERT WITH CHECK (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

CREATE POLICY assets_update_roles ON assets FOR UPDATE USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

UPDATE alembic_version SET version_num='0006' WHERE alembic_version.version_num = '0005';

-- Running upgrade 0006 -> 0007

CREATE TYPE publish_job_status AS ENUM ('pending','publishing','published','failed','cancelled');;

CREATE TABLE publish_jobs (
            id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id    uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            content_item_id uuid NOT NULL REFERENCES content_items(id) ON DELETE CASCADE,
            platform        text NOT NULL,
            scheduled_time  timestamptz NOT NULL,
            status          publish_job_status NOT NULL DEFAULT 'pending',
            external_post_id text,
            error_message   text,
            published_at    timestamptz,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            created_by      uuid REFERENCES profiles(id),
            updated_by      uuid REFERENCES profiles(id),
            version         integer NOT NULL DEFAULT 1,
            deleted_at      timestamptz
        );;

CREATE INDEX ix_publish_jobs_workspace_time ON publish_jobs (workspace_id, scheduled_time) WHERE deleted_at IS NULL;;

CREATE INDEX ix_publish_jobs_workspace_status ON publish_jobs (workspace_id, status);;

CREATE INDEX ix_publish_jobs_item ON publish_jobs (content_item_id);;

CREATE TRIGGER trg_publish_jobs_version BEFORE UPDATE ON publish_jobs FOR EACH ROW EXECUTE FUNCTION set_version_and_updated_at();;

ALTER TABLE publish_jobs ENABLE ROW LEVEL SECURITY;;

ALTER TABLE publish_jobs FORCE ROW LEVEL SECURITY;;

GRANT SELECT, INSERT, UPDATE, DELETE ON publish_jobs TO app_runtime;;

CREATE POLICY publish_jobs_select_member ON publish_jobs FOR SELECT USING (deleted_at IS NULL AND app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]));;

CREATE POLICY publish_jobs_insert_roles ON publish_jobs FOR INSERT WITH CHECK (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

CREATE POLICY publish_jobs_update_roles ON publish_jobs FOR UPDATE USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

UPDATE alembic_version SET version_num='0007' WHERE alembic_version.version_num = '0006';

-- Running upgrade 0007 -> 0008

CREATE TYPE review_decision_value AS ENUM ('approved','changes_requested','rejected');;

CREATE TABLE review_decisions (
            id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id       uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            content_item_id    uuid NOT NULL REFERENCES content_items(id) ON DELETE CASCADE,
            content_version_id uuid REFERENCES content_versions(id),
            reviewer_id        uuid NOT NULL REFERENCES profiles(id),
            decision           review_decision_value NOT NULL,
            notes              text,
            created_at         timestamptz NOT NULL DEFAULT now()
        );;

CREATE INDEX ix_review_decisions_item ON review_decisions (content_item_id, created_at DESC);;

CREATE INDEX ix_review_decisions_workspace ON review_decisions (workspace_id);;

CREATE TRIGGER trg_review_decisions_immutable BEFORE UPDATE ON review_decisions FOR EACH ROW EXECUTE FUNCTION prevent_update();;

ALTER TABLE review_decisions ENABLE ROW LEVEL SECURITY;;

ALTER TABLE review_decisions FORCE ROW LEVEL SECURITY;;

GRANT SELECT, INSERT ON review_decisions TO app_runtime;;

CREATE POLICY review_decisions_select_member ON review_decisions FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]));;

CREATE POLICY review_decisions_insert_roles ON review_decisions FOR INSERT WITH CHECK (app_user_has_workspace_role(workspace_id, ARRAY['admin','reviewer']::workspace_role[]));;

UPDATE alembic_version SET version_num='0008' WHERE alembic_version.version_num = '0007';

-- Running upgrade 0008 -> 0009

CREATE TABLE analytics_snapshots (
            id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id    uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            content_item_id uuid NOT NULL REFERENCES content_items(id) ON DELETE CASCADE,
            platform        text NOT NULL,
            metric          text NOT NULL,
            value           numeric NOT NULL,
            captured_at     timestamptz NOT NULL,
            created_at      timestamptz NOT NULL DEFAULT now()
        );;

CREATE INDEX ix_analytics_item_metric_time ON analytics_snapshots (content_item_id, metric, captured_at DESC);;

CREATE INDEX ix_analytics_workspace_time ON analytics_snapshots (workspace_id, captured_at DESC);;

CREATE TRIGGER trg_analytics_snapshots_immutable BEFORE UPDATE ON analytics_snapshots FOR EACH ROW EXECUTE FUNCTION prevent_update();;

ALTER TABLE analytics_snapshots ENABLE ROW LEVEL SECURITY;;

ALTER TABLE analytics_snapshots FORCE ROW LEVEL SECURITY;;

GRANT SELECT, INSERT ON analytics_snapshots TO app_runtime;;

CREATE POLICY analytics_snapshots_select_member ON analytics_snapshots FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]));;

UPDATE alembic_version SET version_num='0009' WHERE alembic_version.version_num = '0008';

