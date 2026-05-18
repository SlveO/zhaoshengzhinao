import tenantConfig from "@/tenant.config";

export const TENANT_SLUG = tenantConfig.tenantSlug;
export const BRAND = tenantConfig.brand;
export const FEATURES = tenantConfig.features;
export const APP_ID = tenantConfig.appId;

export function getBrandCSSVars(): Record<string, string> {
  return {
    "--brand-primary": BRAND.primaryColor,
    "--brand-secondary": BRAND.secondaryColor,
  };
}
