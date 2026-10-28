/**
 * URL Sanitizer and Validator for Official Scheme Guidelines and Direct Application Portals.
 * Enforces strict distinction between:
 *   1. Verified Direct Application URLs (e.g. online application/registration portals)
 *   2. Official Scheme Guidelines / Information URLs
 */

// Generic homepages and informational directories that must NEVER be used as direct application links
const GENERIC_HOMEPAGE_DOMAINS = new Set([
  "msme.gov.in",
  "www.msme.gov.in",
  "cgtmse.in",
  "www.cgtmse.in",
  "mudra.org.in",
  "www.mudra.org.in",
  "sidbi.in",
  "www.sidbi.in",
  "doe.gov.in",
  "www.doe.gov.in",
  "mca.gov.in",
  "www.mca.gov.in",
  "gst.gov.in",
  "www.gst.gov.in",
  "industries.telangana.gov.in",
  "dcmsme.gov.in",
  "www.dcmsme.gov.in",
  "startupindia.gov.in",
  "www.startupindia.gov.in",
]);

// Dedicated subdomains whose root path IS the direct service/application portal
const DEDICATED_PORTAL_HOSTS = new Set([
  "cluster.dcmsme.gov.in",
  "seedfund.startupindia.gov.in",
  "ipass.telangana.gov.in",
  "odr.msme.gov.in",
  "samadhaan.msme.gov.in",
  "gem.gov.in",
  "etenders.gov.in",
  "pmegp.msme.gov.in",
  "zed.msme.gov.in",
  "standupmitra.in",
  "www.standupmitra.in",
  "kviconline.gov.in",
  "www.kviconline.gov.in",
]);

/**
 * Validates whether a given URL is a verified, official direct online application portal.
 * Returns the sanitized URL if valid, or null if unverified / unavailable / generic homepage.
 *
 * Requirements:
 * - Must start with http:// or https://.
 * - Must not be a PDF or static document.
 * - Must belong to an official government or authorized scheme portal domain.
 * - Must NOT be a generic ministry homepage or information listing page.
 *
 * @param {string|null|undefined} rawUrl
 * @returns {string|null}
 */
export function validateDirectApplicationUrl(rawUrl) {
  if (!rawUrl || typeof rawUrl !== "string") {
    return null;
  }

  const trimmed = rawUrl.trim();
  if (!trimmed || !/^https?:\/\//i.test(trimmed)) {
    return null;
  }

  const lower = trimmed.toLowerCase();
  if (lower.includes(".pdf") || lower.endsWith(".doc") || lower.endsWith(".docx")) {
    return null;
  }

  try {
    const parsed = new URL(trimmed);
    const host = parsed.hostname.toLowerCase();
    const path = parsed.pathname.replace(/\/+$/, "");

    // Reject localhost / private IP ranges
    if (
      host === "localhost" ||
      host === "0.0.0.0" ||
      host === "127.0.0.1" ||
      host.startsWith("192.168.") ||
      host.startsWith("10.") ||
      host.endsWith(".local")
    ) {
      return null;
    }

    // Must belong to official government or verified scheme domain
    const isGovDomain =
      host.endsWith(".gov.in") ||
      host.endsWith(".nic.in") ||
      host.endsWith(".org.in") ||
      host.endsWith(".ac.in") ||
      host === "standupmitra.in" ||
      host.endsWith(".standupmitra.in") ||
      host === "cgtmse.in" ||
      host.endsWith(".cgtmse.in") ||
      host === "sidbi.in" ||
      host.endsWith(".sidbi.in") ||
      host === "kviconline.gov.in" ||
      host.endsWith(".kviconline.gov.in");

    if (!isGovDomain) {
      return null;
    }

    // Rejection: generic homepages or informational listings
    if (
      GENERIC_HOMEPAGE_DOMAINS.has(host) &&
      (path === "" ||
        path === "/en" ||
        path === "/offerings/schemes-and-services" ||
        path === "/pmegp")
    ) {
      return null;
    }

    // If path is root, only accept if host is an explicitly dedicated application portal
    if (path === "" || path === "/en") {
      if (!DEDICATED_PORTAL_HOSTS.has(host)) {
        return null;
      }
    }

    return trimmed;
  } catch {
    return null;
  }
}

/**
 * Sanitizes informational and guidelines URLs for reading scheme documentation.
 *
 * @param {string|null|undefined} rawUrl
 * @returns {string}
 */
export function cleanPortalUrl(rawUrl) {
  if (!rawUrl || typeof rawUrl !== "string") {
    return "";
  }

  const trimmed = rawUrl.trim();
  if (!trimmed) {
    return "";
  }

  // Preserve official scheme guidelines / documents verbatim;
  // do NOT strip scheme-specific pages or PDFs to generic domain root.
  return trimmed;
}
