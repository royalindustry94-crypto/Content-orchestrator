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

