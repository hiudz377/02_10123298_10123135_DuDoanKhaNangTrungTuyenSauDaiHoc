import { useRef, useState } from 'react';
import {
    AlertCircle,
    ArrowRight,
    CheckCircle2,
    GraduationCap,
    LoaderCircle,
    RotateCcw,
    Sparkles,
} from 'lucide-react';
import { requestPrediction } from './api.js';
import { FEATURE_DEFINITIONS, validateFeatures } from './validation.js';

const emptyFeatures = Object.fromEntries(FEATURE_DEFINITIONS.map(({ key }) => [key, '']));
const numericFields = FEATURE_DEFINITIONS.filter(({ key }) => key !== 'Research');
const numberFormat = new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 3 });
const percentFormat = new Intl.NumberFormat('vi-VN', {
    style: 'percent',
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
});

function NumberField({ definition, value, error, onChange, inputRef }) {
    return (
        <label className={`field${error ? ' field--invalid' : ''}`}>
            <span className="field__topline">
                <span>{definition.label}</span>
                <span className="field__range">{definition.hint}</span>
            </span>
            <input
                ref={inputRef}
                aria-label={definition.label}
                aria-invalid={Boolean(error)}
                aria-describedby={error ? `${definition.key}-error` : undefined}
                autoComplete="off"
                inputMode={definition.integer ? 'numeric' : 'decimal'}
                max={definition.max}
                min={definition.min}
                name={definition.key}
                placeholder={definition.integer ? String(definition.min) : definition.min.toFixed(2)}
                required
                step={definition.step}
                type="number"
                value={value}
                onChange={(event) => onChange(definition.key, event.target.value)}
            />
            {error && <span className="field__error" id={`${definition.key}-error`}>{error}</span>}
        </label>
    );
}

function ResultPanel({ status, result, error, onReset }) {
    const chance = result?.chance_of_admit;
    const percentage = typeof chance === 'number' ? chance : null;
    const progress = percentage === null ? 0 : Math.max(0, Math.min(100, percentage * 100));

    return (
        <aside className={`result-panel${status === 'success' ? ' result-panel--ready' : ''}`} aria-live="polite">
            <div className="result-panel__top">
                <div className="result-panel__eyebrow"><Sparkles size={15} /> KẾT QUẢ ƯỚC TÍNH</div>
                <div className="result-panel__art" role="img" aria-label="Sinh viên trong khuôn viên đại học">
                    <img
                        alt="Sinh viên tốt nghiệp trong khuôn viên đại học"
                        loading="lazy"
                        src="https://images.unsplash.com/photo-1523050854058-8df90110c9f1?auto=format&fit=crop&w=1000&q=85"
                        onError={(event) => {
                            event.currentTarget.parentElement.classList.add('result-panel__art--fallback');
                            event.currentTarget.remove();
                        }}
                    />
                    <span className="result-panel__art-caption">Mở ra chặng đường học thuật mới</span>
                </div>
            </div>

            {status === 'success' ? (
                <div className="result-content result-content--success">
                    <div className="result-content__label"><CheckCircle2 size={17} /> DỰ ĐOÁN HOÀN TẤT</div>
                    <p className="result-content__title">Chance of Admit</p>
                    <p className="result-content__percent">{percentFormat.format(percentage)}</p>
                    <div className="chance-track" aria-label={`Chance of Admit ${percentFormat.format(percentage)}`}>
                        <span style={{ width: `${progress}%` }} />
                    </div>
                    <div className="result-content__facts">
                        <div>
                            <span>Prediction</span>
                            <strong>{numberFormat.format(percentage)}</strong>
                        </div>
                        <div>
                            <span>Model</span>
                            <strong>{result.model_name || 'Không xác định'}</strong>
                        </div>
                    </div>
                    {result.request_id && (
                        <p className="request-id"><span>Request ID</span><code>{result.request_id}</code></p>
                    )}
                    <button className="text-button" type="button" onClick={onReset}>
                        <RotateCcw size={15} /> Nhập hồ sơ khác
                    </button>
                </div>
            ) : status === 'loading' ? (
                <div className="result-content result-content--waiting">
                    <LoaderCircle className="loading-icon" size={27} />
                    <h2>Đang phân tích hồ sơ</h2>
                    <p>Đang gửi dữ liệu đến hệ thống dự đoán.</p>
                </div>
            ) : status === 'error' ? (
                <div className="result-content result-content--error" role="alert">
                    <AlertCircle size={23} />
                    <h2>Chưa thể dự đoán</h2>
                    <p>{error}</p>
                </div>
            ) : (
                <div className="result-content result-content--waiting">
                    <div className="result-content__placeholder"><GraduationCap size={27} /></div>
                    <h2>Kết quả sẽ hiển thị tại đây</h2>
                    <p>Điền thông tin học tập và nghiên cứu để xem ước tính.</p>
                </div>
            )}
            <div className="result-panel__foot"><span>REGRESSION ESTIMATE</span><span>01 / 01</span></div>
        </aside>
    );
}

export default function App() {
    const [features, setFeatures] = useState(emptyFeatures);
    const [errors, setErrors] = useState({});
    const [status, setStatus] = useState('idle');
    const [result, setResult] = useState(null);
    const [submitError, setSubmitError] = useState('');
    const firstInputRef = useRef(null);

    function updateFeature(key, value) {
        setFeatures((current) => ({ ...current, [key]: value }));
        setErrors((current) => ({ ...current, [key]: undefined }));
        if (status === 'error') setStatus('idle');
    }

    async function handleSubmit(event) {
        event.preventDefault();
        const validation = validateFeatures(features);
        setErrors(validation.errors);
        setSubmitError('');
        setResult(null);

        if (Object.keys(validation.errors).length) {
            setStatus('idle');
            firstInputRef.current?.focus();
            return;
        }

        setStatus('loading');
        try {
            const prediction = await requestPrediction(validation.values);
            setResult(prediction);
            setStatus('success');
        } catch (requestError) {
            setSubmitError(requestError.message || 'Đã xảy ra lỗi. Vui lòng thử lại.');
            setStatus('error');
        }
    }

    function resetForm() {
        setFeatures(emptyFeatures);
        setErrors({});
        setResult(null);
        setSubmitError('');
        setStatus('idle');
        firstInputRef.current?.focus();
    }

    return (
        <div className="app-shell">
            <header className="site-header">
                <a className="brand" href="#main" aria-label="Trang dự đoán tuyển sinh">
                    <span className="brand__mark"><GraduationCap size={22} strokeWidth={1.8} /></span>
                    <span className="brand__name">ADMIT<span>LAB</span></span>
                </a>
                <div className="header-status"><span className="header-status__dot" /> CÔNG CỤ DỰ ĐOÁN</div>
            </header>

            <main id="main" className="main-content">
                <section className="intro">
                    <p className="eyebrow">HỒ SƠ SAU ĐẠI HỌC <span>·</span> ƯỚC TÍNH CÁ NHÂN</p>
                    <h1>Dự đoán khả năng<br className="desktop-break" /> trúng tuyển sau đại học</h1>
                    <p className="intro__copy">Nhập điểm số và thông tin nghiên cứu để nhận kết quả ước tính từ mô hình học máy.</p>
                </section>

                <div className="workspace">
                    <section className="form-section" aria-labelledby="form-title">
                        <div className="form-section__heading">
                            <div>
                                <p className="section-kicker">THÔNG TIN ỨNG VIÊN</p>
                                <h2 id="form-title">Thông tin hồ sơ</h2>
                            </div>
                            <span className="required-note"><i /> Bắt buộc</span>
                        </div>

                        <form noValidate onSubmit={handleSubmit}>
                            <div className="fields-grid">
                                {numericFields.map((definition, index) => (
                                    <NumberField
                                        key={definition.key}
                                        definition={definition}
                                        value={features[definition.key]}
                                        error={errors[definition.key]}
                                        inputRef={index === 0 ? firstInputRef : undefined}
                                        onChange={updateFeature}
                                    />
                                ))}
                            </div>

                            <fieldset className={`research-field${errors.Research ? ' field--invalid' : ''}`}>
                                <legend>Research <span>Đã tham gia nghiên cứu?</span></legend>
                                <div className="segmented-control">
                                    <label className={features.Research === '0' ? 'is-selected' : ''}>
                                        <input
                                            type="radio"
                                            name="Research"
                                            value="0"
                                            checked={features.Research === '0'}
                                            onChange={(event) => updateFeature('Research', event.target.value)}
                                        />
                                        <span>Chưa</span>
                                    </label>
                                    <label className={features.Research === '1' ? 'is-selected' : ''}>
                                        <input
                                            type="radio"
                                            name="Research"
                                            value="1"
                                            checked={features.Research === '1'}
                                            onChange={(event) => updateFeature('Research', event.target.value)}
                                        />
                                        <span>Có</span>
                                    </label>
                                </div>
                                {errors.Research && <span className="field__error">{errors.Research}</span>}
                            </fieldset>

                            {submitError && <div className="form-error" role="alert"><AlertCircle size={17} />{submitError}</div>}
                            <div className="form-actions">
                                <button className="submit-button" type="submit" disabled={status === 'loading'}>
                                    {status === 'loading' ? <LoaderCircle className="loading-icon" size={18} /> : <span>Dự đoán khả năng</span>}
                                    {status !== 'loading' && <ArrowRight size={18} />}
                                </button>
                                <span className="privacy-note">Thông tin chỉ dùng cho lần dự đoán này.</span>
                            </div>
                        </form>
                    </section>

                    <ResultPanel status={status} result={result} error={submitError} onReset={resetForm} />
                </div>

                <footer className="page-footer">
                    <span>ADMITLAB <span className="footer-separator">/</span> HỌC MÁY ỨNG DỤNG</span>
                    <span>Ước tính không thay thế quyết định tuyển sinh chính thức.</span>
                </footer>
            </main>
        </div>
    );
}
