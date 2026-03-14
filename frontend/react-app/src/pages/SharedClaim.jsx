import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { WhatsappShareButton, TwitterShareButton, WhatsappIcon, TwitterIcon } from 'react-share';
import toast from 'react-hot-toast';
import { getSharedClaim } from '../services/api';

export default function SharedClaim() {
  const { token } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getSharedClaim(token)
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [token]);

  const pageUrl = window.location.href;

  if (loading) return <main style={{ maxWidth: 900, margin: '0 auto', padding: '2rem 1rem' }}><div className="skeleton" style={{ height: 220 }} /></main>;
  if (!data) return <main style={{ maxWidth: 900, margin: '0 auto', padding: '2rem 1rem' }}><p>Invalid or expired shared claim link.</p></main>;

  return (
    <main style={{ maxWidth: 900, margin: '0 auto', padding: '2rem 1rem 4rem' }}>
      <section className="glass" style={{ padding: '1.2rem' }}>
        <h1 style={{ marginBottom: 10 }}>Shared Claim Verdict</h1>
        <p style={{ fontWeight: 600, marginBottom: 10 }}>{data.claim}</p>
        <p style={{ marginBottom: 8 }}>Verdict: <strong>{data.verdict}</strong></p>
        <p style={{ marginBottom: 8 }}>Confidence: <strong>{Math.round(data.confidence || 0)}%</strong></p>
        <p style={{ opacity: 0.8 }}>{data.transcript?.reasoning || 'No detailed reasoning available.'}</p>

        <div style={{ marginTop: 14, display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
          <TwitterShareButton url={pageUrl} title={`VeritasAI Verdict: ${data.verdict}`}><TwitterIcon size={36} round /></TwitterShareButton>
          <WhatsappShareButton url={pageUrl} title={`VeritasAI Verdict: ${data.verdict}`}><WhatsappIcon size={36} round /></WhatsappShareButton>
          <button
            onClick={async () => {
              await navigator.clipboard.writeText(pageUrl);
              toast.success('Link copied');
            }}
            style={{ border: '1px solid var(--border-dark)', borderRadius: 10, padding: '8px 12px', background: 'transparent', color: 'inherit', cursor: 'pointer' }}
          >
            🔗 Copy Link
          </button>
        </div>

        <Link to="/" style={{ display: 'inline-block', marginTop: 16, color: '#818cf8' }}>Verify your own claim →</Link>
      </section>
    </main>
  );
}
