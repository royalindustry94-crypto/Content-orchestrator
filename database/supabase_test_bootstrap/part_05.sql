-- Running upgrade 0040 -> 0041

CREATE TABLE research_runs (
    id UUID NOT NULL, 
    workspace_id UUID NOT NULL, 
    trigger TEXT DEFAULT 'manual' NOT NULL, 
    research_objective TEXT NOT NULL, 
    permitted_sources JSONB DEFAULT '[]'::jsonb NOT NULL, 
    started_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deadline TIMESTAMP WITH TIME ZONE NOT NULL, 
    max_searches INTEGER NOT NULL, 
    max_provider_calls INTEGER NOT NULL, 
    max_tokens INTEGER NOT NULL, 
    max_cost_usd NUMERIC(10, 4) NOT NULL, 
    max_attempts INTEGER NOT NULL, 
    status TEXT DEFAULT 'queued' NOT NULL, 
    provider_state TEXT DEFAULT 'not_configured' NOT NULL, 
    searches_used INTEGER DEFAULT '0' NOT NULL, 
    provider_calls_used INTEGER DEFAULT '0' NOT NULL, 
    tokens_used INTEGER DEFAULT '0' NOT NULL, 
    reserved_cost_usd NUMERIC(10, 4) DEFAULT '0' NOT NULL, 
    actual_cost_usd NUMERIC(10, 4) DEFAULT '0' NOT NULL, 
    opportunity_count INTEGER DEFAULT '0' NOT NULL, 
    audited_opportunity_count INTEGER DEFAULT '0' NOT NULL, 
    blocked_opportunity_count INTEGER DEFAULT '0' NOT NULL, 
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
    CONSTRAINT ck_research_runs_bounds CHECK (max_searches > 0 AND max_provider_calls >= 0 AND max_tokens >= 0 AND max_cost_usd >= 0 AND max_attempts > 0), 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE, 
    FOREIGN KEY(created_by) REFERENCES profiles (id), 
    FOREIGN KEY(updated_by) REFERENCES profiles (id)
);

CREATE INDEX ix_research_runs_workspace_created ON research_runs (workspace_id, created_at);

CREATE INDEX ix_research_runs_workspace_status ON research_runs (workspace_id, status);

CREATE INDEX ix_research_runs_workspace_correlation ON research_runs (workspace_id, correlation_id);

CREATE TABLE research_sources (
    id UUID NOT NULL, 
    workspace_id UUID NOT NULL, 
    research_run_id UUID NOT NULL, 
    canonical_url TEXT NOT NULL, 
    source_type TEXT NOT NULL, 
    retrieved_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    published_at TIMESTAMP WITH TIME ZONE, 
    publisher TEXT, 
    author TEXT, 
    claim_supported TEXT, 
    freshness TEXT DEFAULT 'unknown' NOT NULL, 
    confidence NUMERIC(5, 4) DEFAULT '0' NOT NULL, 
    content_digest TEXT NOT NULL, 
    safe_excerpt TEXT, 
    handling_state TEXT DEFAULT 'accepted' NOT NULL, 
    rejection_reason TEXT, 
    test_data BOOLEAN DEFAULT false NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_research_source_run_url UNIQUE (workspace_id, research_run_id, canonical_url), 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE, 
    FOREIGN KEY(research_run_id) REFERENCES research_runs (id) ON DELETE CASCADE
);

CREATE INDEX ix_research_sources_workspace_run ON research_sources (workspace_id, research_run_id);

CREATE INDEX ix_research_sources_workspace_digest ON research_sources (workspace_id, content_digest);

CREATE TABLE opportunities (
    id UUID NOT NULL, 
    workspace_id UUID NOT NULL, 
    research_run_id UUID NOT NULL, 
    title TEXT NOT NULL, 
    topic TEXT NOT NULL, 
    summary TEXT NOT NULL, 
    proposed_angle TEXT NOT NULL, 
    target_audience TEXT, 
    target_platform TEXT, 
    suggested_format TEXT, 
    discovered_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    freshness TEXT DEFAULT 'unknown' NOT NULL, 
    source_count INTEGER DEFAULT '0' NOT NULL, 
    confidence NUMERIC(5, 4) DEFAULT '0' NOT NULL, 
    risk TEXT DEFAULT 'unknown' NOT NULL, 
    status TEXT DEFAULT 'watching' NOT NULL, 
    created_by_worker TEXT DEFAULT 'scout' NOT NULL, 
    component_scores JSONB DEFAULT '{}'::jsonb NOT NULL, 
    score_reasoning JSONB DEFAULT '{}'::jsonb NOT NULL, 
    dedupe_key TEXT NOT NULL, 
    audit_gate_status TEXT DEFAULT 'not_run' NOT NULL, 
    performance_data_state TEXT DEFAULT 'no_performance_data' NOT NULL, 
    strategist_state TEXT DEFAULT 'not_sent' NOT NULL, 
    test_data BOOLEAN DEFAULT false NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    created_by UUID, 
    updated_by UUID, 
    version INTEGER DEFAULT '1' NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_opportunities_workspace_dedupe UNIQUE (workspace_id, dedupe_key), 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE, 
    FOREIGN KEY(research_run_id) REFERENCES research_runs (id) ON DELETE RESTRICT, 
    FOREIGN KEY(created_by) REFERENCES profiles (id), 
    FOREIGN KEY(updated_by) REFERENCES profiles (id)
);

CREATE INDEX ix_opportunities_workspace_status ON opportunities (workspace_id, status);

CREATE INDEX ix_opportunities_workspace_run ON opportunities (workspace_id, research_run_id);

CREATE INDEX ix_opportunities_workspace_topic ON opportunities (workspace_id, topic);

CREATE TABLE opportunity_evidence (
    id UUID NOT NULL, 
    workspace_id UUID NOT NULL, 
    opportunity_id UUID NOT NULL, 
    source_id UUID NOT NULL, 
    claim_supported TEXT NOT NULL, 
    relevance NUMERIC(5, 4) DEFAULT '0' NOT NULL, 
    contradiction_flag BOOLEAN DEFAULT false NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_opportunity_evidence_link UNIQUE (workspace_id, opportunity_id, source_id), 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE, 
    FOREIGN KEY(opportunity_id) REFERENCES opportunities (id) ON DELETE CASCADE, 
    FOREIGN KEY(source_id) REFERENCES research_sources (id) ON DELETE CASCADE
);

CREATE INDEX ix_opportunity_evidence_workspace_opportunity ON opportunity_evidence (workspace_id, opportunity_id);

CREATE TABLE research_audits (
    id UUID NOT NULL, 
    workspace_id UUID NOT NULL, 
    opportunity_id UUID NOT NULL, 
    research_run_id UUID NOT NULL, 
    state TEXT DEFAULT 'not_run' NOT NULL, 
    evaluator_context_version TEXT DEFAULT 'research-auditor-v1' NOT NULL, 
    scout_snapshot JSONB DEFAULT '{}'::jsonb NOT NULL, 
    findings JSONB DEFAULT '[]'::jsonb NOT NULL, 
    warnings JSONB DEFAULT '[]'::jsonb NOT NULL, 
    blocked_reasons JSONB DEFAULT '[]'::jsonb NOT NULL, 
    checked_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    test_data BOOLEAN DEFAULT false NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE, 
    FOREIGN KEY(opportunity_id) REFERENCES opportunities (id) ON DELETE CASCADE, 
    FOREIGN KEY(research_run_id) REFERENCES research_runs (id) ON DELETE CASCADE
);

CREATE INDEX ix_research_audits_workspace_opportunity_checked ON research_audits (workspace_id, opportunity_id, checked_at);

CREATE INDEX ix_research_audits_workspace_run ON research_audits (workspace_id, research_run_id);

CREATE TABLE research_schedules (
    id UUID NOT NULL, 
    workspace_id UUID NOT NULL, 
    frequency TEXT DEFAULT 'manual' NOT NULL, 
    enabled BOOLEAN DEFAULT false NOT NULL, 
    next_run_at TIMESTAMP WITH TIME ZONE, 
    paused_at TIMESTAMP WITH TIME ZONE, 
    enabled_by UUID, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    created_by UUID, 
    updated_by UUID, 
    version INTEGER DEFAULT '1' NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_research_schedule_workspace UNIQUE (workspace_id), 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE, 
    FOREIGN KEY(enabled_by) REFERENCES profiles (id), 
    FOREIGN KEY(created_by) REFERENCES profiles (id), 
    FOREIGN KEY(updated_by) REFERENCES profiles (id)
);

CREATE TRIGGER trg_research_runs_version BEFORE UPDATE ON research_runs FOR EACH ROW EXECUTE FUNCTION set_version_and_updated_at();;

ALTER TABLE research_runs ENABLE ROW LEVEL SECURITY;;

ALTER TABLE research_runs FORCE ROW LEVEL SECURITY;;

GRANT SELECT, INSERT, UPDATE, DELETE ON research_runs TO app_runtime;;

CREATE POLICY research_runs_select_member ON research_runs FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]));;

CREATE POLICY research_runs_insert_roles ON research_runs FOR INSERT WITH CHECK (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

CREATE POLICY research_runs_update_roles ON research_runs FOR UPDATE USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

CREATE TRIGGER trg_opportunities_version BEFORE UPDATE ON opportunities FOR EACH ROW EXECUTE FUNCTION set_version_and_updated_at();;

ALTER TABLE opportunities ENABLE ROW LEVEL SECURITY;;

ALTER TABLE opportunities FORCE ROW LEVEL SECURITY;;

GRANT SELECT, INSERT, UPDATE, DELETE ON opportunities TO app_runtime;;

CREATE POLICY opportunities_select_member ON opportunities FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]));;

CREATE POLICY opportunities_insert_roles ON opportunities FOR INSERT WITH CHECK (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

CREATE POLICY opportunities_update_roles ON opportunities FOR UPDATE USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

CREATE TRIGGER trg_research_schedules_version BEFORE UPDATE ON research_schedules FOR EACH ROW EXECUTE FUNCTION set_version_and_updated_at();;

ALTER TABLE research_schedules ENABLE ROW LEVEL SECURITY;;

ALTER TABLE research_schedules FORCE ROW LEVEL SECURITY;;

GRANT SELECT, INSERT, UPDATE, DELETE ON research_schedules TO app_runtime;;

CREATE POLICY research_schedules_select_member ON research_schedules FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]));;

CREATE POLICY research_schedules_insert_roles ON research_schedules FOR INSERT WITH CHECK (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

CREATE POLICY research_schedules_update_roles ON research_schedules FOR UPDATE USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

CREATE TRIGGER trg_research_sources_immutable BEFORE UPDATE ON research_sources FOR EACH ROW EXECUTE FUNCTION prevent_update();;

CREATE TRIGGER trg_research_sources_immutable_delete BEFORE DELETE ON research_sources FOR EACH ROW EXECUTE FUNCTION prevent_delete();;

ALTER TABLE research_sources ENABLE ROW LEVEL SECURITY;;

ALTER TABLE research_sources FORCE ROW LEVEL SECURITY;;

GRANT SELECT, INSERT ON research_sources TO app_runtime;;

CREATE POLICY research_sources_select_member ON research_sources FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]));;

CREATE POLICY research_sources_insert_roles ON research_sources FOR INSERT WITH CHECK (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

CREATE TRIGGER trg_opportunity_evidence_immutable BEFORE UPDATE ON opportunity_evidence FOR EACH ROW EXECUTE FUNCTION prevent_update();;

CREATE TRIGGER trg_opportunity_evidence_immutable_delete BEFORE DELETE ON opportunity_evidence FOR EACH ROW EXECUTE FUNCTION prevent_delete();;

ALTER TABLE opportunity_evidence ENABLE ROW LEVEL SECURITY;;

ALTER TABLE opportunity_evidence FORCE ROW LEVEL SECURITY;;

GRANT SELECT, INSERT ON opportunity_evidence TO app_runtime;;

CREATE POLICY opportunity_evidence_select_member ON opportunity_evidence FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]));;

CREATE POLICY opportunity_evidence_insert_roles ON opportunity_evidence FOR INSERT WITH CHECK (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

CREATE TRIGGER trg_research_audits_immutable BEFORE UPDATE ON research_audits FOR EACH ROW EXECUTE FUNCTION prevent_update();;

CREATE TRIGGER trg_research_audits_immutable_delete BEFORE DELETE ON research_audits FOR EACH ROW EXECUTE FUNCTION prevent_delete();;

ALTER TABLE research_audits ENABLE ROW LEVEL SECURITY;;

ALTER TABLE research_audits FORCE ROW LEVEL SECURITY;;

GRANT SELECT, INSERT ON research_audits TO app_runtime;;

CREATE POLICY research_audits_select_member ON research_audits FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]));;

CREATE POLICY research_audits_insert_roles ON research_audits FOR INSERT WITH CHECK (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

UPDATE alembic_version SET version_num='0041' WHERE alembic_version.version_num = '0040';

-- Running upgrade 0041 -> 0042

CREATE POLICY outbox_events_insert_roles ON outbox_events FOR INSERT WITH CHECK (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

UPDATE alembic_version SET version_num='0042' WHERE alembic_version.version_num = '0041';

-- Running upgrade 0042 -> 0043

CREATE INDEX ix_research_runs_created_by ON research_runs (created_by);

CREATE INDEX ix_research_runs_updated_by ON research_runs (updated_by);

CREATE INDEX ix_research_sources_run ON research_sources (research_run_id);

CREATE INDEX ix_opportunities_run ON opportunities (research_run_id);

CREATE INDEX ix_opportunities_created_by ON opportunities (created_by);

CREATE INDEX ix_opportunities_updated_by ON opportunities (updated_by);

CREATE INDEX ix_opportunity_evidence_opportunity ON opportunity_evidence (opportunity_id);

CREATE INDEX ix_opportunity_evidence_source ON opportunity_evidence (source_id);

CREATE INDEX ix_research_audits_opportunity ON research_audits (opportunity_id);

CREATE INDEX ix_research_audits_run ON research_audits (research_run_id);

CREATE INDEX ix_research_schedules_created_by ON research_schedules (created_by);

CREATE INDEX ix_research_schedules_enabled_by ON research_schedules (enabled_by);

CREATE INDEX ix_research_schedules_updated_by ON research_schedules (updated_by);

UPDATE alembic_version SET version_num='0043' WHERE alembic_version.version_num = '0042';

-- Running upgrade 0043 -> 0044

CREATE TABLE strategy_runs (
    id UUID NOT NULL, 
    workspace_id UUID NOT NULL, 
    trigger TEXT DEFAULT 'manual' NOT NULL, 
    strategy_objective TEXT NOT NULL, 
    source_opportunity_ids JSONB DEFAULT '[]'::jsonb NOT NULL, 
    started_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deadline TIMESTAMP WITH TIME ZONE NOT NULL, 
    max_provider_calls INTEGER NOT NULL, 
    max_tokens INTEGER NOT NULL, 
    max_cost_usd NUMERIC(10, 4) NOT NULL, 
    max_attempts INTEGER NOT NULL, 
    status TEXT DEFAULT 'queued' NOT NULL, 
    provider_state TEXT DEFAULT 'not_configured' NOT NULL, 
    business_context_state TEXT DEFAULT 'incomplete' NOT NULL, 
    provider_calls_used INTEGER DEFAULT '0' NOT NULL, 
    tokens_used INTEGER DEFAULT '0' NOT NULL, 
    reserved_cost_usd NUMERIC(10, 4) DEFAULT '0' NOT NULL, 
    actual_cost_usd NUMERIC(10, 4) DEFAULT '0' NOT NULL, 
    briefs_created INTEGER DEFAULT '0' NOT NULL, 
    briefs_passed INTEGER DEFAULT '0' NOT NULL, 
    briefs_blocked INTEGER DEFAULT '0' NOT NULL, 
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
    CONSTRAINT ck_strategy_runs_bounds CHECK (max_provider_calls >= 0 AND max_tokens >= 0 AND max_cost_usd >= 0 AND max_attempts > 0), 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE, 
    FOREIGN KEY(created_by) REFERENCES profiles (id), 
    FOREIGN KEY(updated_by) REFERENCES profiles (id)
);

CREATE INDEX ix_strategy_runs_workspace_created ON strategy_runs (workspace_id, created_at);

CREATE INDEX ix_strategy_runs_workspace_status ON strategy_runs (workspace_id, status);

CREATE INDEX ix_strategy_runs_workspace_correlation ON strategy_runs (workspace_id, correlation_id);

CREATE INDEX ix_strategy_runs_created_by ON strategy_runs (created_by);

CREATE INDEX ix_strategy_runs_updated_by ON strategy_runs (updated_by);

CREATE TABLE strategy_briefs (
    id UUID NOT NULL, 
    workspace_id UUID NOT NULL, 
    strategy_run_id UUID NOT NULL, 
    objective TEXT NOT NULL, 
    target_audience TEXT, 
    target_platform TEXT, 
    content_format TEXT, 
    creative_angle TEXT, 
    core_message TEXT, 
    hook_direction TEXT, 
    cta_direction TEXT, 
    business_goal TEXT, 
    success_metric TEXT, 
    commercial_goal TEXT, 
    estimated_complexity TEXT DEFAULT 'unknown' NOT NULL, 
    risk_level TEXT DEFAULT 'unknown' NOT NULL, 
    evidence_summary TEXT NOT NULL, 
    reasoning TEXT NOT NULL, 
    confidence NUMERIC(5, 4) DEFAULT '0' NOT NULL, 
    priority TEXT DEFAULT 'watch' NOT NULL, 
    component_scores JSONB DEFAULT '{}'::jsonb NOT NULL, 
    score_reasoning JSONB DEFAULT '{}'::jsonb NOT NULL, 
    recommended_length TEXT, 
    recommended_posting_window TEXT, 
    required_assets JSONB DEFAULT '[]'::jsonb NOT NULL, 
    production_requirements JSONB DEFAULT '[]'::jsonb NOT NULL, 
    rights_requirements JSONB DEFAULT '[]'::jsonb NOT NULL, 
    compliance_requirements JSONB DEFAULT '[]'::jsonb NOT NULL, 
    estimated_provider_usage JSONB DEFAULT '{}'::jsonb NOT NULL, 
    estimated_cost_range JSONB DEFAULT '{}'::jsonb NOT NULL, 
    cost_state TEXT DEFAULT 'unknown' NOT NULL, 
    capability_state TEXT DEFAULT 'not_configured' NOT NULL, 
    business_context_state TEXT DEFAULT 'incomplete' NOT NULL, 
    performance_data_state TEXT DEFAULT 'no_data' NOT NULL, 
    structural_fingerprint TEXT NOT NULL, 
    repetition_state TEXT DEFAULT 'not_run' NOT NULL, 
    repetition_reasons JSONB DEFAULT '[]'::jsonb NOT NULL, 
    audit_gate_status TEXT DEFAULT 'not_run' NOT NULL, 
    writer_handoff_state TEXT DEFAULT 'blocked' NOT NULL, 
    created_by_worker TEXT DEFAULT 'strategist' NOT NULL, 
    status TEXT DEFAULT 'draft' NOT NULL, 
    test_data BOOLEAN DEFAULT false NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    created_by UUID, 
    updated_by UUID, 
    version INTEGER DEFAULT '1' NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_strategy_briefs_workspace_fp UNIQUE (workspace_id, structural_fingerprint), 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE, 
    FOREIGN KEY(strategy_run_id) REFERENCES strategy_runs (id) ON DELETE RESTRICT, 
    FOREIGN KEY(created_by) REFERENCES profiles (id), 
    FOREIGN KEY(updated_by) REFERENCES profiles (id)
);

CREATE INDEX ix_strategy_briefs_workspace_status ON strategy_briefs (workspace_id, status);

CREATE INDEX ix_strategy_briefs_workspace_run ON strategy_briefs (workspace_id, strategy_run_id);

CREATE INDEX ix_strategy_briefs_workspace_priority ON strategy_briefs (workspace_id, priority);

CREATE INDEX ix_strategy_briefs_workspace_objective ON strategy_briefs (workspace_id, business_goal);

CREATE INDEX ix_strategy_briefs_run ON strategy_briefs (strategy_run_id);

CREATE INDEX ix_strategy_briefs_created_by ON strategy_briefs (created_by);

CREATE INDEX ix_strategy_briefs_updated_by ON strategy_briefs (updated_by);

CREATE TABLE strategy_brief_opportunities (
    id UUID NOT NULL, 
    workspace_id UUID NOT NULL, 
    strategy_brief_id UUID NOT NULL, 
    opportunity_id UUID NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_strategy_brief_opportunity UNIQUE (workspace_id, strategy_brief_id, opportunity_id), 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE, 
    FOREIGN KEY(strategy_brief_id) REFERENCES strategy_briefs (id) ON DELETE CASCADE, 
    FOREIGN KEY(opportunity_id) REFERENCES opportunities (id) ON DELETE RESTRICT
);

CREATE INDEX ix_strategy_brief_opportunities_workspace_brief ON strategy_brief_opportunities (workspace_id, strategy_brief_id);

CREATE INDEX ix_strategy_brief_opportunities_brief ON strategy_brief_opportunities (strategy_brief_id);

CREATE INDEX ix_strategy_brief_opportunities_opportunity ON strategy_brief_opportunities (opportunity_id);

CREATE TABLE strategy_audits (
    id UUID NOT NULL, 
    workspace_id UUID NOT NULL, 
    strategy_brief_id UUID NOT NULL, 
    strategy_run_id UUID NOT NULL, 
    state TEXT DEFAULT 'not_run' NOT NULL, 
    evaluator_context_version TEXT DEFAULT 'strategy-auditor-v1' NOT NULL, 
    brief_snapshot JSONB DEFAULT '{}'::jsonb NOT NULL, 
    findings JSONB DEFAULT '[]'::jsonb NOT NULL, 
    warnings JSONB DEFAULT '[]'::jsonb NOT NULL, 
    blocked_reasons JSONB DEFAULT '[]'::jsonb NOT NULL, 
    checked_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    test_data BOOLEAN DEFAULT false NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE, 
    FOREIGN KEY(strategy_brief_id) REFERENCES strategy_briefs (id) ON DELETE CASCADE, 
    FOREIGN KEY(strategy_run_id) REFERENCES strategy_runs (id) ON DELETE CASCADE
);

CREATE INDEX ix_strategy_audits_workspace_brief_checked ON strategy_audits (workspace_id, strategy_brief_id, checked_at);

CREATE INDEX ix_strategy_audits_workspace_run ON strategy_audits (workspace_id, strategy_run_id);

CREATE INDEX ix_strategy_audits_brief ON strategy_audits (strategy_brief_id);

CREATE INDEX ix_strategy_audits_run ON strategy_audits (strategy_run_id);

CREATE TABLE strategy_schedules (
    id UUID NOT NULL, 
    workspace_id UUID NOT NULL, 
    frequency TEXT DEFAULT 'manual' NOT NULL, 
    enabled BOOLEAN DEFAULT false NOT NULL, 
    next_run_at TIMESTAMP WITH TIME ZONE, 
    paused_at TIMESTAMP WITH TIME ZONE, 
    enabled_by UUID, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    created_by UUID, 
    updated_by UUID, 
    version INTEGER DEFAULT '1' NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_strategy_schedule_workspace UNIQUE (workspace_id), 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE, 
    FOREIGN KEY(enabled_by) REFERENCES profiles (id), 
    FOREIGN KEY(created_by) REFERENCES profiles (id), 
    FOREIGN KEY(updated_by) REFERENCES profiles (id)
);

CREATE INDEX ix_strategy_schedules_created_by ON strategy_schedules (created_by);

CREATE INDEX ix_strategy_schedules_enabled_by ON strategy_schedules (enabled_by);

CREATE INDEX ix_strategy_schedules_updated_by ON strategy_schedules (updated_by);

CREATE TRIGGER trg_strategy_runs_version BEFORE UPDATE ON strategy_runs FOR EACH ROW EXECUTE FUNCTION set_version_and_updated_at();;

ALTER TABLE strategy_runs ENABLE ROW LEVEL SECURITY;;

ALTER TABLE strategy_runs FORCE ROW LEVEL SECURITY;;

GRANT SELECT, INSERT, UPDATE, DELETE ON strategy_runs TO app_runtime;;

CREATE POLICY strategy_runs_select_member ON strategy_runs FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]));;

CREATE POLICY strategy_runs_insert_roles ON strategy_runs FOR INSERT WITH CHECK (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

CREATE POLICY strategy_runs_update_roles ON strategy_runs FOR UPDATE USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

CREATE TRIGGER trg_strategy_briefs_version BEFORE UPDATE ON strategy_briefs FOR EACH ROW EXECUTE FUNCTION set_version_and_updated_at();;

ALTER TABLE strategy_briefs ENABLE ROW LEVEL SECURITY;;

ALTER TABLE strategy_briefs FORCE ROW LEVEL SECURITY;;

GRANT SELECT, INSERT, UPDATE, DELETE ON strategy_briefs TO app_runtime;;

CREATE POLICY strategy_briefs_select_member ON strategy_briefs FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]));;

CREATE POLICY strategy_briefs_insert_roles ON strategy_briefs FOR INSERT WITH CHECK (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

CREATE POLICY strategy_briefs_update_roles ON strategy_briefs FOR UPDATE USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

CREATE TRIGGER trg_strategy_schedules_version BEFORE UPDATE ON strategy_schedules FOR EACH ROW EXECUTE FUNCTION set_version_and_updated_at();;

ALTER TABLE strategy_schedules ENABLE ROW LEVEL SECURITY;;

ALTER TABLE strategy_schedules FORCE ROW LEVEL SECURITY;;

GRANT SELECT, INSERT, UPDATE, DELETE ON strategy_schedules TO app_runtime;;

CREATE POLICY strategy_schedules_select_member ON strategy_schedules FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]));;

CREATE POLICY strategy_schedules_insert_roles ON strategy_schedules FOR INSERT WITH CHECK (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

CREATE POLICY strategy_schedules_update_roles ON strategy_schedules FOR UPDATE USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

CREATE TRIGGER trg_strategy_brief_opportunities_immutable BEFORE UPDATE ON strategy_brief_opportunities FOR EACH ROW EXECUTE FUNCTION prevent_update();;

CREATE TRIGGER trg_strategy_brief_opportunities_immutable_delete BEFORE DELETE ON strategy_brief_opportunities FOR EACH ROW EXECUTE FUNCTION prevent_delete();;

ALTER TABLE strategy_brief_opportunities ENABLE ROW LEVEL SECURITY;;

ALTER TABLE strategy_brief_opportunities FORCE ROW LEVEL SECURITY;;

GRANT SELECT, INSERT ON strategy_brief_opportunities TO app_runtime;;

CREATE POLICY strategy_brief_opportunities_select_member ON strategy_brief_opportunities FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]));;

CREATE POLICY strategy_brief_opportunities_insert_roles ON strategy_brief_opportunities FOR INSERT WITH CHECK (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

CREATE TRIGGER trg_strategy_audits_immutable BEFORE UPDATE ON strategy_audits FOR EACH ROW EXECUTE FUNCTION prevent_update();;

CREATE TRIGGER trg_strategy_audits_immutable_delete BEFORE DELETE ON strategy_audits FOR EACH ROW EXECUTE FUNCTION prevent_delete();;

ALTER TABLE strategy_audits ENABLE ROW LEVEL SECURITY;;

ALTER TABLE strategy_audits FORCE ROW LEVEL SECURITY;;

GRANT SELECT, INSERT ON strategy_audits TO app_runtime;;

CREATE POLICY strategy_audits_select_member ON strategy_audits FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]));;

CREATE POLICY strategy_audits_insert_roles ON strategy_audits FOR INSERT WITH CHECK (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

UPDATE alembic_version SET version_num='0044' WHERE alembic_version.version_num = '0043';

