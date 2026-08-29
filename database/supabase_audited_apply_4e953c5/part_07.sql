-- Running upgrade 0044 -> 0045

CREATE TABLE content_department_runs (
    id UUID NOT NULL, 
    workspace_id UUID NOT NULL, 
    strategy_brief_id UUID NOT NULL, 
    trigger TEXT DEFAULT 'manual' NOT NULL, 
    status TEXT DEFAULT 'queued' NOT NULL, 
    provider_state TEXT DEFAULT 'not_configured' NOT NULL, 
    business_context_state TEXT DEFAULT 'incomplete' NOT NULL, 
    max_provider_calls INTEGER DEFAULT '0' NOT NULL, 
    max_tokens INTEGER DEFAULT '0' NOT NULL, 
    max_cost_usd NUMERIC(10, 4) DEFAULT '0' NOT NULL, 
    max_attempts INTEGER DEFAULT '1' NOT NULL, 
    timeout_seconds INTEGER DEFAULT '900' NOT NULL, 
    provider_calls_used INTEGER DEFAULT '0' NOT NULL, 
    tokens_used INTEGER DEFAULT '0' NOT NULL, 
    actual_cost_usd NUMERIC(10, 4) DEFAULT '0' NOT NULL, 
    creative_directions_created INTEGER DEFAULT '0' NOT NULL, 
    packages_ready INTEGER DEFAULT '0' NOT NULL, 
    packages_blocked INTEGER DEFAULT '0' NOT NULL, 
    last_error TEXT, 
    correlation_id UUID NOT NULL, 
    trace_id TEXT, 
    test_data BOOLEAN DEFAULT false NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    created_by UUID, 
    updated_by UUID, 
    version INTEGER DEFAULT '1' NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT ck_content_department_run_bounds CHECK (max_provider_calls >= 0 AND max_tokens >= 0 AND max_cost_usd >= 0 AND max_attempts > 0 AND timeout_seconds > 0), 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE, 
    FOREIGN KEY(strategy_brief_id) REFERENCES strategy_briefs (id) ON DELETE RESTRICT, 
    FOREIGN KEY(created_by) REFERENCES profiles (id), 
    FOREIGN KEY(updated_by) REFERENCES profiles (id)
);

CREATE INDEX ix_content_department_runs_workspace_created ON content_department_runs (workspace_id, created_at);

CREATE INDEX ix_content_department_runs_workspace_status ON content_department_runs (workspace_id, status);

CREATE INDEX ix_content_department_runs_workspace_strategy ON content_department_runs (workspace_id, strategy_brief_id);

CREATE INDEX ix_content_department_runs_correlation ON content_department_runs (workspace_id, correlation_id);

CREATE INDEX ix_content_department_runs_strategy ON content_department_runs (strategy_brief_id);

CREATE INDEX ix_content_department_runs_created_by ON content_department_runs (created_by);

CREATE INDEX ix_content_department_runs_updated_by ON content_department_runs (updated_by);

CREATE TABLE creative_directions (
    id UUID NOT NULL, 
    workspace_id UUID NOT NULL, 
    content_department_run_id UUID NOT NULL, 
    strategy_brief_id UUID NOT NULL, 
    objective TEXT NOT NULL, 
    target_platform TEXT, 
    target_audience TEXT, 
    creative_concept TEXT NOT NULL, 
    opening_pattern TEXT, 
    hook_direction TEXT, 
    story_structure TEXT, 
    tone TEXT, 
    pacing TEXT, 
    visual_direction TEXT, 
    audio_direction TEXT, 
    cta_direction TEXT, 
    desired_emotion TEXT, 
    required_claims JSONB DEFAULT '[]'::jsonb NOT NULL, 
    prohibited_claims JSONB DEFAULT '[]'::jsonb NOT NULL, 
    required_assets JSONB DEFAULT '[]'::jsonb NOT NULL, 
    estimated_duration TEXT, 
    production_complexity TEXT DEFAULT 'unknown' NOT NULL, 
    risk_notes JSONB DEFAULT '[]'::jsonb NOT NULL, 
    worker_id TEXT DEFAULT 'creative_director' NOT NULL, 
    provider TEXT DEFAULT 'not_configured' NOT NULL, 
    model TEXT, 
    prompt_version TEXT DEFAULT 'creative-director-v1' NOT NULL, 
    status TEXT DEFAULT 'draft' NOT NULL, 
    test_data BOOLEAN DEFAULT false NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    created_by UUID, 
    PRIMARY KEY (id), 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE, 
    FOREIGN KEY(content_department_run_id) REFERENCES content_department_runs (id) ON DELETE RESTRICT, 
    FOREIGN KEY(strategy_brief_id) REFERENCES strategy_briefs (id) ON DELETE RESTRICT, 
    FOREIGN KEY(created_by) REFERENCES profiles (id)
);

CREATE INDEX ix_creative_directions_workspace_strategy ON creative_directions (workspace_id, strategy_brief_id);

CREATE INDEX ix_creative_directions_workspace_run ON creative_directions (workspace_id, content_department_run_id);

CREATE INDEX ix_creative_directions_workspace_status ON creative_directions (workspace_id, status);

CREATE INDEX ix_creative_directions_run ON creative_directions (content_department_run_id);

CREATE INDEX ix_creative_directions_strategy ON creative_directions (strategy_brief_id);

CREATE INDEX ix_creative_directions_created_by ON creative_directions (created_by);

CREATE TABLE content_packages (
    id UUID NOT NULL, 
    workspace_id UUID NOT NULL, 
    content_department_run_id UUID NOT NULL, 
    creative_direction_id UUID NOT NULL, 
    strategy_brief_id UUID NOT NULL, 
    content_item_id UUID NOT NULL, 
    content_version_id UUID NOT NULL, 
    prior_content_version_id UUID, 
    revision_reason TEXT, 
    writer_worker_id TEXT DEFAULT 'writer' NOT NULL, 
    provider TEXT DEFAULT 'not_configured' NOT NULL, 
    model TEXT, 
    prompt_version TEXT DEFAULT 'writer-v1' NOT NULL, 
    input_references JSONB DEFAULT '{}'::jsonb NOT NULL, 
    package_fields JSONB DEFAULT '{}'::jsonb NOT NULL, 
    status TEXT DEFAULT 'writer_provider_not_configured' NOT NULL, 
    audit_gate_status TEXT DEFAULT 'not_run' NOT NULL, 
    producer_handoff_state TEXT DEFAULT 'blocked' NOT NULL, 
    invalidated_at TIMESTAMP WITH TIME ZONE, 
    test_data BOOLEAN DEFAULT false NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    created_by UUID, 
    updated_by UUID, 
    version INTEGER DEFAULT '1' NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_content_package_version UNIQUE (workspace_id, content_version_id), 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE, 
    FOREIGN KEY(content_department_run_id) REFERENCES content_department_runs (id) ON DELETE RESTRICT, 
    FOREIGN KEY(creative_direction_id) REFERENCES creative_directions (id) ON DELETE RESTRICT, 
    FOREIGN KEY(strategy_brief_id) REFERENCES strategy_briefs (id) ON DELETE RESTRICT, 
    FOREIGN KEY(content_item_id) REFERENCES content_items (id) ON DELETE CASCADE, 
    FOREIGN KEY(content_version_id) REFERENCES content_versions (id) ON DELETE CASCADE, 
    FOREIGN KEY(prior_content_version_id) REFERENCES content_versions (id) ON DELETE SET NULL, 
    FOREIGN KEY(created_by) REFERENCES profiles (id), 
    FOREIGN KEY(updated_by) REFERENCES profiles (id)
);

CREATE INDEX ix_content_packages_workspace_status ON content_packages (workspace_id, status);

CREATE INDEX ix_content_packages_workspace_item ON content_packages (workspace_id, content_item_id);

CREATE INDEX ix_content_packages_workspace_direction ON content_packages (workspace_id, creative_direction_id);

CREATE INDEX ix_content_packages_run ON content_packages (content_department_run_id);

CREATE INDEX ix_content_packages_strategy ON content_packages (strategy_brief_id);

CREATE INDEX ix_content_packages_item ON content_packages (content_item_id);

CREATE INDEX ix_content_packages_version ON content_packages (content_version_id);

CREATE INDEX ix_content_packages_prior_version ON content_packages (prior_content_version_id);

CREATE INDEX ix_content_packages_direction ON content_packages (creative_direction_id);

CREATE INDEX ix_content_packages_created_by ON content_packages (created_by);

CREATE INDEX ix_content_packages_updated_by ON content_packages (updated_by);

CREATE TABLE content_claims (
    id UUID NOT NULL, 
    workspace_id UUID NOT NULL, 
    content_package_id UUID NOT NULL, 
    content_version_id UUID NOT NULL, 
    claim_text TEXT NOT NULL, 
    claim_type TEXT NOT NULL, 
    source_required BOOLEAN DEFAULT true NOT NULL, 
    supporting_evidence JSONB DEFAULT '[]'::jsonb NOT NULL, 
    verification_status TEXT DEFAULT 'not_run' NOT NULL, 
    confidence NUMERIC(5, 4) DEFAULT '0' NOT NULL, 
    risk TEXT DEFAULT 'unknown' NOT NULL, 
    freshness TEXT, 
    evidence_reasoning TEXT, 
    test_data BOOLEAN DEFAULT false NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    created_by UUID, 
    updated_by UUID, 
    version INTEGER DEFAULT '1' NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE, 
    FOREIGN KEY(content_package_id) REFERENCES content_packages (id) ON DELETE CASCADE, 
    FOREIGN KEY(content_version_id) REFERENCES content_versions (id) ON DELETE CASCADE, 
    FOREIGN KEY(created_by) REFERENCES profiles (id), 
    FOREIGN KEY(updated_by) REFERENCES profiles (id)
);

CREATE INDEX ix_content_claims_workspace_version ON content_claims (workspace_id, content_version_id);

CREATE INDEX ix_content_claims_workspace_status ON content_claims (workspace_id, verification_status);

CREATE INDEX ix_content_claims_package ON content_claims (content_package_id);

CREATE INDEX ix_content_claims_version ON content_claims (content_version_id);

CREATE INDEX ix_content_claims_created_by ON content_claims (created_by);

CREATE INDEX ix_content_claims_updated_by ON content_claims (updated_by);

CREATE TABLE content_audits (
    id UUID NOT NULL, 
    workspace_id UUID NOT NULL, 
    content_package_id UUID NOT NULL, 
    content_version_id UUID NOT NULL, 
    auditor_type TEXT NOT NULL, 
    auditor_worker_id TEXT NOT NULL, 
    state TEXT DEFAULT 'not_run' NOT NULL, 
    artifact_snapshot JSONB DEFAULT '{}'::jsonb NOT NULL, 
    requirements_snapshot JSONB DEFAULT '{}'::jsonb NOT NULL, 
    findings JSONB DEFAULT '[]'::jsonb NOT NULL, 
    warnings JSONB DEFAULT '[]'::jsonb NOT NULL, 
    blocked_reasons JSONB DEFAULT '[]'::jsonb NOT NULL, 
    evidence JSONB DEFAULT '[]'::jsonb NOT NULL, 
    checked_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    cost_usd NUMERIC(10, 4) DEFAULT '0' NOT NULL, 
    retry_history JSONB DEFAULT '[]'::jsonb NOT NULL, 
    test_data BOOLEAN DEFAULT false NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE, 
    FOREIGN KEY(content_package_id) REFERENCES content_packages (id) ON DELETE CASCADE, 
    FOREIGN KEY(content_version_id) REFERENCES content_versions (id) ON DELETE CASCADE
);

CREATE INDEX ix_content_audits_workspace_package_checked ON content_audits (workspace_id, content_package_id, checked_at);

CREATE INDEX ix_content_audits_workspace_version_type ON content_audits (workspace_id, content_version_id, auditor_type);

CREATE INDEX ix_content_audits_package ON content_audits (content_package_id);

CREATE INDEX ix_content_audits_version ON content_audits (content_version_id);

CREATE TABLE content_audit_invalidations (
    id UUID NOT NULL, 
    workspace_id UUID NOT NULL, 
    content_audit_id UUID NOT NULL, 
    content_package_id UUID NOT NULL, 
    content_version_id UUID NOT NULL, 
    reason TEXT NOT NULL, 
    affected_dimensions JSONB DEFAULT '[]'::jsonb NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    created_by UUID, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_content_audit_invalidation UNIQUE (content_audit_id, content_version_id), 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE, 
    FOREIGN KEY(content_audit_id) REFERENCES content_audits (id) ON DELETE CASCADE, 
    FOREIGN KEY(content_package_id) REFERENCES content_packages (id) ON DELETE CASCADE, 
    FOREIGN KEY(content_version_id) REFERENCES content_versions (id) ON DELETE CASCADE, 
    FOREIGN KEY(created_by) REFERENCES profiles (id)
);

CREATE INDEX ix_content_audit_invalidations_workspace_version ON content_audit_invalidations (workspace_id, content_version_id);

CREATE INDEX ix_content_audit_invalidations_audit ON content_audit_invalidations (content_audit_id);

CREATE INDEX ix_content_audit_invalidations_package ON content_audit_invalidations (content_package_id);

CREATE INDEX ix_content_audit_invalidations_version ON content_audit_invalidations (content_version_id);

CREATE INDEX ix_content_audit_invalidations_created_by ON content_audit_invalidations (created_by);

CREATE TABLE originality_fingerprints (
    id UUID NOT NULL, 
    workspace_id UUID NOT NULL, 
    content_package_id UUID NOT NULL, 
    content_version_id UUID NOT NULL, 
    text_fingerprint TEXT NOT NULL, 
    hook_fingerprint TEXT NOT NULL, 
    structure_fingerprint TEXT NOT NULL, 
    semantic_reference TEXT, 
    comparison_set JSONB DEFAULT '[]'::jsonb NOT NULL, 
    similarity_findings JSONB DEFAULT '[]'::jsonb NOT NULL, 
    state TEXT DEFAULT 'not_run' NOT NULL, 
    test_data BOOLEAN DEFAULT false NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    created_by UUID, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_originality_fingerprint_version UNIQUE (workspace_id, content_version_id), 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE, 
    FOREIGN KEY(content_package_id) REFERENCES content_packages (id) ON DELETE CASCADE, 
    FOREIGN KEY(content_version_id) REFERENCES content_versions (id) ON DELETE CASCADE, 
    FOREIGN KEY(created_by) REFERENCES profiles (id)
);

CREATE INDEX ix_originality_fingerprints_workspace_text ON originality_fingerprints (workspace_id, text_fingerprint);

CREATE INDEX ix_originality_fingerprints_workspace_hook ON originality_fingerprints (workspace_id, hook_fingerprint);

CREATE INDEX ix_originality_fingerprints_workspace_structure ON originality_fingerprints (workspace_id, structure_fingerprint);

CREATE INDEX ix_originality_fingerprints_package ON originality_fingerprints (content_package_id);

CREATE INDEX ix_originality_fingerprints_version ON originality_fingerprints (content_version_id);

CREATE INDEX ix_originality_fingerprints_created_by ON originality_fingerprints (created_by);

CREATE TRIGGER trg_content_department_runs_version BEFORE UPDATE ON content_department_runs FOR EACH ROW EXECUTE FUNCTION set_version_and_updated_at();;

ALTER TABLE content_department_runs ENABLE ROW LEVEL SECURITY;;

ALTER TABLE content_department_runs FORCE ROW LEVEL SECURITY;;

GRANT SELECT, INSERT, UPDATE, DELETE ON content_department_runs TO app_runtime;;

CREATE POLICY content_department_runs_select_member ON content_department_runs FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]));;

CREATE POLICY content_department_runs_insert_roles ON content_department_runs FOR INSERT WITH CHECK (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

CREATE POLICY content_department_runs_update_roles ON content_department_runs FOR UPDATE USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

CREATE TRIGGER trg_content_packages_version BEFORE UPDATE ON content_packages FOR EACH ROW EXECUTE FUNCTION set_version_and_updated_at();;

ALTER TABLE content_packages ENABLE ROW LEVEL SECURITY;;

ALTER TABLE content_packages FORCE ROW LEVEL SECURITY;;

GRANT SELECT, INSERT, UPDATE, DELETE ON content_packages TO app_runtime;;

CREATE POLICY content_packages_select_member ON content_packages FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]));;

CREATE POLICY content_packages_insert_roles ON content_packages FOR INSERT WITH CHECK (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

CREATE POLICY content_packages_update_roles ON content_packages FOR UPDATE USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

CREATE TRIGGER trg_content_claims_version BEFORE UPDATE ON content_claims FOR EACH ROW EXECUTE FUNCTION set_version_and_updated_at();;

ALTER TABLE content_claims ENABLE ROW LEVEL SECURITY;;

ALTER TABLE content_claims FORCE ROW LEVEL SECURITY;;

GRANT SELECT, INSERT, UPDATE, DELETE ON content_claims TO app_runtime;;

CREATE POLICY content_claims_select_member ON content_claims FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]));;

CREATE POLICY content_claims_insert_roles ON content_claims FOR INSERT WITH CHECK (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

CREATE POLICY content_claims_update_roles ON content_claims FOR UPDATE USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

CREATE TRIGGER trg_creative_directions_immutable BEFORE UPDATE ON creative_directions FOR EACH ROW EXECUTE FUNCTION prevent_update();;

CREATE TRIGGER trg_creative_directions_immutable_delete BEFORE DELETE ON creative_directions FOR EACH ROW EXECUTE FUNCTION prevent_delete();;

ALTER TABLE creative_directions ENABLE ROW LEVEL SECURITY;;

ALTER TABLE creative_directions FORCE ROW LEVEL SECURITY;;

GRANT SELECT, INSERT ON creative_directions TO app_runtime;;

CREATE POLICY creative_directions_select_member ON creative_directions FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]));;

CREATE POLICY creative_directions_insert_roles ON creative_directions FOR INSERT WITH CHECK (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

CREATE TRIGGER trg_content_audits_immutable BEFORE UPDATE ON content_audits FOR EACH ROW EXECUTE FUNCTION prevent_update();;

CREATE TRIGGER trg_content_audits_immutable_delete BEFORE DELETE ON content_audits FOR EACH ROW EXECUTE FUNCTION prevent_delete();;

ALTER TABLE content_audits ENABLE ROW LEVEL SECURITY;;

ALTER TABLE content_audits FORCE ROW LEVEL SECURITY;;

GRANT SELECT, INSERT ON content_audits TO app_runtime;;

CREATE POLICY content_audits_select_member ON content_audits FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]));;

CREATE POLICY content_audits_insert_roles ON content_audits FOR INSERT WITH CHECK (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

CREATE TRIGGER trg_content_audit_invalidations_immutable BEFORE UPDATE ON content_audit_invalidations FOR EACH ROW EXECUTE FUNCTION prevent_update();;

CREATE TRIGGER trg_content_audit_invalidations_immutable_delete BEFORE DELETE ON content_audit_invalidations FOR EACH ROW EXECUTE FUNCTION prevent_delete();;

ALTER TABLE content_audit_invalidations ENABLE ROW LEVEL SECURITY;;

ALTER TABLE content_audit_invalidations FORCE ROW LEVEL SECURITY;;

GRANT SELECT, INSERT ON content_audit_invalidations TO app_runtime;;

CREATE POLICY content_audit_invalidations_select_member ON content_audit_invalidations FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]));;

CREATE POLICY content_audit_invalidations_insert_roles ON content_audit_invalidations FOR INSERT WITH CHECK (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

CREATE TRIGGER trg_originality_fingerprints_immutable BEFORE UPDATE ON originality_fingerprints FOR EACH ROW EXECUTE FUNCTION prevent_update();;

CREATE TRIGGER trg_originality_fingerprints_immutable_delete BEFORE DELETE ON originality_fingerprints FOR EACH ROW EXECUTE FUNCTION prevent_delete();;

ALTER TABLE originality_fingerprints ENABLE ROW LEVEL SECURITY;;

ALTER TABLE originality_fingerprints FORCE ROW LEVEL SECURITY;;

GRANT SELECT, INSERT ON originality_fingerprints TO app_runtime;;

CREATE POLICY originality_fingerprints_select_member ON originality_fingerprints FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]));;

CREATE POLICY originality_fingerprints_insert_roles ON originality_fingerprints FOR INSERT WITH CHECK (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

UPDATE alembic_version SET version_num='0045' WHERE alembic_version.version_num = '0044';

