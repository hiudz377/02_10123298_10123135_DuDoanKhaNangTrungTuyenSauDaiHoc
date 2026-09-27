import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { requestPrediction } from './api.js';
import App from './App.jsx';

vi.mock('./api.js', () => ({
    requestPrediction: vi.fn(),
}));

const validFeatures = {
    'GRE Score': '337',
    'TOEFL Score': '118',
    'University Rating': '4',
    SOP: '4.5',
    LOR: '4.5',
    CGPA: '9.65',
};

describe('admission prediction form', () => {
    beforeEach(() => {
        requestPrediction.mockReset();
    });

    it('shows required-field errors and does not call the Backend for an empty form', () => {
        render(<App />);
        fireEvent.click(screen.getByRole('button', { name: /Dự đoán khả năng/ }));

        expect(screen.getByText('GRE Score là thông tin bắt buộc.')).toBeInTheDocument();
        expect(screen.getByText('Research là thông tin bắt buộc.')).toBeInTheDocument();
        expect(requestPrediction).not.toHaveBeenCalled();
    });

    it('submits all seven features and renders the prediction result', async () => {
        requestPrediction.mockResolvedValue({
            prediction: 0.87,
            chance_of_admit: 0.87,
            model_name: 'SVR',
            model_version: '1.0.0',
            request_id: 'test-request-42',
        });
        render(<App />);

        for (const [name, value] of Object.entries(validFeatures)) {
            fireEvent.change(screen.getByRole('spinbutton', { name }), { target: { value } });
        }
        fireEvent.click(screen.getByRole('radio', { name: 'Có' }));
        fireEvent.click(screen.getByRole('button', { name: /Dự đoán khả năng/ }));

        await waitFor(() => expect(requestPrediction).toHaveBeenCalledWith({
            ...validFeatures,
            'GRE Score': 337,
            'TOEFL Score': 118,
            'University Rating': 4,
            SOP: 4.5,
            LOR: 4.5,
            CGPA: 9.65,
            Research: 1,
        }));
        expect(await screen.findByText('SVR')).toBeInTheDocument();
        expect(screen.getByText('test-request-42')).toBeInTheDocument();
        expect(screen.getByText('Prediction')).toBeInTheDocument();
    });

    it('shows a readable error when the Backend request fails', async () => {
        requestPrediction.mockRejectedValue(new Error('Không kết nối được Backend.'));
        render(<App />);

        for (const [name, value] of Object.entries(validFeatures)) {
            fireEvent.change(screen.getByRole('spinbutton', { name }), { target: { value } });
        }
        fireEvent.click(screen.getByRole('radio', { name: 'Chưa' }));
        fireEvent.click(screen.getByRole('button', { name: /Dự đoán khả năng/ }));

        expect(await screen.findAllByText('Không kết nối được Backend.')).toHaveLength(2);
        expect(screen.getByText('Chưa thể dự đoán')).toBeInTheDocument();
    });
});
