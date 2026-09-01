/** Isolated Founder Studio preview session — never send this token to FastAPI. */

export const FOUNDER_STUDIO_PREVIEW_TOKEN = "founder-studio-preview-ui-only";
export const FOUNDER_STUDIO_PREVIEW_WORKSPACE = "founder-studio-preview";
export const FOUNDER_STUDIO_PREVIEW_EMAIL = "Founder Preview";

export function isFounderStudioPreviewToken(token: string | null | undefined): boolean {
  return token === FOUNDER_STUDIO_PREVIEW_TOKEN;
}
