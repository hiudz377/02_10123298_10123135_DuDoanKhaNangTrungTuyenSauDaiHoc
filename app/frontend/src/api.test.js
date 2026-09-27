import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.stubEnv('VITE_API_URL', 'http://localhost:8000');

const { requestPrediction } = await import('./api.js');

const features = {
    'GRE Score': 337,
    'TOEFL Score': 118,
    'University Rating': 4,
    SOP: 4.5,
    LOR: 4.5,
    CGPA: 9.65,
    Research: 1,
};

describe('requestPrediction', () => {
    beforeEach(() => {
        vi.stubGlobal('fetch', vi.fn());
    });

    it('calls the Backend prediction route using the expected request shape', async () => {
        fetch.mockResolvedValue({
            ok: true,
            json: async () => ({
                prediction: 0.87,
                chance_of_admit: 0.87,
                model_name: 'Linear Regression',
                model_version: '1.0.0',
                request_id: 'req-123',
            }),
        });

        const result = await requestPrediction(features);
        const [url, options] = fetch.mock.calls[0];

        expect(url).toBe('http://localhost:8000/api/predict');
        expect(options.method).toBe('POST');
        expect(options.headers['X-Request-ID']).toBeTruthy();
        expect(JSON.parse(options.body)).toEqual({
            features,
            request_id: options.headers['X-Request-ID'],
        });
        expect(result.chance_of_admit).toBe(0.87);
        expect(result.model_name).toBe('Linear Regression');
    });

    it('shows a useful Backend validation error', async () => {
        fetch.mockResolvedValue({
            ok: false,
            status: 400,
            json: async () => ({ error: 'invalid_input', detail: 'GRE Score is invalid.' }),
        });

        await expect(requestPrediction(features)).rejects.toThrow('GRE Score is invalid.');
    });

    it('handles an unavailable Backend', async () => {
        fetch.mockRejectedValue(new TypeError('Failed to fetch'));

        await expect(requestPrediction(features)).rejects.toThrow(/Không kết nối được Backend/);
    });
});
