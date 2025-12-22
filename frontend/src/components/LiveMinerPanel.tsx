import React from 'react';
import { Claim, MinerResponse, JobProgress } from '../api';

interface LiveMinerPanelProps {
    claims: Claim[];
    progress: JobProgress;
    minerResponses: Map<string, MinerResponse[]>;
    status: 'queued' | 'running' | 'completed' | 'failed';
    connected: boolean;
}

export function LiveMinerPanel({ claims, progress, minerResponses, status, connected }: LiveMinerPanelProps) {
    const progressPercent = progress.miners_contacted > 0
        ? (progress.miners_responded / progress.miners_contacted) * 100
        : 0;

    const getVerdictColor = (verdict: string) => {
        switch (verdict) {
            case 'verified': return 'bg-verdict-supported text-black';
            case 'refuted': return 'bg-verdict-disputed text-white';
            case 'partial': return 'bg-verdict-caution text-black';
            default: return 'bg-gray-600 text-white';
        }
    };

    return (
        <div className="card">
            <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold flex items-center gap-2">
                    Live Validation
                    {status === 'running' && (
                        <span className="flex items-center gap-1.5">
                            <span className="relative flex h-3 w-3">
                                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-xea-accent opacity-75"></span>
                                <span className="relative inline-flex rounded-full h-3 w-3 bg-xea-accent"></span>
                            </span>
                            <span className="text-sm text-xea-accent font-normal">In Progress</span>
                        </span>
                    )}
                    {status === 'completed' && (
                        <span className="badge badge-supported">Complete</span>
                    )}
                </h3>
                <div className="flex items-center gap-2 text-sm">
                    <span className={`w-2 h-2 rounded-full ${connected ? 'bg-verdict-supported' : 'bg-verdict-disputed'}`} />
                    <span className="text-gray-400">{connected ? 'Connected' : 'Disconnected'}</span>
                </div>
            </div>

            {/* Overall Progress */}
            <div className="mb-6">
                <div className="flex justify-between text-sm text-gray-400 mb-2">
                    <span>Miner Responses</span>
                    <span>{progress.miners_responded} / {progress.miners_contacted}</span>
                </div>
                <div className="progress-bar">
                    <div
                        className="progress-fill"
                        style={{ width: `${progressPercent}%` }}
                    />
                </div>
            </div>

            {/* Per-Claim Progress */}
            <div className="space-y-4">
                {claims.map((claim) => {
                    const responses = minerResponses.get(claim.id) || [];
                    const claimProgress = (responses.length / 5) * 100; // Assuming 5 miners per claim

                    return (
                        <div key={claim.id} className="bg-xea-bg-secondary rounded-lg p-4">
                            <div className="flex items-center justify-between mb-2">
                                <span className="text-xea-accent font-semibold text-sm">
                                    {claim.id.toUpperCase()}
                                </span>
                                <span className="text-xs text-gray-400">
                                    {responses.length}/5 miners
                                </span>
                            </div>

                            <p className="text-sm text-gray-300 mb-3 line-clamp-1">{claim.text}</p>

                            {/* Progress bar for this claim */}
                            <div className="progress-bar mb-3">
                                <div
                                    className="progress-fill"
                                    style={{ width: `${claimProgress}%` }}
                                />
                            </div>

                            {/* Miner verdict badges */}
                            <div className="flex flex-wrap gap-2">
                                {responses.map((resp, idx) => (
                                    <span
                                        key={idx}
                                        className={`badge ${getVerdictColor(resp.verdict)}`}
                                        title={resp.miner_id}
                                    >
                                        {resp.miner_id.replace('mock_miner_', 'M')}:{' '}
                                        {resp.verdict === 'verified' ? '✓' : resp.verdict === 'refuted' ? '✗' : '?'}
                                    </span>
                                ))}
                                {responses.length === 0 && (
                                    <span className="text-xs text-gray-500">Waiting for responses...</span>
                                )}
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

export default LiveMinerPanel;
