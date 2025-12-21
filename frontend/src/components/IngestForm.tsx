import React, { useState } from 'react';
import { api, IngestResponse } from '../api';

interface IngestFormProps {
    onIngestComplete: (result: IngestResponse) => void;
}

export function IngestForm({ onIngestComplete }: IngestFormProps) {
    const [inputType, setInputType] = useState<'url' | 'text'>('url');
    const [url, setUrl] = useState('');
    const [text, setText] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError(null);

        try {
            const request = inputType === 'url' ? { url } : { text };
            const result = await api.ingest(request);
            onIngestComplete(result);
        } catch (err: any) {
            setError(err.response?.data?.message || err.message || 'Failed to ingest proposal');
        } finally {
            setLoading(false);
        }
    };

    return (
        <form className="ingest-form" onSubmit={handleSubmit}>
            <div className="input-type-selector">
                <label>
                    <input
                        type="radio"
                        value="url"
                        checked={inputType === 'url'}
                        onChange={() => setInputType('url')}
                    />
                    URL
                </label>
                <label>
                    <input
                        type="radio"
                        value="text"
                        checked={inputType === 'text'}
                        onChange={() => setInputType('text')}
                    />
                    Text
                </label>
            </div>

            {inputType === 'url' ? (
                <input
                    type="url"
                    placeholder="https://snapshot.org/#/example.eth/proposal/..."
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    className="input-field"
                />
            ) : (
                <textarea
                    placeholder="Paste proposal text here..."
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                    className="input-field textarea"
                    rows={10}
                />
            )}

            {error && <div className="error">{error}</div>}

            <button type="submit" disabled={loading} className="submit-button">
                {loading ? 'Ingesting...' : 'Ingest Proposal'}
            </button>
        </form>
    );
}
