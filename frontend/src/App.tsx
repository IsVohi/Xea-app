import React, { useState } from 'react';
import { IngestForm } from './components/IngestForm';
import { ClaimsList } from './components/ClaimsList';
import { LiveDashboard } from './components/LiveDashboard';

interface Claim {
    id: string;
    text: string;
    paragraph_index: number;
    char_range: [number, number];
    type: string;
    canonical: string;
}

interface IngestResult {
    proposal_hash: string;
    canonical_text: string;
    claims: Claim[];
}

function App() {
    const [ingestResult, setIngestResult] = useState<IngestResult | null>(null);
    const [activeJobId, setActiveJobId] = useState<string | null>(null);

    const handleIngestComplete = (result: IngestResult) => {
        setIngestResult(result);
    };

    const handleValidationStart = (jobId: string) => {
        setActiveJobId(jobId);
    };

    return (
        <div className="app">
            <header className="app-header">
                <h1>🔮 Xea Governance Oracle</h1>
                <p>Verifiable governance intelligence powered by decentralized inference</p>
            </header>

            <main className="app-main">
                <section className="section">
                    <h2>📥 Ingest Proposal</h2>
                    <IngestForm onIngestComplete={handleIngestComplete} />
                </section>

                {ingestResult && (
                    <section className="section">
                        <h2>📋 Extracted Claims ({ingestResult.claims.length})</h2>
                        <p className="hash">
                            <strong>Proposal Hash:</strong> {ingestResult.proposal_hash}
                        </p>
                        <ClaimsList
                            claims={ingestResult.claims}
                            proposalHash={ingestResult.proposal_hash}
                            onValidationStart={handleValidationStart}
                        />
                    </section>
                )}

                {activeJobId && (
                    <section className="section">
                        <h2>📊 Live Validation Dashboard</h2>
                        <LiveDashboard jobId={activeJobId} />
                    </section>
                )}
            </main>

            <footer className="app-footer">
                <p>Xea Governance Oracle v0.1.0 | MIT License</p>
            </footer>
        </div>
    );
}

export default App;
