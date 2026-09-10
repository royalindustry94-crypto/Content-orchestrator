import { useEffect, useState, type FormEvent } from "react";
import {
  getContentProfile,
  saveContentProfile,
  type ContentProfile,
  type ContentProfileInput,
} from "./api";
import { useDialogFocus } from "./useDialogFocus";

type Props = {
  token: string;
  workspaceId: string;
  initialProfile: ContentProfile | null;
  onClose: () => void;
  onSaved: (profile: ContentProfile) => void;
};

type StepId = "business" | "audience" | "voice" | "plan";

const STEPS: Array<{ id: StepId; eyebrow: string; title: string }> = [
  { id: "business", eyebrow: "Step 1 of 4", title: "Your business" },
  { id: "audience", eyebrow: "Step 2 of 4", title: "Who you're for" },
  { id: "voice", eyebrow: "Step 3 of 4", title: "Brand voice" },
  { id: "plan", eyebrow: "Step 4 of 4", title: "Content plan" },
];

const PLATFORMS = ["Instagram", "TikTok", "YouTube", "LinkedIn", "Facebook", "Other"];

export function ContentSetupWizard({ token, workspaceId, initialProfile, onClose, onSaved }: Props) {
  const [stepIndex, setStepIndex] = useState(0);
  const [businessName, setBusinessName] = useState(initialProfile?.business_name ?? "");
  const [offer, setOffer] = useState(initialProfile?.offer ?? "");
  const [targetAudience, setTargetAudience] = useState(initialProfile?.target_audience ?? "");
  const [brandVoice, setBrandVoice] = useState(initialProfile?.brand_voice ?? "");
  const [targetPlatform, setTargetPlatform] = useState(initialProfile?.target_platform ?? "");
  const [contentGoal, setContentGoal] = useState(initialProfile?.content_goal ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const dialogRef = useDialogFocus<HTMLDivElement>(true, onClose);
  const step = STEPS[stepIndex];
  const isLastStep = stepIndex === STEPS.length - 1;

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!isLastStep) {
      setStepIndex((current) => current + 1);
      return;
    }
    setSaving(true);
    setError(null);
    const payload: ContentProfileInput = {
      business_name: businessName,
      offer,
      target_audience: targetAudience,
      brand_voice: brandVoice,
      target_platform: targetPlatform,
      content_goal: contentGoal,
    };
    try {
      const saved = await saveContentProfile(token, workspaceId, payload);
      onSaved(saved);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Couldn't save your setup — try again.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <div
        className="setup-wizard"
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="setup-wizard-title"
        tabIndex={-1}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="setup-wizard__header">
          <div>
            <p className="setup-wizard__eyebrow">{step.eyebrow}</p>
            <h2 id="setup-wizard-title">{step.title}</h2>
          </div>
          <button className="setup-wizard__close" onClick={onClose} type="button" aria-label="Close setup">
            ×
          </button>
        </div>

        <div className="setup-wizard__steps" aria-hidden="true">
          {STEPS.map((s, index) => (
            <span
              key={s.id}
              className={
                index === stepIndex
                  ? "setup-wizard__dot setup-wizard__dot--active"
                  : index < stepIndex
                    ? "setup-wizard__dot setup-wizard__dot--done"
                    : "setup-wizard__dot"
              }
            />
          ))}
        </div>

        <form className="setup-wizard__form" onSubmit={handleSubmit}>
          {step.id === "business" ? (
            <>
              <label>
                Business name
                <input
                  value={businessName}
                  onChange={(event) => setBusinessName(event.target.value)}
                  placeholder="e.g. Acme Studio"
                  maxLength={200}
                  autoFocus
                />
              </label>
              <label>
                What do you offer?
                <textarea
                  value={offer}
                  onChange={(event) => setOffer(event.target.value)}
                  placeholder="e.g. Short-form video production for local restaurants"
                  maxLength={2000}
                  rows={3}
                />
              </label>
            </>
          ) : null}

          {step.id === "audience" ? (
            <label>
              Who is this content for?
              <textarea
                value={targetAudience}
                onChange={(event) => setTargetAudience(event.target.value)}
                placeholder="e.g. Restaurant owners in mid-size US cities who don't have time to film themselves"
                maxLength={2000}
                rows={4}
                autoFocus
              />
            </label>
          ) : null}

          {step.id === "voice" ? (
            <label>
              How should your content sound?
              <textarea
                value={brandVoice}
                onChange={(event) => setBrandVoice(event.target.value)}
                placeholder="e.g. Warm, direct, a little playful — never salesy"
                maxLength={2000}
                rows={4}
                autoFocus
              />
            </label>
          ) : null}

          {step.id === "plan" ? (
            <>
              <label>
                Primary platform
                <select value={targetPlatform} onChange={(event) => setTargetPlatform(event.target.value)} autoFocus>
                  <option value="">Choose one</option>
                  {PLATFORMS.map((platform) => (
                    <option key={platform} value={platform.toLowerCase()}>
                      {platform}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                What's the goal?
                <input
                  value={contentGoal}
                  onChange={(event) => setContentGoal(event.target.value)}
                  placeholder="e.g. book more tastings"
                  maxLength={2000}
                />
              </label>
            </>
          ) : null}

          {error ? <p className="setup-wizard__error" role="alert">{error}</p> : null}

          <div className="setup-wizard__actions">
            {stepIndex > 0 ? (
              <button
                className="button button--ghost"
                type="button"
                onClick={() => setStepIndex((current) => current - 1)}
                disabled={saving}
              >
                Back
              </button>
            ) : (
              <button className="button button--ghost" type="button" onClick={onClose} disabled={saving}>
                Skip for now
              </button>
            )}
            <button className="button button--primary" type="submit" disabled={saving}>
              {saving ? "Saving…" : isLastStep ? "Finish setup" : "Next"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

const PLATFORM_OPTIONS = ["Instagram", "TikTok", "YouTube", "LinkedIn", "Facebook", "Other"];

/** The "custom" manual path: every field, one flat form, edit anytime —
 * reads/writes the same profile the guided wizard does. Lives in
 * Settings.
 */
export function BusinessProfileSettings({ token, workspaceId }: { token: string; workspaceId: string }) {
  const [profile, setProfile] = useState<ContentProfile | null | undefined>(undefined);
  const [businessName, setBusinessName] = useState("");
  const [offer, setOffer] = useState("");
  const [targetAudience, setTargetAudience] = useState("");
  const [brandVoice, setBrandVoice] = useState("");
  const [targetPlatform, setTargetPlatform] = useState("");
  const [contentGoal, setContentGoal] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    let active = true;
    getContentProfile(token, workspaceId).then((loaded) => {
      if (!active) return;
      setProfile(loaded);
      setBusinessName(loaded?.business_name ?? "");
      setOffer(loaded?.offer ?? "");
      setTargetAudience(loaded?.target_audience ?? "");
      setBrandVoice(loaded?.brand_voice ?? "");
      setTargetPlatform(loaded?.target_platform ?? "");
      setContentGoal(loaded?.content_goal ?? "");
    });
    return () => {
      active = false;
    };
  }, [token, workspaceId]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setSaved(false);
    const payload: ContentProfileInput = {
      business_name: businessName,
      offer,
      target_audience: targetAudience,
      brand_voice: brandVoice,
      target_platform: targetPlatform,
      content_goal: contentGoal,
    };
    try {
      const result = await saveContentProfile(token, workspaceId, payload);
      setProfile(result);
      setSaved(true);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Couldn't save — try again.");
    } finally {
      setSaving(false);
    }
  }

  if (profile === undefined) {
    return (
      <section className="surface">
        <h3>Business profile</h3>
        <p>Loading…</p>
      </section>
    );
  }

  return (
    <section className="surface">
      <h3>Business profile</h3>
      <p>
        Used as the default business, audience, and brand-voice context for new content. Edit
        anytime — nothing here connects a live AI provider on its own.
      </p>
      <form className="setup-wizard__form" onSubmit={handleSubmit}>
        <label>
          Business name
          <input value={businessName} onChange={(event) => setBusinessName(event.target.value)} maxLength={200} />
        </label>
        <label>
          What do you offer?
          <textarea value={offer} onChange={(event) => setOffer(event.target.value)} maxLength={2000} rows={2} />
        </label>
        <label>
          Target audience
          <textarea
            value={targetAudience}
            onChange={(event) => setTargetAudience(event.target.value)}
            maxLength={2000}
            rows={2}
          />
        </label>
        <label>
          Brand voice
          <textarea value={brandVoice} onChange={(event) => setBrandVoice(event.target.value)} maxLength={2000} rows={2} />
        </label>
        <label>
          Primary platform
          <select value={targetPlatform} onChange={(event) => setTargetPlatform(event.target.value)}>
            <option value="">Choose one</option>
            {PLATFORM_OPTIONS.map((platform) => (
              <option key={platform} value={platform.toLowerCase()}>
                {platform}
              </option>
            ))}
          </select>
        </label>
        <label>
          Content goal
          <input value={contentGoal} onChange={(event) => setContentGoal(event.target.value)} maxLength={2000} />
        </label>
        {error ? <p className="setup-wizard__error" role="alert">{error}</p> : null}
        <div className="setup-wizard__actions">
          <span aria-live="polite">{saved && !saving ? "Saved." : ""}</span>
          <button className="button button--primary" type="submit" disabled={saving}>
            {saving ? "Saving…" : "Save"}
          </button>
        </div>
      </form>
    </section>
  );
}
