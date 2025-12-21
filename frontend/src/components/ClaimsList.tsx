import React, { useState } from 'react';
import { api, Claim } from '../api';

interface ClaimsListProps {
    claims: Claim[];
    proposalHash: string;
    onValidationStart: (jobId: string) => void;
}

export function ClaimsList({ claims, proposalHash, onValidationStart }: ClaimsListProps) {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleValidate = async () => {
        setLoading(true);
        setError(null);

        try {
            const result = await api.validate({ proposal_hash: proposalHash });
            onValidationStart(result.job_id);
        } catch (err: any) {
            setError(err.response?.data?.message || err.message || 'Failed to start validation');
        } finally {
            setLoading(false);
        }
    };

    const getTypeEmoji = (type: string): string => {
        const emojis: Record<string, string> = {
            factual: '📊',
            mathematical: '🔢',
            temporal: '⏰',
            comparative: '⚖️',
            procedural: '📋',
            conditional: '🔀',
        };
        return emojis[type] || '📝';
    };

    return (
        <div className="claims-list">
            <ul className="claims">
                {claims.map((claim) => (
                    <li key={claim.id} className="claim-item">
                        <div className="claim-header">
                            <span className="claim-id">{claim.id}</span>
                            <span className="claim-type">
                                {getTypeEmoji(claim.type)} {claim.type}
                            </span>
                        </div>
                        <p className="claim-text">{claim.text}</p>
                        <div className="claim-meta">
                            <span>Paragraph: {claim.paragraph_index}</span>
                            <span>Chars: {claim.char_range[0]}-{claim.char_range[1]}</span>
                        </div>
                    </li>
                ))}
            </ul>

            {error && <div className="error">{error}</div>}

            <button
                onClick={handleValidate}
                disabled={loading}
                className="validate-button"
            >
                {loading ? 'Starting Validation...' : `Validate ${claims.length} Claims`}
            </button>
        </div>
    );
}
