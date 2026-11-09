export function Icon({ kind }: { kind: 'supported' | 'contradicted' | 'insufficient_evidence' }) {
  return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><circle cx="12" cy="12" r="9"/>{kind === 'supported' ? <path d="m7.5 12 3 3 6-6"/> : kind === 'contradicted' ? <path d="m9 9 6 6m0-6-6 6"/> : <path d="M12 7v6m0 3v1"/>}</svg>;
}
