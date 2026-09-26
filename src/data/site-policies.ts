// src/data/site-policies.ts
// Shared values for the Privacy, Terms of Use, and Accessibility pages.
// Change them here and every policy page updates.

export const POLICY = {
  /** Public contact address for privacy, removal, and accessibility requests. CONFIRM BEFORE DEPLOY. */
  contactEmail:    'editor@gunnsinamerica.org',
  /** Publisher of the website and holder of its copyright. */
  publisher:       'WriteNow.Media',
  copyrightHolder: 'WriteNow.Media',
  /** Imprint that publishes the book (an imprint of the publisher above). */
  bookImprint:     'Wepawaug Press',
  maintainer:      'John Paul Lumpp',
  governingLaw:    'the State of Connecticut',
  /** Effective / last-reviewed dates, shown at the top of each page. */
  privacyEffective:       'September 25, 2026',
  termsEffective:         'September 25, 2026',
  accessibilityReviewed:  'September 25, 2026',
};

export const POLICY_PAGES = [
  { href: '/privacy',       label: 'Privacy Policy' },
  { href: '/terms',         label: 'Terms of Use' },
  { href: '/accessibility', label: 'Accessibility' },
];
