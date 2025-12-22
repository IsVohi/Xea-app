import React, { useState } from 'react';
import { api, Claim, IngestResponse } from '../api';

interface ProposalInputProps {
    onIngestComplete: (result: IngestResponse, autoValidate: boolean) => void;
}

export function ProposalInput({ onIngestComplete }: ProposalInputProps) {
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!input.trim()) return;

        setLoading(true);
        setError(null);

        try {
            // Detect if input is URL or text
            const isUrl = input.trim().startsWith('http');
            const request = isUrl ? { url: input.trim() } : { text: input.trim() };

            const result = await api.ingest(request);
            onIngestComplete(result, true); // Auto-start validation
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to ingest proposal');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="card">
            <form onSubmit={handleSubmit} className="space-y-4">
                <textarea
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Paste DAO proposal text OR Snapshot/Forum URL..."
                    className="input-field min-h-[160px] resize-y"
                    disabled={loading}
                />

                <div className="flex items-center justify-between">
                    <p className="text-sm text-gray-400">
                        Supports: Snapshot, Tally, Commonwealth, or raw proposal text
                    </p>

                    <button
                        type="submit"
                        disabled={loading || !input.trim()}
                        className="btn-primary flex items-center gap-2"
                    >
                        {loading ? (
                            <>
                                <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                                </svg>
                                Processing...
                            </>
                        ) : (
                            <>
                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                </svg>
                                Verify Proposal with Xea
                            </>
                        )}
                    </button>
                </div>

                {error && (
                    <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-red-400">
                        {error}
                    </div>
                )}
            </form>
        </div>
    );
}

export default ProposalInput;
