import { useState, useEffect } from 'react';
import {
    Settings as SettingsIcon, Key, Globe, CheckCircle,
    AlertCircle, Eye, EyeOff, RefreshCw, Shield, Zap
} from 'lucide-react';
import { getSettings, saveAWSCredentials, switchToMock } from '../services/settingsService';

const REGIONS = [
    'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2',
    'eu-west-1', 'eu-west-2', 'eu-central-1',
    'ap-south-1', 'ap-southeast-1', 'ap-southeast-2', 'ap-northeast-1',
    'ca-central-1', 'sa-east-1',
];

export default function Settings() {
    const [current, setCurrent] = useState(null);
    const [form, setForm] = useState({
        aws_access_key_id: '',
        aws_secret_access_key: '',
        aws_region: 'us-east-1',
        scan_regions: ['us-east-1'],
    });
    const [showSecret, setShowSecret] = useState(false);
    const [loading, setLoading] = useState(false);
    const [toast, setToast] = useState(null); // {type: 'success'|'error', message}

    useEffect(() => {
        getSettings().then(setCurrent).catch(() => { });
    }, []);

    const showToast = (type, message) => {
        setToast({ type, message });
        setTimeout(() => setToast(null), 5000);
    };

    const handleRegionToggle = (region) => {
        setForm(f => {
            const has = f.scan_regions.includes(region);
            if (has && f.scan_regions.length === 1) return f; // keep at least 1
            return {
                ...f,
                scan_regions: has
                    ? f.scan_regions.filter(r => r !== region)
                    : [...f.scan_regions, region],
            };
        });
    };

    const handleSave = async (e) => {
        e.preventDefault();
        if (!form.aws_access_key_id || !form.aws_secret_access_key) {
            showToast('error', 'Access Key and Secret Key are required.');
            return;
        }
        setLoading(true);
        try {
            const result = await saveAWSCredentials(form);
            setCurrent({
                mock_aws: false,
                aws_region: form.aws_region,
                scan_regions: form.scan_regions,
                aws_access_key_id_hint: result.key_hint,
                connected: true,
            });
            showToast('success', `✅ ${result.message}`);
            setForm(f => ({ ...f, aws_access_key_id: '', aws_secret_access_key: '' }));
        } catch (err) {
            const detail = err.response?.data?.detail || 'Failed to connect to AWS. Check your credentials.';
            showToast('error', `❌ ${detail}`);
        } finally {
            setLoading(false);
        }
    };

    const handleMock = async () => {
        setLoading(true);
        try {
            await switchToMock();
            setCurrent(c => ({ ...c, mock_aws: true, connected: false, aws_access_key_id_hint: null }));
            showToast('success', 'Switched to Mock Mode — no AWS credentials needed');
        } catch {
            showToast('error', 'Failed to switch mode');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="page-content">
            {/* Toast */}
            {toast && (
                <div style={{
                    position: 'fixed', top: '1.5rem', right: '1.5rem', zIndex: 9999,
                    padding: '1rem 1.5rem', borderRadius: '0.75rem', maxWidth: '36rem',
                    background: toast.type === 'success' ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)',
                    border: `1px solid ${toast.type === 'success' ? '#10b981' : '#ef4444'}`,
                    color: toast.type === 'success' ? '#6ee7b7' : '#fca5a5',
                    backdropFilter: 'blur(8px)', fontSize: '0.9rem',
                }}>
                    {toast.message}
                </div>
            )}

            {/* Header */}
            <div className="page-header">
                <div>
                    <h1 className="page-title">
                        <SettingsIcon size={28} style={{ marginRight: '0.75rem', color: 'var(--accent)' }} />
                        Settings
                    </h1>
                    <p className="page-subtitle">Configure your AWS account to start scanning real resources</p>
                </div>
            </div>

            {/* Current Status Card */}
            {current && (
                <div className="card" style={{ marginBottom: '1.5rem', padding: '1.25rem 1.5rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            {current.connected
                                ? <CheckCircle size={20} color="#10b981" />
                                : <Zap size={20} color="#f59e0b" />}
                            <span style={{ fontWeight: 600, color: current.connected ? '#10b981' : '#f59e0b' }}>
                                {current.mock_aws ? 'Mock Mode (Demo Data)' : 'Connected to AWS'}
                            </span>
                        </div>
                        {current.aws_access_key_id_hint && (
                            <span style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                                Key: <code style={{ background: 'rgba(255,255,255,0.05)', padding: '0.15rem 0.4rem', borderRadius: '0.25rem' }}>
                                    {current.aws_access_key_id_hint}
                                </code>
                            </span>
                        )}
                        {current.aws_region && !current.mock_aws && (
                            <span className="badge badge-info">{current.aws_region}</span>
                        )}
                        {!current.mock_aws && (
                            <button className="btn btn-sm" onClick={handleMock} disabled={loading}
                                style={{ marginLeft: 'auto', background: 'rgba(245,158,11,0.1)', color: '#f59e0b', border: '1px solid rgba(245,158,11,0.3)' }}>
                                Switch to Mock Mode
                            </button>
                        )}
                    </div>
                </div>
            )}

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>

                {/* Credentials Form */}
                <div className="card">
                    <div className="card-header">
                        <h2 className="card-title">
                            <Key size={18} style={{ marginRight: '0.5rem' }} />
                            AWS Credentials
                        </h2>
                    </div>

                    <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                        <div>
                            <label className="form-label">Access Key ID</label>
                            <input
                                className="form-input"
                                type="text"
                                placeholder="AKIAXXXXXXXXXXXXXXXX"
                                value={form.aws_access_key_id}
                                onChange={e => setForm(f => ({ ...f, aws_access_key_id: e.target.value }))}
                                autoComplete="off"
                                spellCheck={false}
                            />
                        </div>

                        <div>
                            <label className="form-label">Secret Access Key</label>
                            <div style={{ position: 'relative' }}>
                                <input
                                    className="form-input"
                                    type={showSecret ? 'text' : 'password'}
                                    placeholder="Your secret access key"
                                    value={form.aws_secret_access_key}
                                    onChange={e => setForm(f => ({ ...f, aws_secret_access_key: e.target.value }))}
                                    autoComplete="new-password"
                                    spellCheck={false}
                                    style={{ paddingRight: '3rem' }}
                                />
                                <button type="button" onClick={() => setShowSecret(s => !s)}
                                    style={{ position: 'absolute', right: '0.75rem', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>
                                    {showSecret ? <EyeOff size={16} /> : <Eye size={16} />}
                                </button>
                            </div>
                        </div>

                        <div>
                            <label className="form-label">Default Region</label>
                            <select className="form-input" value={form.aws_region}
                                onChange={e => setForm(f => ({ ...f, aws_region: e.target.value }))}>
                                {REGIONS.map(r => <option key={r} value={r}>{r}</option>)}
                            </select>
                        </div>

                        <button type="submit" className="btn btn-primary" disabled={loading}
                            style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}>
                            {loading
                                ? <><RefreshCw size={16} className="spin" /> Validating…</>
                                : <><CheckCircle size={16} /> Connect & Validate</>}
                        </button>
                    </form>

                    <div style={{ marginTop: '1rem', padding: '0.75rem', background: 'rgba(99,102,241,0.08)', borderRadius: '0.5rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                        <Shield size={14} style={{ marginRight: '0.4rem', verticalAlign: 'middle' }} />
                        Credentials are validated via <code>sts:GetCallerIdentity</code>, held in memory only, and never stored on disk or sent anywhere else.
                    </div>
                </div>

                {/* Regions Selector */}
                <div className="card">
                    <div className="card-header">
                        <h2 className="card-title">
                            <Globe size={18} style={{ marginRight: '0.5rem' }} />
                            Regions to Scan
                        </h2>
                        <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                            {form.scan_regions.length} selected
                        </span>
                    </div>

                    <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
                        Select the AWS regions where your resources live. Only selected regions will be scanned.
                    </p>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
                        {REGIONS.map(region => {
                            const active = form.scan_regions.includes(region);
                            return (
                                <button key={region} type="button" onClick={() => handleRegionToggle(region)}
                                    style={{
                                        padding: '0.5rem 0.75rem', borderRadius: '0.5rem', fontSize: '0.8rem',
                                        cursor: 'pointer', textAlign: 'left', transition: 'all 0.15s',
                                        background: active ? 'rgba(99,102,241,0.18)' : 'rgba(255,255,255,0.04)',
                                        border: `1px solid ${active ? 'rgba(99,102,241,0.6)' : 'rgba(255,255,255,0.08)'}`,
                                        color: active ? '#a5b4fc' : 'var(--text-muted)',
                                        fontWeight: active ? 600 : 400,
                                    }}>
                                    {active && <CheckCircle size={12} style={{ marginRight: '0.35rem', verticalAlign: 'middle' }} />}
                                    {region}
                                </button>
                            );
                        })}
                    </div>

                    <div style={{ marginTop: '1.25rem', padding: '0.75rem', background: 'rgba(16,185,129,0.06)', borderRadius: '0.5rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                        💡 Tip: Only select regions you actually use to speed up scans.
                    </div>
                </div>
            </div>

            {/* How-to guide */}
            <div className="card" style={{ marginTop: '1.5rem' }}>
                <div className="card-header">
                    <h2 className="card-title">How to Get Your AWS Keys</h2>
                </div>
                <ol style={{ color: 'var(--text-muted)', fontSize: '0.9rem', lineHeight: 2, paddingLeft: '1.25rem' }}>
                    <li>Log in to <strong style={{ color: 'var(--text)' }}>AWS Console → IAM → Users → your user</strong></li>
                    <li>Click the <strong style={{ color: 'var(--text)' }}>Security credentials</strong> tab</li>
                    <li>Click <strong style={{ color: 'var(--text)' }}>Create access key</strong> → select "Application running outside AWS"</li>
                    <li>Copy the <strong style={{ color: 'var(--text)' }}>Access Key ID</strong> and <strong style={{ color: 'var(--text)' }}>Secret Access Key</strong></li>
                    <li>Paste them above and click <strong style={{ color: 'var(--accent)' }}>Connect & Validate</strong></li>
                </ol>
                <div style={{ marginTop: '0.75rem', padding: '0.75rem', background: 'rgba(239,68,68,0.06)', borderRadius: '0.5rem', fontSize: '0.8rem', color: '#fca5a5' }}>
                    ⚠️ Make sure the IAM user has the <strong>CloudAuditScannerPolicy</strong> attached (from <code>infra/iam-policy.json</code>). This gives read-only access only.
                </div>
            </div>
        </div>
    );
}
