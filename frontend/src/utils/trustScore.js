/**
 * Trust Score Calculation & Bucketing Engine
 * 
 * Computes a 0-100 weighted trust score across 5 independent verification signals:
 * 1. RERA registration status (weight: 25%)
 * 2. Encumbrance certificate status (weight: 25%)
 * 3. Title clarity (weight: 20%)
 * 4. Document completeness ratio (weight: 15%)
 * 5. Owner/seller name match (weight: 15%)
 * 
 * Rules & Guarantees:
 * - Explicit handling of null/pending/not-applicable states (distinct from failure/flagged).
 * - Avoids legal certainty language (per compliance requirements).
 */

export const SIGNAL_WEIGHTS = {
  rera: 25,
  encumbrance: 25,
  title: 20,
  documentCompleteness: 15,
  ownerMatch: 15,
};

/**
 * Computes the individual signal breakdown and weighted overall trust score.
 * 
 * @param {Object} signals
 * @param {string|null} signals.rera_status - 'verified' | 'pending' | 'not_applicable' | 'unregistered' | null
 * @param {string|null} signals.encumbrance_status - 'clear' | 'pending' | 'encumbered' | 'not_applicable' | null
 * @param {string|null} signals.title_clarity - 'clear' | 'pending' | 'disputed' | null
 * @param {number|null} signals.document_completeness - float 0.0 - 1.0 or null
 * @param {string|null} signals.owner_match - 'match' | 'pending' | 'mismatch' | null
 * 
 * @returns {Object} Score details and breakdown
 */
export function computeTrustScore(signals = {}) {
  const {
    rera_status = null,
    encumbrance_status = null,
    title_clarity = null,
    document_completeness = null,
    owner_match = null,
  } = signals;

  const checks = [];
  let totalScore = 0;

  // 1. RERA Registration Status (25%)
  let reraScore = 0;
  let reraState = 'missing'; // 'pass' | 'fail' | 'pending' | 'not_applicable' | 'missing'
  let reraLabel = 'Not Provided';
  let reraDetail = 'RERA registration number not submitted.';

  if (rera_status === 'verified') {
    reraScore = SIGNAL_WEIGHTS.rera;
    reraState = 'pass';
    reraLabel = 'Registered & Validated';
    reraDetail = 'State RERA portal registration records match.';
  } else if (rera_status === 'not_applicable') {
    reraScore = SIGNAL_WEIGHTS.rera; // Not penalized
    reraState = 'not_applicable';
    reraLabel = 'RERA Exempt';
    reraDetail = 'Exempt under local real estate regulations.';
  } else if (rera_status === 'pending') {
    reraScore = SIGNAL_WEIGHTS.rera * 0.5;
    reraState = 'pending';
    reraLabel = 'In Verification';
    reraDetail = 'State authority verification in progress.';
  } else if (rera_status === 'unregistered') {
    reraScore = 0;
    reraState = 'fail';
    reraLabel = 'Unregistered / Notice';
    reraDetail = 'Project not found on active registry.';
  }
  totalScore += reraScore;
  checks.push({
    id: 'rera',
    title: 'RERA Registration',
    score: reraScore,
    maxScore: SIGNAL_WEIGHTS.rera,
    state: reraState,
    label: reraLabel,
    detail: reraDetail,
  });

  // 2. Encumbrance Certificate Status (25%)
  let ecScore = 0;
  let ecState = 'missing';
  let ecLabel = 'Not Provided';
  let ecDetail = 'Encumbrance Certificate not yet submitted.';

  if (encumbrance_status === 'clear') {
    ecScore = SIGNAL_WEIGHTS.encumbrance;
    ecState = 'pass';
    ecLabel = 'Nil Encumbrance';
    ecDetail = 'No active mortgages, liens, or legal encumbrances found.';
  } else if (encumbrance_status === 'not_applicable') {
    ecScore = SIGNAL_WEIGHTS.encumbrance;
    ecState = 'not_applicable';
    ecLabel = 'Exempt / Not Applicable';
    ecDetail = 'Property classification does not require EC.';
  } else if (encumbrance_status === 'pending') {
    ecScore = SIGNAL_WEIGHTS.encumbrance * 0.5;
    ecState = 'pending';
    ecLabel = 'Search in Progress';
    ecDetail = 'Sub-registrar digital archive search underway.';
  } else if (encumbrance_status === 'encumbered') {
    ecScore = 0;
    ecState = 'fail';
    ecLabel = 'Active Encumbrance';
    ecDetail = 'Lien or mortgage registered against property.';
  }
  totalScore += ecScore;
  checks.push({
    id: 'encumbrance',
    title: 'Encumbrance Status',
    score: ecScore,
    maxScore: SIGNAL_WEIGHTS.encumbrance,
    state: ecState,
    label: ecLabel,
    detail: ecDetail,
  });

  // 3. Title Clarity (20%)
  let titleScore = 0;
  let titleState = 'missing';
  let titleLabel = 'Not Provided';
  let titleDetail = 'Chain of title deeds not provided.';

  if (title_clarity === 'clear') {
    titleScore = SIGNAL_WEIGHTS.title;
    titleState = 'pass';
    titleLabel = 'Marketable Title';
    titleDetail = 'Continuous chain of ownership verified without gaps.';
  } else if (title_clarity === 'pending') {
    titleScore = SIGNAL_WEIGHTS.title * 0.5;
    titleState = 'pending';
    titleLabel = 'Chain Under Review';
    titleDetail = 'Historical title deeds undergoing scrutiny.';
  } else if (title_clarity === 'disputed') {
    titleScore = 0;
    titleState = 'fail';
    titleLabel = 'Defect / Dispute Noted';
    titleDetail = 'Ownership chain defect or civil claim indicated.';
  }
  totalScore += titleScore;
  checks.push({
    id: 'title',
    title: 'Title Clarity',
    score: titleScore,
    maxScore: SIGNAL_WEIGHTS.title,
    state: titleState,
    label: titleLabel,
    detail: titleDetail,
  });

  // 4. Document Completeness Ratio (15%)
  let docScore = 0;
  let docState = 'missing';
  let docLabel = 'No Documents';
  let docDetail = '0% required documentation uploaded.';

  if (typeof document_completeness === 'number') {
    const clamped = Math.max(0, Math.min(1, document_completeness));
    docScore = Math.round(clamped * SIGNAL_WEIGHTS.documentCompleteness * 10) / 10;
    const pct = Math.round(clamped * 100);

    if (clamped >= 0.8) {
      docState = 'pass';
      docLabel = `${pct}% Complete`;
      docDetail = 'Essential core documents uploaded and intact.';
    } else if (clamped >= 0.4) {
      docState = 'pending';
      docLabel = `${pct}% Partial`;
      docDetail = 'Partial documents submitted; supplementary records pending.';
    } else {
      docState = 'fail';
      docLabel = `${pct}% Incomplete`;
      docDetail = 'Missing critical supporting records.';
    }
  }
  totalScore += docScore;
  checks.push({
    id: 'documentCompleteness',
    title: 'Document Completeness',
    score: docScore,
    maxScore: SIGNAL_WEIGHTS.documentCompleteness,
    state: docState,
    label: docLabel,
    detail: docDetail,
  });

  // 5. Owner/Seller Name Match (15%)
  let ownerScore = 0;
  let ownerState = 'missing';
  let ownerLabel = 'Not Provided';
  let ownerDetail = 'Seller identity records not provided.';

  if (owner_match === 'match') {
    ownerScore = SIGNAL_WEIGHTS.ownerMatch;
    ownerState = 'pass';
    ownerLabel = 'Records Match';
    ownerDetail = 'Seller name matches title deed and government tax records.';
  } else if (owner_match === 'pending') {
    ownerScore = SIGNAL_WEIGHTS.ownerMatch * 0.5;
    ownerState = 'pending';
    ownerLabel = 'Cross-Check Pending';
    ownerDetail = 'Matching against municipal property tax database.';
  } else if (owner_match === 'mismatch') {
    ownerScore = 0;
    ownerState = 'fail';
    ownerLabel = 'Name Discrepancy';
    ownerDetail = 'Listed seller name does not match recorded deed holder.';
  }
  totalScore += ownerScore;
  checks.push({
    id: 'ownerMatch',
    title: 'Seller Name Match',
    score: ownerScore,
    maxScore: SIGNAL_WEIGHTS.ownerMatch,
    state: ownerState,
    label: ownerLabel,
    detail: ownerDetail,
  });

  const finalScore = Math.round(totalScore);

  // 3-Tier Bucketing per requirements
  let tier = 'unverified';
  let tierLabel = 'Needs Verification';
  let badgeTone = 'slate'; // slate | amber | emerald

  if (finalScore >= 75) {
    tier = 'high';
    tierLabel = 'Checks Passed'; // avoids legal certainty
    badgeTone = 'emerald';
  } else if (finalScore >= 50) {
    tier = 'partial';
    tierLabel = 'Partial Checks';
    badgeTone = 'amber';
  } else {
    tier = 'unverified';
    tierLabel = 'Needs Verification';
    badgeTone = 'slate';
  }

  return {
    score: finalScore,
    tier,
    tierLabel,
    badgeTone,
    checks,
    disclaimer: 'Preliminary automated check. Does not constitute legal title guarantee.',
  };
}
