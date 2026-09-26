import { describe, expect, it } from 'vitest';
import { validateFeatures } from './validation.js';

const validFeatures = {
    'GRE Score': '337',
    'TOEFL Score': '118',
    'University Rating': '4',
    SOP: '4.5',
    LOR: '3.5',
    CGPA: '9.65',
    Research: '1',
};

describe('validateFeatures', () => {
    it('converts a complete valid form to the Backend feature schema', () => {
        const result = validateFeatures(validFeatures);

        expect(result.errors).toEqual({});
        expect(result.values).toEqual({
            'GRE Score': 337,
            'TOEFL Score': 118,
            'University Rating': 4,
            SOP: 4.5,
            LOR: 3.5,
            CGPA: 9.65,
            Research: 1,
        });
    });

    it('requires all seven values', () => {
        const result = validateFeatures({ ...validFeatures, 'CGPA': '' });
        expect(result.errors.CGPA).toMatch(/bắt buộc/);
    });

    it('rejects values outside the model input range', () => {
        const result = validateFeatures({ ...validFeatures, 'GRE Score': '341' });
        expect(result.errors['GRE Score']).toMatch(/290 đến 340/);
    });

    it('rejects unsupported SOP increments', () => {
        const result = validateFeatures({ ...validFeatures, SOP: '4.2' });
        expect(result.errors.SOP).toMatch(/bước nhập 0.5/);
    });
});
