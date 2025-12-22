import React, { useState } from 'react';
import { Claim, ClaimCanonical } from '../api';

interface ClaimRowProps {
    claim: Claim;
    status: 'pending' | 'validating' | 'completed';
    minerCount?: number;
    totalMiners?: number;
}

export function ClaimRow({ claim, status, minerCount = 0, totalMiners = 5 }: ClaimRowProps) {
    const [expanded, setExpanded] = useState(false);

    const statusBadge = {
        pending: 'badge-pending',
        validating: 'badge-validating animate-pulse-subtle',
        completed: 'badge-supported',
    }[status];

    const statusLabel = {
        pending: 'Pending',
        validating: `Validating (${minerCount}/${totalMiners})`,
        completed: 'Completed',
    }[status];

    return (
        <div className="bg-xea-bg-secondary rounded-lg border border-xea-border overflow-hidden">
            <div
                className="p-4 cursor-pointer hover:bg-xea-border/30 transition-colors"
                onClick={() => setExpanded(!expanded)}
            >
                <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-3 mb-2">
                            <span className="text-xea-accent font-semibold text-sm">
                                {claim.id.toUpperCase()}
                            </span>
                            <span className="text-xs text-gray-500 px-2 py-0.5 bg-xea-bg rounded">
                                {claim.type}
                            </span>
                        </div>
                        <p className="text-gray-200 line-clamp-2">{claim.text}</p>
                    </div>

                    <div className="flex items-center gap-3">
                        <span className={`badge ${statusBadge}`}>
                            {statusLabel}
                        </span>
                        <svg
                            className={`w-5 h-5 text-gray-400 transition-transform ${expanded ? 'rotate-180' : ''}`}
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                        >
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                        </svg>
                    </div>
                </div>
            </div>

            {expanded && (
                <div className="px-4 pb-4 border-t border-xea-border/50 pt-3">
                    <div className="grid grid-cols-3 gap-4 text-sm">
                        <div>
                            <p className="text-gray-500 mb-1">Paragraph</p>
                            <p className="text-gray-300">#{claim.paragraph_index + 1}</p>
                        </div>
                        <div>
                            <p className="text-gray-500 mb-1">Character Range</p>
                            <p className="text-gray-300">{claim.char_range[0]}–{claim.char_range[1]}</p>
                        </div>
                        <div>
                            <p className="text-gray-500 mb-1">Type</p>
                            <p className="text-gray-300 capitalize">{claim.type}</p>
                        </div>
                    </div>

                    {claim.canonical && (
                        <div className="mt-3 pt-3 border-t border-xea-border/30">
                            <p className="text-gray-500 text-sm mb-2">Canonicalized Data</p>
                            <div className="flex flex-wrap gap-2">
                                {claim.canonical.numbers?.length > 0 && (
                                    <span className="text-xs px-2 py-1 bg-blue-500/20 text-blue-300 rounded">
                                        Numbers: {claim.canonical.numbers.join(', ')}
                                    </span>
                                )}
                                {claim.canonical.addresses?.length > 0 && claim.canonical.addresses.map((addr, i) => (
                                    <span key={i} className="text-xs px-2 py-1 bg-purple-500/20 text-purple-300 rounded font-mono">
                                        {addr.slice(0, 6)}...{addr.slice(-4)}
                                    </span>
                                ))}
                                {claim.canonical.urls?.length > 0 && (
                                    <span className="text-xs px-2 py-1 bg-green-500/20 text-green-300 rounded">
                                        URLs: {claim.canonical.urls.length}
                                    </span>
                                )}
                                {(!claim.canonical.numbers?.length && !claim.canonical.addresses?.length && !claim.canonical.urls?.length) && (
                                    <span className="text-xs text-gray-500">No special values extracted</span>
                                )}
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

export default ClaimRow;
