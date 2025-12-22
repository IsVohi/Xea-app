import React, { useState } from 'react';
import { api, EvidenceBundle, AttestResponse } from '../api';

interface EvidencePanelProps {
    jobId: string;
    bundle: EvidenceBundle;
    ipfsCid?: string;
}

export function EvidencePanel({ jobId, bundle, ipfsCid: initialCid }: EvidencePanelProps) {
    const [showJson, setShowJson] = useState(false);
    const [attestation, setAttestation] = useState<AttestResponse | null>(null);
    const [attesting, setAttesting] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [ipfsCid, setIpfsCid] = useState(initialCid);

    const handleAttest = async () => {
        setAttesting(true);
        setError(null);

        try {
            const response = await api.attest({ job_id: jobId, publish: true });
            setAttestation(response);
            setIpfsCid(response.ipfs_cid);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Attestation failed');
        } finally {
            setAttesting(false);
        }
    };

    const copyToClipboard = (text: string) => {
        navigator.clipboard.writeText(text);
    };

    return (
        <div className="card space-y-4">
            <h3 className="text-lg font-semibold">Evidence & Attestation</h3>

            {/* Buttons */}
            <div className="flex gap-3">
                <button
                    onClick={() => setShowJson(!showJson)}
                    className="btn-secondary"
                >
                    {showJson ? 'Hide' : 'View'} Evidence Bundle (JSON)
                </button>

                <button
                    onClick={handleAttest}
                    disabled={attesting || !!attestation}
                    className="btn-primary"
                >
                    {attesting ? 'Attesting...' : attestation ? '✓ Attested' : 'Attest Verification'}
                </button>
            </div>

            {error && (
                <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-red-400 text-sm">
                    {error}
                </div>
            )}

            {/* JSON Viewer */}
            {showJson && (
                <div className="bg-xea-bg rounded-lg p-4 border border-xea-border overflow-auto max-h-96">
                    <div className="flex justify-between items-center mb-2">
                        <span className="text-xs text-gray-400">Evidence Bundle</span>
                        <button
                            onClick={() => copyToClipboard(JSON.stringify(bundle, null, 2))}
                            className="text-xs text-xea-accent hover:text-xea-accent-hover"
                        >
                            Copy JSON
                        </button>
                    </div>
                    <pre className="text-xs text-gray-300 font-mono whitespace-pre-wrap">
                        {JSON.stringify(bundle, null, 2)}
                    </pre>
                </div>
            )}

            {/* Attestation Details */}
            {(ipfsCid || attestation) && (
                <div className="bg-xea-bg-secondary rounded-lg p-4 space-y-3">
                    {ipfsCid && (
                        <div className="flex items-center justify-between">
                            <span className="text-sm text-gray-400">IPFS CID</span>
                            <div className="flex items-center gap-2">
                                <code className="text-xs font-mono text-xea-accent">
                                    {ipfsCid.length > 40 ? `${ipfsCid.slice(0, 20)}...${ipfsCid.slice(-12)}` : ipfsCid}
                                </code>
                                <button
                                    onClick={() => copyToClipboard(ipfsCid)}
                                    className="text-gray-400 hover:text-white"
                                    title="Copy CID"
                                >
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                                    </svg>
                                </button>
                            </div>
                        </div>
                    )}

                    {attestation && (
                        <>
                            <div className="flex items-center justify-between">
                                <span className="text-sm text-gray-400">Signature</span>
                                <code className="text-xs font-mono text-gray-300">
                                    {attestation.signature.slice(0, 16)}...{attestation.signature.slice(-8)}
                                </code>
                            </div>

                            <div className="flex items-center justify-between">
                                <span className="text-sm text-gray-400">Signer</span>
                                <code className="text-xs font-mono text-gray-300">
                                    {attestation.signer}
                                </code>
                            </div>

                            <div className="flex items-center justify-between">
                                <span className="text-sm text-gray-400">Timestamp</span>
                                <span className="text-xs text-gray-300">
                                    {new Date(bundle.timestamp).toLocaleString()}
                                </span>
                            </div>
                        </>
                    )}
                </div>
            )}

            {/* Verification Instructions */}
            {attestation && (
                <details className="text-sm">
                    <summary className="text-gray-400 cursor-pointer hover:text-white">
                        Verification Instructions
                    </summary>
                    <ol className="mt-2 space-y-1 text-gray-300 list-decimal list-inside pl-2">
                        <li>{attestation.verification_instructions.step_1}</li>
                        <li>{attestation.verification_instructions.step_2}</li>
                        <li>{attestation.verification_instructions.step_3}</li>
                        <li>{attestation.verification_instructions.step_4}</li>
                    </ol>
                </details>
            )}
        </div>
    );
}

export default EvidencePanel;
