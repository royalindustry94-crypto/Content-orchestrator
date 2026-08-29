-- Running upgrade 0047 -> 0048

CREATE TABLE platform_policy_sources (
    id UUID NOT NULL, 
    workspace_id UUID NOT NULL, 
    platform TEXT NOT NULL, 
    policy_category TEXT NOT NULL, 
    source TEXT NOT NULL, 
    source_reference TEXT NOT NULL, 
    effective_at TIMESTAMP WITH TIME ZONE, 
    retrieved_at TIMESTAMP WITH TIME ZONE, 
    last_verified_at TIMESTAMP WITH TIME ZONE, 
    rule_version TEXT NOT NULL, 
    status TEXT DEFAULT 'freshness_unverified' NOT NULL, 
    test_data BOOLEAN DEFAULT false NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    created_by UUID, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_policy_source_version UNIQUE (workspace_id, platform, policy_category, rule_version), 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE, 
    FOREIGN KEY(created_by) REFERENCES profiles (id)
);

CREATE INDEX ix_policy_sources_workspace_platform ON platform_policy_sources (workspace_id, platform);

CREATE INDEX ix_policy_sources_workspace_status ON platform_policy_sources (workspace_id, status);

CREATE INDEX ix_policy_sources_created_by ON platform_policy_sources (created_by);

CREATE TABLE audit_gate_manifests (
    id UUID NOT NULL, 
    workspace_id UUID NOT NULL, 
    content_type TEXT NOT NULL, 
    manifest_version INTEGER NOT NULL, 
    required_gates JSONB DEFAULT '[]'::jsonb NOT NULL, 
    requirements JSONB DEFAULT '{}'::jsonb NOT NULL, 
    is_active BOOLEAN DEFAULT true NOT NULL, 
    test_data BOOLEAN DEFAULT false NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    created_by UUID, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_audit_gate_manifest_version UNIQUE (workspace_id, content_type, manifest_version), 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE, 
    FOREIGN KEY(created_by) REFERENCES profiles (id)
);

CREATE INDEX ix_audit_gate_manifest_workspace_active ON audit_gate_manifests (workspace_id, is_active);

CREATE INDEX ix_audit_gate_manifest_created_by ON audit_gate_manifests (created_by);

CREATE TABLE artifact_rights_evidence (
    id UUID NOT NULL, 
    workspace_id UUID NOT NULL, 
    final_artifact_id UUID NOT NULL, 
    asset_id UUID, 
    origin TEXT NOT NULL, 
    provider_or_source TEXT, 
    license_or_right_basis TEXT, 
    generation_record JSONB DEFAULT '{}'::jsonb NOT NULL, 
    source_reference TEXT, 
    modification_lineage JSONB DEFAULT '{}'::jsonb NOT NULL, 
    rights_status TEXT DEFAULT 'unverified' NOT NULL, 
    test_data BOOLEAN DEFAULT false NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    created_by UUID, 
    PRIMARY KEY (id), 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE, 
    FOREIGN KEY(final_artifact_id) REFERENCES final_artifacts (id) ON DELETE CASCADE, 
    FOREIGN KEY(asset_id) REFERENCES assets (id) ON DELETE SET NULL, 
    FOREIGN KEY(created_by) REFERENCES profiles (id)
);

CREATE INDEX ix_rights_workspace_artifact ON artifact_rights_evidence (workspace_id, final_artifact_id);

CREATE INDEX ix_rights_workspace_status ON artifact_rights_evidence (workspace_id, rights_status);

CREATE INDEX ix_rights_artifact ON artifact_rights_evidence (final_artifact_id);

CREATE INDEX ix_rights_asset ON artifact_rights_evidence (asset_id);

CREATE INDEX ix_rights_created_by ON artifact_rights_evidence (created_by);

CREATE TABLE compliance_audits (
    id UUID NOT NULL, 
    workspace_id UUID NOT NULL, 
    final_artifact_id UUID NOT NULL, 
    artifact_hash TEXT NOT NULL, 
    content_version_id UUID NOT NULL, 
    target_platform TEXT NOT NULL, 
    policy_source_id UUID, 
    policy_version TEXT, 
    compliance_worker_id TEXT NOT NULL, 
    input_snapshot JSONB DEFAULT '{}'::jsonb NOT NULL, 
    status TEXT DEFAULT 'not_run' NOT NULL, 
    risk_level TEXT DEFAULT 'unknown' NOT NULL, 
    findings JSONB DEFAULT '[]'::jsonb NOT NULL, 
    evidence JSONB DEFAULT '[]'::jsonb NOT NULL, 
    required_disclosures JSONB DEFAULT '[]'::jsonb NOT NULL, 
    rights_status TEXT DEFAULT 'unverified' NOT NULL, 
    reused_content_risk TEXT DEFAULT 'unknown' NOT NULL, 
    monetization_risk TEXT DEFAULT 'unknown' NOT NULL, 
    recommended_action TEXT, 
    provider_state TEXT DEFAULT 'not_configured' NOT NULL, 
    provider_calls_used INTEGER DEFAULT '0' NOT NULL, 
    verification_calls_used INTEGER DEFAULT '0' NOT NULL, 
    token_count INTEGER DEFAULT '0' NOT NULL, 
    cost_usd NUMERIC(10, 4) DEFAULT '0' NOT NULL, 
    retry_history JSONB DEFAULT '[]'::jsonb NOT NULL, 
    started_at TIMESTAMP WITH TIME ZONE, 
    completed_at TIMESTAMP WITH TIME ZONE, 
    test_data BOOLEAN DEFAULT false NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_compliance_audit_artifact_hash UNIQUE (final_artifact_id, artifact_hash), 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE, 
    FOREIGN KEY(final_artifact_id) REFERENCES final_artifacts (id) ON DELETE CASCADE, 
    FOREIGN KEY(content_version_id) REFERENCES content_versions (id) ON DELETE RESTRICT, 
    FOREIGN KEY(policy_source_id) REFERENCES platform_policy_sources (id) ON DELETE SET NULL
);

CREATE INDEX ix_compliance_audits_workspace_artifact ON compliance_audits (workspace_id, final_artifact_id);

CREATE INDEX ix_compliance_audits_workspace_status ON compliance_audits (workspace_id, status);

CREATE INDEX ix_compliance_audits_artifact ON compliance_audits (final_artifact_id);

CREATE INDEX ix_compliance_audits_version ON compliance_audits (content_version_id);

CREATE INDEX ix_compliance_audits_policy ON compliance_audits (policy_source_id);

CREATE TABLE compliance_invalidations (
    id UUID NOT NULL, 
    workspace_id UUID NOT NULL, 
    compliance_audit_id UUID NOT NULL, 
    final_artifact_id UUID NOT NULL, 
    reason TEXT NOT NULL, 
    affected_dimensions JSONB DEFAULT '[]'::jsonb NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    created_by UUID, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_compliance_invalidation_reason UNIQUE (compliance_audit_id, reason), 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE, 
    FOREIGN KEY(compliance_audit_id) REFERENCES compliance_audits (id) ON DELETE CASCADE, 
    FOREIGN KEY(final_artifact_id) REFERENCES final_artifacts (id) ON DELETE CASCADE, 
    FOREIGN KEY(created_by) REFERENCES profiles (id)
);

CREATE INDEX ix_compliance_invalidations_workspace_artifact ON compliance_invalidations (workspace_id, final_artifact_id);

CREATE INDEX ix_compliance_invalidations_audit ON compliance_invalidations (compliance_audit_id);

CREATE INDEX ix_compliance_invalidations_artifact ON compliance_invalidations (final_artifact_id);

CREATE INDEX ix_compliance_invalidations_created_by ON compliance_invalidations (created_by);

CREATE TABLE chief_audits (
    id UUID NOT NULL, 
    workspace_id UUID NOT NULL, 
    final_artifact_id UUID NOT NULL, 
    artifact_hash TEXT NOT NULL, 
    content_version_id UUID NOT NULL, 
    gate_manifest_id UUID NOT NULL, 
    chief_auditor_worker_id TEXT NOT NULL, 
    gate_snapshot JSONB DEFAULT '{}'::jsonb NOT NULL, 
    lineage_status TEXT DEFAULT 'incomplete' NOT NULL, 
    version_integrity_status TEXT DEFAULT 'incomplete' NOT NULL, 
    cost_reconciliation_status TEXT DEFAULT 'incomplete' NOT NULL, 
    provider_reconciliation_status TEXT DEFAULT 'incomplete' NOT NULL, 
    warnings JSONB DEFAULT '[]'::jsonb NOT NULL, 
    blockers JSONB DEFAULT '[]'::jsonb NOT NULL, 
    evidence JSONB DEFAULT '[]'::jsonb NOT NULL, 
    status TEXT DEFAULT 'blocked' NOT NULL, 
    cost_usd NUMERIC(10, 4) DEFAULT '0' NOT NULL, 
    retry_history JSONB DEFAULT '[]'::jsonb NOT NULL, 
    started_at TIMESTAMP WITH TIME ZONE, 
    completed_at TIMESTAMP WITH TIME ZONE, 
    test_data BOOLEAN DEFAULT false NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_chief_audit_artifact_hash UNIQUE (final_artifact_id, artifact_hash), 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE, 
    FOREIGN KEY(final_artifact_id) REFERENCES final_artifacts (id) ON DELETE CASCADE, 
    FOREIGN KEY(content_version_id) REFERENCES content_versions (id) ON DELETE RESTRICT, 
    FOREIGN KEY(gate_manifest_id) REFERENCES audit_gate_manifests (id) ON DELETE RESTRICT
);

CREATE INDEX ix_chief_audits_workspace_artifact ON chief_audits (workspace_id, final_artifact_id);

CREATE INDEX ix_chief_audits_workspace_status ON chief_audits (workspace_id, status);

CREATE INDEX ix_chief_audits_artifact ON chief_audits (final_artifact_id);

CREATE INDEX ix_chief_audits_version ON chief_audits (content_version_id);

CREATE INDEX ix_chief_audits_manifest ON chief_audits (gate_manifest_id);

CREATE TABLE chief_audit_invalidations (
    id UUID NOT NULL, 
    workspace_id UUID NOT NULL, 
    chief_audit_id UUID NOT NULL, 
    final_artifact_id UUID NOT NULL, 
    reason TEXT NOT NULL, 
    affected_dimensions JSONB DEFAULT '[]'::jsonb NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    created_by UUID, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_chief_audit_invalidation_reason UNIQUE (chief_audit_id, reason), 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE, 
    FOREIGN KEY(chief_audit_id) REFERENCES chief_audits (id) ON DELETE CASCADE, 
    FOREIGN KEY(final_artifact_id) REFERENCES final_artifacts (id) ON DELETE CASCADE, 
    FOREIGN KEY(created_by) REFERENCES profiles (id)
);

CREATE INDEX ix_chief_audit_invalidations_workspace_artifact ON chief_audit_invalidations (workspace_id, final_artifact_id);

CREATE INDEX ix_chief_audit_invalidations_chief ON chief_audit_invalidations (chief_audit_id);

CREATE INDEX ix_chief_audit_invalidations_artifact ON chief_audit_invalidations (final_artifact_id);

CREATE INDEX ix_chief_audit_invalidations_created_by ON chief_audit_invalidations (created_by);

CREATE TABLE human_review_packages (
    id UUID NOT NULL, 
    workspace_id UUID NOT NULL, 
    final_artifact_id UUID NOT NULL, 
    artifact_hash TEXT NOT NULL, 
    content_version_id UUID NOT NULL, 
    chief_audit_id UUID NOT NULL, 
    review_gate_id UUID, 
    target_platform TEXT NOT NULL, 
    package_snapshot JSONB DEFAULT '{}'::jsonb NOT NULL, 
    warnings JSONB DEFAULT '[]'::jsonb NOT NULL, 
    required_disclosures JSONB DEFAULT '[]'::jsonb NOT NULL, 
    total_cost_usd NUMERIC(10, 4) DEFAULT '0' NOT NULL, 
    test_data BOOLEAN DEFAULT false NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    created_by UUID, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_human_review_package_artifact_hash UNIQUE (final_artifact_id, artifact_hash), 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE, 
    FOREIGN KEY(final_artifact_id) REFERENCES final_artifacts (id) ON DELETE CASCADE, 
    FOREIGN KEY(content_version_id) REFERENCES content_versions (id) ON DELETE RESTRICT, 
    FOREIGN KEY(chief_audit_id) REFERENCES chief_audits (id) ON DELETE RESTRICT, 
    FOREIGN KEY(review_gate_id) REFERENCES review_gates (id) ON DELETE SET NULL, 
    FOREIGN KEY(created_by) REFERENCES profiles (id)
);

CREATE INDEX ix_human_review_packages_workspace_artifact ON human_review_packages (workspace_id, final_artifact_id);

CREATE INDEX ix_human_review_packages_workspace_gate ON human_review_packages (workspace_id, review_gate_id);

CREATE INDEX ix_human_review_packages_artifact ON human_review_packages (final_artifact_id);

CREATE INDEX ix_human_review_packages_chief ON human_review_packages (chief_audit_id);

CREATE INDEX ix_human_review_packages_gate ON human_review_packages (review_gate_id);

CREATE INDEX ix_human_review_packages_created_by ON human_review_packages (created_by);

CREATE TABLE artifact_publication_eligibility (
    id UUID NOT NULL, 
    workspace_id UUID NOT NULL, 
    final_artifact_id UUID NOT NULL, 
    artifact_hash TEXT NOT NULL, 
    content_version_id UUID NOT NULL, 
    target_platform TEXT NOT NULL, 
    chief_audit_id UUID, 
    review_gate_id UUID, 
    review_decision_id UUID, 
    status TEXT DEFAULT 'blocked' NOT NULL, 
    blocking_reasons JSONB DEFAULT '[]'::jsonb NOT NULL, 
    publication_eligible BOOLEAN DEFAULT false NOT NULL, 
    test_data BOOLEAN DEFAULT false NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    created_by UUID, 
    updated_by UUID, 
    version INTEGER DEFAULT '1' NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_artifact_publication_eligibility UNIQUE (workspace_id, final_artifact_id, target_platform), 
    FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE, 
    FOREIGN KEY(final_artifact_id) REFERENCES final_artifacts (id) ON DELETE CASCADE, 
    FOREIGN KEY(content_version_id) REFERENCES content_versions (id) ON DELETE RESTRICT, 
    FOREIGN KEY(chief_audit_id) REFERENCES chief_audits (id) ON DELETE SET NULL, 
    FOREIGN KEY(review_gate_id) REFERENCES review_gates (id) ON DELETE SET NULL, 
    FOREIGN KEY(review_decision_id) REFERENCES review_decisions (id) ON DELETE SET NULL, 
    FOREIGN KEY(created_by) REFERENCES profiles (id), 
    FOREIGN KEY(updated_by) REFERENCES profiles (id)
);

CREATE INDEX ix_artifact_publication_eligibility_workspace_artifact ON artifact_publication_eligibility (workspace_id, final_artifact_id);

CREATE INDEX ix_artifact_publication_eligibility_workspace_status ON artifact_publication_eligibility (workspace_id, status);

CREATE INDEX ix_artifact_publication_eligibility_artifact ON artifact_publication_eligibility (final_artifact_id);

CREATE INDEX ix_artifact_publication_eligibility_chief ON artifact_publication_eligibility (chief_audit_id);

CREATE INDEX ix_artifact_publication_eligibility_gate ON artifact_publication_eligibility (review_gate_id);

CREATE INDEX ix_artifact_publication_eligibility_created_by ON artifact_publication_eligibility (created_by);

CREATE INDEX ix_artifact_publication_eligibility_updated_by ON artifact_publication_eligibility (updated_by);

CREATE TRIGGER trg_platform_policy_sources_immutable BEFORE UPDATE ON platform_policy_sources FOR EACH ROW EXECUTE FUNCTION prevent_update();;

CREATE TRIGGER trg_platform_policy_sources_immutable_delete BEFORE DELETE ON platform_policy_sources FOR EACH ROW EXECUTE FUNCTION prevent_delete();;

ALTER TABLE platform_policy_sources ENABLE ROW LEVEL SECURITY;;

ALTER TABLE platform_policy_sources FORCE ROW LEVEL SECURITY;;

GRANT SELECT, INSERT ON platform_policy_sources TO app_runtime;;

CREATE POLICY platform_policy_sources_select_member ON platform_policy_sources FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]));;

CREATE POLICY platform_policy_sources_insert_roles ON platform_policy_sources FOR INSERT WITH CHECK (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

CREATE TRIGGER trg_artifact_rights_evidence_immutable BEFORE UPDATE ON artifact_rights_evidence FOR EACH ROW EXECUTE FUNCTION prevent_update();;

CREATE TRIGGER trg_artifact_rights_evidence_immutable_delete BEFORE DELETE ON artifact_rights_evidence FOR EACH ROW EXECUTE FUNCTION prevent_delete();;

ALTER TABLE artifact_rights_evidence ENABLE ROW LEVEL SECURITY;;

ALTER TABLE artifact_rights_evidence FORCE ROW LEVEL SECURITY;;

GRANT SELECT, INSERT ON artifact_rights_evidence TO app_runtime;;

CREATE POLICY artifact_rights_evidence_select_member ON artifact_rights_evidence FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]));;

CREATE POLICY artifact_rights_evidence_insert_roles ON artifact_rights_evidence FOR INSERT WITH CHECK (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

CREATE TRIGGER trg_audit_gate_manifests_immutable BEFORE UPDATE ON audit_gate_manifests FOR EACH ROW EXECUTE FUNCTION prevent_update();;

CREATE TRIGGER trg_audit_gate_manifests_immutable_delete BEFORE DELETE ON audit_gate_manifests FOR EACH ROW EXECUTE FUNCTION prevent_delete();;

ALTER TABLE audit_gate_manifests ENABLE ROW LEVEL SECURITY;;

ALTER TABLE audit_gate_manifests FORCE ROW LEVEL SECURITY;;

GRANT SELECT, INSERT ON audit_gate_manifests TO app_runtime;;

CREATE POLICY audit_gate_manifests_select_member ON audit_gate_manifests FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]));;

CREATE POLICY audit_gate_manifests_insert_roles ON audit_gate_manifests FOR INSERT WITH CHECK (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

CREATE TRIGGER trg_compliance_audits_immutable BEFORE UPDATE ON compliance_audits FOR EACH ROW EXECUTE FUNCTION prevent_update();;

CREATE TRIGGER trg_compliance_audits_immutable_delete BEFORE DELETE ON compliance_audits FOR EACH ROW EXECUTE FUNCTION prevent_delete();;

ALTER TABLE compliance_audits ENABLE ROW LEVEL SECURITY;;

ALTER TABLE compliance_audits FORCE ROW LEVEL SECURITY;;

GRANT SELECT, INSERT ON compliance_audits TO app_runtime;;

CREATE POLICY compliance_audits_select_member ON compliance_audits FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]));;

CREATE POLICY compliance_audits_insert_roles ON compliance_audits FOR INSERT WITH CHECK (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

CREATE TRIGGER trg_compliance_invalidations_immutable BEFORE UPDATE ON compliance_invalidations FOR EACH ROW EXECUTE FUNCTION prevent_update();;

CREATE TRIGGER trg_compliance_invalidations_immutable_delete BEFORE DELETE ON compliance_invalidations FOR EACH ROW EXECUTE FUNCTION prevent_delete();;

ALTER TABLE compliance_invalidations ENABLE ROW LEVEL SECURITY;;

ALTER TABLE compliance_invalidations FORCE ROW LEVEL SECURITY;;

GRANT SELECT, INSERT ON compliance_invalidations TO app_runtime;;

CREATE POLICY compliance_invalidations_select_member ON compliance_invalidations FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]));;

CREATE POLICY compliance_invalidations_insert_roles ON compliance_invalidations FOR INSERT WITH CHECK (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

CREATE TRIGGER trg_chief_audits_immutable BEFORE UPDATE ON chief_audits FOR EACH ROW EXECUTE FUNCTION prevent_update();;

CREATE TRIGGER trg_chief_audits_immutable_delete BEFORE DELETE ON chief_audits FOR EACH ROW EXECUTE FUNCTION prevent_delete();;

ALTER TABLE chief_audits ENABLE ROW LEVEL SECURITY;;

ALTER TABLE chief_audits FORCE ROW LEVEL SECURITY;;

GRANT SELECT, INSERT ON chief_audits TO app_runtime;;

CREATE POLICY chief_audits_select_member ON chief_audits FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]));;

CREATE POLICY chief_audits_insert_roles ON chief_audits FOR INSERT WITH CHECK (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

CREATE TRIGGER trg_chief_audit_invalidations_immutable BEFORE UPDATE ON chief_audit_invalidations FOR EACH ROW EXECUTE FUNCTION prevent_update();;

CREATE TRIGGER trg_chief_audit_invalidations_immutable_delete BEFORE DELETE ON chief_audit_invalidations FOR EACH ROW EXECUTE FUNCTION prevent_delete();;

ALTER TABLE chief_audit_invalidations ENABLE ROW LEVEL SECURITY;;

ALTER TABLE chief_audit_invalidations FORCE ROW LEVEL SECURITY;;

GRANT SELECT, INSERT ON chief_audit_invalidations TO app_runtime;;

CREATE POLICY chief_audit_invalidations_select_member ON chief_audit_invalidations FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]));;

CREATE POLICY chief_audit_invalidations_insert_roles ON chief_audit_invalidations FOR INSERT WITH CHECK (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

CREATE TRIGGER trg_human_review_packages_immutable BEFORE UPDATE ON human_review_packages FOR EACH ROW EXECUTE FUNCTION prevent_update();;

CREATE TRIGGER trg_human_review_packages_immutable_delete BEFORE DELETE ON human_review_packages FOR EACH ROW EXECUTE FUNCTION prevent_delete();;

ALTER TABLE human_review_packages ENABLE ROW LEVEL SECURITY;;

ALTER TABLE human_review_packages FORCE ROW LEVEL SECURITY;;

GRANT SELECT, INSERT ON human_review_packages TO app_runtime;;

CREATE POLICY human_review_packages_select_member ON human_review_packages FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]));;

CREATE POLICY human_review_packages_insert_roles ON human_review_packages FOR INSERT WITH CHECK (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

CREATE TRIGGER trg_artifact_publication_eligibility_version BEFORE UPDATE ON artifact_publication_eligibility FOR EACH ROW EXECUTE FUNCTION set_version_and_updated_at();;

ALTER TABLE artifact_publication_eligibility ENABLE ROW LEVEL SECURITY;;

ALTER TABLE artifact_publication_eligibility FORCE ROW LEVEL SECURITY;;

GRANT SELECT, INSERT, UPDATE, DELETE ON artifact_publication_eligibility TO app_runtime;;

CREATE POLICY artifact_publication_eligibility_select_member ON artifact_publication_eligibility FOR SELECT USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor','reviewer']::workspace_role[]));;

CREATE POLICY artifact_publication_eligibility_insert_roles ON artifact_publication_eligibility FOR INSERT WITH CHECK (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

CREATE POLICY artifact_publication_eligibility_update_roles ON artifact_publication_eligibility FOR UPDATE USING (app_user_has_workspace_role(workspace_id, ARRAY['admin','editor']::workspace_role[]));;

UPDATE alembic_version SET version_num='0048' WHERE alembic_version.version_num = '0047';

-- Running upgrade 0048 -> 0049

ALTER TABLE compliance_audits DROP CONSTRAINT uq_compliance_audit_artifact_hash;

ALTER TABLE chief_audits DROP CONSTRAINT uq_chief_audit_artifact_hash;

UPDATE alembic_version SET version_num='0049' WHERE alembic_version.version_num = '0048';

-- Running upgrade 0049 -> 0050

CREATE INDEX ix_human_review_packages_version ON human_review_packages (content_version_id);

CREATE INDEX ix_artifact_publication_eligibility_version ON artifact_publication_eligibility (content_version_id);

CREATE INDEX ix_artifact_publication_eligibility_decision ON artifact_publication_eligibility (review_decision_id);

UPDATE alembic_version SET version_num='0050' WHERE alembic_version.version_num = '0049';
