import React, { useState, useEffect } from 'react';
import { api, Claim, IngestResponse, EvidenceBundle, MinerResponse, JobProgress } from './api';
import { useJobStream } from './hooks/useJobStream';
import { ProposalInput } from './components/ProposalInput';
import { ClaimsTable } from './components/ClaimsTable';
import { LiveMinerPanel } from './components/LiveMinerPanel';
import { AggregationSummary } from './components/AggregationSummary';
import { EvidencePanel } from './components/EvidencePanel';

type AppStage = 'input' | 'validating' | 'aggregating' | 'complete';

function App() {
    const [stage, setStage] = useState<AppStage>('input');
    const [proposal, setProposal] = useState<IngestResponse | null>(null);
    const [jobId, setJobId] = useState<string | null>(null);
    const [evidenceBundle, setEvidenceBundle] = useState<EvidenceBundle | null>(null);
    const [ipfsCid, setIpfsCid] = useState<string | undefined>();
    const [error, setError] = useState<string | null>(null);

    // WebSocket for live updates
    const stream = useJobStream(stage === 'validating' ? jobId : null);

    // Polling fallback for status (WebSocket may not always be available)
    const [polledProgress, setPolledProgress] = useState<JobProgress | null>(null);
    const [polledResponses, setPolledResponses] = useState<MinerResponse[]>([]);

    const minerResponses = stream.connected ? stream.minerResponses :
        new Map<string, MinerResponse[]>(
            Object.entries(
                polledResponses.reduce((acc, r) => {
                    if (!acc[r.claim_id]) acc[r.claim_id] = [];
                    acc[r.claim_id].push(r);
                    return acc;
                }, {} as Record<string, MinerResponse[]>)
            )
        );

    const progress = stream.connected ? stream.progress : polledProgress || {
        claims_total: proposal?.claims.length || 0,
        claims_validated: 0,
        miners_contacted: 0,
        miners_responded: 0,
    };

    // Poll for status when not connected via WebSocket
    useEffect(() => {
        if (stage !== 'validating' || !jobId || stream.connected) return;

        const poll = async () => {
            try {
                const status = await api.getStatus(jobId);
                setPolledProgress(status.progress);
                setPolledResponses(status.partial_results);

                if (status.status === 'completed') {
                    handleValidationComplete();
                }
            } catch (err) {
                console.error('Polling error:', err);
            }
        };

        const interval = setInterval(poll, 2000);
        poll(); // Initial poll

        return () => clearInterval(interval);
    }, [stage, jobId, stream.connected]);

    // Handle WebSocket-based completion
    useEffect(() => {
        if (stream.status === 'completed' && stage === 'validating') {
            handleValidationComplete();
        }
    }, [stream.status]);

    const handleIngestComplete = async (result: IngestResponse, autoValidate: boolean) => {
        setProposal(result);
        setError(null);

        if (autoValidate) {
            try {
                const validateResponse = await api.validate({ proposal_hash: result.proposal_hash });
                setJobId(validateResponse.job_id);
                setStage('validating');
            } catch (err: any) {
                setError(err.response?.data?.detail || 'Failed to start validation');
            }
        }
    };

    const handleValidationComplete = async () => {
        if (!jobId) return;

        setStage('aggregating');

        try {
            const aggregateResponse = await api.aggregate({ job_id: jobId, publish: true });
            setEvidenceBundle(aggregateResponse.evidence_bundle);
            setIpfsCid(aggregateResponse.ipfs_cid);
            setStage('complete');
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to aggregate results');
            setStage('validating');
        }
    };

    const getClaimStatuses = (): Map<string, 'pending' | 'validating' | 'completed'> => {
        const statuses = new Map<string, 'pending' | 'validating' | 'completed'>();
        if (!proposal) return statuses;

        proposal.claims.forEach(claim => {
            const responses = minerResponses.get(claim.id) || [];
            if (stage === 'complete' || (evidenceBundle && evidenceBundle.claims.find(c => c.id === claim.id))) {
                statuses.set(claim.id, 'completed');
            } else if (responses.length > 0) {
                statuses.set(claim.id, 'validating');
            } else {
                statuses.set(claim.id, 'pending');
            }
        });

        return statuses;
    };

    const handleReset = () => {
        setStage('input');
        setProposal(null);
        setJobId(null);
        setEvidenceBundle(null);
        setIpfsCid(undefined);
        setError(null);
        setPolledProgress(null);
        setPolledResponses([]);
    };

    return (
        <div className="min-h-screen bg-xea-bg">
            {/* Header */}
            <header className="gradient-bg border-b border-xea-border">
                <div className="max-w-5xl mx-auto px-6 py-8 text-center">
                    <h1 className="text-4xl font-bold gradient-text mb-2">Xea</h1>
                    <p className="text-gray-400">
                        Verifiable governance intelligence powered by decentralized inference
                    </p>
                </div>
            </header>

            {/* Main Content */}
            <main className="max-w-5xl mx-auto px-6 py-8 space-y-6">
                {/* Stage Indicator */}
                {stage !== 'input' && (
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                            <Step number={1} label="Ingest" active={false} complete={true} />
                            <Connector complete={stage !== 'input'} />
                            <Step
                                number={2}
                                label="Validate"
                                active={stage === 'validating'}
                                complete={stage === 'aggregating' || stage === 'complete'}
                            />
                            <Connector complete={stage === 'aggregating' || stage === 'complete'} />
                            <Step
                                number={3}
                                label="Results"
                                active={stage === 'aggregating' || stage === 'complete'}
                                complete={stage === 'complete'}
                            />
                        </div>
                        <button onClick={handleReset} className="text-sm text-gray-400 hover:text-white">
                            Start Over
                        </button>
                    </div>
                )}

                {/* Error Display */}
                {error && (
                    <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-400">
                        {error}
                    </div>
                )}

                {/* Proposal Input (Stage 1) */}
                {stage === 'input' && (
                    <section>
                        <h2 className="text-xl font-semibold mb-4">📥 Verify a DAO Proposal</h2>
                        <ProposalInput onIngestComplete={handleIngestComplete} />
                    </section>
                )}

                {/* Claims Table (shown after ingest) */}
                {proposal && stage !== 'input' && (
                    <section>
                        <div className="flex items-center justify-between mb-4">
                            <h2 className="text-xl font-semibold">📋 Extracted Claims</h2>
                            <span className="text-sm text-gray-400 font-mono">
                                {proposal.proposal_hash.replace('sha256:', '').slice(0, 16)}...
                            </span>
                        </div>
                        <ClaimsTable
                            claims={proposal.claims}
                            claimStatuses={getClaimStatuses()}
                            minerResponses={minerResponses}
                            totalMiners={5}
                        />
                    </section>
                )}

                {/* Live Validation Panel (Stage 2) */}
                {stage === 'validating' && proposal && (
                    <section>
                        <h2 className="text-xl font-semibold mb-4">⚡ Live Validation</h2>
                        <LiveMinerPanel
                            claims={proposal.claims}
                            progress={progress}
                            minerResponses={minerResponses}
                            status={stream.connected ? stream.status : 'running'}
                            connected={stream.connected}
                        />
                    </section>
                )}

                {/* Loading state during aggregation */}
                {stage === 'aggregating' && (
                    <div className="card text-center py-12">
                        <svg className="animate-spin h-10 w-10 mx-auto text-xea-accent mb-4" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                        </svg>
                        <p className="text-gray-400">Aggregating miner responses...</p>
                    </div>
                )}

                {/* Aggregation Summary (Stage 3) */}
                {stage === 'complete' && evidenceBundle && (
                    <>
                        <section>
                            <h2 className="text-xl font-semibold mb-4">📊 Verification Results</h2>
                            <AggregationSummary bundle={evidenceBundle} />
                        </section>

                        <section>
                            <h2 className="text-xl font-semibold mb-4">🔐 Evidence & Attestation</h2>
                            <EvidencePanel
                                jobId={jobId!}
                                bundle={evidenceBundle}
                                ipfsCid={ipfsCid}
                            />
                        </section>
                    </>
                )}
            </main>

            {/* Footer */}
            <footer className="border-t border-xea-border mt-12">
                <div className="max-w-5xl mx-auto px-6 py-6 text-center text-sm text-gray-500">
                    Xea Governance Oracle v0.1.0 • Powered by decentralized inference
                </div>
            </footer>
        </div>
    );
}

// Helper components for stage indicator
function Step({ number, label, active, complete }: { number: number; label: string; active: boolean; complete: boolean }) {
    return (
        <div className="flex items-center gap-2">
            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold ${complete ? 'bg-verdict-supported text-black' :
                    active ? 'bg-xea-accent text-white' :
                        'bg-xea-bg-secondary text-gray-400 border border-xea-border'
                }`}>
                {complete ? '✓' : number}
            </div>
            <span className={`text-sm ${active || complete ? 'text-white' : 'text-gray-500'}`}>
                {label}
            </span>
        </div>
    );
}

function Connector({ complete }: { complete: boolean }) {
    return (
        <div className={`w-8 h-0.5 ${complete ? 'bg-verdict-supported' : 'bg-xea-border'}`} />
    );
}

export default App;
