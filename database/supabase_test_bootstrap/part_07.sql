-- Running upgrade 0045 -> 0046

CREATE TABLE production_jobs (
    id UUID NOT NULL, 
    workspace_id UUID NOT NULL, 
    content_package_id UUID NOT NULL, 
    content_item_id UUID NOT NULL, 
    content_version_id UUID NOT NULL, 
    pipeline_run_id UUID, 
    producer_worker_id TEXT DEFAULT 'producer' NOT NULL, 
    target_platform TEXT, 
    target_format TEXT, 
    target_duration_seconds INTEGER, 
    required_assets JSONB DEFAULT '[]'::jsonb NOT NULL, 
    provider_plan JSONB DEFAULT '{}'::jsonb NOT NULL, 
    status TEXT DEFAULT 'queued' NOT NULL, 
    provider_state TEXT DEFAULT 'not_configured' NOT NULL, 
    max_provider_calls INTEGER DEFAULT '0' NOT NULL, 
    max_render_calls INTEGER DEFAULT '0' NOT NULL, 
    max_cost_usd NUMERIC(10, 4) DEFAULT '0' NOT NULL, 
    max_total_cost_usd NUMERIC(10, 4) DEFAULT '0' NOT NULL, 
    max_attempts INTEGER DEFAULT '1' NOT NULL, 
    max_repair_cycles INTEGER DEFAULT '0' NOT NULL, 
    timeout_seconds INTEGER DEFAULT '900' NOT NULL, 
    deadline_at TIMESTAMP WITH TIME ZONE, 
    provider_calls_used INTEGER DEFAULT '0' NOT NULL, 
    render_calls_used INTEGER DEFAULT '0' NOT NULL, 
    repair_cycles_used INTEGER DEFAULT '0' NOT NULL, 
    actual_cost_usd NUMERIC(10, 4) DEFAULT '0' NOT NULL, 
    retry_count INTEGER DEFAULT '0' NOT NULL, 
    last_error TEXT, 
    correlation_id UUID NOT NULL, 
    trace_id TEXT, 
    started_at TIMESTAMP WITH TIME ZONE, 
    completed_at TIMESTAMP WITH TIME ZONE, 
    test_data BOOLEAN DEFAULT false NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    created_by UUID, 
    updated_by UUID, 
    version INTEGER DEFAULT '1' NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT ck_production_job_bounds CHECK (max_provider_calls >= 0 AND max_render_calls >= 0 AND max_cost_usd >= 0 AND max_total_cost_usd >= 0 AND max_attempts > 0 AND max_repair_cycles >= 0 AND timeout_seconds > 0), 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE, 
    FOREIGN KEY(content_package_id) REFERENCES content_packages (id) ON DELETE RESTRICT, 
    FOREIGN KEY(content_item_id) REFERENCES content_items (id) ON DELETE CASCADE, 
    FOREIGN KEY(content_version_id) REFERENCES content_versions (id) ON DELETE RESTRICT, 
    FOREIGN KEY(pipeline_run_id) REFERENCES pipeline_runs (id) ON DELETE SET NULL, 
    FOREIGN KEY(created_by) REFERENCES profiles (id), 
    FOREIGN KEY(updated_by) REFERENCES profiles (id)
);

CREATE INDEX ix_production_jobs_workspace_created ON production_jobs (workspace_id, created_at);

CREATE INDEX ix_production_jobs_workspace_status ON production_jobs (workspace_id, status);

CREATE INDEX ix_production_jobs_workspace_package ON production_jobs (workspace_id, content_package_id);

CREATE INDEX ix_production_jobs_workspace_version ON production_jobs (workspace_id, content_version_id);

CREATE INDEX ix_production_jobs_package ON production_jobs (content_package_id);

CREATE INDEX ix_production_jobs_item ON production_jobs (content_item_id);

CREATE INDEX ix_production_jobs_version ON production_jobs (content_version_id);

CREATE INDEX ix_production_jobs_pipeline ON production_jobs (pipeline_run_id);

CREATE INDEX ix_production_jobs_created_by ON production_jobs (created_by);

CREATE INDEX ix_production_jobs_updated_by ON production_jobs (updated_by);

CREATE TABLE production_assets (
    id UUID NOT NULL, 
    workspace_id UUID NOT NULL, 
    production_job_id UUID NOT NULL, 
    asset_id UUID NOT NULL, 
    content_item_id UUID NOT NULL, 
    content_version_id UUID NOT NULL, 
    asset_type TEXT NOT NULL, 
    provider TEXT DEFAULT 'not_configured' NOT NULL, 
    provider_job_id TEXT, 
    source_inputs JSONB DEFAULT '{}'::jsonb NOT NULL, 
    generation_settings JSONB DEFAULT '{}'::jsonb NOT NULL, 
    model_version TEXT, 
    file_hash TEXT, 
    duration_seconds NUMERIC(12, 3), 
    dimensions JSONB DEFAULT '{}'::jsonb NOT NULL, 
    cost_usd NUMERIC(10, 4) DEFAULT '0' NOT NULL, 
    status TEXT DEFAULT 'not_configured' NOT NULL, 
    test_data BOOLEAN DEFAULT false NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    created_by UUID, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_production_asset_asset UNIQUE (workspace_id, asset_id), 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE, 
    FOREIGN KEY(production_job_id) REFERENCES production_jobs (id) ON DELETE RESTRICT, 
    FOREIGN KEY(asset_id) REFERENCES assets (id) ON DELETE RESTRICT, 
    FOREIGN KEY(content_item_id) REFERENCES content_items (id) ON DELETE CASCADE, 
    FOREIGN KEY(content_version_id) REFERENCES content_versions (id) ON DELETE RESTRICT, 
    FOREIGN KEY(created_by) REFERENCES profiles (id)
);

CREATE INDEX ix_production_assets_workspace_job ON production_assets (workspace_id, production_job_id);

CREATE INDEX ix_production_assets_workspace_version ON production_assets (workspace_id, content_version_id);

CREATE INDEX ix_production_assets_job ON production_assets (production_job_id);

CREATE INDEX ix_production_assets_asset ON production_assets (asset_id);

CREATE INDEX ix_production_assets_version ON production_assets (content_version_id);

CREATE INDEX ix_production_assets_created_by ON production_assets (created_by);

CREATE TABLE final_artifacts (
    id UUID NOT NULL, 
    workspace_id UUID NOT NULL, 
    production_job_id UUID NOT NULL, 
    content_item_id UUID NOT NULL, 
    content_version_id UUID NOT NULL, 
    render_asset_id UUID, 
    render_provider TEXT DEFAULT 'not_configured' NOT NULL, 
    render_job_id TEXT, 
    artifact_hash TEXT NOT NULL, 
    storage_reference JSONB DEFAULT '{}'::jsonb NOT NULL, 
    duration_seconds NUMERIC(12, 3), 
    resolution JSONB DEFAULT '{}'::jsonb NOT NULL, 
    aspect_ratio TEXT, 
    container TEXT, 
    codec TEXT, 
    cost_usd NUMERIC(10, 4) DEFAULT '0' NOT NULL, 
    status TEXT DEFAULT 'not_configured' NOT NULL, 
    test_data BOOLEAN DEFAULT false NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    created_by UUID, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_final_artifact_hash UNIQUE (workspace_id, artifact_hash), 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE, 
    FOREIGN KEY(production_job_id) REFERENCES production_jobs (id) ON DELETE RESTRICT, 
    FOREIGN KEY(content_item_id) REFERENCES content_items (id) ON DELETE CASCADE, 
    FOREIGN KEY(content_version_id) REFERENCES content_versions (id) ON DELETE RESTRICT, 
    FOREIGN KEY(render_asset_id) REFERENCES assets (id) ON DELETE SET NULL, 
    FOREIGN KEY(created_by) REFERENCES profiles (id)
);

CREATE INDEX ix_final_artifacts_workspace_job ON final_artifacts (workspace_id, production_job_id);

CREATE INDEX ix_final_artifacts_workspace_version ON final_artifacts (workspace_id, content_version_id);

CREATE INDEX ix_final_artifacts_job ON final_artifacts (production_job_id);

CREATE INDEX ix_final_artifacts_version ON final_artifacts (content_version_id);

CREATE INDEX ix_final_artifacts_created_by ON final_artifacts (created_by);

CREATE TABLE media_qa_results (
    id UUID NOT NULL, 
    workspace_id UUID NOT NULL, 
    final_artifact_id UUID NOT NULL, 
    artifact_hash TEXT NOT NULL, 
    auditor_worker_id TEXT NOT NULL, 
    status TEXT DEFAULT 'not_configured' NOT NULL, 
    checks_run JSONB DEFAULT '[]'::jsonb NOT NULL, 
    visual_findings JSONB DEFAULT '[]'::jsonb NOT NULL, 
    audio_findings JSONB DEFAULT '[]'::jsonb NOT NULL, 
    subtitle_findings JSONB DEFAULT '[]'::jsonb NOT NULL, 
    script_alignment JSONB DEFAULT '{}'::jsonb NOT NULL, 
    platform_check JSONB DEFAULT '{}'::jsonb NOT NULL, 
    package_alignment JSONB DEFAULT '{}'::jsonb NOT NULL, 
    evidence JSONB DEFAULT '[]'::jsonb NOT NULL, 
    recommended_repair JSONB DEFAULT '[]'::jsonb NOT NULL, 
    cost_usd NUMERIC(10, 4) DEFAULT '0' NOT NULL, 
    started_at TIMESTAMP WITH TIME ZONE, 
    completed_at TIMESTAMP WITH TIME ZONE, 
    test_data BOOLEAN DEFAULT false NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_media_qa_artifact_hash UNIQUE (final_artifact_id, artifact_hash), 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE, 
    FOREIGN KEY(final_artifact_id) REFERENCES final_artifacts (id) ON DELETE CASCADE
);

CREATE INDEX ix_media_qa_workspace_artifact ON media_qa_results (workspace_id, final_artifact_id);

CREATE INDEX ix_media_qa_workspace_status ON media_qa_results (workspace_id, status);

CREATE INDEX ix_media_qa_artifact ON media_qa_results (final_artifact_id);

CREATE TABLE production_repairs (
    id UUID NOT NULL, 
    workspace_id UUID NOT NULL, 
    production_job_id UUID NOT NULL, 
    final_artifact_id UUID, 
    media_qa_result_id UUID, 
    affected_component TEXT NOT NULL, 
    finding_snapshot JSONB DEFAULT '{}'::jsonb NOT NULL, 
    repair_operation TEXT NOT NULL, 
    repair_cycle INTEGER NOT NULL, 
    status TEXT DEFAULT 'blocked' NOT NULL, 
    cost_usd NUMERIC(10, 4) DEFAULT '0' NOT NULL, 
    provider_calls_used INTEGER DEFAULT '0' NOT NULL, 
    result_references JSONB DEFAULT '{}'::jsonb NOT NULL, 
    test_data BOOLEAN DEFAULT false NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    created_by UUID, 
    PRIMARY KEY (id), 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE, 
    FOREIGN KEY(production_job_id) REFERENCES production_jobs (id) ON DELETE RESTRICT, 
    FOREIGN KEY(final_artifact_id) REFERENCES final_artifacts (id) ON DELETE SET NULL, 
    FOREIGN KEY(media_qa_result_id) REFERENCES media_qa_results (id) ON DELETE SET NULL, 
    FOREIGN KEY(created_by) REFERENCES profiles (id)
);

CREATE INDEX ix_production_repairs_workspace_job ON production_repairs (workspace_id, production_job_id);

CREATE INDEX ix_production_repairs_workspace_artifact ON production_repairs (workspace_id, final_artifact_id);

CREATE INDEX ix_production_repairs_job ON production_repairs (production_job_id);

CREATE INDEX ix_production_repairs_artifact ON production_repairs (final_artifact_id);

CREATE INDEX ix_production_repairs_qa ON production_repairs (media_qa_result_id);

CREATE INDEX ix_production_repairs_created_by ON production_repairs (created_by);

CREATE TABLE artifact_invalidations (
    id UUID NOT NULL, 
    workspace_id UUID NOT NULL, 
    final_artifact_id UUID NOT NULL, 
    media_qa_result_id UUID, 
    reason TEXT NOT NULL, 
    affected_dimensions JSONB DEFAULT '[]'::jsonb NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    created_by UUID, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_artifact_invalidation_reason UNIQUE (final_artifact_id, reason), 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE, 
    FOREIGN KEY(final_artifact_id) REFERENCES final_artifacts (id) ON DELETE CASCADE, 
    FOREIGN KEY(media_qa_result_id) REFERENCES media_qa_results (id) ON DELETE SET NULL, 
    FOREIGN KEY(created_by) REFERENCES profiles (id)
);

CREATE INDEX ix_artifact_invalidations_workspace_artifact ON artifact_invalidations (workspace_id, final_artifact_id);

CREATE INDEX ix_artifact_invalidations_qa ON artifact_invalidations (media_qa_result_id);

CREATE INDEX ix_artifact_invalidations_created_by ON artifact_invalidations (created_by);

CREATE TABLE production_readiness (
    id UUID NOT NULL, 
    workspace_id UUID NOT NULL, 
    final_artifact_id UUID NOT NULL, 
    content_version_id UUID NOT NULL, 
    media_qa_state TEXT DEFAULT 'not_run' NOT NULL, 
    compliance_state TEXT DEFAULT 'not_run' NOT NULL, 
    chief_audit_state TEXT DEFAULT 'not_run' NOT NULL, 
    human_review_state TEXT DEFAULT 'blocked' NOT NULL, 
    status TEXT DEFAULT 'blocked' NOT NULL, 
    blocking_reasons JSONB DEFAULT '[]'::jsonb NOT NULL, 
    total_cost_usd NUMERIC(10, 4) DEFAULT '0' NOT NULL, 
    test_data BOOLEAN DEFAULT false NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    created_by UUID, 
    updated_by UUID, 
    version INTEGER DEFAULT '1' NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_production_readiness_artifact UNIQUE (workspace_id, final_artifact_id), 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE, 
    FOREIGN KEY(final_artifact_id) REFERENCES final_artifacts (id) ON DELETE CASCADE, 
    FOREIGN KEY(content_version_id) REFERENCES content_versions (id) ON DELETE RESTRICT, 
    FOREIGN KEY(created_by) REFERENCES profiles (id), 
    FOREIGN KEY(updated_by) REFERENCES profiles (id)
);

CREATE INDEX ix_production_readiness_workspace_artifact ON production_readiness (workspace_id, final_artifact_id);

CREATE INDEX ix_production_readiness_workspace_status ON production_readiness (workspace_id, status);

CREATE INDEX ix_production_readiness_artifact ON production_readiness (final_artifact_id);

CREATE INDEX ix_production_readiness_created_by ON production_readiness (created_by);

CREATE INDEX ix_production_readiness_updated_by ON production_readiness (updated_by);

CREATE TRIGGER trg_production_jobs_version BEFORE UPDATE ON production_jobs FOR EACH ROW EXECUTE FUNCTION set_version_and_updated_at();;

ALTER TABLE production_jobs ENABLE ROW LEVEL SECURITY;;

ALTER TABLE production_jobs FORCE ROW LEVEL SECURITY;;

GRANT SELECT, INSERT, UPDATE, DELETE ON production_jobs TO app_runtime;;

CREATE POLICY production_jobs_select_member ON production_jobs FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]));;

CREATE POLICY production_jobs_insert_roles ON production_jobs FOR INSERT WITH CHECK (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

CREATE POLICY production_jobs_update_roles ON production_jobs FOR UPDATE USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

CREATE TRIGGER trg_production_readiness_version BEFORE UPDATE ON production_readiness FOR EACH ROW EXECUTE FUNCTION set_version_and_updated_at();;

ALTER TABLE production_readiness ENABLE ROW LEVEL SECURITY;;

ALTER TABLE production_readiness FORCE ROW LEVEL SECURITY;;

GRANT SELECT, INSERT, UPDATE, DELETE ON production_readiness TO app_runtime;;

CREATE POLICY production_readiness_select_member ON production_readiness FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]));;

CREATE POLICY production_readiness_insert_roles ON production_readiness FOR INSERT WITH CHECK (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

CREATE POLICY production_readiness_update_roles ON production_readiness FOR UPDATE USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

CREATE TRIGGER trg_production_assets_immutable BEFORE UPDATE ON production_assets FOR EACH ROW EXECUTE FUNCTION prevent_update();;

CREATE TRIGGER trg_production_assets_immutable_delete BEFORE DELETE ON production_assets FOR EACH ROW EXECUTE FUNCTION prevent_delete();;

ALTER TABLE production_assets ENABLE ROW LEVEL SECURITY;;

ALTER TABLE production_assets FORCE ROW LEVEL SECURITY;;

GRANT SELECT, INSERT ON production_assets TO app_runtime;;

CREATE POLICY production_assets_select_member ON production_assets FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]));;

CREATE POLICY production_assets_insert_roles ON production_assets FOR INSERT WITH CHECK (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

CREATE TRIGGER trg_final_artifacts_immutable BEFORE UPDATE ON final_artifacts FOR EACH ROW EXECUTE FUNCTION prevent_update();;

CREATE TRIGGER trg_final_artifacts_immutable_delete BEFORE DELETE ON final_artifacts FOR EACH ROW EXECUTE FUNCTION prevent_delete();;

ALTER TABLE final_artifacts ENABLE ROW LEVEL SECURITY;;

ALTER TABLE final_artifacts FORCE ROW LEVEL SECURITY;;

GRANT SELECT, INSERT ON final_artifacts TO app_runtime;;

CREATE POLICY final_artifacts_select_member ON final_artifacts FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]));;

CREATE POLICY final_artifacts_insert_roles ON final_artifacts FOR INSERT WITH CHECK (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

CREATE TRIGGER trg_media_qa_results_immutable BEFORE UPDATE ON media_qa_results FOR EACH ROW EXECUTE FUNCTION prevent_update();;

CREATE TRIGGER trg_media_qa_results_immutable_delete BEFORE DELETE ON media_qa_results FOR EACH ROW EXECUTE FUNCTION prevent_delete();;

ALTER TABLE media_qa_results ENABLE ROW LEVEL SECURITY;;

ALTER TABLE media_qa_results FORCE ROW LEVEL SECURITY;;

GRANT SELECT, INSERT ON media_qa_results TO app_runtime;;

CREATE POLICY media_qa_results_select_member ON media_qa_results FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]));;

CREATE POLICY media_qa_results_insert_roles ON media_qa_results FOR INSERT WITH CHECK (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

CREATE TRIGGER trg_production_repairs_immutable BEFORE UPDATE ON production_repairs FOR EACH ROW EXECUTE FUNCTION prevent_update();;

CREATE TRIGGER trg_production_repairs_immutable_delete BEFORE DELETE ON production_repairs FOR EACH ROW EXECUTE FUNCTION prevent_delete();;

ALTER TABLE production_repairs ENABLE ROW LEVEL SECURITY;;

ALTER TABLE production_repairs FORCE ROW LEVEL SECURITY;;

GRANT SELECT, INSERT ON production_repairs TO app_runtime;;

CREATE POLICY production_repairs_select_member ON production_repairs FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]));;

CREATE POLICY production_repairs_insert_roles ON production_repairs FOR INSERT WITH CHECK (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

CREATE TRIGGER trg_artifact_invalidations_immutable BEFORE UPDATE ON artifact_invalidations FOR EACH ROW EXECUTE FUNCTION prevent_update();;

CREATE TRIGGER trg_artifact_invalidations_immutable_delete BEFORE DELETE ON artifact_invalidations FOR EACH ROW EXECUTE FUNCTION prevent_delete();;

ALTER TABLE artifact_invalidations ENABLE ROW LEVEL SECURITY;;

ALTER TABLE artifact_invalidations FORCE ROW LEVEL SECURITY;;

GRANT SELECT, INSERT ON artifact_invalidations TO app_runtime;;

CREATE POLICY artifact_invalidations_select_member ON artifact_invalidations FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]));;

CREATE POLICY artifact_invalidations_insert_roles ON artifact_invalidations FOR INSERT WITH CHECK (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

UPDATE alembic_version SET version_num='0046' WHERE alembic_version.version_num = '0045';

-- Running upgrade 0046 -> 0047

CREATE INDEX ix_production_assets_item ON production_assets (content_item_id);

CREATE INDEX ix_final_artifacts_item ON final_artifacts (content_item_id);

CREATE INDEX ix_final_artifacts_render_asset ON final_artifacts (render_asset_id);

CREATE INDEX ix_production_readiness_version ON production_readiness (content_version_id);

UPDATE alembic_version SET version_num='0047' WHERE alembic_version.version_num = '0046';

