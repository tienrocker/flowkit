/**
 * Google Flow Agent — Chrome Extension Background Service Worker
 * 
 * Responsibilities:
 * 1. Capture Google Flow bearer token (ya29.*) from aisandbox-pa.googleapis.com
 * 2. Solve reCAPTCHA v2 when required
 * 3. Provide WebSocket server for local agent to call Google Flow APIs
 * 4. Wrap all Google Flow API endpoints
 */

const FLOW_API = 'https://aisandbox-pa.googleapis.com';
const API_KEY = 'AIzaSyBtrm0o5ab1c-Ec8ZuLcGt3oJAA5VWt3pY';
const RECAPTCHA_SITE_KEY = '6LdsFiUsAAAAAIjVDZcuLhaHiDn5nnHVXVRQGeMV';

let flowKey = null; // Bearer token ya29.*
let wsPort = 9222;
let metrics = { tokenCapturedAt: null, requestCount: 0, lastError: null };

// ─── Token Capture ──────────────────────────────────────────

chrome.webRequest.onBeforeSendHeaders.addListener(
  (details) => {
    if (!details?.requestHeaders?.length) return;
    const authHeader = details.requestHeaders.find(h => h.name?.toLowerCase() === 'authorization');
    const value = authHeader?.value || '';
    if (!value.startsWith('Bearer ya29.')) return;
    
    const token = value.replace(/^Bearer\s+/i, '').trim();
    if (token === flowKey) return;
    
    flowKey = token;
    metrics.tokenCapturedAt = Date.now();
    chrome.storage.local.set({ flowKey, metrics });
    console.log('[FlowAgent] Bearer token captured');
  },
  { urls: ['https://aisandbox-pa.googleapis.com/*'] },
  ['requestHeaders']
);

// ─── Google Flow API Wrapper ────────────────────────────────

async function callFlowAPI(path, body, method = 'POST') {
  if (!flowKey) throw new Error('No bearer token — open Google Labs first');
  
  const url = `${FLOW_API}${path}${path.includes('?') ? '&' : '?'}key=${API_KEY}`;
  const resp = await fetch(url, {
    method,
    headers: {
      'Authorization': `Bearer ${flowKey}`,
      'Content-Type': 'application/json',
    },
    body: method !== 'GET' ? JSON.stringify(body) : undefined,
  });
  
  if (!resp.ok) {
    const err = await resp.text();
    throw new Error(`Flow API ${resp.status}: ${err.slice(0, 200)}`);
  }
  return resp.json();
}

async function generateImage(params) {
  const { prompt, characters, orientation } = params;
  const aspectRatio = orientation === 'HORIZONTAL' ? '16:9' : '9:16';
  
  // Build character references
  const charRefs = (characters || [])
    .filter(c => c.media_gen_id)
    .map(c => ({ mediaGenerationId: c.media_gen_id }));
  
  const body = {
    generationRequest: {
      prompt: prompt,
      aspectRatio: aspectRatio,
      numOutputs: 1,
      ...(charRefs.length > 0 && { characterReferences: charRefs }),
    },
  };
  
  const result = await callFlowAPI('/v1/images:generate', body);
  const generated = result?.generatedImages?.[0] || {};
  
  return {
    mediaGenerationId: generated.mediaGenerationId || '',
    imageUrl: generated.imageUri || '',
  };
}

async function generateVideo(params) {
  const { mediaGenerationId, prompt, orientation, endSceneMediaGenerationId, model } = params;
  const aspectRatio = orientation === 'HORIZONTAL' ? '16:9' : '9:16';
  
  const body = {
    generationRequest: {
      imageMediaGenerationId: mediaGenerationId,
      prompt: prompt,
      aspectRatio: aspectRatio,
      model: model || 'veo_3_1_fast',
      ...(endSceneMediaGenerationId && { endSceneMediaGenerationId }),
    },
  };
  
  // Submit generation
  const submit = await callFlowAPI('/v1/videos:generate', body);
  const operationId = submit?.operationId || submit?.name;
  
  if (!operationId) {
    return { mediaGenerationId: submit?.mediaGenerationId || '', videoUrl: '' };
  }
  
  // Poll for completion
  for (let i = 0; i < 60; i++) {
    await new Promise(r => setTimeout(r, 5000));
    try {
      const status = await callFlowAPI(`/v1/operations/${operationId}`, null, 'GET');
      if (status?.done) {
        const video = status?.response?.generatedVideos?.[0] || {};
        return {
          mediaGenerationId: video.mediaGenerationId || '',
          videoUrl: video.videoUri || '',
        };
      }
    } catch (e) {
      console.warn('[FlowAgent] Poll error:', e.message);
    }
  }
  return { error: 'Video generation timeout' };
}

async function upscaleVideo(params) {
  const { mediaGenerationId, orientation, resolution } = params;
  
  const body = {
    mediaGenerationId: mediaGenerationId,
    resolution: resolution || 'VIDEO_RESOLUTION_4K',
  };
  
  const submit = await callFlowAPI('/v1/videos:upscale', body);
  const operationId = submit?.operationId || submit?.name;
  
  if (!operationId) {
    return { mediaGenerationId: submit?.mediaGenerationId || '', videoUrl: '' };
  }
  
  // Poll
  for (let i = 0; i < 40; i++) {
    await new Promise(r => setTimeout(r, 5000));
    try {
      const status = await callFlowAPI(`/v1/operations/${operationId}`, null, 'GET');
      if (status?.done) {
        const video = status?.response || {};
        return {
          mediaGenerationId: video.mediaGenerationId || '',
          videoUrl: video.videoUri || '',
        };
      }
    } catch (e) {
      console.warn('[FlowAgent] Upscale poll error:', e.message);
    }
  }
  return { error: 'Upscale timeout' };
}

async function generateCharacterImage(params) {
  const { name, description } = params;
  const body = {
    generationRequest: {
      prompt: `Character reference: ${name}. ${description}`,
      aspectRatio: '1:1',
      numOutputs: 1,
    },
  };
  
  const result = await callFlowAPI('/v1/images:generate', body);
  const generated = result?.generatedImages?.[0] || {};
  
  return {
    mediaGenerationId: generated.mediaGenerationId || '',
    imageUrl: generated.imageUri || '',
  };
}

async function getCredits() {
  const result = await callFlowAPI('/v1/credits', null, 'GET');
  return result;
}

// ─── Method Router ──────────────────────────────────────────

const METHODS = {
  generate_image: generateImage,
  generate_video: generateVideo,
  upscale_video: upscaleVideo,
  generate_character_image: generateCharacterImage,
  get_credits: getCredits,
};

// ─── WebSocket Bridge (via content script relay) ────────────
// Since service workers can't run a WS server, we use chrome.runtime messaging
// The local agent connects via a native messaging host or HTTP polling

chrome.runtime.onMessageExternal.addListener(async (msg, sender, sendResponse) => {
  const { requestId, method, params } = msg;
  const handler = METHODS[method];
  
  if (!handler) {
    sendResponse({ requestId, error: `Unknown method: ${method}` });
    return true;
  }
  
  try {
    metrics.requestCount++;
    const result = await handler(params || {});
    sendResponse({ requestId, ...result });
  } catch (e) {
    metrics.lastError = e.message;
    sendResponse({ requestId, error: e.message });
  }
  return true;
});

// Also handle internal messages from popup
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === 'getStatus') {
    sendResponse({
      connected: !!flowKey,
      tokenAge: flowKey && metrics.tokenCapturedAt ? Date.now() - metrics.tokenCapturedAt : null,
      requestCount: metrics.requestCount,
      lastError: metrics.lastError,
    });
    return true;
  }
  
  if (msg.type === 'apiCall') {
    const handler = METHODS[msg.method];
    if (!handler) {
      sendResponse({ error: `Unknown method: ${msg.method}` });
      return true;
    }
    handler(msg.params || {}).then(r => sendResponse(r)).catch(e => sendResponse({ error: e.message }));
    return true;
  }
});

// Restore token on startup
chrome.storage.local.get(['flowKey', 'metrics'], (data) => {
  if (data.flowKey) flowKey = data.flowKey;
  if (data.metrics) Object.assign(metrics, data.metrics);
});

console.log('[FlowAgent] Extension loaded');
