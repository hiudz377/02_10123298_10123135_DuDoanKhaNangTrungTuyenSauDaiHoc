const configuredApiUrl = import.meta.env.VITE_API_URL?.trim();
const apiBaseUrl = configuredApiUrl || (import.meta.env.DEV ? 'http://localhost:8000' : '');

export async function requestPrediction(features) {
    if (!apiBaseUrl) {
        throw new Error('Chưa cấu hình Backend. Hãy đặt VITE_API_URL trước khi build ứng dụng.');
    }

    const requestId = globalThis.crypto?.randomUUID?.()
        ?? `web-${Date.now()}-${Math.random().toString(16).slice(2)}`;

    let response;
    try {
        response = await fetch(`${apiBaseUrl.replace(/\/+$/, '')}/api/predict`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Request-ID': requestId,
            },
            body: JSON.stringify({ features, request_id: requestId }),
            signal: AbortSignal.timeout(15000),
        });
    } catch (error) {
        if (error.name === 'TimeoutError' || error.name === 'AbortError') {
            throw new Error('Backend phản hồi quá thời gian. Vui lòng thử lại.');
        }
        throw new Error('Không kết nối được Backend. Hãy kiểm tra dịch vụ và thử lại.');
    }

    let result;
    try {
        result = await response.json();
    } catch {
        throw new Error('Backend trả về phản hồi không hợp lệ.');
    }

    if (!response.ok) {
        throw new Error(result.detail || result.error || `Yêu cầu thất bại (${response.status}).`);
    }
    if (!Number.isFinite(Number(result.chance_of_admit ?? result.prediction))) {
        throw new Error('Backend không trả về giá trị dự đoán hợp lệ.');
    }

    return {
        ...result,
        chance_of_admit: Number(result.chance_of_admit ?? result.prediction),
        request_id: result.request_id || requestId,
    };
}
