export const FEATURE_DEFINITIONS = [
    { key: 'GRE Score', label: 'GRE Score', min: 290, max: 340, step: 1, integer: true, hint: '290-340' },
    { key: 'TOEFL Score', label: 'TOEFL Score', min: 92, max: 120, step: 1, integer: true, hint: '92-120' },
    { key: 'University Rating', label: 'University Rating', min: 1, max: 5, step: 1, integer: true, hint: '1-5' },
    { key: 'SOP', label: 'SOP', min: 1, max: 5, step: 0.5, integer: false, hint: '1-5, bước 0.5' },
    { key: 'LOR', label: 'LOR', min: 1, max: 5, step: 0.5, integer: false, hint: '1-5, bước 0.5' },
    { key: 'CGPA', label: 'CGPA', min: 6.8, max: 9.92, step: 0.01, integer: false, hint: '6.80-9.92' },
    { key: 'Research', label: 'Research', min: 0, max: 1, step: 1, integer: true, hint: 'Không / Có' },
];

export function validateFeatures(rawFeatures) {
    const values = {};
    const errors = {};

    for (const definition of FEATURE_DEFINITIONS) {
        const rawValue = rawFeatures[definition.key];
        if (rawValue === '' || rawValue === null || rawValue === undefined) {
            errors[definition.key] = `${definition.label} là thông tin bắt buộc.`;
            continue;
        }

        const value = Number(rawValue);
        if (!Number.isFinite(value)) {
            errors[definition.key] = `${definition.label} phải là một số hợp lệ.`;
            continue;
        }
        if (value < definition.min || value > definition.max) {
            errors[definition.key] = `${definition.label} phải trong khoảng ${definition.min} đến ${definition.max}.`;
            continue;
        }
        if (definition.integer && !Number.isInteger(value)) {
            errors[definition.key] = `${definition.label} phải là số nguyên.`;
            continue;
        }
        if (!definition.integer && Math.abs(value / definition.step - Math.round(value / definition.step)) > 1e-8) {
            errors[definition.key] = `${definition.label} không đúng bước nhập ${definition.step}.`;
            continue;
        }
        values[definition.key] = value;
    }

    return { values, errors };
}
