import React, { useEffect, useState } from 'react';
import { api, StatusResponse, EvidenceBundle } from '../api';

interface LiveDashboardProps {
    jobId: string;
}

export function LiveDashboard({ jobId }: LiveDashboardProps) {
    const [status, setStatus] = useState<StatusResponse | null>(null);
    const [bundle, setBundle] = useState<EvidenceBundle | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [polling, setPolling] = useState(true);

    useEffect(() => {
        if (!polling) return;

        const pollStatus = async () => {
            try {
                const result = await api.getStatus(jobId);
                setStatus(result);

                if (result.status === 'completed' || result.status === 'failed') {
                    setPolling(false);
                }
            } catch (err: any) {
                setError(err.message || 'Failed to fetch status');
                setPolling(false);
            }
        };

        pollStatus();
        const interval = setInterval(pollStatus, 2000);

        return () => clearInterval(interval);
    }, [jobId, polling]);

    const handleAggregate = async () => {
        try {
            const result = await api.aggregate(jobId);
            setBundle(result);
        } catch (err: any) {
            setError(err.message || 'Failed to aggregate results');
        }
    };

    const getStatusColor = (s: string): string => {
        const colors: Record<string, string> = {
            queued: '#ffa500',
            running: '#00bfff',
            completed: '#00ff00',
            failed: '#ff0000',
        };
        return colors[s] || '#888';
    };

    if (error) {
        return <div className="error">{error}</div>;
    }

    if (!status) {
        return <div className="loading">Loading job status...</div>;
    }

    return (
        <div className="live-dashboard">
            <div className="status-header">
                <span
                    className="status-badge"
                    style={{ backgroundColor: getStatusColor(status.status) }}
                >
                    {status.status.toUpperCase()}
                </span>
                <span className="job-id">Job: {jobId}</span>
            </div>

            <div className="progress-section">
                <h3>Progress</h3>
                <div className="progress-grid">
                    <div className="progress-item">
                        <span className="label">Claims Validated</span>
                        <span className="value">
                            {status.progress.claims_validated} / {status.progress.claims_total}
                        </span>
                    </div>
                    <div className="progress-item">
                        <span className="label">Miners Responded</span>
                        <span className="value">
                            {status.progress.miners_responded} / {status.progress.miners_contacted}
                        </span>
                    </div>
                </div>
                <div className="progress-bar">
                    <div
                        className="progress-fill"
                        style={{
                            width: `${(status.progress.claims_validated / status.progress.claims_total) * 100 || 0}%`,
                        }}
                    />
                </div>
            </div>

            {status.partial_results.length > 0 && (
                <div className="partial-results">
                    <h3>Partial Results ({status.partial_results.length})</h3>
                    <ul>
                        {status.partial_results.slice(0, 5).map((r, i) => (
                            <li key={i} className="result-item">
                                <span>{r.claim_id}</span>
                                <span className={`verdict verdict-${r.verdict}`}>{r.verdict}</span>
                                <span>Score: {r.scores.composite.toFixed(3)}</span>
                            </li>
                        ))}
                    </ul>
                </div>
            )}

            {status.ready_for_aggregation && !bundle && (
                <button onClick={handleAggregate} className="aggregate-button">
                    Aggregate Results
                </button>
            )}

            {bundle && (
                <div className="evidence-bundle">
                    <h3>Evidence Bundle</h3>
                    <div className="metrics">
                        <div className="metric">
                            <span className="label">PoI Agreement</span>
                            <span className="value">{(bundle.aggregated_metrics.poi_agreement * 100).toFixed(1)}%</span>
                        </div>
                        <div className="metric">
                            <span className="label">PoUW Score</span>
                            <span className="value">{(bundle.aggregated_metrics.pouw_score * 100).toFixed(1)}%</span>
                        </div>
                        <div className="metric">
                            <span className="label">Consensus</span>
                            <span className={`verdict verdict-${bundle.aggregated_metrics.consensus_verdict}`}>
                                {bundle.aggregated_metrics.consensus_verdict}
                            </span>
                        </div>
                    </div>
                    <div className="recommendation">
                        <h4>Recommendation</h4>
                        <p className={`action action-${bundle.recommendation.action}`}>
                            {bundle.recommendation.action.toUpperCase()}
                        </p>
                        <p>{bundle.recommendation.summary}</p>
                    </div>
                    {bundle.ipfs_cid && (
                        <p className="ipfs-link">
                            <strong>IPFS:</strong> {bundle.ipfs_cid}
                        </p>
                    )}
                </div>
            )}
        </div>
    );
}
